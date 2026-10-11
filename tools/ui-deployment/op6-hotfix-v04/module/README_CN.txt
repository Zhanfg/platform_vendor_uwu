uwuAOSP hotfix v0.4 — OnePlus 6 / Android 17

这是第一份真正尝试替换白条绘制资源的轻量修复包，而不是只写 Secure 设置值。
保留原模块 ID uwu-ui-live-hotfix，安装时替换 v0.1/v0.2/v0.3。
需要 KernelSU + Mountify（TMPFS 系统文件挂载）。

实现：
- 编译并签名独立的资源覆盖 APK（RRO），放入 system_ext/overlay。
- 覆盖 SystemUI 中 navigation_handle_radius、navigation_home_handle_additional_height_for_animation 为 0dp。
- 不改动导航栏大小、手势 inset 或触摸区域，不强杀 SystemUI。
- 原模块的 DPI 420 逻辑保留，并避免反复和其他 DPI 设置争抢。
- 不替换或重签 SystemUI.apk，不要求 ROM 平台私钥。
- 仅允许 OnePlus 6 Android 17 CP2A.260605.016，且 SystemUI 原 APK 的 SHA256 必须匹配。

限制：
- 这条路径取决于你的 OverlayManager/idmap 是否接纳预装资源覆盖层。
  首次 GitHub CI 可以证明 RRO APK 能实际编译、签名，但不等于真机已成功激活。
- 当前 SystemUI 的 MomentArc 卡顿、Clock 秒钟回调等代码级修复位于
  Zhanfg/platform_frameworks_base PR #7。没有完成原 ROM 平台签名和完整编译前，
  不能声称它们已被本模块安装修复。
- 未经验证不强制打开秒钟，因为旧 APK 的秒钟 Handler 仍有生命周期风险。
- 系统更新后若原文件哈希不一致，禁止继续依旧版资源布局编译发布。
- 如白条仍可见，请在 KernelSU “执行”操作中查看 RRO 状态，不用重刷 ROM。

安装：KernelSU 管理器 -> 从本地安装 ZIP -> 重启。
