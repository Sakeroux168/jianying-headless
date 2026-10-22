# 交接：无头剪映 Windows 移植（windows-port 分支）


## 一、白名单（无界面导出只放行这里的效果）

由用户在剪映里确认：看会员角标，或用剪映正常导出看会不会弹会员提示。
名字之间空两个空格。确认一个，就从「待确认」挪到对应的一行。

白名单：

要会员：

待确认：叠化  摇镜  左移弹动  模糊放大  推远 II  无缝转场
待确认：轻微抖动  聚光灯  渐渐放大  多屏球形  火光包围  流光暗角
待确认：圆形蒙版  矩形蒙版  线性蒙版  镜面蒙版  星形蒙版  爱心蒙版  抖动放大

规则：只有「白名单」一行的效果可以无界面导出。
「要会员」和「待确认」里的效果，一律拒绝导出。

名字和代码里的对应：导入的效果，代码里的名字就是剪映里的名字，
  例如 transition/摇镜、effect/聚光灯（见本地效果库 catalog.json）。
  原作者自带的几个用英文：叠化=transition/dissolve，轻微抖动=effect/light-shake，
  圆形/矩形/线性/镜面/星形/爱心蒙版=mask/circle、rectangle、line、mirror、star、heart。


## 二、背景

上游 mcncarl/jianying-headless 只支持 macOS。
本分支已移植到 Windows 剪映专业版 11.6.0.14552，
并在剪映界面里逐项验收。详细用法见 docs/windows-native.md。

所有命令的入口：
python skills\yichen-jianying-edit\scripts\headless_draft.py <命令>


## 三、环境（这台电脑）

- 剪映安装：E:\全局软件\JianyingPro\11.6.0.14552
  （从注册表 Uninstall\JianyingPro 自动识别）
- 草稿目录：E:\全局软件\JianyingPro Drafts
- 首页索引：%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft\root_meta_info.json
- 效果缓存：%LOCALAPPDATA%\JianyingPro\User Data\Cache\effect\<效果ID>\<md5>
- C++ 编译器：E:\Dev\VSBuildTools（bridge\windows\build.bat 默认用它）
- 本地语音识别：E:\Dev\asr-venv（FunASR），模型在 E:\Dev\modelscope-cache
- 工作目录：E:\Dev\jianying-work（路径要短，见第六节）
- 本地效果库：E:\项目文件\本地效果库（导入的效果都在这里，不进 GitHub）


## 四、已完成（都在剪映里验收过，回读校验通过）

1. 加解密桥接：bridge/windows/jy14_codec_win.cpp
   加载本机 videoeditor.dll，调用导出的 lvve::EncryptUtils
   （enable / encrypt / decrypt(input, "{}", valid)），和 macOS 用的是同一个类。
   配套 IO：bridge/windows/runtime_io_win.py

2. 运行时：engine/headless_runtime.py
   WINDOWS 分支；时间线文件叫 draft_content.json；
   草稿目录和首页索引目录分开；路径统一写成正斜杠；校验 DLL 数字签名。
   engine/runtime_profiles.py 里用 WINDOWS_PROFILES 固定 videoeditor.dll 的哈希。

3. 新建草稿（build / publish / verify，加 --backend native）
   分段、多轨、变速、音量、字幕、关键帧。
   默认字幕字体用安装目录里的 Resources/Font/SystemFont/zh-hans.ttf。

4. 效果：
   - 6 种蒙版、叠化：资源包和 macOS 逐字节相同，直接复用。
   - 轻微抖动：Windows 版是另一种着色器包，
     用 engine/native-resource-catalog-windows.json 替换资源位置，模板不变。

5. 编辑已有草稿（edit inspect / build / publish / verify）
   生成独立副本，原草稿不动。
   Windows 草稿没有 key_value.json，代码已改为有才处理。

6. 导出成片的校验（ui-export plan / verify）
   用户在剪映导出窗口里导出，脚本检查帧数、编码、时长、完整解码。

7. 口播自动剪辑流程：
   FunASR 逐字时间戳
   → 按音量修正切点（识别的起止时间会偏 40-80 毫秒）
   → edit_plan.py compile
   → from-compiled --backend native
   → build → publish
   注意：edit_plan.py 必须有字幕轨；不要字幕时，在 from-compiled 的输出里删掉 text 轨再 build。

8. Skill 脚本读写文本统一用 UTF-8（Windows 默认是 GBK，会报错）。

9. 效果导入工具：tools/import_effects.py
   用户把要用的转场、特效拖进「效果导入」草稿（让剪映下载），退出剪映，运行：
     python tools\import_effects.py
   工具会：读草稿里的转场和画面特效 → 从剪映缓存复制资源包到本地效果库
   → 记录素材模板和参数 → 把新名字追加到第一节「待确认」
   → 生成并发布「导入测试-月日时分」草稿供用户验收。
   - 本地效果库：E:\项目文件\本地效果库（packages\ 资源包，catalog.json 登记表，work\ 测试构建）。
     位置记在 %LOCALAPPDATA%\jianying-headless\config.json；--library 可改。
     效果库不进 GitHub（剪映资源不能分发）。
   - 引擎改动：native_resources.catalog() 叠加效果库，已审查的条目优先；
     剪映保存后路径改指缓存，verify_binding 接受记录的 native_cache 位置并逐字节核对。
     转场 / 特效名字改为按目录识别；特效参数按各自 adjust_params 读取
     （计划里写去掉 effects_adjust_ 前缀的短名，例如 speed、volume）。
   - 已验收：摇镜、左移弹动、模糊放大、推远 II、无缝转场、聚光灯、渐渐放大、多屏球形、
     火光包围、流光暗角、抖动放大（11 个），保存后回读通过。

10. Openverse 免费音效（skills/yichen-jianying-edit/scripts/openverse_sfx.py）
   Windows 上已跑通：search（只搜索）和 add（搜索 → 下载 → 调音量 → 写进计划的音效轨 → 生成 credits.md 许可说明）。
   用法：口播计划 sfx 里写 {"source_time": 秒, "openverse": "英文关键词"} → compile → from-compiled
   → openverse_sfx.py add → build。商用视频加 --commercial（只用 CC0 / CC BY）。
   cdn.freesound.org 在这台电脑上较慢，偶发 SSLError；换一个新的 --work 目录重跑即可。
   尚未在剪映里试听验收。


## 五、未完成

1. 无界面导出（要做）
   - 只针对 11.6.0.14552。用户不升级剪映，要在剪映设置里关掉自动更新。
   - 必须先过第一节的白名单：导出前检查草稿里所有效果，
     有一个不在白名单就拒绝导出。
     原因：直接调引擎导出，不经过剪映导出窗口的会员检查。
   - videoeditor.dll 已经公开导出了大部分需要的接口：
     lyra::Server::instance / openSession / invokeSync
     lvve::GetDraftFromJson / GetJsonFromDraft
     Deserializer::deserialize_persistent_draft
     ProjectClient、Session::draftTransaction、lvve::Logger
     ExportClient::exportStart(shared_ptr<lyra::ExportStartReqStruct>, 回调, bool, long)
   - 还要逆向的只有一个：ExportStartReqStruct
     （大小、虚表、里面的导出参数：输出路径、宽高、帧率、码率），它的构造函数没导出。
   - 参考 macOS 实现 engine/native_export.cpp。
     偏移不能照搬：Windows 是 MSVC 编译，std::string 是 32 字节，
     shared_ptr 和 function 的布局也不同。
   - 判断导出完成：沿用 macOS 做法，捕获引擎日志里的 compile done 事件；
     成片用 native_export.py 的探测和完整解码校验；
     在 runtime_profiles.EXPORT_PROFILES 里登记 Windows 配置。
   - 做好之前，成片用 ui-export 或 export --backend windows-ffmpeg。

2. 效果导入的后续（可做）
   导入工具已经可用（见第四节第 9 条）。还没做的：
   - 滤镜、贴纸、花字、文字模板：工具只导入转场（materials.transitions）和画面特效
     （materials.video_effects），其他类型列在「暂不支持」里。
   - 导入的特效统一用「轻微抖动」的轨道和片段模板，转场按居中重叠处理；
     目前导入的 11 个都验收过，但新类型效果仍要看测试草稿确认。

3. 复合片段（嵌套时间线）：native_compound.SUPPORTED_PROFILES 里没有 Windows。
   上游在 macOS 上也只是实验阶段。

4. 付费语音识别没接：
   豆包（yichen-volc-asr）需要 VOLC_ASR_* 环境变量；Step 2.5 公开仓库里没有执行脚本。

5. 口播第一版有些接缝略卡：停顿收到了 0.03-0.22 秒。
   可以少收一点，或者在接缝加叠化。


## 六、必须遵守

- 改了 engine/ 下任何被固定哈希的文件，
  都要更新 skills/yichen-jianying-edit/scripts/headless_draft.py 里的 PINS。
- native-resource-catalog-windows.json 还固定在 native_resources.WINDOWS_OVERLAY_SHA，
  文件必须是 LF 换行。
- publish 和 edit 之前，剪映主程序和托盘都要退出（tasklist 里没有 JianyingPro.exe）。
  不要强行结束进程。
- 剪映升级后 doctor 会因为 DLL 哈希不对而拒绝运行。
  先核对新版本，再登记，不要直接改哈希放行。
- 路径长度：Windows 有 260 字符限制。
  资源目录名只用树哈希前 16 位；构建时路径超过 240 字符会报错；工作目录要放在短路径下。
  ui-export 的任务目录路径里必须有一级叫 work 的目录。
- 原草稿只读，编辑一律生成独立副本。发布前备份 root_meta_info.json。
- 许可：上游原创部分只限个人学习和非商业使用。
