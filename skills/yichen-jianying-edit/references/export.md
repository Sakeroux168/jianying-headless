# 导出成片（Windows）

只在用户明确要成片时执行。默认草稿交付不产出 MP4。

## 现状：没有无界面原生导出

Windows 侧**没有**已审核的无界面导出配置，`runtime_profiles.EXPORT_PROFILES` 里没有
Windows 条目。原因是还没逆向出 `ExportStartReqStruct`（大小、虚表、里面的输出路径 / 宽高 /
帧率 / 码率），它的构造函数没有导出；macOS 的偏移不能照搬，Windows 是 MSVC 编译，
`std::string` 是 32 字节，`shared_ptr` 和 `function` 的布局也不同。
`videoeditor.dll` 已经公开导出的部分（`lyra::Server::instance` / `openSession` /
`invokeSync`、`lvve::GetDraftFromJson` / `GetJsonFromDraft`、
`Deserializer::deserialize_persistent_draft`、`ProjectClient`、
`Session::draftTransaction`、`lvve::Logger`、`ExportClient::exportStart`）只能说明
路线可行，不代表已经能用；不要用 `export --backend native` 去试，它会按 macOS 门禁拒绝。

结论：成片走下面两条路之一。`ui-export` 是剪映自己渲染，属另一档证据；
`windows-ffmpeg` 是脚本用 FFmpeg 重渲染，不产生剪映草稿。

## 白名单门禁（选路之前先过）

只有 [SKILL.md](../SKILL.md) 白名单里的效果允许走脚本渲染的无界面路
（`windows-ffmpeg`，以及将来接入的原生导出）。白名单外的效果一律不能由脚本渲染：

- 需要会员的效果，脚本渲染会绕过剪映的会员 / 付费素材检查，属于不能做的事。
- 这类需求只能走 `ui-export`：由剪映自己的导出窗口渲染，会员检查由剪映执行；
  并在交付说明里提醒用户确认有没有弹会员提示。
- 新导入、用户还没确认是否免费的效果，按白名单外处理。

白名单是渲染放行清单，不是商用许可；授权边界见
[运行依赖与来源](dependencies-and-notices.md)。

## 路线一：`ui-export`（剪映界面渲染 + 脚本校验）

导出的是**已登记的 live 草稿**，所以 build 必须先 `publish`。任务目录路径里必须有一级
叫 `work` 的目录（例如 `D:\work\ui-export-1`）。

```bat
python SKILL\scripts\headless_draft.py ui-export plan --build WORK\build1 --out WORK\work\ui-export-1
rem 按 plan 打印的 dialog_settings_required 在剪映里导出，然后：
python SKILL\scripts\headless_draft.py ui-export verify --job WORK\work\ui-export-1
```

`plan` 会校验 build、证明登记草稿仍等于它，并打印必须照做的对话框设置：格式 **MP4**、
分辨率 **原始**、帧率按计划、导出到 job 目录、**音频导出保持关闭**（那是单独的音频文件，
不是视频里的音轨）、**一键超清保持关闭**。渲染结束页带第三方发布入口，只点关闭，不发布。

`verify` 默认找 `plan` 记录的路径；导出到别处用 `--video ABSOLUTE_MP4`，`--report` 另存
证据。每次 `verify` 写自己的 `attempt-NNN\`，被拒的导出不会被后一次覆盖。帧数不足判为
残次品，不按取整容差放过。容器接受 `isom` / `mp41` / `mp42` / `qt  `
（剪映可能写出扩展名是 `.mp4` 的 QuickTime 容器，只看扩展名会误判）。

必须先告诉用户两件事：

- 界面导出**会修改被导出的那个草稿**（打开期间剪映会重写备份、封面和保存的时间线），
  以它为来源的编辑副本之后会在「来源未变」检查上失败。
- 导出后、校验前草稿不能再被修改。

## 路线二：`export --backend windows-ffmpeg`（FFmpeg 重渲染）

不需要剪映草稿时用它：按计划重渲染出 MP4，产物不是原生草稿。Windows 上 `export` 默认
就走 `windows-ffmpeg`，显式写出来是为了不让人误解成原生导出。

```bat
python SKILL\scripts\headless_draft.py export --build WORK\build1 --out WORK\work\export-1
```

可调 `--ffmpeg`、`--ffprobe`、`--font`、`--crf`（默认 18）、`--preset`（默认 medium）、
`--timeout`（秒）。参数细节与已知差异见核心项目 `docs\windows-ffmpeg.md`。
它的渲染结果与剪映不是逐像素一致，字幕排版、特效、蒙版都需要看图核对；白名单外的效果
不接受这条路。

## 验收与失败处理

成功状态 `encoded-and-decoded` 只表示拿到了完整文件、标准 MP4/H.264/AAC 检查通过、
完整解码通过、素材与来源 build 没变。仍须看实际画面，检查内容、字幕位置、变速、转场、
结尾，涉及音量变化时检查音频。

- 时长与帧率相乘为整数时帧数必须完全一致；真正非整帧的时长只接受相邻两个整数帧数。
  容器时长容差是一帧或 50 ms 中较大者，不能拿音轨或容器时长掩盖视频少帧。
- 失败保留日志和部分文件，标为失败，不交付部分 MP4；没有自动重试、降级编码、去掉效果
  或改成界面代操作。
- 不同分辨率、帧率、效果组合仍需各自核对；一个样本通过不代表组合都通过。
