# OnePlus 6 uwuAOSP Android 17 — 原生 KernelSU 系统界面整合审查

2026-10-11 | 工程状态：整合源码和打包门禁完成；**实际 APK 编译、原平台签名和真机验证未完成**。

## 唯一技术路线

- 一个 KernelSU 模块：`uwu-ui-live-hotfix`，显示名称 `uwuAOSP hotfix v0.6`。
- 唯一挂载后端：Mountify TMPFS/OverlayFS 的 `system/` 文件树。
- 不使用 LSPosed/LSP Hook、不加载旧 PR #11 的 Xposed APK；不修改 system 分区、boot、vbmeta 或 SELinux 策略。
- 仅覆盖四个**真的改变、已编译、与原 ROM 签名相同**的特权/系统 APK。安装时不携带备份 APK 和重复副本。保留 upstream A/B OTA，基线变化即停止挂载。
- 已完成的 RRO v0.4 **不作为 SystemUI 逻辑崩溃修复**，不得取代原生 SystemUI 构建。
- DPI 以用户明确指定的 **420** 为目标；失败不重试循环，已经是 420 就不写。默认不增加常驻监听器。

## 这轮已整合的四个真实源码提交

| 组件 | 编译分支与 SHA | 合并来源 | 实质修改 | 独立构建/真机 |
|---|---|---|---|---|
| SystemUI | `Zhanfg/platform_frameworks_base@5f78233070530b853fcc6501776f19d00393ca63` | PR #1,#2,#3,#4,#7 → 统一 PR #8 | Moment Arc 的同步 LauncherApps IPC、窗口超时、秒针 Handler 生命周期、白条绘制判断、双面板调用宽度/顶部安全区/刘海提示 | 待验证 |
| Settings | `Zhanfg/platform_packages_apps_Settings@c3cfe7b63318bb17f6e8e542f4a7e33e1b38f94d` | PR #1–3 → 统一 PR #4 | MD3E 首页动效、原生存储/内存设置、真实 HDR/刷新率能力展示 | 待验证 |
| Launcher3 | `Zhanfg/platform_packages_apps_Launcher3@601c7068193663506e154f1333f7dcc070f7fb49` | PR #1–3 → 统一 PR #4 | 弹窗进入抽屉、设置页过渡、动态色提示组件 | 待验证 |
| uwuSettingsExt | `Zhanfg/platform_packages_apps_uwuSettingsExt@289a20b44e68ce8b3836335b32793bbfd243213c` | PR #1–2 → 统一 PR #3 | 响应式 Header/手势提示条开关状态同步 | 待验证 |

这些 PR 的 Python 静态 CI 已通过，**不等于 Android 17 Kotlin/Java/Compose/aapt2 全量编译成功**。多组件替换只有在匹配的签名 APK 都齐全时才生成 ZIP，避免界面风格分裂和错版资源。

## MD3E / Material 3 Expressive 完整性门禁

目标：Google MD3E 组件和动态色使用规范；在当前类 AOSP 17 系统保留既有优秀交互，并吸收 ColorOS 17 风格的圆润、克制动效、低阴影、清晰层级，**不是把 ColorOS 专有 COUI 服务强行植入 AOSP**。

| 区域 | 当前证据/进度 | 仍需工作 |
|---|---|---|
| SystemUI 状态栏/秒钟 | 统一源码包含新 Clock 生命周期补丁 | 全状态切换、420 DPI、12/24 小时、刘海和运营商字符压力测试 |
| Quick Settings 双下拉 | 统一源码包含尺寸、头部安全区、DualShade tooltip 修补 | scene/Compose 新旧容器互斥及实际动画转场、无截断 |
| 通知/锁屏 | AOSP/uwuAOSP 功能既存，但未完整逐页对照 | 动态色、对比度、键盘和 media、隐私指示、无重叠 |
| Settings 首页与子页面 | 首页 PR 已纳入 + 原生入口恢复 | 所有二级/三级页面卡片分组、Switch 禁止白描边/亮边、列表图标层级、搜索可达性 |
| Launcher/设置内页 | 当前有 3 个对应补丁 | 快速滚动、预测性返回、动画时长统一、字体 1.3x 及 RTL |
| ThemePicker/uwuPrism/uwuCompose | ROM 内已有部分彩色 Material3 Expressive 和动态色实现线索 | 逐项审计 ThemePicker/Prism/Monet 与系统色彩令牌；当前**没有**纳入四 APK 打包，不能宣称 100% MD3E |
| OnePlus 原生服务 | LOS/SDM845 已有 KeyHandler、OnePlusDoze、LiveDisplay/Touch/Dirac 参考 | ROM 是否安装 HAL、SELinux 与具体驱动需单独验证；不虚构开关 |
| Accessibility/稳定性 | 禁止状态栏/顶部安全区重叠；注意低端旧 SoC 功耗 | 420dpi/大字/夜间/横屏/RTL/多窗口、SystemUI 100 次连续操作与休眠恢复 |

## 签名与目标设备门禁

当前已安装的 OnePlus 6 Android 17 系统使用平台签名的 `SystemUI.apk`，且与 Settings 共证书；Launcher3 的证书不同。已确认原始 APK SHA256，见打包脚本中的 exact hashes。

完整原生编译需要确切 ROM 17.0.101 的资源闭包和各包的**原证书相同的签名**。现有仓库与只读用户 APK 仅能得到公开证书、不能逆推出私钥。未经 ROM 原始签名，KSU 替换即使能通过文件挂载，也不等于 PackageManager 接受。不得用公开 AOSP testkey、签名强制跳过或 LSP 替代。

签名齐备的构建 APK 才可放入 `tools/ui-deployment/staging/built/`，原始 APK放入 `staging/original/`，执行**不带参数**的 `sh tools/ui-deployment/package_ui_hotfix.sh`。
无 APK、只有部分 APK、Signer 不匹配或基线 SHA 不符时**明确失败，不生成假称已修复的 ZIP**。

## 真机验收与回退

1. ROM ID、设备/API、原始四个 APK SHA 与签名证书全通过；Mountify TMPFS metamodule 处于可用/允许挂载状态。
2. 单模块原位升级，未重复安装 v0.4、旧 `uwu-ui-hotfix` 开发模块或 PR #11 LSPosed。
3. 每次启动先核对实际 `/system/system_ext/priv-app/` 映射文件哈希，再让固定 420 DPI 与修复版 SystemUI 的秒钟/白条状态生效。
4. SystemUI 100 次连续切换导航/瞬间展开关闭 Moment Arc、旋转/IME/屏灭唤醒，均无崩溃、ANR 或触摸区域丢失。
5. 8 小时屏灭待机/蓝牙/Wi-Fi/指纹/通话/充电不倒退；内存和 Mountify TMPFS 使用量记录。
6. OTA 或原 APK Hash 变化自动停止挂载；可从 KSU 安全模式禁用唯一模块恢复原 ROM。

当前结论：**源码集成/打包流程推进成功，但还没有足够证据交付“已修好 SystemUI 的可刷 APK 热更新包”。**
