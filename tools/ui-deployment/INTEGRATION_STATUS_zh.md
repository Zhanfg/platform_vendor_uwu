# OnePlus 6 uwuAOSP Android 17 — 原生 KernelSU 系统界面整合审查

2026-10-11 | 工程状态：整合源码和打包门禁完成；**实际 APK 编译、原平台签名和真机验证未完成**。

## 唯一技术路线

- 一个 KernelSU 模块：`uwu-ui-live-hotfix`，显示名称 `uwuAOSP hotfix v0.7`。
- 唯一挂载后端：Mountify TMPFS/OverlayFS 的 `system/` 文件树。
- 不使用 LSPosed/LSP Hook、不加载旧 PR #11 的 Xposed APK；不修改 system 分区、boot、vbmeta 或 SELinux 策略。
- 仅覆盖五个**真的改变、已编译、与各自原 ROM 签名相同**的特权/系统 APK。安装时不携带备份 APK 和重复副本。保留 upstream A/B OTA，基线变化即停止挂载。
- 已完成的 RRO v0.4 **不作为 SystemUI 逻辑崩溃修复**，不得取代原生 SystemUI 构建。
- DPI 以用户明确指定的 **420** 为目标；失败不重试循环，已经是 420 就不写。默认不增加常驻监听器。

## 这轮已整合的五个真实源码提交

| 组件 | 编译分支与 SHA | 合并来源 | 实质修改 | 独立构建/真机 |
|---|---|---|---|---|
| SystemUI | `Zhanfg/platform_frameworks_base@5f78233070530b853fcc6501776f19d00393ca63` | PR #1,#2,#3,#4,#7 → 统一 PR #8 | Moment Arc 的同步 LauncherApps IPC、窗口超时、秒针 Handler 生命周期、白条绘制判断、双面板调用宽度/顶部安全区/刘海提示 | 待验证 |
| Settings | `Zhanfg/platform_packages_apps_Settings@c3cfe7b63318bb17f6e8e542f4a7e33e1b38f94d` | PR #1–3 → 统一 PR #4 | MD3E 首页动效、原生存储/内存设置、真实 HDR/刷新率能力展示 | 待验证 |
| Launcher3 | `Zhanfg/platform_packages_apps_Launcher3@601c7068193663506e154f1333f7dcc070f7fb49` | PR #1–3 → 统一 PR #4 | 弹窗进入抽屉、设置页过渡、动态色提示组件 | 待验证 |
| ThemePicker | `Zhanfg/platform_packages_apps_ThemePicker@0859e053a7de17180b4e8168705732b46515b787` | PR #1 | 原生主题色盘可访问性文本与 MD3E 内容描述 | 待验证；独立于 SystemUI 签名 |
| uwuSettingsExt | `Zhanfg/platform_packages_apps_uwuSettingsExt@289a20b44e68ce8b3836335b32793bbfd243213c` | PR #1–2 → 统一 PR #3 | 响应式 Header/手势提示条开关状态同步 | 待验证 |

这些 PR 的 Python 静态 CI 已通过，**不等于 Android 17 Kotlin/Java/Compose/aapt2 全量编译成功**。多组件替换只有在匹配的五个签名 APK 都齐全时才生成 ZIP，避免界面风格分裂和错版资源。

## MD3E / Material 3 Expressive 完整性门禁

目标：Google MD3E 组件和动态色使用规范；在当前类 AOSP 17 系统保留既有优秀交互，并吸收 ColorOS 17 风格的圆润、克制动效、低阴影、清晰层级，**不是把 ColorOS 专有 COUI 服务强行植入 AOSP**。

| 区域 | 当前证据/进度 | 仍需工作 |
|---|---|---|
| SystemUI 状态栏/秒钟 | 统一源码包含新 Clock 生命周期补丁 | 全状态切换、420 DPI、12/24 小时、刘海和运营商字符压力测试 |
| Quick Settings 双下拉 | 统一源码包含尺寸、头部安全区、DualShade tooltip 修补 | scene/Compose 新旧容器互斥及实际动画转场、无截断 |
| 通知/锁屏 | AOSP/uwuAOSP 功能既存，但未完整逐页对照 | 动态色、对比度、键盘和 media、隐私指示、无重叠 |
| Settings 首页与子页面 | 首页 PR 已纳入 + 原生入口恢复 | 所有二级/三级页面卡片分组、Switch 禁止白描边/亮边、列表图标层级、搜索可达性 |
| Launcher/设置内页 | 当前有 3 个对应补丁 | 快速滚动、预测性返回、动画时长统一、字体 1.3x 及 RTL |
| ThemePicker/uwuPrism/uwuCompose | ROM101 内确有 ThemePicker APK 及 uwuPrism 产物；已比对原始哈希与两套签名域 | ThemePicker 纳入五 APK 原生门禁；uwuPrism 保持原版、安装前比对产品 RRO 哈希；Monet/Compose 动态色仍需继续审计，不能宣称 100% MD3E |
| OnePlus 原生服务 | LOS/SDM845 已有 KeyHandler、OnePlusDoze、LiveDisplay/Touch/Dirac 参考 | ROM 是否安装 HAL、SELinux 与具体驱动需单独验证；不虚构开关 |
| Accessibility/稳定性 | 禁止状态栏/顶部安全区重叠；注意低端旧 SoC 功耗 | 420dpi/大字/夜间/横屏/RTL/多窗口、SystemUI 100 次连续操作与休眠恢复 |

## 后续稳定性与 MD3E 直接修复（原生 KSU 增量）

基于整合 PR #15 的原生挂载链，增量 PR #16 已完成：

- 打包前增加 `aapt2 dump packagename` 双侧检查：即使 APK 使用正确证书，
  只要替换包名与原系统组件不同，立刻拒绝；SystemUI 与 Settings 还要符合
  已知包名常量。避免把有效签名但错误功能的 APK 放进核心系统目录。
- 打包脚本修复临时 ZIP 文件名中 `# OnePlus 6 uwuAOSP Android 17 — 原生 KernelSU 系统界面整合审查

2026-10-11 | 工程状态：整合源码和打包门禁完成；**实际 APK 编译、原平台签名和真机验证未完成**。

## 唯一技术路线

- 一个 KernelSU 模块：`uwu-ui-live-hotfix`，显示名称 `uwuAOSP hotfix v0.7`。
- 唯一挂载后端：Mountify TMPFS/OverlayFS 的 `system/` 文件树。
- 不使用 LSPosed/LSP Hook、不加载旧 PR #11 的 Xposed APK；不修改 system 分区、boot、vbmeta 或 SELinux 策略。
- 仅覆盖五个**真的改变、已编译、与各自原 ROM 签名相同**的特权/系统 APK。安装时不携带备份 APK 和重复副本。保留 upstream A/B OTA，基线变化即停止挂载。
- 已完成的 RRO v0.4 **不作为 SystemUI 逻辑崩溃修复**，不得取代原生 SystemUI 构建。
- DPI 以用户明确指定的 **420** 为目标；失败不重试循环，已经是 420 就不写。默认不增加常驻监听器。

## 这轮已整合的五个真实源码提交

| 组件 | 编译分支与 SHA | 合并来源 | 实质修改 | 独立构建/真机 |
|---|---|---|---|---|
| SystemUI | `Zhanfg/platform_frameworks_base@5f78233070530b853fcc6501776f19d00393ca63` | PR #1,#2,#3,#4,#7 → 统一 PR #8 | Moment Arc 的同步 LauncherApps IPC、窗口超时、秒针 Handler 生命周期、白条绘制判断、双面板调用宽度/顶部安全区/刘海提示 | 待验证 |
| Settings | `Zhanfg/platform_packages_apps_Settings@c3cfe7b63318bb17f6e8e542f4a7e33e1b38f94d` | PR #1–3 → 统一 PR #4 | MD3E 首页动效、原生存储/内存设置、真实 HDR/刷新率能力展示 | 待验证 |
| Launcher3 | `Zhanfg/platform_packages_apps_Launcher3@601c7068193663506e154f1333f7dcc070f7fb49` | PR #1–3 → 统一 PR #4 | 弹窗进入抽屉、设置页过渡、动态色提示组件 | 待验证 |
| ThemePicker | `Zhanfg/platform_packages_apps_ThemePicker@0859e053a7de17180b4e8168705732b46515b787` | PR #1 | 原生主题色盘可访问性文本与 MD3E 内容描述 | 待验证；独立于 SystemUI 签名 |
| uwuSettingsExt | `Zhanfg/platform_packages_apps_uwuSettingsExt@289a20b44e68ce8b3836335b32793bbfd243213c` | PR #1–2 → 统一 PR #3 | 响应式 Header/手势提示条开关状态同步 | 待验证 |

这些 PR 的 Python 静态 CI 已通过，**不等于 Android 17 Kotlin/Java/Compose/aapt2 全量编译成功**。多组件替换只有在匹配的五个签名 APK 都齐全时才生成 ZIP，避免界面风格分裂和错版资源。

## MD3E / Material 3 Expressive 完整性门禁

目标：Google MD3E 组件和动态色使用规范；在当前类 AOSP 17 系统保留既有优秀交互，并吸收 ColorOS 17 风格的圆润、克制动效、低阴影、清晰层级，**不是把 ColorOS 专有 COUI 服务强行植入 AOSP**。

| 区域 | 当前证据/进度 | 仍需工作 |
|---|---|---|
| SystemUI 状态栏/秒钟 | 统一源码包含新 Clock 生命周期补丁 | 全状态切换、420 DPI、12/24 小时、刘海和运营商字符压力测试 |
| Quick Settings 双下拉 | 统一源码包含尺寸、头部安全区、DualShade tooltip 修补 | scene/Compose 新旧容器互斥及实际动画转场、无截断 |
| 通知/锁屏 | AOSP/uwuAOSP 功能既存，但未完整逐页对照 | 动态色、对比度、键盘和 media、隐私指示、无重叠 |
| Settings 首页与子页面 | 首页 PR 已纳入 + 原生入口恢复 | 所有二级/三级页面卡片分组、Switch 禁止白描边/亮边、列表图标层级、搜索可达性 |
| Launcher/设置内页 | 当前有 3 个对应补丁 | 快速滚动、预测性返回、动画时长统一、字体 1.3x 及 RTL |
| ThemePicker/uwuPrism/uwuCompose | ROM101 内确有 ThemePicker APK 及 uwuPrism 产物；已比对原始哈希与两套签名域 | ThemePicker 纳入五 APK 原生门禁；uwuPrism 保持原版、安装前比对产品 RRO 哈希；Monet/Compose 动态色仍需继续审计，不能宣称 100% MD3E |
| OnePlus 原生服务 | LOS/SDM845 已有 KeyHandler、OnePlusDoze、LiveDisplay/Touch/Dirac 参考 | ROM 是否安装 HAL、SELinux 与具体驱动需单独验证；不虚构开关 |
| Accessibility/稳定性 | 禁止状态栏/顶部安全区重叠；注意低端旧 SoC 功耗 | 420dpi/大字/夜间/横屏/RTL/多窗口、SystemUI 100 次连续操作与休眠恢复 |

 未正确展开为 `$` 的问题；新
  检查失败时删除旧的同名发布 ZIP，不会错误留下“可刷”的过时产物。
- KSU 预挂载阶段确认 5 个不同组件都有实体文件、两份清单均有 5 项且
  无重复。挂载后再核对 5 个 APK 的实际哈希，避免部分挂载被误判成功。
- 原生 `uwuCompose` 的搜索框与文本输入对话框同步动态色背景、焦点主色和
  失焦轮廓色。该补丁直接应用于锁定版本源码，不使用 LSPosed。
- 模拟 APK 签名/身份异常、缺件、重复条目、OTA 与输出污染的 CI 均已运行；
  源码级检测**不替代真实 APK 编译或 KernelSU 真机挂载**。

**当前仍缺少五个原 ROM 证书匹配的实际新编译 APK。PR #16 不能直接变成
声称修复 SystemUI 崩溃的可刷 ZIP，签名验证不应跳过。**

## 签名与目标设备门禁

当前已安装的 OnePlus 6 Android 17 系统使用平台签名的 `SystemUI.apk`，且与 Settings 共证书；Launcher3 的证书不同。已确认原始 APK SHA256，见打包脚本中的 exact hashes。

完整原生编译需要确切 ROM 17.0.101 的资源闭包和各包的**原证书相同的签名**。现有仓库与只读用户 APK 仅能得到公开证书、不能逆推出私钥。未经 ROM 原始签名，KSU 替换即使能通过文件挂载，也不等于 PackageManager 接受。不得用公开 AOSP testkey、签名强制跳过或 LSP 替代。

签名齐备的构建 APK 才可放入 `tools/ui-deployment/staging/built/`，原始 APK放入 `staging/original/`，执行**不带参数**的 `sh tools/ui-deployment/package_ui_hotfix.sh`。
无 APK、只有部分 APK、Signer 不匹配或基线 SHA 不符时**明确失败，不生成假称已修复的 ZIP**。

## 真机验收与回退

1. ROM ID、设备/API、原始五个 APK SHA 与签名证书全通过；Mountify TMPFS metamodule 处于可用/允许挂载状态。
2. 单模块原位升级，未重复安装 v0.4、旧 `uwu-ui-hotfix` 开发模块或 PR #11 LSPosed。
3. 每次启动先核对实际 `/system/system_ext/priv-app/` 映射文件哈希，再让固定 420 DPI 与修复版 SystemUI 的秒钟/白条状态生效。
4. SystemUI 100 次连续切换导航/瞬间展开关闭 Moment Arc、旋转/IME/屏灭唤醒，均无崩溃、ANR 或触摸区域丢失。
5. 8 小时屏灭待机/蓝牙/Wi-Fi/指纹/通话/充电不倒退；内存和 Mountify TMPFS 使用量记录。
6. OTA 或原 APK Hash 变化自动停止挂载；可从 KSU 安全模式禁用唯一模块恢复原 ROM。

当前结论：**源码集成/打包流程推进成功，但还没有足够证据交付“已修好 SystemUI 的可刷 APK 热更新包”。**

## 补充：MD3E 公共 Switch 关闭态配色（2026-10-11）

源头已定位于 `uwu-sdk/uwuCompose/.../SettingsSwitch.kt`：关闭状态默认 `uncheckedBorderColor = colorScheme.outline`，在某些动态壁纸色系、暗色模式下呈现过亮描边。此轮新增 `patches/uwu-sdk-md3e-switch-contrast.patch`，将关闭态边框与 `surfaceContainerHighest` 轨道保持同一色阶，拇指采用 `onSurfaceVariant`，禁用态也避免亮边。公共组件可同时覆盖 Settings、uwuSettingsExt、Prism 等实际使用它的页面，无需逐页 LSP Hook。

该源码补丁在固定 `uwu-sdk` SHA 上通过 `git apply --check` 和 CI 静态测试，纳入 `prepare_native_sources.sh`；**尚未编译进已安装 ROM/可刷模块**。MD3E 其它区域（QS Compose、通知、锁屏、动态色完整色阶）仍需继续适配和真机压力测试。
