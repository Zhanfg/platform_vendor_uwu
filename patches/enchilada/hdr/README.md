# OnePlus 6 HDR HWC legacy metadata compatibility (DRAFT)

## Baseline and actual evidence
- OnePlus 6 A6003 / Android 17 uwuAOSP 101 line / Linux 4.19.325.
- Runtime: Qualcomm composer and SurfaceFlinger are both running.
- HWC advertises HDR10, HDR10+, HLG and lists actual calibration names
  CTS, DCI_P3, SRGB, bt2020_hlg and bt2020_pq.
- Every enumerated mode in the phone log reports RenderIntent: -1.
- The HWC color-mode map dump is empty and Android exposes only NATIVE (0).
- HDR/SDR ratio is not available, and HdrBrightnessData is null.
- Current dynamic_range=SDR was captured on an SDR desktop; that alone is
  *not* a valid proof that all HDR content would remain SDR.

## Candidate root cause
Some Qualcomm HWC2 implementations reject any negative RenderIntent while
initializing the color-mode map. The observed -1 attributes can therefore
leave the map empty even though SDM returns PQ/HLG mode names.
In the reference code, a color-mode map of size <= 1 also prevents dynamic
range color-mode switching.

## Scoped patch
`0001-legacy-hdr-render-intent.patch` changes only the metadata-to-mode
mapping. For modes enumerated by the real SDM driver with:
- RenderIntent exactly -1;
- PictureQuality exactly standard;
- recognized native, sRGB, DCI-P3 or BT.2020 transfer attributes;
it falls back to COLORIMETRIC. Unrecognized or nonstandard modes remain
rejected. It does not fake HDR flags, change the panel, modify color depth,
overclock the panel, or enable HBM.

Candidate source path: `hardware/qcom/sm7250/display/composer/hwc_display.cpp`,
`LineageOS/android_hardware_qcom_sm7250_display`, `lineage-24.0`.
This is a source-level *candidate*, not proof that the installed vendor
composer binary was built from exactly that source or version.

## Before integration or flashing
1. Resolve the exact source and ABI of the installed
   vendor.qti.hardware.display.composer-service and linked libraries.
2. Confirm the color-mode parser matches the candidate code. Reject this
   patch if the source or firmware mismatch.
3. `git apply --check` in the pinned HWC source tree and compile HWC against
   the full Android 17 device/vendor baseline.
4. Validate VINTF, SELinux, service start, recovery and reproducible build.
5. Boot on a rollback-safe test slot or restore image and inspect
   `dumpsys SurfaceFlinger` HWC color-mode mappings.
6. Only after mappings appear, test trusted PQ/HLG video surfaces and prove
   HDR dataspace, dynamic_range=HDR, no unintended SDR tone mapping,
   correct colorimetry, power and thermal behavior.
7. Address independent HDR brightness ratio / displayconfig support after
   real HDR output is established. Do not fabricate HDR/SDR ratio.

No patch is applied automatically by this repository staging change.
Do not replace an existing vendor service with an unverified binary.
