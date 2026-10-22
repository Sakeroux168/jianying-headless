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

## 支持范围

视频分段、多轨、变速、音量、画中画、字幕、本地字体、线性关键帧。
蒙版、转场、滤镜、特效、花字依赖 macOS 采集的资源，Windows 上会明确报错。
编辑已有草稿（`edit`）和原生导出暂未移植；成片导出用 `export --backend windows-ffmpeg`。

## 验收记录

2026-10-21，剪映 11.6.0.14552：生成 2 段视频（含 1.5 倍速）+ 配音 + 2 句字幕的草稿，
首页可见，打开、播放、修改、保存、完全退出后冷重开均正常。保存后时间线由 185.0.0
升级为 189.0.0（`last_modified_platform.app_version` = 11.6.0），素材、时长、变速与字体绑定不变。
