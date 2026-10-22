# Windows 原生剪映草稿

在 Windows 上生成可在剪映专业版中继续编辑的草稿。加解密由本机已安装的
`videoeditor.dll` 提供（`lvve::EncryptUtils`，与 macOS 桥接同一个类），
不复制、不分发任何官方文件。

## 前提

- 剪映专业版 Windows **11.6.0.14552**（其他版本会被拒绝，需要先登记哈希）。
- Python 3.9+、FFmpeg / ffprobe（在 PATH 中）。
- Visual Studio Build Tools（C++ 工作负载），用于编译桥接。

## 准备

~~~bat
bridge\windows\build.bat
python skills\yichen-jianying-edit\scripts\headless_draft.py doctor --backend native
~~~

`doctor` 从注册表读取安装位置，从 `globalSetting` 读取自定义草稿目录，
首页索引固定在 `%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft`。
安装位置识别不到时设置 `JIANYING_INSTALL`（含 `uninst.exe` 的目录）。

## 构建与发布

~~~bat
python skills\yichen-jianying-edit\scripts\headless_draft.py build --backend native --plan D:\plan.json --out D:\work\build1
python skills\yichen-jianying-edit\scripts\headless_draft.py publish --build D:\work\build1 --audit D:\work\audit1
python skills\yichen-jianying-edit\scripts\headless_draft.py verify --build D:\work\build1
~~~

`publish` 前须完全退出剪映（`JianyingPro.exe` 不在运行；托盘程序不影响）。
不带 `--backend native` 时，`build` / `verify-build` 仍走原有的 FFmpeg 渲染路径。

## 与 macOS 的差异

| 项目 | macOS | Windows |
| --- | --- | --- |
| 时间线文件 | `draft_info.json` | `draft_content.json` |
| 首页索引 | 草稿目录内 | `%LOCALAPPDATA%` 下，可与自定义草稿目录分离 |
| 路径写法 | 原生 | 正斜杠 `E:/...` |
| 默认字幕字体 | 应用包内 `zh-hans.ttf` | 安装目录 `Resources/Font/SystemFont/zh-hans.ttf` |
| 扩展属性 / clonefile | 保留 | 不适用 |
| 特效资源目录名 | 完整 64 位树哈希 | 前 16 位（受 260 字符路径限制；完整哈希仍逐字节校验） |
| 键值登记 `key_value.json` | 存在 | 草稿中没有，编辑时只维护已存在的文件 |

## 支持范围

视频分段、多轨、变速、音量、画中画、字幕、本地字体、线性关键帧；
6 种蒙版、叠化转场、轻微抖动特效；编辑已有草稿的独立副本（`edit`）；
UI 导出验收（`ui-export`）。复合片段（嵌套时间线）仍只在 macOS 上开放。

特效资源取自本机剪映缓存：某个效果须先在剪映里用过一次（触发下载），否则构建会提示。
蒙版与叠化的资源包与 macOS 采集逐字节相同；轻微抖动在 Windows 上是 GLSL 版本，
由 `engine/native-resource-catalog-windows.json` 只替换来源与字节身份，素材模板不变。

整套草稿文件路径须少于 240 字符，草稿名或草稿目录过长时构建会提前报错。

### 编辑已有草稿

~~~bat
python skills\yichen-jianying-edit\scripts\headless_draft.py edit inspect --draft "E:\...\JianyingPro Drafts\某草稿" --out D:\work\inspect.json
python skills\yichen-jianying-edit\scripts\headless_draft.py edit build --plan D:\work\edit-plan.json --out D:\work\edit-build
python skills\yichen-jianying-edit\scripts\headless_draft.py edit publish --build D:\work\edit-build --audit D:\work\edit-audit
python skills\yichen-jianying-edit\scripts\headless_draft.py edit verify --build D:\work\edit-build
~~~

计划格式与 macOS 相同，见 `skills/yichen-jianying-edit/references/edit-existing.md`。

### 导出成片

默认用无界面导出（开发中，见 HANDOFF.md 第五节第 1 条）：一条命令直接出 MP4，不用打开剪映。
导出前先检查草稿里的效果是否都在 HANDOFF.md 第一节的白名单里 不在的询问用户经过同意直接在导出：
- 都在：直接导出。
- 有一个不在：用户没有明确拒绝 也导出（用户不说默认导出）

无界面导出做好之前，可以用剪映导出窗口 + 脚本校验（ui-export plan / verify），
或者用 export --backend windows-ffmpeg（只支持基础剪辑，没有特效）。

## 验收记录

2026-10-21，剪映 11.6.0.14552：生成 2 段视频（含 1.5 倍速）+ 配音 + 2 句字幕的草稿，
首页可见，打开、播放、修改、保存、完全退出后冷重开均正常。保存后时间线由 185.0.0
升级为 189.0.0（`last_modified_platform.app_version` = 11.6.0），素材、时长、变速与字体绑定不变。

2026-10-21，同版本补充验收：
- 6 种蒙版 + 叠化转场的草稿：显示正确；剪映保存（189）后完整回读通过。保存会把资源路径改指本机缓存
  （`native_cache_dependency: true`，与 macOS 行为一致）。
- 11.5.3 保存的已有草稿的编辑副本（缩放、位移、音量）：显示正确，保存后完整回读通过，原草稿不变。
- UI 导出：成片 5290 帧、1080×1920、H.264/AAC、完整解码，与导出计划一致；该次校验因导出后草稿
  又被修改，按设计拒绝出具结论。
- 口播自动剪辑：FunASR 本地转写 → 按能量修正切点 → `edit_plan.py compile` → 原生草稿，
  185 秒剪至 176 秒，打开播放正常。
