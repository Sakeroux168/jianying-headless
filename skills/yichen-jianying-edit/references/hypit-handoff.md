# Hypit 素材与字体交接

按具体项目把选定的已完成 Hypit 成片及独立素材转换为 `jy14-headless-plan/v1`。
本 Skill 不提供任意 Hypit 工程的通用导出器；SVML、SVRun 和结果对象都不是剪映计划。
已准备好的素材和时间线可直接复用，无需安装或更新 Hypit、重新生成素材。

1. 确认所选成片版本实际使用的画面、音频、文字和时间安排。需要读取 Hypit 结果时，
   按 Hypit Skill 使用公开 CLI 检查结果；不要用当前源文件猜测历史成片内容。
2. 把画面、音轨和文字分为独立轨道，时间转换为整数微秒。第一条视频轨必须连续，
   其他片段不能超过主轨总长；格式与命令见 [计划与命令](headless-plan.md)。
   Windows 全部命令用 `python`，路径反斜杠，`build` / `verify-build` 要加 `--backend native`。
3. 对可编辑文字，把 Hypit 中实际使用的 Font 资产解析为本机绝对文件路径，写进对应
   片段的 `font_path`。例如项目已确认引用 `SourceHanSerif-Bold.otf`，便直接传入该文件，
   不要先省略字体生成草稿，再通过 `set_text_font` 修改。标题与字幕可指定不同文件。
   不指定时用剪映安装目录自带的中文字体 `Resources\Font\SystemFont\zh-hans.ttf`。
4. 字体引用的相对路径按所属工程解析；`font-family` 名称和 CSS 字重不能代替字体文件。
   当前只接受单个静态 OTF/TTF（不接受 TTC/OTC 集合、可变字体或在线账号字体）。
   文件缺失或格式不支持时先解决依赖，不能静默省略参数。
5. 构建独立草稿并执行 `verify-build`；按需登记首页，再检查画面、声音、保存与冷重开。
   只有用户另行要求成片时才导出，路线见 [导出](export.md)；成片里的效果要过白名单。

文字片段示例：

```json
{"text":"直接使用原工程字体","start_us":0,"duration_us":2000000,
 "font_path":"E:\\素材\\fonts\\SourceHanSerif-Bold.otf","size":6,"y":-0.7}
```

字体会按内容哈希复制到草稿 `Resources\headless-fonts\` 并接受字节校验；原字体路径在构建
完成后仅作来源记录。未指定字体的普通新建计划保持原行为。

Windows 侧的验收范围：安装目录自带中文字体已在剪映 11.6.0.14552 界面显示、保存重开
通过；外部 OTF/TTF 目前做到构建与回读字节校验，界面排版（字号、行距、缺字、动画）仍需
实际看图核对。指定同一字体不代表两种渲染器逐像素一致。macOS 的字体验收记录见核心项目
`docs/LOCAL-FONTS.md`，不能直接当 Windows 结论。
