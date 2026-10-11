# uwuAOSP 17 / OnePlus 6：LineageOS 特征暴露与兼容性审查

日期：2026-10-11。范围：`uwu-17.0` 的 `vendor/uwu` 源码。**此文件是源码审查，不是当前手机的运行时特征检测。**

## 已确认的事实

uwuAOSP 是混合来源的 Android 17 ROM，并非纯 LineageOS。其源码 manifest 继承了 AOSP 17，也包含大量 LineageOS 24.0 组件、若干 PixelOS 组件和 uwuAOSP 自有的 frameworks/Settings/Launcher 项目。实际已装系统的配置，还依赖具体设备产品树和发布时使用的冻结 manifest。

| 分类 | 发现的位置 | 普通应用能否读取 | 处理 |
| --- | --- | --- | --- |
| SDK 系统镜像构建元数据 | `build/target/product/source.properties` 中 `SystemImage.TagId=lineage` | 不等同于 Android 运行时属性；通常供 SDK 镜像管理工具识别 | 改为 `uwuaosp`，让构建工具标签与发行方一致；不宣称改变手机指纹 |
| 平台授权权限名 | `config/permissions/privapp-permissions-lineagehw.xml` 中两种 `lineageos.permission.*` | 权限声明可经授权/可见性的 API 被查询，但并不意味着任何应用均可枚举 | 暂时保留；SystemUI 和 Settings 的权限授予不可直接删改 |
| 厂商服务接口命名 | `config/framework_compatibility_matrix.xml` 中 `vendor.lineage.health`、`powershare`、`livedisplay`、`touch` | 取决于 Vendor 服务是否实际存在、SELinux/Binder 可见性和权限；VINTF 可选声明不证明服务已安装 | 保留 VINTF 名称。重命名需要同步 HAL AIDL、server、client、VINTF、sepolicy 和相关权限 |
| 系统源码内包路径 | Settings 中 `com.android.settings.lineage`，LiveDisplay 控制器等 | Java 包路径并不自动变成设备属性；不能凭源码路径认定第三方能读取 | 保留必要源依赖；按编译输出与 Android manifest 再分类 |
| 系统属性 / build identity | 用户当前 ROM `ro.build.*` 和定制属性 | 普通软件通常可读取部分 Build API / 可访问系统属性，且完整性服务有独立认证链 | 尚未核对当前设备实际值；不得从源码猜测或伪造 Android 认证、Play Integrity |

## 分类标准

1. **发行品牌、文案、纯构建标识**：若只用于描述 uwuAOSP 产物且没有外部协议依赖，可以改为准确的 uwuAOSP 名称。
2. **SDK、平台权限、HAL、SELinux、系统组件包名、OTA 信任根**：即使名字带 LineageOS，也应默认视作兼容接口。除非完成所有调用者与二进制依赖审计，否则不可替换或删除。
3. **可被第三方观察的运行时接口**：须逐项验证真实权限边界与 Android API，可经 `Build`、`PackageManager`、可读属性、公开组件或系统服务观察。不能把 `/system` 中存在某个字符串等同于运行时可识别。
4. **应用把设备判成非官方 ROM**：可能由 bootloader、Verified Boot、签名证书、设备认证状态、非标准 API、Root 状态等多因素触发，绝不是只清理 LOS 名称就能解决。

## 不做的事情

- 不修改 `ro.build.fingerprint`、`ro.product.*`、`ro.boot.verifiedbootstate` 来伪装官方认证设备。
- 不直接删 `lineageos.permission.*`、`vendor.lineage.*` 或停掉相关硬件服务。
- 不对全局应用注入隐藏/欺骗检测结果，也不通过重签核心系统应用破坏权限链。
- 不把仅用于 SDK 源码打包的 `SystemImage.TagId` 修复夸大成“手机已去 LOS 化”。

## 下一阶段（非本 PR 完成项）

- 审核发布构建配置与当前 ROM 的实际 installed packages / properties / HAL 可见性，区分 `17.0.101` 与后续 ROM 版本。
- 建立逐项 SDK / VINTF 接口依赖图；评估哪些可替换为不带品牌的通用功能，保留已发布 AIDL 接口兼容层。
- AOSP/OnePlus 原生功能完整性、SystemUI 稳定性、OTA 兼容性应优先于“修改所有命名”。
- 最终设备侧验证安排在其他源码工作完成之后，避免反复要求用户跑探针。

**完成标准**：静态检查、ROM 构建、系统服务启动、功能回归、普通应用可观测面审计与 OTA 前后兼容性均通过，才可称作实际减少了运行时 LOS 特征暴露。
