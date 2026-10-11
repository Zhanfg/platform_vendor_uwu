uwuAOSP hotfix v0.5 (SystemUI 运行时修补程序)

这次不是仅改小白条尺寸的 RRO，也不覆盖 SystemUI.apk。
基于 OnePlus 6 当前 Android 17 SystemUI.apk 中实际存在的
com.android.systemui.moment.arc.MomentArcController 等类开发。

需要兼容 Android 17 的 LSPosed/同类框架；默认只有手动启用插件
并将作用域限定 com.android.systemui 后才工作。

修补内容：
1. 绘制底部白条时跳过画圆角矩形，不更改任何导航/触控区域。
2. 秒钟 Tick 保护：运行时检查 Clock 的原生 Handler 是否仍有效，
   避免在已清空 Handler 的视图生命周期路径上继续执行 Tick。
3. Moment Arc：12 个图标与快捷方式查找从 SystemUI 主线程转移到
   单个有界的后台 worker，加载结果失效则丢弃。
4. 高频手势事件读取设置采用短期缓存，降低 SettingsProvider Binder IPC。
5. 退出动画未结束时延迟清理遗留的覆盖层；不终止或重启 SystemUI。
6. 只处理 com.android.systemui，缺失类或方法时跳过对应 Hook。
7. 不替换系统 APK、修改平台签名、内核、SELinux、导航栏布局或 OTA。

限制：
- 这需要 Hook 框架，并不由普通 KernelSU 模块单独提供这些能力。
- 不保证能修复所有 SystemUI 原生 Java/Native/ANR 故障；无崩溃堆栈时不能
  宣称根因已完全查明。用户必须确认 LSPosed Android 17 版本适配。
- 运行时补丁有兼容性风险；首次启用务必能在安全模式或 KernelSU 下关闭
  LSPosed，保留 ROM 回退路径。
- 因仍需真机安装、Hook、生效日志与压力测试，此为候选测试版。

源码：Zhanfg/platform_vendor_uwu -> tools/ui-deployment/op6-runtime-hook-v05
整合原生修复：Zhanfg/platform_frameworks_base PR #7
