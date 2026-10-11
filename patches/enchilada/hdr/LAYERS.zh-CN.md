# OnePlus 6 Android 17 HDR 修复层级与部署决策

## 已确认的基线
- OnePlus 6 A6003，uwuAOSP 101 系列，Android 17；不迁移 133。
- 内核 Linux 4.19.325；本项目不合入新的 BOOT、DTBO、内核和 DPI 变更。
- 1080×2280 60 Hz，面板 DTS 已声明 HDR，接口配置 24 bpp。
- 真机 HWC: `vendor.qti.hardware.display.composer-service`，android.hardware.graphics.composer@2.4。
- 显示色彩映射异常：已枚举的 native/sRGB/P3/PQ/HLG 色彩条目 RenderIntent=-1，
  HWC `color modes supported:` 为空，上层只暴露 NATIVE。
- `hdrSdrRatio=NaN` / `mHdrBrightnessData=null` 为独立的亮度管理缺口，
  不能通过设置 HDR 声明或改内核直接消除。

## 需要修改哪些层

| 层面 | 当前是否必须 | 原因与处理 |
|---|---|---|
| Vendor HWC/SDM 用户空间 | **第一优先级** | 修复 SDM 已枚举的色彩模式转 HWC ColorMode/RenderIntent 映射；编译匹配当前 ROM 的 composer |
| Vendor 校准与显示配置 | **按验证结果** | 保留面板实际存在的 sRGB、P3、BT.2020 PQ/HLG 模式及校准，缺失则修实际配置 |
| Android SurfaceFlinger / Display HAL 接口 | **条件性** | 若修复 HWC 后 PQ/HLG Dataspace 仍无法穿透或动态范围切换失败，再定位框架 |
| DisplayDeviceConfig 与亮度策略 | **后续单独阶段** | 补充经过校验的 HDR 亮度映射；先确认 HWC 实际输出，禁止伪造 `hdrSdrRatio` |
| MediaCodec / VDEC | **必要时检查** | 媒体声明中有 HEVC/VP9，但只有运行测试才能确定 Main10 和 HDR 元数据传递 |
| Kernel BOOT | **现在不需要** | DRM/DSI 面板 HDR 标志已存在；仅在后续发现驱动层特定缺陷时再考虑 |
| DTBO / DTB | **现在不需要** | 已有 1080×2280@60 时序；不引入 6T 面板或更改 DSI bpp/亮度上限 |
| 内核 LKM | **不采用** | HWC 色彩模式解析处于 Vendor 用户空间，LKM 不直接处理此问题 |

## 为什么不是 LKM
KernelSU 可以以 LKM 方式工作，但 KernelSU 模块对用户空间文件的系统无关挂载
不是内核 LKM 补丁。二者不能混为一谈。

## 如何交付
1. **建议正式交付：**在精准匹配的 Android 17 HWC 源码树中编译
   `vendor.qti.hardware.display.composer-service`，核查 ABI、链接库、VINTF、
   SELinux 后通过 Vendor 更新集成；保留原有分区镜像和回退路径。
2. **可选测试交付：**把经过 ABI 确认的 Vendor 用户空间二进制及必要配置通过
   KernelSU/Magisk 的早期 systemless 挂载注入。必须先验证模块挂载时序、
   原有 SELinux 上下文、服务依赖和安全模式能回退。**不能把源码 patch
   直接刷成 LKM 或模块。**
3. 如仅靠配置补齐无法恢复 HWC ColorMode 映射，则不能用 `setprop`、
   `settings put` 或一键强制 HDR 代替修复。

## 下一步验证门槛
- 运行 `tools/op6_hwc_fingerprint.sh`（无需参数）确认手机已有 composer
  二进制及 libsdmcore 等文件版本。输出位于 Download。
- 对比源代码构建产物、ELF Build ID、依赖库和实际服务版本。
- 源码 patch 可在参考树应用 ≠ 匹配当前 ROM 的原始 HAL ≠ 已完成编译。
- 首先验证 HWC mode map 恢复（NATIVE、SRGB、P3、PQ、HLG）及 SDR 无色偏；
  然后验证 HDR 图层 `current dynamic_range: HDR`、Dataspace 与光度表现。
- 再验证亮度保护、待机功耗、热限制、横竖屏切换、关屏唤醒。
- 未完成实际设备测试前，PR 保持 Draft，任何产物均不能标记为可刷入正式版。
