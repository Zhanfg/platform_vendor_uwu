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

## 2026-10-11 原机 HAL 二进制与校准 XML 离线分析
实际从手机只读提取 11 个原始文件（**原始厂商二进制及 4 MB QDCM 文件未上传到 GitHub**）。检测到：
- Composer 是 AArch64、Android API 37 的 ELF，运行 HWC 2.4 / Qualcomm Composer 3.0，加载 `libsdmcore.so`、`libsdmutils.so`、`libgpu_tonemapper.so` 等 38 项动态依赖。
- Composer 二进制中包含与参考实现一致的 `Invalid render intent`、`GetColorModeCount failed, use native color mode`、`color modes supported:` 等字符串；这支持源码族判断，但**不能根据字符串或 ELF Build ID 就声称源码提交完全一致**。
- SOFEF00_M XML 解析成功，`Disp_Modes NumModes=11`，实际也有 11 个模式。
- 校准 XML 明确包含 `hal_hdr`（DCI-P3 + HDR）与 `CTS`、`SRGB`、`DCI_P3`、`advance_*` 等；这些 XML `Mode` 节点都未显式提供 `RenderIntent` 属性。
- 真机运行时 PQ/HLG 来自 SDM 枚举的 `bt2020_pq` / `bt2020_hlg` 条目，但它们不属于上述 11 个 XML Mode。反过来，`hal_hdr` 在本次运行时 HWC 可选模式列表中缺席，不能擅自补造。
- 不修改 QDCM 大型二进制校准数据，不向 `hal_hdr`、`zhal_native`、`fod_native`、锐化或 `advance_*` 强行赋予标准色彩模式身份。
- 针对补丁的 C++ 映射谓词测试已新增上述误识别负例，总计 20 个；它仍然**不等于原机 HWC 构建、VINTF 检测或 HDR 真机验证**。

### 下一步：真正可刷版本的门槛
1. 找到现有 uwuAOSP 101 Android 17 的**实际显示构建来源**，确认使用的 Soong 目标与此参考 `composer/hwc_display.cpp` 匹配，而不是按芯片相似性推断。
2. 在配套 Android 17 编译环境中编译 Vendor Composer，比较 ELF 动态依赖、入口、服务 rc、SELinux 标签及原机运行接口。
3. 先完成原机可回退机制验证，再考虑 KernelSU/Magisk systemless 挂载新 Vendor 用户空间服务；**无需 BOOT / DTBO / LKM**。
4. 真机分别检查色彩映射表、普通 SDR 色准和 HWC HDR 输出模式；随后按原有亮度曲线实现有验证依据的 HDR/SDR 亮度控制。不能用伪造 HDR 元数据替代以上步骤。


## 2026-10-11 官方构建源锁定与自动门禁

从 uwuAOSP 官方 manifest (https://github.com/uwuAOSP/platform_manifests/blob/uwu-17.0/snippets/lineage.xml) 确定：
- 源码路径：hardware/qcom/sm7250/display
- 项目：LineageOS/android_hardware_qcom_sm7250_display
- 上游分支：lineage-24.0
- 当前复现固定 SHA：d3fae6913731a30c135a6cd1fab803913da06998
- Soong 目标：vendor.qti.hardware.display.composer-service

这是官方 ROM 清单的真实来源，但并不证明本机 101 ROM 使用了完全相同的提交。

### 新增自动化检查
- test_real_populate_color_modes.py：提取补丁后的真实 HWCColorMode::PopulateColorModes() 函数，在模拟底层 DisplayInterface 上编译并执行；验证 CTS、SRGB、DCI_P3、PQ、HLG 的映射及特殊预设的拒绝，验证 native fallback。
- tools/prepare_op6_hdr_hwc_build.sh：完整 Android 17 ROM 构建树中运行（无参数）。强制验证 enchilada 目标、上游来源及固定 SHA、Git 工作区干净、补丁可应用；仅修改本地源码。
- tools/verify_composer_abi.py：编译后的主机工具。对比原始 Composer 与候选 ELF 的 ARM64、动态库 DT_NEEDED 列表、Build ID 和补丁标记。发现差异自动拒绝。

### 实际编译流程（在完整 ROM 构建机，不是在手机）
1. 同步 uwuAOSP 17.0 清单，导入正在使用的 enchilada device/vendor 配置。
2. source build/envsetup.sh，然后选择该 ROM 已有的 enchilada lunch target。
3. 把 vendor/uwu 切换到 PR #9 分支，在构建树中运行：
   sh vendor/uwu/patches/enchilada/hdr/tools/prepare_op6_hdr_hwc_build.sh
4. 编译：m vendor.qti.hardware.display.composer-service
5. 在构建机上运行：
   python3 vendor/uwu/patches/enchilada/hdr/tools/verify_composer_abi.py 原始Composer文件 新Composer文件
6. 通过后仍须完成 VINTF/SELinux、真实启动和可回退部署测试。

### 当前验收边界
CI 通过了真实 HWC 函数的主机编译执行、官方 manifest 核对、固定源码提交的补丁应用、候选 ELF ABI 工具静态检查。但尚未完成整套 Android 17 Soong 编译、可刷模块生成和真机 HDR 验证。保留 Draft。
