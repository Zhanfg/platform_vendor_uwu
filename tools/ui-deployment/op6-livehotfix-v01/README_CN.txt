uwuAOSP 17 OnePlus 6 UI Live Hotfix v0.1

安装方式：KernelSU 管理器 -> 模块 -> 从本地安装 -> 选择当前 ZIP -> 重启。
不要使用 Recovery / ADB sideload 安装此包。

已实现：
1. 让 ROM 现有状态栏时钟显示秒钟（TunerService：clock_seconds）。
2. 请求隐藏底部手势白条（Secure：uwu_hide_gesture_handle）。
3. 首次应用前保存上述两个设置的原值；卸载时尽量恢复。
4. Android 启动完成后运行一次；不会常驻后台、循环重启 SystemUI。
5. 不替换 APK、不使用 /system 目录、不修改 A/B 槽位或 OTA 密钥。
6. KernelSU 模块 Action 一次切换手势白条隐藏请求；不影响秒钟开关。

重要限制：
* 你当前 ROM 的底部白条绘制逻辑仍有源码缺陷。本模块已写入设置，但未
  替换尚未编译的 SystemUI，因此不保证白条立即消失。
* 之前提交的 SystemUI 闪退/卡顿、双下拉、Launcher/Settings 页面修复，
  仍在 GitHub 的独立 PR 中。它们尚未编译签名，本 ZIP 不包含这些代码修复。
* LineageOS HAL/权限名称与 Verified Boot/设备认证均不更改。
* 仅支持 OnePlus 6 / Android 17（API 37）。OTA 升级到其他 API 时脚本自动跳过。
* 此 ZIP 可直接由 KernelSU 管理器识别，但尚未在你的手机上真机刷入测试。

检查结果：
/data/adb/uwu-ui-live-hotfix-state/last_status.txt
状态文件仅含简短的执行结果，不收集个人隐私。

卸载：KernelSU 管理器卸载本模块；uninstall.sh 尝试恢复之前记录的设置。
