uwuAOSP hotfix v0.2

目标系统：OnePlus 6 / uwuAOSP Android 17 / KernelSU + Mountify TMPFS。
安装：在 KernelSU 管理器选择“从本地安装模块”，选 ZIP 后重启。
模块 ID 保持 uwu-ui-live-hotfix，可原位升级 v0.1，不重复安装另一模块。

本版实际功能：
1. 调用 ROM 已有的状态栏 clock_seconds 设置来开启秒钟。
2. 请求将 uwu_hide_gesture_handle 设置为 1，尝试隐藏底部白条。
3. 首次安装保留原值；重复开机不会覆盖用户后来明确更改的设置。
4. KernelSU Action 在隐藏白条“请求开启/关闭”之间切换，并跨升级保留手动关闭状态。
5. 卸载保守恢复备份值；系统设置已经被用户改变时不覆盖。
6. 设备/Android API 不符时跳过操作；不创建常驻进程、不重启 SystemUI。

注意：此包没有替换 SystemUI/Settings APK。之前的 SystemUI ANR、手势白条绘制问题以及
LOS 功能补齐仍需对应源码编译、原 ROM 平台签名和真机测试。不能将本包视作这些问题
全部修复。设置只能对 user 0 生效，其他用户需单独适配。

首次应用状态（不包含隐私数据）：
/data/adb/uwu-ui-live-hotfix-state/last_status.txt

请勿使用 Recovery 或 ADB sideload。安装不会改变系统槽位、OTA、AVB 或指纹信息。
