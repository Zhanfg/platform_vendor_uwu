# OnePlus 6 · uwuAOSP 17 的 KernelSU 静态 UI 修复架构

基线：OnePlus 6 (enchilada)、uwuAOSP Android 17 / API 37、build `CP2A.260605.016`，DPI 420。
开发规范：最终只能是**一个 KernelSU 模块**，名称 `uwuAOSP hotfix vX.Y`，ID 固定
`uwu-ui-live-hotfix`；不以 LSP/LSPosed 常驻 Java 方法 Hook 为主方案，不修改 A/B 系统槽位，
不因额外 UI 组件增加长驻后台服务。

## 经过原始 ROM 文件校验的签名事实

原始样本来自用户提供的 `01_UI_Reference.tar.gz.part_aa` 至 `ag` 七段归档，
并非从 GitHub 推断：

- `/system/system_ext/priv-app/SystemUI/SystemUI.apk` SHA256
  `47e4e849e99a695b3c698566fb451cf3cd671ddb17f3e5844d15b2b35188f841`。
- `/system/system_ext/priv-app/Settings/Settings.apk` SHA256
  `16b8902482965ce7246e2c2e20bb29b627dbfff7472f9bd90e51ac47adf3ae98`。
- 两者的 `META-INF/CERT.RSA` X.509 证书 SHA256 一致：
  `FE3D64FEDE78183BB479DD684F03A1B3FAE475B6742E9CBA0880A9CA59A91E44`。
- 证书生效日期为 2026-03-29；与网上常见 2008 年 AOSP 证书**不能仅凭同样的
  Android 发行者字段认定兼容**。
- 此仓库仅包含公开证书指纹，**不包含、不得上传任何签名私钥**。

### 不可绕过的约束

APK v2/v3 验证覆盖修改后的 APK 内容；修改 ZIP 中任何 DEX、resources.arsc、XML
或 ZIP 元数据都会使原 APK 的内容签名失效，哪怕只改变一个字节。
`bsdiff` / `xdelta` 只减小下载的差量文件，最终仍需合法签名的完整 APK；
KernelSU OverlayFS / Mountify TMPFS 也不能按 ZIP 条目或几个字节做有效的只读静态替换。
`APK 原位补丁 + 保留旧签名` **不是可部署方案**。

绝不能以删除签名检查、清除 `/data/system/packages.xml`、重签 `SystemUI.apk` 为另一
任意私钥或全局修改 `PackageManager` 验证逻辑代替合规构建。

## 同一个 KSU 模块下的两个清晰通道

| 类别 | 推荐实施 | 启动与性能 | 允许的改动 | 不能解决 |
|---|---|---|---|---|
| A：静态 UI/MD3E 资源 | 一至数个小型 RRO APK，KSU+Mountify 作为 `system_ext/overlay` 预装，Boot 时由 OMS/idmap2 映射 | APK 通常 KB 级；系统自带的资源查找机制，无每帧 Hook | 正确 overlayable 资源的尺寸、颜色、字形、圆角、间距、部分布局 | Kotlin/Java 控制流、ANR 根因、触控事件派发 |
| B：配置及系统能力 | 原生 `SettingsProvider`、兼容 XML、只写一次的 Boot 脚本，KSU 动作手动重试 | 不常驻、不每秒轮询 | 经源代码实证已有控制器的配置，420 DPI 单次设置 | 尚未由代码实现的开关、服务逻辑 |
| C：SystemUI 内部代码 | 在 `platform_frameworks_base` 修复原源码，编译新的 SystemUI APK，**使用与运行 ROM 相同的平台签名链** | 无额外运行时框架，但要完整替换经签名的 APK 文件 | MomentArc IPC、秒钟 Handler、手势绘制条件等代码逻辑 | 在无原始签名能力时不能按 A、B 方式交付 |
| D：一次性原生运行时注入 | 仅技术预研：把变更限制在 SystemUI 进程启动时做一次方法替换 | 不等于零 Hook；仍涉及 ART 版本绑定、Zygote/SELinux/触发顺序、崩溃风险 | 理论上修改运行中的方法，不改 APK | 不满足当前“极端稳定、无 LSP 一类注入”的默认交付条件 |

C 类的未满足条件是**是否拥有匹配签名的产物/签名服务**，而不是 ZIP 压缩率。
不能从证书、公钥或 APK 签名块反推出私钥；不能夸称用户已有相同密钥。

## 必须纳入同一套发布清单的功能（含 MD3E）

| 目标 | 实际受影响组件 | 当前修复级别 | 部署策略 |
|---|---|---|---|
| 小白条视觉隐藏 | SystemUI `NavigationHandle`、QuickSwitch 旋转态 | 已有 SystemUI 源码 PR #7；独立 `v0.4` RRO 已构建但真机 idmap 未证实 | A：视觉绘制尺寸资源；不要缩减导航高度/手势 inset |
| 返回/桌面/最近任务 | SystemUI 以及 Launcher3QuickStep/WM Shell | 尚不能断言所有手势故障根因 | 先排除触控覆盖、主线程 ANR；不得停用导航功能 |
| MomentArc 卡顿 | **实际集成** `frameworks_base/packages/SystemUI/moment/arc` | PR #7 把 Icon IPC 移至后台、加状态缓存与回收保护 | C（需要合法同签名 SystemUI 构建）；不能把独立 uwuSystemUI 插件 PR 当成运行时修复 |
| 状态栏秒钟 | SystemUI `Clock.java` | PR #7 有 Handler 生命周期代码修改 | C；旧 APK 不宜仅强制开启未经修复的 Tick |
| Settings Material 3 Expressive | Settings UI 控制器 + 现有 `SettingsOverlayUwU.apk` | 资源存在不代表当前正确渲染 | 能由 XML 解决的用 A；需行为修复的列 C，禁用伪开关 |
| Quick Settings + Shade MD3E | SystemUI ShadeScene/QuickSettingsScene 以及 `SystemUI...rro` | 未完成端到端运行时验收 | 资源型走 A；场景切换、事件处理走 C |
| Launcher/抽屉/最近任务 MD3E | Launcher3QuickStep（非 SystemUI 同签名） | 其他独立 PR，未产出对应的同签名 APK | 资源型 A；执行流修改必须核对**Launcher 自己的证书** |
| 三段式拨杆、LiveDisplay、Doze | Device tree / OnePlus HAL / 服务端 | 有上游参考实现，但当前 ROM 后端可用性未证实 | 保留 LOS HAL ABI；先实现后端再显示 UI，不做假的配置项 |
| 固定 DPI 420 | WindowManager/用户显式设置 | v0.3/v0.4 的一次性受控读写，不是内核属性 | 维持 B；已 420 完全不写，Binder 失败不猜、不循环 |

## 下一版成品必须通过的发布门禁

1. KSU 模块始终是**一个 ID** `uwu-ui-live-hotfix`；后续版本覆盖升级，不并排安装多套 UI 热修复。
2. 无 LSP Hooks，无对所有 App 的 Zygote 注入，无 SystemUI 守护进程/自动强杀重启。
3. 每个 RRO 经 `aapt2`/ `apksigner` 静态测试后还必须经真实 Android 17
   `cmd overlay list`、`idmap2` 和生效资源值核对；未通过则不声明“白条已修复”。
4. 包含字节码修改的 APK 必须由构建器 `apksigner verify --min-sdk-version 37 --print-certs`
   验证与原始证书完全相同；仅有签名证书摘要相同也无法代替签名本身的有效性。
5. ROM build ID + 原始 APK SHA 双锁。OTA 变更时在 Mountify 挂载**之前**
   停止旧资源补丁，不能只在安装时检测。
6. 实机连续滑动、左右返回、最近任务、屏幕关闭/唤醒、旋转和输入法测试，
   并统计真实 ANR/Java exception，而不是静态 CI 成功即宣布系统稳定。
7. 所有 MD3E 修复须按 Framework/Settings/SystemUI/Launcher/uwuSettingsExt
   分项列出资源/行为边界，不得遗漏先前任务。

参考：
- Android APK v2+ 验证：https://source.android.com/docs/security/features/apksigning
- Android RRO：https://source.android.com/docs/core/runtime/rros
- 真实集成的 SystemUI 修复：https://github.com/Zhanfg/platform_frameworks_base/pull/7
- 已构建的白条 RRO：https://github.com/Zhanfg/platform_vendor_uwu/pull/10

**最终结论**：在“无原签名能力 + 不改 Android 包验证链 + 不运行任何针对 SystemUI 的代码注入”
三项约束同时成立时，只能安全交付资源和配置级 KSU 修复，不能承诺交付
任意 SystemUI DEX 方法修改。这是 APK 完整性机制的边界，不是压缩/挂载技巧所能突破的。
