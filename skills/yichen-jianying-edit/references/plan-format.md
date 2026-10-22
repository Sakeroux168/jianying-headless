# 剪辑计划与脚本接口

## 输入计划

`edit_plan.py compile` 读取 `jianying-edit-plan/v1`。所有时间都是原片秒数，只有编译结果
使用微秒。路径、hash、时长由本次素材实测取得，不沿用示例值；Windows 路径写反斜杠，
JSON 里双写反斜杠或统一用正斜杠都可以。

```json
{
  "schema": "jianying-edit-plan/v1",
  "source": "E:\\素材\\source.mp4",
  "source_sha256": "本次副本的 SHA-256",
  "source_duration": 10.0,
  "fps": 30,
  "speed": 1.5,
  "voice_volume": 1.0,
  "settings_confirmed": true,
  "settings": {"intensity": "本次确认的力度", "sound_effects": "本次确认的需求"},
  "check_decisions_pending": false,
  "bgm": false,
  "keeps": [
    {"start": 0.0, "end": 2.4, "protect": [[0.08, 2.32]], "reason": "完整开场"},
    {"start": 3.0, "end": 6.0, "protect": [[3.08, 5.92]], "reason": "保留重说中更完整的一遍"}
  ],
  "subtitles": [
    {"start": 0.08, "end": 2.32, "text": "这里是第一句"},
    {"start": 3.08, "end": 5.92, "text": "这里是后一句"}
  ],
  "sfx": [{"source_time": 3.08, "name": "啵1", "volume": 0.13, "reason": "演示开始"},
          {"source_time": 5.2, "openverse": "whoosh", "volume": 0.4, "max_duration": 1.2, "reason": "转场"}],
  "decisions": [{"action": "DELETE", "start": 2.4, "end": 3.0, "reason": "气口"}]
}
```

- `settings_confirmed` 表示 Agent 已从当前用户请求取得参数；字段自身不能代替用户指令。
- `check_decisions_pending=false` 只能在 CHECK 项已经解决后填写。草稿中间版可继续准备，
  但不能把未决定的删除伪装成最终计划。
- `protect` 为保留词的有效发音区间，可按词列多个。只有明确无语音、且确实需要保留的画面
  才用空列表。Windows 上这些区间应按 [切点按音量修正](editing-and-qc.md) 的结果填，
  不要直接用 ASR 原始时间。
- 编译器向内选择可容纳完整发音的整帧区间，不自动延长保留区间。无解时报错，应调整低能量处
  的边界，而不是删保护词来通过检查。
- 一条字幕可以跨多个保留片段；起止点必须仍在保留内容中，文字仅包含保留语义。编译器增加
  20ms/40ms 的轻微显示余量并裁掉相邻字幕重叠。
- `edit_plan.py` 要求计划里必须有字幕段：没有字幕时也会报
  `This speech-edit workflow requires a subtitle track.`。不要字幕时的做法见
  [计划与命令](headless-plan.md)（`from-compiled` 输出里删 `text` 轨再 build）。
- 音效事件落在删除区间时默认报错。确认应随下一段保留内容开始时，可显式设置
  `"snap": "next"`。
- `openverse` 事件用英文关键词描述要找的声音：1–60 个英文字母、数字、空格、连字符或撇号，
  以字母或数字开头，大小写和多余空格会被规范化，例如 `pop`、`whoosh`、`camera shutter`；
  同一事件不能再写 `name`。`volume` 为 0–1，默认 0.5，相对统一后的响度；`max_duration`
  为 0.1–8 秒，默认 1.5。起点离成片结尾不足 0.1 秒时报错。
- 编译结果把这类事件写入 `openverse_sfx`，时间已映射到剪后时间轴；`from-compiled` 不处理
  它，必须再运行 `openverse_sfx.py add`。没有该字段的旧编译结果仍可校验和转换。
- `voice_volume` 是线性增益；先检查源音量与峰值，再决定是否调整，不机械套用 2 倍。
- 编译器只生成口播映射、普通字幕、白名单音效提示和 Openverse 关键词提示。输出转为
  [计划与命令](headless-plan.md) 的多轨计划后，可以按用户需求加入本地 BGM、其他音效和
  B-roll；无界面新计划的 build/verify 会核对这些内容。需在线账号资源时再使用原生 UI。

## 命令

脚本均位于 Skill 的 `scripts/`。下列 `WORK`、`SKILL` 表示本次工作目录和 Skill 目录；
实际调用使用绝对路径，并保留每一版新文件。Windows 用 `python`，不要写 `python3`。

```bat
python SKILL\scripts\edit_plan.py compile --plan WORK\edit-plan.json --out WORK\compiled-v1
python SKILL\scripts\edit_plan.py render-audio --plan WORK\compiled-v1\compiled.json --out WORK\voice-v1.wav --work WORK\audio-render-v1
```

转写：Windows 用本机 FunASR 取逐字时间戳（见 [转写](editing-and-qc.md)），把结果整理成
`words` 后写进计划。`asr_once.py` 只是去重包装器，需要另行提供执行器
（默认找用户目录下 `scripts\transcribe.py`，或用 `YICHEN_ASR_EXECUTOR` 指定绝对路径），
本发行不含执行器与凭据；有本地 FunASR 时不必绕这一层。

```bat
python SKILL\scripts\headless_draft.py from-compiled --compiled WORK\compiled-v1\compiled.json --name 本次草稿名 --out WORK\plan.json --backend native
```

确认参数和删留决定后，用 `from-compiled` 转换并无界面创建草稿；`--backend native` 必须写，
否则会落到 FFmpeg 便携后端。`compile` 输出的 `openverse_sfx` 大于 0 时，会提示在
`from-compiled` 之后运行 `openverse_sfx.py add`，再用它写出的新计划 build。本发行不包含
旧版模板适配器 `native_draft.py`，不调用未分发的脚本。
