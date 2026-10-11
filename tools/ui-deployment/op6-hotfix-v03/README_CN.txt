uwuAOSP hotfix v0.3

目标：OnePlus 6，uwuAOSP 17.0 / Android API 37。
在 KernelSU 管理器中安装本 ZIP，重启；继续沿用旧的模块 ID，因此覆盖 v0.1/v0.2。

本版本是“稳定性/回退版”：
1. 停止每次开机强制打开状态栏秒钟、强制隐藏白条。原因：原 ROM 的秒钟回调存在
   生命周期风险；白条绘制本身还没编译修复。此版不承诺白条消失。
2. 从 v0.1/v0.2 升级时，如果找到备份且用户未手动覆盖，则一次性恢复两项 Secure 设置。
3. 将屏幕 DPI 目标值设为 420：若实际有效值已是 420，完全不调用 wm density。
   若不同，只尝试一次写入并验证；后续 DPI 再漂移时暂停自动改动，避免配置互相抢占。
   KernelSU 的“执行”操作可手动重试。无法读取 wm density 时不会猜测、循环操作。
4. 不覆盖 SystemUI/Settings APK，不启动后台守护进程，不修改触摸或导航手势区域。
5. 不改动系统分区、A/B 槽位、Verified Boot、LOS HAL 或其他模块。

限制与注意：
- v0.3 并未解决原 ROM 内部 SystemUI 或手势失效的全部问题。源码 PR 需要完整
  Android 17 编译、同签名及真机复核才能安全封入 APK 模块。
- v0.3 不做每秒后台检测，也不会和其他 DPI 模块不断争抢显示参数。
- 如果你需要立刻隔离之前的模块，请使用独立的 uwuAOSP hotfix rescue.sh，
  它会将旧模块禁用并请求关闭秒钟/白条，保留其他模块。
- 因为 420 是你明确指定的显示偏好，卸载本模块不会主动把 DPI 改回其他值。
- 当前仅完成模拟测试，真机 KernelSU 安装与重启需要你最后验证。

执行结果：/data/adb/uwu-ui-live-hotfix-state/last_status.txt
