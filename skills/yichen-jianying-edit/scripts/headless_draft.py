#!/usr/bin/env python3
"""Pinned Skill entrypoint for a separately checked-out Jianying Headless project."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

def project_root():
    configured = os.environ.get('JIANYING_HEADLESS_ROOT')
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            raise SystemExit('JIANYING_HEADLESS_ROOT must be an absolute checkout path')
        candidates = [path.resolve()]
    else:
        candidates = list(Path(__file__).resolve().parents)
    for path in candidates:
        marker = path / 'project.json'
        if marker.is_file() and not marker.is_symlink():
            try:
                identity = json.loads(marker.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if identity.get('id') == 'jianying-headless' and identity.get('schema') == 'jianying-headless-project/v1':
                return path
    raise SystemExit('Jianying Headless checkout unavailable. Clone the project with authorized GitHub access, '
                     'then set JIANYING_HEADLESS_ROOT to its absolute path. The Skill alone does not include the engine.')


PROJECT_ROOT = project_root()
BACKEND = PROJECT_ROOT / 'engine'
PINS = {
    'native_fonts.py': '20f6186cfa8e20cfbb3160e4c62216d1ad22a16feb8e241add40569668aef96d',
    'runtime_profiles.py': '227dac21aad9a28f50164f20ba6aed10cf9eaab5b2f56a12dc66a13bd92ecae3',
    'jy14_headless.py': '24c47219b5b9a197b72ec7c567a5b6da9e5d6bc17f6ed37941b568db4cf193bd',
    'native_motion.py': '5d743caaa38c921779166e5663d36f72a0c3fdb130a690ac3942a7adcf62d6c2',
    'native_effects.py': 'c46b2fc9221dd613f220564b752e532f8f3753dd5595aaffc24f41d5236e4e97',
    'native_resources.py': 'cbaf631460ac436826efdc5b313b34f5c6614e1775530c44f625fc559195a6d9',
    'native_visual_effects.py': '15df7e56cc7d575a552c180e72ec712f136c618d271b2f3ad2d32dd5929e844c',
    'native-resource-catalog.json': '97af2df27463a9183fb1aa8f2ef534b37a644cb196f340fe88fdc50b456abde9',
    'native_compound.py': 'aef25fece82c05cc934d441dcb3ae2b6afd8351252215bee7db205da97719d28',
    'compound-blueprint.json': '9cba9435053280abf9072d5eaccb8586c841b11dac6854b32daf9cbdba76af8e',
    'native_edit.py': 'ddfe6c762198f35d210a7c7527bef64436c24e77d4810f73f30c40fca9b23d6a',
    'native_export.py': '10191828c86c12396c77be5ac7a39ee712c4b5f1ac341a09f73418eac5d7202d',
    'ui_export.py': 'e839b15ff39c61ff103e16af40c677a26849980500524ff8a24b108e1015e87c',
    'native_export.cpp': 'c60da6c65f5bb7ac733b8f5b619401be3921f9254b953a55903d4e7566156379',
    'headless_runtime.py': 'f25b83bf55e12d20c4dbd73576256156f00f1f387b14d6abe68491369fd1ea95',
    'blueprint.json': '91f7eddad5bff9af23eb88b53713c180e3e3d4054edd469140cfa9aa56bc1dc9',
    'windows_portable.py': '707e5f1040ad59384f864e5e2ad41ff2c93853be8c7bd562d44f6fb632d244ca',
    'windows_export.py': 'b4f20ce94b6ca0a72d5c542bc56ce9fd23a13a09826ba71a34beb99e23474fc8',
    'ffmpeg_graph.py': 'bc0d897993f9e7c2c5f6c0233a3002c07e235323da20fe0eca2755f1410aa594',
    'ffmpeg_tools.py': 'c8d0817c57573e0e755f3277466fa13e08bdc588d90471344faaf30438e9992f',
}

for name, expected in PINS.items():
    path = BACKEND / name
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Headless component changed or unavailable; reverify before updating the pin: ' + name)

sys.path.insert(0, str(BACKEND))
entrypoint = 'jy14_headless.py'
command = sys.argv[1] if len(sys.argv) > 1 else None
if command == 'edit':
    entrypoint = 'native_edit.py'
    del sys.argv[1]
elif command == 'export':
    requested = None
    if '--backend' in sys.argv:
        index = sys.argv.index('--backend')
        if index + 1 >= len(sys.argv):
            raise SystemExit('--backend needs a value')
        requested = sys.argv[index + 1]
        del sys.argv[index:index + 2]
    if requested not in {None, 'native', 'windows-ffmpeg'}:
        raise SystemExit('Unsupported export backend: ' + requested)
    entrypoint = ('windows_export.py'
                  if requested == 'windows-ffmpeg' or (requested is None and os.name == 'nt')
                  else 'native_export.py')
    del sys.argv[1]
elif command == 'ui-export':
    entrypoint = 'ui_export.py'
    del sys.argv[1]
elif os.name == 'nt':
    # Native Jianying drafts on Windows: publish/verify/create always, and
    # doctor/build/verify-build when asked with --backend native.
    native = command in {'publish', 'resume-publish', 'create', 'verify'}
    if '--backend' in sys.argv:
        index = sys.argv.index('--backend')
        if index + 1 >= len(sys.argv) or sys.argv[index + 1] not in {'native', 'windows-ffmpeg'}:
            raise SystemExit('--backend must be native or windows-ffmpeg')
        native = native or sys.argv[index + 1] == 'native'
        del sys.argv[index:index + 2]
    if not native:
        if command not in {None, '--help', '-h', 'doctor', 'build', 'verify-build'}:
            raise SystemExit('Unsupported Windows command: ' + str(command))
        entrypoint = 'windows_portable.py'
runpy.run_path(str(BACKEND / entrypoint), run_name='__main__')
