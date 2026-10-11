# uwuAOSP 17.0 · OnePlus 6 系统稳定性与第三方 ROM 功能对齐

审查日期：2026-10-11。本文是**功能候选与源码验证矩阵**，不等于功能全部实现，也不代表 Android 17 ROM 已内置所有后端。

## 参考基线

- [crDroid 17.x 功能清单](https://github.com/crdroidandroid/crdroid_features/tree/17.0)：截至 2026-10-02 的全 ROM 功能列表，部分功能有设备限制，**不代表 OnePlus 6 已适配该版本**。
- [Evolution X 官方功能清单](https://evolution-x.org/features)：显示状态栏时钟日期、QS 卡片与亮度、通知、锁屏等功能。具体机型支持需另核对。
- [LineageOS OnePlus SDM845 设备树](https://github.com/LineageOS/android_device_oneplus_sdm845-common/tree/lineage-24.0)：验证 OnePlus 原厂三段拨杆、Doze/传感器、LiveDisplay、Touch HAL、Dirac 等后端路径的参考；不能未经 HAL/VINTF/SELinux 验证直接移植。
- 自己的源代码：`uwu-17.0` 下的 `frameworks_base`、`Settings`、`uwuSettingsExt`、`uwuSystemUI`、`Launcher3`。

只对**源代码中实证定位到的实现**标注“已存在”；未遍历完整设备镜像的项目一律为“待确认”，不可把菜单不见等同于功能不存在。

## P0：稳定性优先（必须先于叠加特性）

| 检查点 | 具体风险与修复 | 目前状态 / 对应 PR |
|---|---|---|
| SystemUI 主线程跨进程查询 | MomentArc 手势广播在主线程执行；展开菜单同步查询最多约 12 个应用/快捷方式图标，可阻塞状态栏 UI | `uwuSystemUI PR #1`：单线程有界异步图标加载、销毁后失效、积压触摸点限流。待 APK 编译及 ANR 压测 |
| 秒钟 Tick 生命周期 | Clock 每秒定时回调直接引用可能在 detach 时清空的 Handler | `frameworks_base PR #6`：主线程秒级定时、暂停后台更新、解挂载时取消回调。待 SystemUI 编译及电耗验证 |
| 手势提示条失效 | SystemUI 绘制与 SettingsExt 开关依赖异步同步的 NAVIGATION_MODE | `frameworks_base PR #5`、`uwuSettingsExt PR #2`。只隐藏图形，不修改 gesture/insets |
| 刘海提示条越界 | Dual Shade 教育气泡顶部偏移方式可能进入显示切口 | `frameworks_base PR #3`；需要验证多窗口、旋转、各种 DPI |
| 高 DPI 时钟与标题 | 物理 499DPI 下 dp 宽度收紧；固定时钟放大易遮挡相邻组件 | `frameworks_base PR #4`；需要验收安全区 |
| 现场崩溃归因 | 目前缺少原始 SystemUI Java Exception/Native tombstone/ANR trace，不能断言已定位全部故障 | 真机复核排最后：先完成源码风险消减，再集中获取崩溃栈；绝不循环重启 SystemUI 掩盖故障 |

### 稳定性护栏

- 不加入常驻巡检守护进程，也不通过不停 `pkill com.android.systemui` 伪造稳定。
- 不在 SystemUI UI 线程进行 PackageManager/LauncherApps 大量跨进程访问、磁盘扫描或阻塞等待。
- 网络速率/电量统计等 UI 可选功能仅在可见时刷新，屏幕关闭后取消定时；功能关闭时不运行采样。
- 每个 PR 独立启停，完整 APK 必须使用 ROM 兼容签名与 Mountify TMPFS 单 ZIP；上游 OTA 改变系统哈希时停用热补丁。
- 崩溃统计与审计输出不记录帐号、应用内容、通知文本、个人资料或其它隐私内容。
- 全量编译 + 真机 499DPI 横/竖屏 + 长运营商名 + 双下拉 + 语言/字号 + 屏幕关闭/唤醒 + 30 分钟压力操作通过前，保持 Draft。

## 功能对齐优先级

| 分类 | crDroid/Evolution X 参考功能 | uwuAOSP 源码状态 | 我们的决策 |
|---|---|---|---|
| 状态栏 | 时钟日期/秒钟格式、图标控制 | Clock 已有 `clock_seconds` 与 Hms/hms；默认隐藏秒钟 | P1：打开默认秒钟、尊重系统 12/24h、屏灭停时钟，已提交 |
| 状态栏 | 快捷下拉、状态栏亮度滑动 | 暂未验证当前双下拉手势与这两项能正确共存 | P2：先修遮挡/布局，避免叠加手势冲突 |
| 状态栏 | 网络速率指示 | 当前完整状态未知 | P2：需低频、屏亮且可见时刷新，禁止后台常驻高频采样 |
| 快捷设置 | 卡片行列、亮度条样式/位置、haptic | 两套旧/新 shade 布局并存，已观察明显顶部空间问题 | P1：先统一安全区和标题区域，再引入有限可配样式 |
| 通知 | 抬头通知、隐私指标、紧凑模式 | 基础 AOSP 通知系统与额外 ROM 功能仍需逐路径确认 | P2：优先可用性，无强制系统级隐私指标开关 |
| 锁屏 | 充电电流/预计时间、媒体封面、字体 | 未证明机型充电 HAL 和锁屏文字布局兼容 | P2：复用现有 `BatteryManager`/AOSP 状态，不常驻读取 sysfs |
| 设备按键 | 音量键播控/手电筒、三段拨杆 | OnePlus SDM845 社区设备树有 KeyHandler；当前 ROM 集成状态未知 | P2：先实际服务接入，回退安全；不能丢三段拨杆静音动作 |
| OnePlus 显示 | LiveDisplay、P3 和色温 | Kernel 面板具备元数据，社区有显示 HAL；Android 17 色彩链路未验证 | P2：匹配原始 HAL 与 overlay，不虚构 HDR10 |
| OnePlus 传感器 | 抬起唤醒、口袋、双击亮屏 | 设备树有 OnePlusDoze 与传感器线索 | P2：按 sensor availability 动态显示，验证深睡耗电 |
| OnePlus 音效 | Dirac | 社区设备树有 OnePlusDiracGef，当前 ROM 实际音效链未知 | P3：不能盲开以免与 V4A/AudioEffect 冲突 |
| 物理 VRR | 30/48/60/90/120Hz 等 | OP6 SOFEF00_M DTS 仅 60Hz | 不制造虚假的高刷/VRR 模式 |
| UDFPS | 屏下指纹动画/手势 | OnePlus 6 指纹为背部，不具备 UDFPS 面板 | 不纳入计划 |
| 安全与隐私 | 绕开截图安全标志、隐藏应用检测 | 第三方 ROM 可选但会降低安全性 | 本项目不默认添加或开启 |

## 差距不等于直接移植

原则是**对齐成熟交互体验，不复刻每一项开关**。对其它 ROM 的功能源码做 License/依赖核对后才可移植：大部分 CRDroid 特性跨 SystemUI + Settings + Framework + 设备树，直接复制一个 Settings XML 只会出现空白或崩溃。

## 交付验收清单（作为最终构建门禁）

1. 全部必要源码已提交到各自 fork，分支与依赖 SHA 固定，静态 CI 全部通过。
2. Android 17 完整编译，关键 SystemUI/Settings 签名与运行 ROM 保持兼容，不能被替换模块破坏 privileged app 权限。
3. 真机压力场景：连续 100 次双下拉/屏幕开关/状态栏展开，Moment Arc 连续 100 次展开取消，应用安装卸载期间快捷入口仍可响应；记录最大 UI 卡顿和原始 ANR。
4. 秒钟只在屏亮可见时刷新，不创建额外常驻后台进程；强制停用后的行为回归标准 AOSP。
5. 每项 OEM 功能先通过 HAL 和 SELinux 检测，验证录音、通话、GPS、手环、蓝牙和深睡不倒退。
6. Mountify TMPFS 内存、数据分区占用、上游 OTA 兼容保护和可回退路径复核。
7. **最后一阶段** 再请求设备探针/日志，集中校验仍未证实的 HAL/ANR 信息，避免重复干扰用户。
