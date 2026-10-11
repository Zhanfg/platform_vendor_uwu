# uwuAOSP 17 UI deployment — verification first

Target: OnePlus 6 / Android 17 `uwu-17.0`. All work stays on development branches until module builds, signing and device QA pass.

## Deployment choices

| Change | First-choice deployment | Mandatory gate |
| --- | --- | --- |
| Theme colors, dimensions and permitted layout resources | Build an RRO with a correct overlay target/overlayable policy; then test via a rollback-capable, systemless module | Resource linking, overlay policy, idmap state, no conflict with active RROs |
| Code changes to SystemUI, Settings or Launcher3 | Build the module within the **matching ROM source tree** and sign with the **same APK certificate** as the installed original; only then stage a systemless test | Package certificate identity, installed APK paths, ROM fingerprint, signed artifacts, recovery plan |
| Cross-component changes, platform signing key changes, framework modifications | Full ROM build, signed `target_files`, correctly trusted OTA signature, then stock verified A/B sideload | Recovery key trust, AVB/vbmeta consistency, slot mapping, rollback and backup |

**Do not remove APK signature checks, Recovery OTA signature checks or AVB in the installed daily-driver ROM.**
Disabling sideload's ZIP signature verification **does not** fix a mismatched SystemUI/platform APK certificate or privileged package permissions. An unsigned `adb sideload` package is not the same thing as `adb install`.

## Signed APK compatibility check

1. Gather original installed APKs with a **read-only device probe**. Always prefer `pm path` for the currently active package, and record the build fingerprint and partition path. The system partition's file may be stale if the package was updated.
2. Build APKs from the exact `uwu-17.0` tree. Put original, currently installed APKs in `tools/ui-deployment/staging/original/`, and newly built APKs in `.../staging/built/`, keeping identical filenames.
3. On a Linux build host with Android build-tools `apksigner`, `sha256sum` and POSIX shell, run `sh tools/ui-deployment/verify_apk_signatures.sh` with **no parameters**.
4. Any certificate mismatch, missing baseline or verification failure **blocks** systemless APK mounting. The script records only public certificate digests and APK hashes; it does not load signing private keys.

For systemless experiments, the exact path hierarchy must match the live device (such as `/system/system_ext/priv-app/SystemUI/SystemUI.apk`). Verify which KernelSU/Magisk mounting mechanism is active; do not assume a static overlay location works across root variants. Preserve an out-of-band disable/uninstall path, plus an unchanged signed bootable slot/recovery.

## ADB sideload with a trusted development key

The recovery OTA key is a separate public trust root. For development, configure a **recovery you control** to trust the public half of your dedicated development OTA key, and sign the complete OTA with its private half using Android release tooling (`sign_target_files_apks` / `ota_from_target_files`). Keep private signing material **outside Git**, secure storage and public CI logs.

Changing the recovery's verification policy is not a substitute for platform package signing or AVB correctness. A production build should retain verification; prefer a documented, revocable development signing key over unconditional acceptance of unsigned packages.

## Rollback gates

- No partition remount as writable and no blind copy into `/system`, `system_ext`, `product` or `vendor`.
- No install if the base fingerprint or original APK hash differs from the validated baseline.
- First test a small RRO or a separately signed development APK, not SystemUI replacement.
- Record build commit IDs, exact signing certificate digests, original APK checksums and expected device path.
- After systemless install, reboot, verify `pm path`, package signature, SystemUI crash logs, shade gestures and the Settings home/secondary-page UX.
- An unbootable test must be recoverable by disabling the module in recovery/KernelSU safe mode; maintain a prior known-good system slot/backup. A/B does not automatically guarantee rollback after changing shared userdata.

This is a staging workflow, not a finished flashable ROM or a bypass for signature checks.

## OTA-aware KernelSU hotfix channel

The `ksu-hotfix/` template and `package_ui_hotfix.sh` implement a separate
**systemless hot-update layer**. Upstream A/B OTA continues unchanged and keeps
its recovery signature / APK signature / AVB checks. The hotfix never flashes
or modifies an A/B slot.

1. Build each selected APK against the current uwuAOSP 17.0 ROM source and
   sign it with the matching **original APK certificate**.
2. Stage original APKs as `staging/original/<APK-name>`, built APKs as
   `staging/built/<APK-name>`, and copy
   `ksu-hotfix/target.properties.example` to
   `staging/target.properties` after checking device properties.
3. Run `sh tools/ui-deployment/package_ui_hotfix.sh` on a Linux build host,
   with no arguments. Output: `tools/ui-deployment/out/uwu-ui-hotfix.zip`.
   It will fail if no APK pair, invalid platform signature, unexpected build,
   or missing build dependencies are found.
4. Inspect ZIP contents and test only after checking the currently installed
   KernelSU **mounting metamodule** and rollback/safe-mode procedure.

**Before each mount**: the regular module's `post-fs-data.sh` runs before
the KernelSU metamodule's `metamount.sh` in the documented KernelSU boot
sequence. The guard checks device, API, ROM build ID, and the original
per-component APK SHA-256. On mismatch, it writes `skip_mount` and preserves
the upstream ROM view, without disabling verified boot. The pause is sticky,
and a user must explicitly re-enable after installing a revalidated build.

**On upstream OTA**: leave the module installed but let the guard suspend it
if any original APK or ROM build ID has changed. Rebuild and revalidate our
UI changes for the new OTA. Never blindly remount a previous ROM's SystemUI.

**Scope limits**:
- Applies only to four known `system_ext/priv-app` APK paths; no generic
  platform APK replacement or untrusted path input.
- Does not provide an instant code hot-swap: a privileged APK replacement
  generally requires at least a controlled restart to take effect.
- The read-only probe found `ksud` and `/data/adb/ksu`, **not** proof that
  a functioning KernelSU mount metamodule is installed.
- A signed, verified **RRO-only** live-resource channel may be added later;
  it requires overlayable/idmap/target-policy verification before deployment.
- The phone's reported `ro.build.fingerprint` is an Android 11 identity
  despite Android 17, so compatibility is based on build ID + exact base APK
  hashes, not fingerprint alone.

