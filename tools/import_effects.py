#!/usr/bin/env python3
"""Import Jianying transitions and video effects from a dedicated draft into the local effect library.

Workflow: drag the effects you want into the draft (default "效果导入") so Jianying downloads
them, quit Jianying, then run this tool. Each new effect's package is copied from Jianying's
cache into the local library (never into this repository), its material template is recorded,
and a test draft using every newly imported effect is built and published for UI review.
New names are appended to the 待确认 line of HANDOFF.md; whether an effect is free is decided
by the user in Jianying, never by this tool.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'engine'))

import headless_runtime as nd  # noqa: E402
import jy14_headless as j  # noqa: E402
import native_resources as resources  # noqa: E402

DEFAULT_DRAFT = '效果导入'
BUCKETS = {'transitions': 'transition', 'video_effects': 'effect'}
FIELDS = {
    'transition': ('type', 'name', 'effect_id', 'resource_id', 'third_resource_id', 'source_platform',
                   'is_overlap', 'category_id', 'category_name'),
    'effect': ('type', 'name', 'effect_id', 'resource_id', 'third_resource_id', 'sub_type', 'value',
               'category_id', 'category_name', 'source_platform', 'apply_target_type', 'adjust_params'),
}
SEGMENT_US = 2_000_000
TRANSITION_US = 600_000  # 18 frames at 30 fps: even, as centered transitions require


def require(value, message):
    if not value:
        raise SystemExit('导入失败：' + message)


def cache_root():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'JianyingPro/User Data/Cache/effect'


def set_library(path):
    resources.CONFIG.parent.mkdir(parents=True, exist_ok=True)
    config = json.loads(resources.CONFIG.read_text(encoding='utf-8')) if resources.CONFIG.is_file() else {}
    config['effects_home'] = str(Path(path).resolve())
    resources.CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding='utf-8')


def load_library(home):
    path = home / 'catalog.json'
    if path.is_file():
        value = json.loads(path.read_text(encoding='utf-8'))
        require(value.get('schema') == resources.LIBRARY_SCHEMA, '效果库格式不对：' + str(path))
        return value
    return {'schema': resources.LIBRARY_SCHEMA, 'resources': {}}


def save_library(home, library):
    home.mkdir(parents=True, exist_ok=True)
    temporary = home / 'catalog.json.tmp'
    temporary.write_text(json.dumps(library, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')
    os.replace(temporary, home / 'catalog.json')


def copy_package(cache, files, destination):
    if not destination.exists():
        staging = destination.with_name(destination.name + '.tmp')
        if staging.exists():
            shutil.rmtree(staging)
        for name in files:
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cache / name, target, follow_symlinks=False)
        os.replace(staging, destination)
    require(resources.tree_manifest(destination) == files, '复制后的效果包和剪映缓存不一致：' + str(destination))


def material_template(kind, node):
    template = {key: deepcopy(node[key]) for key in FIELDS[kind] if key in node}
    for param in template.get('adjust_params', []):
        param['value'] = param.get('default_value', param.get('value'))
    if 'value' in template:
        template['value'] = 1.0
    return template


def collect(timeline, catalog, library):
    """New (key, entry) pairs, already-known names, and unsupported materials."""
    known_ids = {}
    for key, entry in catalog['resources'].items():
        material = entry.get('material', {})
        if isinstance(material, dict) and material.get('effect_id'):
            known_ids[(key.split('/', 1)[0], material['effect_id'])] = key
    root = cache_root().resolve()
    new, existing, seen = [], [], set()
    for bucket, kind in BUCKETS.items():
        for node in timeline.get('materials', {}).get(bucket, []):
            effect_id = str(node.get('effect_id') or node.get('resource_id') or '')
            if not effect_id or (kind, effect_id) in seen:
                continue
            seen.add((kind, effect_id))
            if (kind, effect_id) in known_ids:
                existing.append(known_ids[(kind, effect_id)])
                continue
            cache = Path(node.get('path', '')).resolve()
            require(cache.is_dir() and root in cache.parents,
                    '「%s」的资源不在剪映缓存里，请先在剪映里预览一次再导入' % node.get('name'))
            files = resources.tree_manifest(cache)
            tree = resources.manifest_hash(files)
            name = node.get('name') or effect_id
            key = kind + '/' + name
            if key in catalog['resources'] or key in library['resources'] or key in dict(new):
                key = kind + '/' + name + '#' + effect_id[-4:]
            entry = {'source': str(resources.library_home() / 'packages' / tree[:16]), 'native_cache': str(cache),
                     'tree_sha256': tree, 'files': files, 'material': material_template(kind, node),
                     'usage': {'ui_label_observed': name, 'paid_badge_observed': None, 'entitlement_verified': False,
                               'redistribution_authorized': False,
                               'scope': 'local editable preview; the user decides free/paid in Jianying'},
                     'imported_at': time.strftime('%Y-%m-%d %H:%M:%S')}
            if kind == 'effect':
                base = resources.definition('effect/light-shake')
                entry['track_template'] = deepcopy(base['track_template'])
                entry['segment_template'] = deepcopy(base['segment_template'])
            new.append((key, entry))
    unsupported = sorted({'%s（%s）' % (node.get('name', '?'), node.get('type', bucket))
                          for bucket, nodes in timeline.get('materials', {}).items()
                          if bucket in ('effects', 'stickers', 'filters') for node in nodes
                          if node.get('effect_id') or node.get('resource_id')})
    return new, existing, unsupported


def mark_pending(names):
    """Append names to the 待确认 line of HANDOFF.md unless already listed anywhere."""
    handoff = ROOT / 'HANDOFF.md'
    if not handoff.is_file() or not names:
        return []
    text = handoff.read_text(encoding='utf-8')
    lines = text.split('\n')
    listed = set()
    for line in lines:
        if line.startswith(('白名单：', '要会员：', '待确认：')):
            listed.update(re.split(r'\s{2,}', line.split('：', 1)[1].strip()))
    added = [n for n in names if n not in listed]
    if not added:
        return []
    index = max((i for i, line in enumerate(lines) if line.startswith('待确认：')), default=None)
    if index is None:
        index = max(i for i, line in enumerate(lines) if line.startswith('要会员：'))
        lines.insert(index + 1, '')
        lines.insert(index + 2, '待确认：')
        index += 2
    current = lines[index].rstrip()
    lines[index] = current + ('' if current.endswith('：') else '  ') + '  '.join(added)
    handoff.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    return added


def test_media(home):
    clip = home / 'test-media' / 'bars.mp4'
    if not clip.is_file():
        clip.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1920x1080:rate=30',
                        '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', '60', '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(clip)], check=True)
    return clip


def test_plan(keys, home, name):
    transitions = [k.split('/', 1)[1] for k in keys if k.startswith('transition/')]
    effects = [k.split('/', 1)[1] for k in keys if k.startswith('effect/')]
    count = max(len(transitions) + 1, len(effects), 1)
    require(count * 3 <= 56, '一次导入的效果太多（最多 18 个），请分批导入')
    clip = test_media(home).as_posix()
    video, labels = [], []
    for i in range(count):
        segment = {'source': clip, 'start_us': i * SEGMENT_US, 'duration_us': SEGMENT_US,
                   'source_start_us': 1_000_000 + i * 3_000_000, 'source_duration_us': SEGMENT_US, 'volume': 0}
        parts = []
        if i < len(transitions):
            segment['transition_out'] = {'name': transitions[i], 'duration_us': TRANSITION_US,
                                         'edge_policy': 'require-handles'}
            parts.append('转场→' + transitions[i])
        if i < len(effects):
            parts.append('特效：' + effects[i])
        video.append(segment)
        labels.append({'text': '  '.join(parts) or '—', 'start_us': i * SEGMENT_US, 'duration_us': SEGMENT_US,
                       'size': 6, 'y': -0.8})
    tracks = [{'type': 'video', 'name': '测试素材', 'segments': video}]
    if effects:
        tracks.append({'type': 'effect', 'name': '导入的特效', 'segments': [
            {'name': e, 'start_us': i * SEGMENT_US, 'duration_us': SEGMENT_US} for i, e in enumerate(effects)]})
    tracks.append({'type': 'text', 'name': '说明', 'segments': labels})
    return {'schema': j.SCHEMA, 'name': name, 'canvas': {'width': 1920, 'height': 1080, 'fps': 30}, 'tracks': tracks}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--draft', default=DEFAULT_DRAFT, help='导入用的草稿名（默认：效果导入）')
    parser.add_argument('--library', help='效果库目录；指定一次后会被记住')
    parser.add_argument('--no-test', action='store_true', help='只导入，不生成测试草稿')
    args = parser.parse_args()
    if args.library:
        set_library(args.library)
    home = resources.library_home()
    nd.doctor()
    helper = nd.helper()
    helper._ensure_editor_closed(True)
    draft = nd.DRAFT_ROOT / args.draft
    require(draft.is_dir(), '找不到草稿「%s」（%s）' % (args.draft, draft))
    timeline = helper._decrypt_metadata_in_memory(draft / nd.TIMELINE_FILE)
    library = load_library(home)
    new, existing, unsupported = collect(timeline, resources.catalog(), library)
    for key, entry in new:
        copy_package(Path(entry['native_cache']), entry['files'], Path(entry['source']))
        library['resources'][key] = entry
    if new:
        save_library(home, library)
    names = [key.split('/', 1)[1] for key, _ in new]
    pending = mark_pending(names)
    result = {'效果库': str(home), '新导入': names, '已登记过': sorted(set(existing)),
              '暂不支持（滤镜/贴纸/花字等）': unsupported, '已写进交接文档待确认': pending}
    if new and not args.no_test:
        name = '导入测试-' + time.strftime('%m%d%H%M')
        work = home / 'work' / time.strftime('%m%d%H%M%S')
        work.mkdir(parents=True)
        plan = work / 'plan.json'
        plan.write_text(json.dumps(test_plan([k for k, _ in new], home, name), ensure_ascii=False, indent=1),
                        encoding='utf-8')
        j.build(plan, work / 'build')
        j.publish(work / 'build', work / 'audit')
        result.update({'测试草稿': name, '测试构建': str(work / 'build'),
                       '下一步': '在剪映里打开「%s」看效果；确认后把效果名从「待确认」挪到「白名单」或「要会员」，'
                                 '再回到「%s」草稿里删掉这些效果' % (name, args.draft)})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
