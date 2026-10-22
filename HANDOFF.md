# 交接：无头剪映 Windows 移植（windows-port 分支）

上游 `mcncarl/jianying-headless` 只支持 macOS。本分支已把它移植到 Windows 剪映专业版
**11.6.0.14552**，并在剪映界面里逐项验收。详细用法见 `docs/windows-native.md`。

## 环境（这台机器）

| 项目 | 位置 |
| --- | --- |
| 剪映安装 | `E:\全局软件\JianyingPro\11.6.0.14552`（注册表 Uninstall\JianyingPro 自动识别） |
| 草稿目录（自定义） | `E:\全局软件\JianyingPro Drafts` |
| 首页索引 | `%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft\root_meta_info.json` |
| 效果缓存 | `%LOCALAPPDATA%\JianyingPro\User Data\Cache\effect\<effect_id>\<md5>` |
| MSVC | `E:\Dev\VSBuildTools`（`bridge\windows\build.bat` 默认用它） |
| 本地 ASR | `E:\Dev\asr-venv`（FunASR），模型 `E:\Dev\modelscope-cache` |
| 工作目录 | `E:\Dev\jianying-work`（路径要短，见下方限制） |

入口统一是 `python skills\yichen-jianying-edit\scripts\headless_draft.py <命令>`。

## 已完成（均在剪映 UI 中验收并回读通过）

1. **加解密桥接** `bridge/windows/jy14_codec_win.cpp`：LoadLibrary 本机 `videoeditor.dll`，调用导出的
   `lvve::EncryptUtils::enable/encrypt/decrypt(input, "{}", valid)`，与 macOS 桥接同一个类。
   IO 层 `bridge/windows/runtime_io_win.py`（tasklist 检查编辑器、临时目录传明文、msvcrt 锁）。
2. **运行时** `engine/headless_runtime.py`：`WINDOWS` 分支、`TIMELINE_FILE=draft_content.json`、
   `DRAFT_ROOT` 与 `INDEX_ROOT` 分离、`native_path()` 统一正斜杠、Authenticode 校验。
   `engine/runtime_profiles.py`：`WINDOWS_PROFILES` 固定 `videoeditor.dll` 的 SHA-256；
   Windows 配置已加入 SCHEMA_RUNTIMES / SAVE_UPGRADES(185/187→189) / RESOURCE / EDIT / UI_EXPORT。
3. **新建草稿**（`build/publish/verify --backend native`）：分段、多轨、变速、音量、字幕、关键帧；
   默认字体改用安装目录 `Resources/Font/SystemFont/zh-hans.ttf`。
4. **效果**：6 种蒙版、叠化（与 mac 采集逐字节相同，直接复用目录）；轻微抖动（Windows 是 GLSL 包，
   由 `engine/native-resource-catalog-windows.json` 覆盖 source/tree/files，模板不变）。
5. **编辑已有草稿副本**（`edit inspect/build/publish/verify`）：Windows 草稿无 `key_value.json`，
   改为存在才维护；来源草稿允许 11.5.3/11.6.0 保存（`WINDOWS_PRIOR_APPS`）。
6. **UI 导出验收**（`ui-export plan/verify`）：用户在剪映导出窗口导出，脚本校验成片。
7. **口播流程**：FunASR 逐字时间戳 → 按音量修正切点（ASR 起止会偏 40–80ms）→
   `edit_plan.py compile` → `from-compiled --backend native` → build → publish。
   `edit_plan.py` 要求字幕轨；不要字幕时在 from-compiled 输出里删掉 text 轨再 build。
8. Skill 脚本文本读写统一 UTF-8（Windows 默认 GBK）。

## 未完成

1. **更多效果（可做）**。下列 10 个效果的资源已在本机缓存，但代码不认识，`build` 会拒绝：
   转场：摇镜 7305969268259033609、左移弹动 7312690473108247078、模糊放大 7301280654015074842、
   推远 II 7360987817066893862、无缝转场 7695311799868181822；
   画面特效：聚光灯 7399493048838786344、渐渐放大 7399496101104995584、多屏球形 7548426771805343003、
   火光包围 7399492277615332623、流光暗角 7665341904963554584。
   它们的原生素材/片段/轨道模板在解密快照
   `E:\Dev\jianying-work\tests\inspect-220702\社保福利-无头剪辑v1.json`（materials.transitions / video_effects）。
   新增一个效果需要：
   - 资源条目：`files = native_resources.tree_manifest(缓存目录)`，`tree_sha256 = manifest_hash(files)`；
     参考 `native-resource-catalog.json` 中 `transition/dissolve`（只有 material）与
     `effect/light-shake`（material + usage + track_template + segment_template）的结构。
     目前 Windows 覆盖文件只能**修改已有键**，新增键要扩展 `native_resources.catalog()` 的合并逻辑。
   - 名称登记：转场加到 `native_effects.TRANSITIONS`，画面特效加到 `native_visual_effects.NAMES['effect']`，
     并核对 `native_visual_effects` 中 params ↔ `adjust_params` 的映射与校验。
   - 收费：草稿数据里没有付费字段，须在剪映界面确认有无会员/付费角标；`usage` 记录观察结果，
     付费效果不得加入（不解锁、不伪造授权）。
   - 每个效果都要发布测试草稿，由用户在剪映里看效果、保存、冷重开，再 `verify` 回读。
2. **复合片段（嵌套时间线）**：`native_compound.SUPPORTED_PROFILES` 未含 Windows；上游在 mac 上也仅实验性。
3. **无界面原生导出：要做。** 前提与要求：
   - 只针对固定版本 11.6.0.14552（用户不升级剪映，需在剪映设置里关闭自动更新）。
   - **必须有白名单闸门**：直接调用引擎导出不会经过剪映导出窗口的会员检查，所以导出前逐个检查草稿里
     所有效果/素材资源，只要有一个不在下方「白名单」里就拒绝导出。白名单只收用户确认免费的效果。
   - 已查到 `videoeditor.dll` 公开导出了大部分所需接口：`lyra::Server::instance/openSession/invokeSync`、
     `lvve::GetDraftFromJson/GetJsonFromDraft`、`Deserializer::deserialize_persistent_draft`、`ProjectClient`、
     `Session::draftTransaction`、`lvve::Logger`，以及
     `ExportClient::exportStart(shared_ptr<lyra::ExportStartReqStruct>, const function<void(shared_ptr<RespStruct>)>&, bool, long)`。
   - 剩下要逆向的：`ExportStartReqStruct` 的大小、虚表和内部 ExportConfig 字段布局（输出路径、宽高、帧率、码率），
     它的构造函数没有导出。参考 macOS 实现 `engine/native_export.cpp`（偏移和 libc++ 布局不能照搬；
     Windows 是 MSVC：`std::string` 32 字节、`shared_ptr`/`function` 布局也不同）。
   - 完成判定沿用 mac 的做法：捕获引擎日志中的 compile done 事件，成片再用 `native_export.py`
     的探测与完整解码校验；在 `runtime_profiles.EXPORT_PROFILES` 里登记 Windows 配置。
   - 在此之前，成片走 `ui-export` 或 `export --backend windows-ffmpeg`。
4. **付费 ASR 未接**（豆包 `yichen-volc-asr` 需要 `VOLC_ASR_*` 环境变量；Step 2.5 公开仓库无执行器）。
5. 口播 v1 的部分接缝有轻微跳帧感：停顿收到 0.03–0.22s；可放宽收紧幅度或在接缝加叠化。

## 白名单（无界面导出只放行这里的效果）

草稿数据里没有付费标记，以下由用户在剪映里确认（看会员角标 / 用剪映正常导出不弹会员提示）。

白名单：（待用户确认后填写）

待确认：叠化  圆形蒙版  矩形蒙版  线性蒙版  镜面蒙版  星形蒙版  爱心蒙版  轻微抖动
　　　  摇镜  左移弹动  模糊放大  推远 II  无缝转场  聚光灯  渐渐放大  多屏球形  火光包围  流光暗角

## 必须遵守

- 改了 `engine/` 下任何被固定的文件，都要更新 `skills/.../headless_draft.py` 的 `PINS`；
  `native-resource-catalog-windows.json` 还固定在 `native_resources.WINDOWS_OVERLAY_SHA`，文件须为 LF 换行。
- publish / edit 前剪映主程序和托盘都要退出（`JianyingPro.exe` 不在 tasklist），不要强杀进程。
- 剪映升级后 `doctor` 会因 DLL 哈希拒绝；核对新版本行为后再登记，不要直接改哈希放行。
- MAX_PATH：资源目录在 Windows 用树哈希前 16 位；构建对 ≥240 字符的路径报错；工作目录放短路径。
  `ui-export` 的任务目录路径须含一级名为 `work` 的目录。
- 原草稿只读；编辑一律生成独立副本。发布前备份 `root_meta_info.json`。
- 许可：上游原创部分仅限个人学习和非商业使用。
