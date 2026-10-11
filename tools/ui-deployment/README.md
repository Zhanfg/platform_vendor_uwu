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
