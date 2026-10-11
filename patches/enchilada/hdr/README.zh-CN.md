# OnePlus 6 HDR HWC 旧版元数据兼容补丁（候选）

**当前状态：仅源码候选，不是刷机模块，不得直接覆盖现有 HAL。**

## 现有基线与真机证据
- OnePlus 6 A6003，Android 17，现有 uwuAOSP 101 系列（不迁移 133）。
- Qualcomm Composer 和 SurfaceFlinger 均正常运行。
- 驱动枚举 CTS、DCI_P3、SRGB、bt2020_hlg、bt2020_pq。
- 上述模式的 RenderIntent 都为 -1。
- Composer 的 `color modes supported:` 映射表为空。
- Android 仅暴露 ColorMode::NATIVE (0)，HDR/SDR 亮度比例不可用。
- 日志取自普通 SDR 桌面，不能用来证明所有 HDR 视频都无法切换。

## 本轮定位
某些新版 Qualcomm HWC2 实现会跳过 RenderIntent 小于 0 的校准模式，导致底层虽有 PQ/HLG，映射到 SurfaceFlinger 的模式表仍为空。如果运行中的 HAL 使用相同解析逻辑，该问题足以阻止 HDR 色彩模式选择。

## 兼容补丁
`0001-legacy-hdr-render-intent.patch` 现在只针对日志已经确认、名称与元数据都匹配的 **五个标准校准模式**：`CTS`（native）、`SRGB`、`DCI_P3`、`bt2020_pq`（ST2084）、`bt2020_hlg`（HLG）。

**不映射 `advance_native` / `advance_srgb` / `advance_p3` 等模式**：这些旧校准配置报告为 sRGB，之前的宽泛兼容方式可能覆盖标准色彩预设。这是本轮收紧的重点。

仅在以下条件全部满足时修复：
- RenderIntent 恰好为 -1；
- PictureQuality 为 standard；
- 色域和传递函数为已识别的 native / sRGB / DCI-P3 / BT.2020 PQ / HLG。

仅为上述五个模式默认提供 COLORIMETRIC 渲染意图。对未知元数据不放宽检查，也不伪造 HDR 格式、10-bit 面板能力、亮度数值或刷新率。

新增 CI：`git apply --check`、针对 patched HWC 实际条件表达式的 C++ 编译和 14 个正反例回归测试（仅测试映射谓词，不是完整 HAL 编译）。

## 合入与真机测试前置条件
1. 先确认手机当前 `vendor.qti.hardware.display.composer-service` 的实际源码、依赖库和 ABI 版本。参考树为 LineageOS 的 `android_hardware_qcom_sm7250_display`，它不保证就是当前 ROM 所用的精确代码。
2. 当前机器已确认 `/vendor/etc/qdcm_calib_data_samsung_sofef00_m_cmd_mode_dsi_panel.xml` 存在，同时存在 OnePlus 6T 面板文件，但**不能选错**。SHA-256 文件指纹足以确认同一二进制，不足以单独判定源码身份；需要对真实 ELF 和校准 XML 进行匹配。
3. 在匹配的 HAL 源码树执行 `git apply --check`、编译和 VINTF/SELinux 检查。
4. 使用可靠回退方案进行真机启动，确认 SurfaceFlinger/HWC 色彩映射真正恢复，且普通 SDR 无偏色、黑屏或异常耗电。
5. 随后才验证实际 HDR10 / HLG 图层的 Dataspace 与动态范围切换，排除错误的 SDR tone mapping。
6. 最后单独补齐 HDR 亮度策略及显示设备配置；不能通过假写 HDR/SDR 比例绕过缺失的硬件能力。

**目前 CI 只能证明补丁可应用于选定的参考源码，不能证明当前手机已经获得 HDR 输出。** 此 Draft PR 不会自动修改正在使用的 ROM 或 Boot。