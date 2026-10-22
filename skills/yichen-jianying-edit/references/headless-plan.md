# 本机无界面原生草稿（Windows）

## 入口与验证边界

- 入口：核心项目的 `skills\yichen-jianying-edit\scripts\headless_draft.py`，代码在
  `engine\`。独立安装 Skill 时用 `JIANYING_HEADLESS_ROOT` 指向核心项目根目录，
  入口会核对固定文件的 SHA-256。
- 只支持 Windows 剪映 **11.6.0.14552**：安装位置从注册表 `Uninstall\JianyingPro` 读取，
  也可用 `JIANYING_INSTALL`（含 `uninst.exe` 的目录）指定；草稿目录从 `globalSetting`
  读取（本机 `E:\全局软件\JianyingPro Drafts`）；首页索引固定在
  `%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft\root_meta_info.json`。
  三个目录可以彼此分离，不要假设首页索引在草稿目录里。
- 加解密由本机已安装的 `videoeditor.dll` 提供（`lvve::EncryptUtils`，与 macOS 桥接同
  一个类）：`bridge\windows\jy14_codec_win.cpp` + `runtime_io_win.py`。运行时会校验
  DLL 数字签名，`engine\runtime_profiles.py` 的 `WINDOWS_PROFILES` 固定它的哈希；
  版本不符就拒绝运行，不改哈希放行。
- 时间线文件是 `draft_content.json`（macOS 是 `draft_info.json`）；草稿内路径统一写成
  正斜杠；Windows 草稿没有 `key_value.json`，编辑链路只在文件存在时处理。
- 草稿 build/publish 不联网、不调用 ASR、不导出视频。要成片另看 [导出](export.md)。
- 复合片段（嵌套时间线）在 Windows 上没有配置，`native_compound.SUPPORTED_PROFILES`
  里只有 macOS profile；遇到复合草稿直接说明不可做。

## 正常调用

大写路径是待替换参数，实际用绝对路径；输出必须是本次 `work\` 下的新目录。Windows 上
`publish` / `create` / `verify` / `edit` / `ui-export` 默认走原生，不需要 `--backend`；
`doctor` / `build` / `verify-build` / `from-compiled` 必须显式加 `--backend native`，
否则落到 FFmpeg 渲染的便携后端。

```bat
python SKILL\scripts\headless_draft.py doctor --backend native
python SKILL\scripts\headless_draft.py from-compiled --compiled WORK\compiled\compiled.json --name 本次草稿名 --out WORK\plan.json --backend native
python SKILL\scripts\headless_draft.py build --backend native --plan WORK\plan.json --out WORK\build1
python SKILL\scripts\headless_draft.py verify-build --backend native --build WORK\build1
python SKILL\scripts\headless_draft.py publish --build WORK\build1 --audit WORK\audit1
python SKILL\scripts\headless_draft.py verify --build WORK\build1 --report WORK\after-save.json
```

- `build` 可以在剪映运行时执行；`publish` / `resume-publish` 必须让用户完全退出剪映
  （主程序与托盘都退出，`tasklist` 里没有 `JianyingPro.exe`），不能随手强杀进程。
- `verify` 是结构回读，保存退出后执行，避免读到保存中的镜像；它不代替播放验收。
- 已关闭剪映且计划审查过时，可用 `create --plan WORK\plan.json --work WORK\new-dir`
  一次做 build + publish；它只是登记到本机首页，不是公开发布。

口播链路里 `edit_plan.py` 必须有字幕轨。不要字幕时：先在编译结果里保留字幕轨生成计划，
在 `from-compiled` 输出的计划里删掉 `text` 轨，再 `build`。

有编译音效提示时（受支持的本机缓存音效「啵1」）：

```bat
python SKILL\scripts\headless_draft.py cached-sound --name 啵1 --backend native
python SKILL\scripts\headless_draft.py from-compiled --compiled WORK\compiled\compiled.json --name 本次草稿名 --out WORK\plan.json --cached-sounds-as-local --backend native
```

有 Openverse 音效提示时（`compile` 输出的 `openverse_sfx` 大于 0），在 `from-compiled` 和
`build` 之间加一步；同时含「啵1」时 `from-compiled` 照常加 `--cached-sounds-as-local`：

```bat
python SKILL\scripts\openverse_sfx.py add --compiled WORK\compiled\compiled.json --plan WORK\plan.json --out WORK\plan-sfx.json --work WORK\openverse-sfx-v1
python SKILL\scripts\headless_draft.py build --backend native --plan WORK\plan-sfx.json --out WORK\build1
```

- 联网范围：只用 HTTPS 请求 `api.openverse.org` 检索 Freesound 来源，再从
  `cdn.freesound.org` 下载预览 MP3；明文 HTTP、其他主机和跨主机重定向都被拒绝。
  每个关键词检索一次，请求里只有关键词和筛选条件。匿名额度约每分钟 20 次、每天 200 次；
  短暂限流会等待后重试，需等待超过 60 秒时报错，不换来源。
- 挑选：标题和标签都对不上关键词的不选；音乐、循环、环境声、人声、合集排在干净匹配之后；
  CC BY-NC 只在没有干净的 CC0 / CC BY 时选中，同等条件 CC0 优先。默认允许
  CC0 / CC BY / CC BY-NC，`--commercial` 只检索 CC0 / CC BY。某关键词没有合格结果时
  整步失败、写 `status=failed` 的 `report.json`、不写新计划。
- 处理：起音前保留 3 ms，长度不超过该提示的 `max_duration`，截短处 40 ms 淡出；
  最响 50 ms 窗口统一到约 -20 dBFS，峰值不超过 -1 dBFS，计划里的 `volume` 在此基础上
  缩放。输出 48 kHz PCM WAV，按时间点写入「Openverse 音效 N」音轨，重叠时另开一轨，
  到成片结尾截止；口播和字幕轨不变。
- 输出：`--work` 下保留 `search\`、`downloads\`、`sounds\`、`report.json`、`credits.md`。
  `--out` 和 `--work` 必须是新路径；已含 Openverse 音轨的计划会被拒绝，避免重复添加。
- 挑选不试听；原生验收时要听音效，不合适就改关键词重跑。只想看候选时用
  `python SKILL\scripts\openverse_sfx.py search --query whoosh --max-duration 1.2`，只检索
  不下载，也占一次额度。

## `jy14-headless-plan/v1`

时间全部是整数微秒。计划可以手写，也可以在 `from-compiled` 输出后加 BGM、标题或 B-roll；
任何改动都发生在 build 之前。

```json
{
  "schema": "jy14-headless-plan/v1",
  "name": "本次独立草稿",
  "canvas": {"width": 1920, "height": 1080, "fps": 30},
  "tracks": [
    {"type": "video", "name": "主视频", "segments": [
      {"source": "E:/素材/source.mp4", "start_us": 0, "duration_us": 2000000,
       "source_start_us": 1000000, "source_duration_us": 3000000, "speed": 1.5, "volume": 1.0}
    ]},
    {"type": "text", "name": "字幕", "segments": [
      {"text": "这是一条可编辑字幕", "start_us": 0, "duration_us": 2000000,
       "size": 6, "x": 0, "y": -0.78, "color": "#FFFFFF", "border_color": "#000000", "border_width": 0.05}
    ]},
    {"type": "audio", "name": "按需 BGM", "segments": [
      {"source": "E:/素材/music.wav", "start_us": 0, "duration_us": 2000000, "volume": 0.12}
    ]}
  ]
}
```

- 非空草稿第一轨必须是连续的主视频：首段从 0 开始，同轨有序不重叠，不留黑场。后续
  `video` 轨是画中画 / B-roll，可以有间隙；`text` 用于字幕和标题；`audio` 用于本地
  BGM / 音效。所有轨道须在主视频长度内。空 `tracks` 可离线构造空草稿，但没做原生验收。
- 视频 / 音频：`source` 用本次授权的绝对本地路径（正斜杠或反斜杠都可，工具统一写正斜杠）；
  `source_start_us` 默认 0，`source_duration_us` 默认等于目标时长，`speed` 默认 1。
  `source_duration_us / speed` 必须等于 `duration_us`，源区间不能越界。
- 速度 0.1–8；`volume` 是 0–4 线性增益。保持音高没有独立计划字段，不能宣称已精确控制。
- 视频还支持 `scale`（统一缩放，默认 1）、`x`/`y`（默认 0）、`rotation`（默认 0）、
  `opacity`（0–1，默认 1）。不是像素坐标，按剪映画面实测调整。文字默认 `y=-0.78`，
  多行或画面主体不同不要盲用默认位置。
- 文字支持 `size`、`x`/`y`、`color`、`border_color`、`border_width` 和可选 `font_path`；
  颜色为 `#RRGGBB`。省略 `font_path` 时用安装目录内置中文字库
  `Resources\Font\SystemFont\zh-hans.ttf`；指定时用绝对路径的本地静态 `.otf` / `.ttf`，
  文件缺失或格式不支持直接报错，不回退默认字体。普通字号与描边是剪映内部值，不等于 CSS px。
- 字体按内容哈希复制到草稿 `Resources\headless-fonts\`，同字节字体只留一份，记入
  `build.json` 的 `font_assets`；构建后不再依赖原字体文件。不接受字体名称、URL、
  TTC/OTC 集合、可变字体或在线账号字体；每个文字片段用一个字体。
- 输入视频限 H.264 / HEVC、单视频流、最多一条音频流，拒绝旋转元数据与未知像素格式，
  不偷偷转码。`video` 轨也可直接用 PNG、JPEG、GIF。静态图片不能指定源偏移或非 1 倍速度。
  复合片段、文字/自定义蒙版、未采集的滤镜/特效/花字、除白名单外的转场与在线模板未接入，
  未知字段会报错。
- 每个源文件按内容哈希复制一份到草稿内，源路径不再是播放依赖；不要清理草稿 `Resources`。

片段可加 `keyframes`，例如
`"keyframes": {"x": [{"at_us": 0, "value": -0.5}, {"at_us": 2000000, "value": 0.5}]}`。
时间相对片段开头，每条曲线至少两点、第一点在 0、严格递增、不超过片段时长，只支持线性
插值。视频支持 x/y/scale/rotation/opacity/volume，文字支持 x/y/scale/rotation，音频支持
volume；不能只改静态基值。关键帧当前限制源起点为 0、速度为 1，剪过源入点或变速的会拒绝。

## 蒙版

视频轨片段可加 `"mask": {"shape": "circle", "width": 0.28, "height": 0.5}`。`shape` 可选
`circle` / `rectangle` / `line` / `mirror` / `star` / `heart`（对应剪映里的圆形、矩形、
线性、镜面、星形、爱心蒙版）。尺寸是原生归一化包围框，不是像素，默认 0.28 × 0.5。
支持 `x`/`y`、`rotation`、`feather`（0–1）、`invert`（布尔），矩形另支持
`round_corner`（0–1）。线性蒙版是半平面，拒绝无效果的 `width`/`height`。蒙版关键帧未接入。

## 转场

主视频片段可加
`"transition_out": {"name": "dissolve", "duration_us": 400000, "edge_policy": "require-handles"}`，
表示接到下一段的叠化（剪映里的「叠化」）。只有主视频相邻片段可用，末段不能加；时长需对应
偶数帧且不长于两边任一段。默认要求两侧各有半个转场长度的源余量（变速按速度换算，静态图
可自然保持）；余量不足会拒绝，只有明确接受端点重复帧时才用 `repeat-edge`，受影响边会记在
`transition_audit`，时间线总时长不缩短。

叠化不等于音频淡入淡出：同相测试原声在重叠区间约 +6.03 dB，剪映界面导出约 +6.02 dB。
这是原生叠加行为，仍须检查真实音频，不静默修正音量。

## 效果（转场、特效）

效果名按本地效果库目录名识别：`transition/<名字>`、`effect/<名字>`。原作者自带的少数保留
英文键：`transition/dissolve`（叠化）、`effect/light-shake`（轻微抖动）；6 种蒙版见上节。

特效轨写法（主视频之后，有序、不重叠、位于主视频内）：

```json
{"type":"effect","segments":[{"name":"light-shake","start_us":0,"duration_us":2000000,"params":{"range":0.15,"speed":0.33}}]}
```

效果参数写**去掉 `effects_adjust_` 前缀的短名**，例如 `speed`、`volume`，按各效果自己的
`adjust_params` 读取；`range` / `speed` 是 0–1，分别控制幅度和运动速度（后者不是视频倍速），
默认 0.15 / 0.33。不接受 source、关键帧或片段速度字段。

资源来自本机剪映缓存或本地效果库，保持原有许可字段与逐字节哈希：

- 缓存位置：`%LOCALAPPDATA%\JianyingPro\User Data\Cache\effect\<效果ID>\<md5>`。某个效果
  必须先在剪映里用过一次（触发下载），否则构建会提示缺资源。
- 本地效果库：`E:\项目文件\本地效果库`（`packages\` 资源包、`catalog.json` 登记表、
  `work\` 测试构建），位置记在 `%LOCALAPPDATA%\jianying-headless\config.json`，
  可用 `--library` 改。`native_resources.catalog()` 会叠加效果库，已审查条目优先。
- 导入新效果：让用户把转场/特效拖进草稿（默认 `效果导入`）让剪映下载，完全退出剪映后运行
  `python tools\import_effects.py`（`--draft` 换草稿名，`--no-test` 只导入不生成测试草稿）。
  工具最后会发布一份「导入测试-月日时分」草稿，供用户在剪映里验收。
  目前只支持转场（`materials.transitions`）和画面特效（`materials.video_effects`）；
  滤镜、贴纸、花字、文字模板列在「暂不支持」。导入的特效统一用「轻微抖动」的轨道与片段
  模板，转场按居中重叠处理。
- 是否收费由用户在剪映里确认（看会员角标或试导出），脚本不判断。只有白名单里的效果可以走
  无界面导出，其余见 [导出](export.md)。白名单在 [SKILL.md](../SKILL.md)。
- 资源目录名只用树哈希前 16 位（Windows 260 字符限制），完整哈希仍然逐字节校验。剪映保存
  后会把路径改指自己的缓存，`verify_binding` 接受记录的 `native_cache` 位置并逐字节核对，
  报告 `native_cache_dependency: true`；缓存缺失时停止，不自动下载。
- 高清黑白滤镜和橙色描边花字早已移除，不在支持范围；旧计划含这两项直接报错。

## 验证与部分失败

`verify-build` 核对完整文件清单、计划哈希、编解码、目标路径、轨道/素材引用、时间、速度、
音量、画布、文字内容与样式、字体字节。`verify` 还检查 live 草稿与首页身份、活动镜像内容
一致与 inode 独立、所有媒体字节。原生保存会把路径改成 draftpath 占位或 `./Resources/`，
验证器只接受已实测格式并解析到同一素材。

- 原生把时间吸附到帧网格，回读容差一帧；这不是允许删发音保护区，口播映射仍由
  `edit_plan.py` 在 build 前审查。
- 首页索引原件与替换前后的备份在审计目录；发布前备份 `root_meta_info.json`，不要删。
- 目录已写入但首页登记失败时，看审计里的 `published.json`，然后可运行
  `python SKILL\scripts\headless_draft.py resume-publish --build WORK\build1 --audit WORK\resume1`。
  它只在整个目标目录仍与清单逐字节一致、剪映已关闭、runtime 一致时继续，不覆盖草稿。
  已成功登记时返回只读幂等结果。用户或剪映改过任何文件就保留现场，定向诊断。
- 路径：整套草稿文件路径须少于 240 字符（Windows 260 上限），超了构建会提前报错。
- 改过 `engine\` 下任何被固定的文件（含 `native-resource-catalog-windows.json`，该文件
  必须 LF 换行），都要同步更新 `scripts\headless_draft.py` 里的 `PINS`，否则入口直接拒绝运行。
- 本机封装不等于可分发安装包：不打包 codec、真实草稿、缓存音效、bookmark 或账号配置。
