# uwuAOSP 17 / OnePlus 6：LineageOS 特征面审计

日期：2026-10-11。状态：**源码实证 + 待构建镜像验证**。
目标是让 uwuAOSP 正确表明自己的系统身份、减少不必要的上游品牌残留，并保证 OnePlus 6 的 HAL、三段拨杆、LiveDisplay、Doze、触控及系统稳定性不退化。

**不以绕过 App 风控、伪造官方认证、隐藏 Root 或伪造设备完整性作为验收标准。** 即使所有字面上的 LineageOS 标记消失，也不能据此认定银行、支付或高风控服务会改变其信任判断。

## 已核对的来源

- `uwuAOSP/platform_manifests` 的 `uwu-17.0/default.xml` 包含 AOSP 基线和 `snippets/lineage.xml`、`snippets/uwu.xml`、`snippets/pixelos.xml`。
- uwuAOSP 17.0.101 固定发布清单（`platform_vendor_uwu-versions/manifest/17.0.101.xml`）含约 160 项 LineageOS 上游工程及自己的 `frameworks/base`、`Settings`、`Launcher3` 修改。
- `vendor/uwu/config/framework_compatibility_matrix.xml` 含可选 `vendor.lineage.health`、`vendor.lineage.livedisplay`、`vendor.lineage.touch`、`vendor.lineage.powershare`。
- `vendor/uwu/config/permissions/privapp-permissions-lineagehw.xml` 含 LineageOS 权限授权。
- `vendor/uwu/overlay/common/.../SystemUI/res/values/config.xml` 包含 `org.lineageos.settings.device` 插件允许项。
- `vendor/uwu/build/target/product/source.properties` 将 SDK 镜像 `SystemImage.TagId` 写为 `lineage`，本 PR 修改为 `uwu`。**这不是 ROM 的 `ro.build.fingerprint`，不应夸大为修复应用识别。**
- `vendor/uwu/config/common.mk` 对非 `user` 构建包含 `ro.adb.secure=0`。这是独立的调试构建安全审查项，不能为了品牌清理顺手改变调试访问政策。

此外，`uwuSettingsExt/res/values/strings.xml` 和简体中文资源将 `default_music_app` 配置为 `org.lineageos.twelve`，SmartSuggestions 与 AppSelection 会读取此默认包名。**源码常量不是已安装应用的证明**，但若 Twelve 不存在，可能使音乐建议的默认目标失效。后续应按实际已安装且能响应音乐 Intent 的应用决定默认目标，不宜随意代换为另一包名。

`uwuSettingsExt/.../PuiSystemIconController.kt` 中的 `PUIThemedLineages*` 属于主题资源/标识符；直接更名可能破坏 Overlay 引用，应先检查运行时可见性。

## 区分曝光范围，而不是字符串全局替换

| 分级 | 来源 | 处理策略 |
|---|---|---|
| 构建时命名 | 源码作者、git remote、脚本函数、SDK 镜像 TagId | 保留许可证与作者；可以清除明确错误的产品品牌元数据 |
| 非公开内部实现 | Java/Kotlin package、编译中使用的目录名、Soong 项目名 | 不因包含 lineage 字符串而大规模重命名，避免 ABI/资源/权限回归 |
| 可见产品信息 | build.prop、Build.DISPLAY、实际安装包的 package ID、公开系统特性 | 在 **ROM 构建产物** 中审计；按照项目真实身份及兼容性规范维护 |
| 系统契约 | `vendor.lineage.*` AIDL/VINTF、`lineageos.permission.*`、设备插件 allowlist | 若改名须同时维护服务、客户、VINTF、SELinux、系统签名授权；否则保留稳定接口 |
| 平台可信度 | bootloader/Verified Boot、签名证书、Play Integrity / 硬件认证 | 完全独立于品牌字符串，不通过 spoof 或热补丁假装认证通过 |

注意：`<hal optional="true">` 是**支持该接口的契约声明**，不说明当前手机实际安装了对应服务。源代码 `org.lineageos.*` 不等于普通应用必定可以枚举/调用。包可见性、权限、Binder 安全限制也会影响可观测性。

## 当前能实施且已做的变更

- `build/target/product/source.properties`：SDK 镜像 TagId 从遗留 `lineage` 改为自身 `uwu`，TagDisplay 继续为 `uwuAOSP`。
- `tools/identity/audit_identity_surface.py`：**只读**源码审计；可选读取构建后的 `ANDROID_PRODUCT_OUT`，报告 ROM build.prop、安装文件名称线索及已声明的 VINTF 服务名称。
- `tools/identity/test_identity_surface.py` 和 CI：防止测试不经验证地删掉设备 HAL 兼容接口，验证已更正的 SDK 元数据和报告能力。

没有修改 `ro.product.*`、`ro.build.fingerprint`、`ro.build.tags`、系统签名、AVB、Play Integrity 或任何手机上的属性。当前手机仍使用 ROM 构建者发布的冷更新基线，已有 Mountify TMPFS 热更新不应直接篡改整机身份。

## 后续提交门槛（不要靠猜测删除）

1. 以 ROM **101 实际构建源码**和构建者的 OnePlus 6 Device/Vendor 项目作比对，避免仅以 uwuAOSP 通用 manifest 推断此设备中真正包含的包和服务。
2. 在独立构建环境生成 ROM 产品镜像，读取打包后的 build.prop、priv-app、VINTF/权限声明和签名摘要，证明哪些标记实际存在。
3. 对“无功能依赖的品牌残留”做单独 PR 清理；对“必须依赖 Lineage HAL”的功能保持 ABI 不变，或提供经过编译/真机验证的兼容迁移层。
4. 设备从上游 OTA 升级后重跑镜像级审计；不将旧版本属性强行覆写到新 ROM。
5. 真机校验安排最后，按用户要求先完成源码级功能恢复与稳定性完善。对仍不工作的具体应用记录其公开兼容要求，不推测原因是 LOS 检测。

## 安全提示

对非 user 构建，当前 `ro.adb.secure=0` 需要独立复核，特别是在生产日常使用环境。修正可能影响当前调试和设备救援通道，不在本身份审计 PR 中暗改。不要为了让软件误判 ROM 而削弱 Verified Boot 或把所有 APK 统一伪装为官方签名。
