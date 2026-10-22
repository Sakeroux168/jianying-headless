---
name: yichen-jianying-edit
description: 在 Windows 上用剪映专业版 11.6.0.14552 无界面生成可编辑草稿、修改已有草稿的独立副本、按白名单规则交付成片，含口播自动剪辑与效果导入。需要另行检出 Jianying Headless 核心项目；其他剪映版本不支持；纯转写不使用本 Skill。
---

# 剪映无界面剪辑（Windows）

- 平台：Windows + 剪映专业版 **11.6.0.14552**。版本不符时 `doctor` 会因 `videoeditor.dll`
  哈希不一致拒绝运行；不要改固定哈希放行，先核对新版本再登记。
- 命令一律 `python`（不是 `python3`），路径写反斜杠，CMD 和 PowerShell 都能执行。
- 核心项目单独检出；`JIANYING_HEADLESS_ROOT` 指向它的根目录。入口是核心项目的
  `skills\yichen-jianying-edit\scripts\headless_draft.py`，所有命令都从这里进。
- 环境、验收记录与 macOS 差异表：核心项目 `docs\windows-native.md`。

默认交付可继续编辑的原生草稿，不生成 MP4。用户明确要成片时才导出；Windows 目前没有
已审核的无界面导出配置，成片一律走剪映自己的导出窗口（`ui-export`），能不能导先看下一节。

## 先确认依赖和本次范围

1. 跑 `python SKILL\scripts\headless_draft.py doctor --backend native`：核对
   `videoeditor.dll` 哈希、从注册表读安装位置、从 `globalSetting` 读草稿目录、固定首页索引。
   首次使用或桥接源码改过之后，先跑 `bridge\windows\build.bat` 编译。
2. 从请求确定素材、新建还是修改、速度、音量、音效/BGM 和剪辑力度；不沿用历史项目的
   速度和删减偏好，不明确的语义删减集中询问。
3. 转写是可选依赖。Windows 用本机 FunASR，必须取**逐字时间戳**，不要按句切分的结果
   （字和时间会对不上）；细节见 [语义与音频质检](references/editing-and-qc.md)。
   付费 ASR 需本次明确授权，不自动充值、切换服务商或重复提交。
4. Windows 有 260 字符路径上限：整套草稿文件路径须少于 240 字符，工作目录放在短路径下
   （例如 `E:\Dev\jianying-work\...`），不要放在很深的下载或项目目录里。

## 选择入口

- 新建草稿：读 [计划与命令](references/headless-plan.md)。直接创建独立草稿，不要求先在
  界面里准备模板；在线模板不在发行范围。
- 修改已有草稿：读 [独立副本编辑](references/edit-existing.md)，原草稿只读。
- 要成片：读 [导出](references/export.md)。先按下面白名单判断，再决定 `ui-export`
  （剪映界面渲染 + 脚本校验）还是 `export --backend windows-ffmpeg`。
- 口播语义剪辑：读 [语义与音频质检](references/editing-and-qc.md) 和
  [口播计划格式](references/plan-format.md)，由 `scripts/edit_plan.py` 统一编译时间映射。
- 口播自动音效：用户要音效又没给本地音频时，在口播计划里写英文关键词的 `openverse`
  事件；`from-compiled` 之后用 `scripts/openverse_sfx.py add`，步骤见
  [计划与命令](references/headless-plan.md)。
- Hypit 工程交接：读 [素材与字体交接](references/hypit-handoff.md)。

## 导出白名单

无界面导出只放行 HANDOFF.md 第一节「白名单：」那一行里的效果，以那里为准，这里不另存一份。
。当前这 19 项都由用户在剪映里确认过不弹会员提示。
- 白名单外的效果（新导入的转场、滤镜、贴纸、花字、其他特效）用户同意才可以用：
  需要做无界面交付
- 新导入的效果先算白名单内，等用户明确踢出某个效果才放到白名单外
- 白名单是渲染放行清单
  [运行依赖与来源](references/dependencies-and-notices.md)。

## 命令速查

```bat
python SKILL\scripts\headless_draft.py doctor --backend native
python SKILL\scripts\headless_draft.py from-compiled --compiled WORK\compiled\compiled.json --name 本次草稿 --out WORK\plan.json --backend native
python SKILL\scripts\headless_draft.py build --backend native --plan WORK\plan.json --out WORK\build1
python SKILL\scripts\headless_draft.py verify-build --backend native --build WORK\build1
python SKILL\scripts\headless_draft.py publish --build WORK\build1 --audit WORK\audit1
python SKILL\scripts\headless_draft.py verify --build WORK\build1 --report WORK\after-save.json
```

- `publish` / `resume-publish` / `create` / `verify` / `edit` / `ui-export` 在 Windows 上
  默认就是原生，不用加 `--backend`。
- `doctor` / `build` / `verify-build` 不加 `--backend native` 会走 FFmpeg 渲染的便携后端：
  产出的是视频，不是剪映草稿。`from-compiled` 和其余命令不加会直接报 `Unsupported Windows command`。

## 执行与验收

- 源片保持不动，只用本次授权的本地素材。字幕默认需要，样式按本次画面调整；BGM 没提出
  就不加。不要删掉难以确认的数字、产品名或核心判断。
- `build` 只写本次 `work\` 下的新目录。`publish` / `resume-publish` 是本机剪映首页登记，
  不是线上发布。**执行前让用户完全退出剪映，执行前让用户完全退出剪映，包括托盘图标**（`tasklist` 里看不到
  `JianyingPro.exe`）；不要按名字强杀进程。发布前工具会备份 `root_meta_info.json`，
  保留该备份。
- 素材副本、哈希、一致性和目录锁由工具核对；不要把 `--expect-*` 这类一致性参数当成
  要用户逐项确认的问题。
- 特效资源只能来自本机已合法取得的匹配缓存或本地效果库，保持原有许可字段与逐字节校验。
  不下载、不解锁、不伪造授权；缓存存在或渲染成功都不等于会员/商用许可。
- 效果查找顺序：先看本地效果库 `E:\项目文件\本地效果库`（`catalog.json` 登记表、
  `packages\` 资源包）。库里没有的效果，让用户把它们拖进任意草稿（默认草稿名
  `效果导入`）让剪映下载，完全退出剪映后运行 `python tools\import_effects.py`，
  工具会导入资源包、登记模板、追加到 `HANDOFF.md` 的「待确认」，并发布一份测试草稿
  供用户在界面验收。导入后仍按白名单规则处理。
- `openverse_sfx.py` 会联网，只访问 Openverse API 与 Freesound 预览地址；草稿
  build/publish 不联网。音效保留各自的 CC 许可：默认 CC0、CC BY、CC BY-NC 都可用，
  CC BY-NC 只在没有合适的 CC0 / CC BY 时选中。商单、广告、带货、引流或开通收益的
  视频加 `--commercial`，只用 CC0 / CC BY。
- 某个关键词找不到合格音效或遇到限流时整步失败、不写新计划；改关键词重新编译，或换新的
  `--work` 稍后重跑。不换未审查的来源、不绕过限流、不为了成功去掉用户要的音效。
- 用了 Openverse 音效时，交付说明须转述本次 `credits.md`：是否含 CC BY-NC、哪些需要
  署名，并附可直接粘贴的署名文字。挑选只依据标题、标签、时长和许可，没有试听。
- 复合片段（嵌套时间线）在 Windows 上仍未开放，`native_compound.SUPPORTED_PROFILES`
  里没有 Windows 配置；遇到复合草稿要明说不可做，不要试着绕过。
- 草稿要在剪映里检查画面、字幕、音量和切口，保存、退出并冷重开后回读。缺 UI 条件时
  继续离线部分，但明确标注原生验收未完成。
- 导出后检查实际画面和声音；`encoded-and-decoded` 不代表内容正确。默认草稿交付不生成
  临时 MP4。失败保留现场，不自动重试、去掉效果或换旧快照。
- 保留原始素材和现有草稿；清理只按本次明确授权执行，不自动永久删除文件。

## 安装范围与许可

Skill 与核心项目分别安装；只装 Skill 不包含后端。代码许可、剪映协议、素材许可和账号
权益分别适用，见 [运行依赖与来源](references/dependencies-and-notices.md)。
