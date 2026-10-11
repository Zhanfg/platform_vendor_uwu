# OnePlus 6 — Android 17 Settings 功能缺失审计（初版）

> 范围：uwuAOSP 17.0 / OnePlus 6 (enchilada)。
> 当前只确认源码、资源开关及社区参考实现。**不代表用户 ROM 已集成对应 HAL/应用。**
> 不把其他品牌或 OnePlus 6T 的设备接口直接当作 OP6 可用接口。

## 1. 手势提示条（P0）

- `packages/SystemUI/src/com/android/systemui/navigationbar/gestural/NavigationHandle.java` 负责绘制底部 `home_handle`。
- `uwuSettingsExt/interfaceui/InterfaceSettingsActivity.kt` 写入 `Settings.Secure.UWU_HIDE_GESTURE_HANDLE`。
- 原来两处依赖 `Settings.Secure.NAVIGATION_MODE`，而 `NavigationModeController` 异步写入这个缓存。
- **已独立提交** SystemUI PR #5 + uwuSettingsExt PR #2：保留触控区域，只隐藏图形，使用当前资源 Overlay 判断手势布局。
- 仍需真机验证：普通应用、桌面、横屏、输入法 IME 自绘导航条与沉浸模式。**不要将窗口底部 inset 强制设为 0**。

## 2. AOSP 已有但被禁用 / 被掩藏

| 功能 | 源码证据 | 修改策略 |
|---|---|---|
| 自动存储管理的 AOSP 系统 Intent | Settings `config_storage_manager_settings_enabled=false`，Manifest 已定义 `android.settings.STORAGE_MANAGER_SETTINGS`，存在 `AutomaticStorageManagerSettings` | 已在 Settings 独立 PR 恢复标准 Activity 导出；仍受已有存储管理服务和权限限制 |
| 应用信息 → 内存 | `config_show_app_info_settings_memory=false`，现成 `AppMemoryPreferenceController` 检查开发者选项并用真实 ProcStats | 已在 Settings 独立 PR 恢复为仅开发者可见的入口；不强开 PSS，不能制造采集数据 |
| 自动清理/存储管理 | `config_show_smart_storage_toggle=true`，`AutomaticStorageManagementSwitchPreferenceController` 已存在 | **已存在**：不重复加开关，先检查当前存储服务 |
| 手势导航详细设置 | `SystemNavigationGestureSettings` 和 `gesture_navigation_settings.xml` 已存在 | 先修手势白条，避免第二个相冲突的设置 |
| 高刷新率 | `RefreshRateUtils` 已存在且 SystemUI HAL 才是模式来源 | 禁止虚构大于 60Hz 的模式；见 Settings display PR #2 |
| HDR 亮度 | `HdrBrightnessUtils` 仅在显示报告 HDR + HDR/SDR 比例可用时放行 | 保持真实能力门控；不靠更改布尔值假装 HDR 输出 |
| LiveDisplay 入口 | `display_settings.xml` 已有 `livedisplay`，`LiveDisplayPreferenceController` 负责可用性 | 若 HAL 不存在则不显示；需要设备的 color service 才能恢复 |
| 色温调节（开发者选项） | `config_enableColorTemperature=false`，有 `CoolColorTemperaturePreferenceController` | 暂不盲开，先查校色/显示服务能否实际应用参数 |

## 3. 一加原生及 Lineage 参考实现

参考来源：`LineageOS/android_device_oneplus_sdm845-common` 的
`lineage-24.0/common.mk`（仅作移植参考，不代表当前 uwuAOSP 已具备）：

| 功能 | 社区实现依据 | 集成前的硬条件 |
|---|---|---|
| 三段式静音拨杆 | `KeyHandler`、`KeyHandlerResCommon` | 开关输入事件映射、铃声音量/勿扰策略、Android 17 通知权限/广播兼容 |
| 双击亮屏 / 抬起唤醒 / 息屏手势 | `OnePlusDoze`、`OplusDozeResCommon`（名称依分支） | 真实传感器/触控节点、系统唤醒权限、权限策略、深度睡眠电耗测试 |
| 色彩模式、色温与 LiveDisplay | `vendor.lineage.livedisplay-service.oneplus[_sdm845]` | 兼容的 Vendor HAL/SELinux，真实设备支持的色彩命令与校色参数 |
| 防误触 / 口袋模式 | 设备树 `pocketmode` 目录及 `oneplus.sensor.pocket` | 传感器报告及 Doze 适配，不能凭目录断言有服务 |
| 触控游戏/敏感度控制 | `vendor.lineage.touch-service.oneplus` | 正确触控驱动节点，机型差异与耗电验证 |
| Dirac / 音频调校 | `OnePlusDiracGef` 与音频效果配置 | 音频 HAL/EFFECT UUID 有效、音效链不重复、不破坏现有 V4A |
| 自适应充电/限制充电 | 设备树可选 `/sys/class/power_supply/battery/op_disable_charge` | 只读核对节点；不要在电池系统尚未确认前写入 |
| HDR 和广色域 | OP6 Kernel DTS 的 SOFEF00_M 2280x1080@60 节点含 HDR 元数据和 P3 命令 | 验证 HWC/SurfaceFlinger/解码/10bit 等完整输出链 |

## 4. 下一阶段的工程范围

1. **先读取实际 ROM 环境**：执行同目录 `feature_probe.sh`（无参数只读），发送 Download 目录的 TXT。
2. 对用户 ROM **确实已存在的服务**：在 uwuSettingsExt 的 AOSP/OnePlus 功能入口接入真实控制器或 Activity，并对不可用能力隐藏或禁用。
3. 对不存在的厂商服务：先移植或重新实现必要的 Android 17 HAL/后台，跑测试后再添加 UI，不能出现“能点却不生效”的设置项。
4. 优先次序：三段式静音拨杆 > 息屏手势/口袋模式 > 屏幕色彩 > 触控模式 > 音频附加处理。
5. 任何后续 SystemUI/Settings 改动必须经过 **uwuAOSP + 当前 OnePlus 6 ROM 基线** 编译、签名匹配、Mountify TMPFS 单 ZIP 挂载验证，保留上游 A/B OTA 更新能力。

**不要**将功能缺失视为必须关闭签名检查或编辑内核时序的理由。
