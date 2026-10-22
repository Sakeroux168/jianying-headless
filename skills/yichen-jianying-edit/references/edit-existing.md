# 修改已有草稿的独立副本（Windows）

入口是 `scripts\headless_draft.py edit`，走 `engine\native_edit.py`；Windows 上不需要
`--backend`。适用于剪映 11.6.0.14552 能打开的本地单时间线多轨草稿，交付的是独立副本，
原草稿一个字节都不动。

## 边界

- **必须先完全退出剪映（主程序和托盘都退出）**，再执行 inspect / build / publish。
- 只接受当前草稿根的直接子目录；不解析符号链接，不复制云端身份，不处理多时间线草稿。
- 用草稿 ID 与时间线 SHA-256 固定来源；原草稿的完整文件清单在构建、登记、回读时再校验。
  用户或剪映改动过来源就停下，不用旧计划覆盖。
- 时间线文件是 `draft_content.json`；Windows 草稿没有 `key_value.json`，代码只在文件
  存在时维护它。
- 源目录与已有本地素材不写入；替换素材复制到副本 `Resources\headless-edited-media\`，
  草稿内路径重定向到副本，外部依赖保留原路径并校验字节。所以这是本机私有副本，
  不是可分发项目包。
- 复合片段在 Windows 上没有配置，`edit publish` 遇到含复合片段的构建会直接拒绝；
  不要尝试绕过。
- 本机验收：11.6.0.14552 上打开 11.5.3 保存的草稿做副本编辑（缩放、位移、音量），
  显示正确，保存后完整回读通过，原草稿不变。

## 工作流

```bat
python SKILL\scripts\headless_draft.py edit inspect --draft "E:\全局软件\JianyingPro Drafts\某草稿" --out WORK\source-inspection.json
python SKILL\scripts\headless_draft.py edit build --plan WORK\edit-plan.json --out WORK\edited-build
python SKILL\scripts\headless_draft.py edit verify-build --build WORK\edited-build
python SKILL\scripts\headless_draft.py edit publish --build WORK\edited-build --audit WORK\edited-publish
python SKILL\scripts\headless_draft.py edit verify --build WORK\edited-build --report WORK\after-save.json
```

`inspect` 输出草稿身份、轨道/片段/文字素材 ID 与当前时间范围；按结果准备计划，不按文件名
猜素材身份。

```json
{
  "schema": "jy14-edit-plan/v1",
  "name": "本次修改副本",
  "source": {
    "draft_path": "E:/全局软件/JianyingPro Drafts/某草稿",
    "draft_id": "FROM_INSPECTION",
    "timeline_sha256": "FROM_INSPECTION"
  },
  "operations": [
    {"op": "replace_text", "id": "TEXT_MATERIAL_ID", "text": "新的字幕内容"},
    {"op": "set_segment", "id": "VIDEO_SEGMENT_ID", "set": {"x": -0.3, "scale": 0.5}},
    {"op": "set_segment", "id": "AUDIO_SEGMENT_ID", "set": {"volume": 0.15}}
  ]
}
```

## 可用操作

- `set_segment`：片段 ID；`set` 支持 `start_us`、`duration_us`、`source_start_us`、
  `source_duration_us`、`speed`、`volume`、`visible`。视频/文字还支持
  `x`/`y`/`scale`/`rotation`/`opacity`；文字不接受源时间、速度、音量。改速度要同时给出
  相符的源/目标时长。动画属性不能只改静态基值；已带关键帧片段的源时间变更暂不支持重映射。
- `replace_text`：文字素材 ID；保留全文一致样式，按 UTF-16 更新长度。局部多样式文字拒绝
  自动改范围。
- `set_text_font`：`{"op":"set_text_font","id":"TEXT_MATERIAL_ID","source":"E:/fonts/font.otf"}`。
  只处理外层与各样式字体路径一致、无在线字体身份的普通文字；静态 OTF/TTF 复制到
  副本 `Resources\headless-fonts\`，保留文字、样式和时间。
- `replace_media`：视频/图片/GIF/本地音频素材 ID 和绝对 `source`。媒体类别须与原素材一致，
  引用范围都要落在新素材实际时长内。
- `rename_track`：轨道 ID 和 `name`。
- `duplicate_segment`：片段 ID、`start_us`，可指定同类 `track_id`。复制配套素材节点与
  关键帧 ID，复用媒体库文件，不共享可变片段节点。
- `remove_segment`：只从副本时间线移除，不删源文件。涉及已绑定转场或复合片段的复制/移除
  拒绝执行。
- `set_filter_intensity`：已登记 `filter` 素材 ID，`set` 为 `{"value": 0.5}`，范围 0–1。
  只改强度，不能造出未登记或未授权的在线滤镜。

所有时间是整数微秒。同轨新增重叠会拒绝，已有重叠保留。原生保存会把时间吸附到帧网格，
回读最多放一帧并列出差异。

## 回读与中断

`verify` 比较完整已知结构与非空字段、轨道/片段顺序、活动镜像、媒体字节、首页身份和原草稿
不变性，不替代画面/声音验收。登记中断用
`edit resume-publish --build WORK\edited-build --audit WORK\resume`：只有目标目录与构建清单
逐字节一致、剪映已关闭时才会继续，已成功登记时返回只读幂等结果。
