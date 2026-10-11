# OnePlus 6 实际 SystemUI.apk 的 DEX Hook 兼容性审查

- ROM: uwuAOSP Android 17, API 37, ro.build.id = CP2A.260605.016
- 文件：`/system/system_ext/priv-app/SystemUI/SystemUI.apk`
- SHA256: `47e4e849e99a695b3c698566fb451cf3cd671ddb17f3e5844d15b2b35188f841`
- 仅在用户提供的 ROM 参考归档内验证；不代表 OTA 后仍相同
- 原生 `SystemUI` 必须保持原 APK 和平台签名，Hook 自身另行签名并需要用户主动配置 LSPosed 作用域

## DEX 文件类定义核对（classes2.dex）

| 实际类 | 已声明方法 / 字段 | Hook 决策 |
|---|---|---|
| `NavigationHandle` | `onDraw`, `mRadius`, `mBottom` | 只跳过白条绘制，不更改 WindowInsets 或 View 尺寸 |
| `QuickswitchOrientedNavHandle` | `onDraw` | 同时处理旋转后的白条 |
| `Clock` | `onAttachedToWindow`, `mSecondTick`, `mSecondsHandler` | 安装内部 Tick 的空 Handler 保护 |
| `Clock$4` | `run`, `this$0` | 可以找到所属 Clock 实例；屏灭/拆卸保护 |
| `MomentArcController` | `createIconView`, `loadIcon`, `hide`, `isMomentArcEnabled`, `overlayView`, `windowManager` | 支持异步图标加载、退出清理和设置缓存 |
| `MomentArcController` | **无** `onTouchCoordinates` | 禁止对此方法挂钩，原源码已被 R8 内联 |
| `MomentArcStartable$gestureReceiver$1` | `onReceive`, `this$0` | 在真实广播入口区分手势触摸事件，限定异常处理和设置缓存 |
| `MomentArcStartable` | `controller`, `start` | 可由 Receiver 找回正确 Controller |

## 风险控制

1. 此文件是**目标方法的实际 DEX 存在性证据**，不是运行时 Hook 成功证明。仍需用户设备的 LSPosed 模块加载记录与 SystemUI 崩溃堆栈。
2. `onDraw` 不执行任何跨进程 Settings 查询，只读取由 ContentObserver 缓存的状态。
3. 图标加载使用一个有界、空闲退出的后台执行器，避免 SystemUI 主线程等待 LauncherApps/PackageManager。
4. Hook 只允许 OnePlus 6 + API 37 + 当前固定 Build ID。系统 OTA 或变更 ROM 后自动跳过。
5. 如运行时存在 Hook 兼容性冲突，不强制重启 SystemUI，也不尝试通过伪造平台签名安装新 SystemUI。
6. CI 使用 compile-only Xposed API 接口验证 Java/DEX 编译；**需要真机 LSPosed 加载及交互测试**才能判定功能可用。
7. 当前发布构建使用临时测试签名；没有稳定生产密钥时，不承诺后续 APK 可直接覆盖升级。

## 真正的原生源码修复

`Zhanfg/platform_frameworks_base` PR #7 是不依赖 Hook 的原生 SystemUI 改动。但它尚未针对用户 ROM 完整构建，也缺少匹配的原始平台私钥。两条路线相互补充，不可把运行时 APK 视为改写了原 SystemUI.apk。
