# yichen-jianying-edit

这是 Jianying Headless 的独立 Agent Skill：说明、口播计划编译器和固定哈希的调用入口。
它不包含剪映引擎，也不把核心源码复制进安装后的 Skill 目录。

本分支（`windows-port`）只面向 Windows 剪映专业版 **11.6.0.14552**。上游 macOS 实现
仍在同一份引擎里，但这里只写 Windows 可用的路径，macOS 相关内容留给上游文档。

## 使用方式

这份 Skill 不安装、不复制、不设环境变量，就放在核心仓库里直接用：
`E:\项目文件\剪映\jianying-headless\skills\yichen-jianying-edit\`。
让 AI 读仓库里的这份 `SKILL.md` 即可，脚本也按这个位置调用。

1. 核心仓库：`E:\项目文件\剪映\jianying-headless`（分支 `windows-port`）。
2. 在该仓库根目录编译桥接并自检：

```bat
bridge\windows\build.bat
python skills\yichen-jianying-edit\scripts\headless_draft.py doctor --backend native
```

3. 不要复制到 `C:\Users\1\.claude\skills\`，也不要 `setx JIANYING_HEADLESS_ROOT`。
   只有以后改用 Claude Code、需要把这套说明单独挂到宿主技能目录时，才复制整个
   目录并设置该环境变量指向仓库根。现在不需要。

Skill 会校验核心组件的固定哈希；改过
`engine\` 下任何被固定的文件后必须同步 `scripts\headless_draft.py` 里的 `PINS`，
不能静默接受任意其他版本。

## 运行前提

- 剪映专业版 Windows 11.6.0.14552（版本不符会被拒绝，剪映设置里关掉自动更新）。
- Python 3.9+、FFmpeg / ffprobe 在 PATH 中。
- Visual Studio Build Tools（C++ 工作负载），用于编译 `bridge\windows`。
- 工作目录放在短路径下：Windows 有 260 字符上限，草稿文件路径须少于 240 字符。

## 可选依赖

- 转写：本机 FunASR 环境 `E:\Dev\asr-venv`（`paraformer-zh`，标点用 `ct-punc-c`），
  模型缓存 `E:\Dev\modelscope-cache`。`scripts\asr_once.py` 只是去重包装器，需要另行
  提供执行器（`YICHEN_ASR_EXECUTOR`），本发行不含执行器与凭据。没有转写依赖时直接
  使用用户提供的逐字时间戳计划。
- 自动音效：`openverse_sfx.py` 联网访问 Openverse 与 Freesound，音效保留各自 CC 许可，
  CC BY-NC 禁止商用。不需要就不运行；草稿 build/publish 不联网。

详细操作见 [SKILL.md](SKILL.md)。本 Skill 不授权自动上传视频、公开草稿、购买资源或将
剪映官方文件重新分发。来源与许可边界见
[dependencies-and-notices.md](references/dependencies-and-notices.md)。

## 许可

原创部分采用[个人学习和非商业使用条款](LICENSE)，商业用途须取得作者明确书面授权。
第三方内容保留各自原许可证；本 Skill 不授予剪映程序库、账号、素材或服务的使用权。
