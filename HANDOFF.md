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

2. 更多效果（可做）
   第一节里除了叠化、6 种蒙版、轻微抖动，其余 10 个效果资源已在本机缓存，
   但代码还不认识，build 会拒绝。
   效果 ID：
     摇镜 7305969268259033609
     左移弹动 7312690473108247078
     模糊放大 7301280654015074842
     推远II 7360987817066893862
     无缝转场 7695311799868181822
     聚光灯 7399493048838786344
     渐渐放大 7399496101104995584
     多屏球形 7548426771805343003
     火光包围 7399492277615332623
     流光暗角 7665341904963554584
   它们的参数模板在解密快照里：
     E:\Dev\jianying-work\tests\inspect-220702\社保福利-无头剪辑v1.json
     （materials.transitions 和 materials.video_effects）
   新增一个效果要做：
   - 资源条目：files = native_resources.tree_manifest(缓存目录)，
     tree_sha256 = manifest_hash(files)。
     结构参考 native-resource-catalog.json 里的 transition/dissolve（只有 material）
     和 effect/light-shake（material、usage、track_template、segment_template）。
     现在的 Windows 覆盖文件只能改已有的条目，新增条目要扩展 native_resources.catalog() 的合并逻辑。
   - 登记名字：转场加到 native_effects.TRANSITIONS，
     画面特效加到 native_visual_effects.NAMES['effect']，
     并核对参数和 adjust_params 的对应关系。
   - 要会员的效果不能加（不解锁、不伪造授权）。
   - 每个效果都要发布测试草稿，让用户在剪映里看效果、保存、重开，再用 verify 回读。
   - 建议先做一个「批量登记」工具，别一个个手写：
     用户在剪映里把一批效果拖进同一个草稿（让剪映下载到缓存）
     → 工具解密这个草稿，读出里面所有转场 / 特效 / 滤镜的素材模板和缓存目录
     → 自动生成资源条目、计算文件指纹、登记名字
     → 自动生成一个包含这批效果的测试草稿，用户一次看完。
     新效果自动进「待确认」，用户确认免费后才挪进白名单。
   - 用户决定：按需登记，用到哪个加哪个；不批量下载剪映的全部效果。
     用户流程：在任意草稿里拖入要用的效果 → 退出剪映 → 告诉你草稿名和效果名
     → 你登记并生成测试草稿 → 用户验收后写进白名单或「要会员」。

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
