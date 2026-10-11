#!/usr/bin/env python3
"""Read-only audit of ROM identity signals in source and optional built images.

No identity patching, package removal, attestation spoofing, or property writes.
Use ANDROID_PRODUCT_OUT=<path> for a completed ROM build; otherwise only
known source signals are reported. Suitable for CI, not an on-device probe.
"""
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_PARTITIONS = ("system", "system_ext", "product", "vendor", "odm")

SOURCE_MARKERS = (
    ("sdk_image_tag", "build/target/product/source.properties",
     "SystemImage.TagId=uwu", "build-only", "SDK image metadata, not Android runtime"),
    ("lineage_permission_contract", "config/permissions/privapp-permissions-lineagehw.xml",
     "lineageos.permission.MANAGE_LIVEDISPLAY", "service-contract",
     "Do not rename without migrating both permission definition and callers"),
    ("lineage_hal_contract", "config/framework_compatibility_matrix.xml",
     "vendor.lineage.livedisplay", "service-contract",
     "Optional declared VINTF interface: not proof service is installed"),
    ("lineage_plugin_allowlist",
     "overlay/common/frameworks/base/packages/SystemUI/res/values/config.xml",
     "org.lineageos.settings.device", "internal-resource",
     "Allowlist entry alone does not prove an installed package"),
    ("insecure_adb_on_nonuser",
     "config/common.mk", "ro.adb.secure=0", "security-review",
     "Check non-user build authentication policy separately"),
)

def scan_source(root=ROOT):
    findings = []
    for marker_id, rel, needle, exposure, note in SOURCE_MARKERS:
        p = Path(root) / rel
        try:
            present = needle in p.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            present = False
        findings.append({
            "id": marker_id, "source": rel, "matched": present,
            "scope": exposure, "note": note,
        })
    return findings


def scan_build_properties(product_out):
    """Only inspect packaged build.prop / default.prop, not private user data."""
    findings = []
    root = Path(product_out)
    for partition in PRODUCT_PARTITIONS:
        for rel in ("build.prop", "etc/build.prop", "default.prop"):
            p = root / partition / rel
            if not p.is_file():
                continue
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                kind = None
                if key.startswith(("ro.lineage.", "persist.lineage.")):
                    kind = "lineage-property"
                elif key in ("ro.build.fingerprint", "ro.system.build.fingerprint",
                             "ro.product.brand", "ro.product.manufacturer",
                             "ro.build.display.id", "ro.build.tags", "ro.build.type"):
                    kind = "generic-build-identity"
                elif key == "ro.adb.secure" and value == "0":
                    kind = "adb-authentication-review"
                elif key in ("ro.modversion", "ro.rom.version") and "lineage" in value.lower():
                    kind = "lineage-version-branding"
                if kind:
                    findings.append({"location": str(p.relative_to(root)),
                                     "key": key, "value": value, "kind": kind})
    return findings


def scan_packages_and_vintf(product_out):
    root = Path(product_out)
    findings = []
    for partition in PRODUCT_PARTITIONS:
        for app_tree in ("app", "priv-app"):
            parent = root / partition / app_tree
            if not parent.exists():
                continue
            for path in parent.iterdir():
                # File or directory name is a hint, not a parsed package ID.
                if "lineage" in path.name.lower() or "org.lineageos" in path.name.lower():
                    findings.append({"location": str(path.relative_to(root)),
                                     "kind": "package-filename-hint"})
        vintf = root / partition / "etc" / "vintf"
        if not vintf.exists():
            continue
        for path in vintf.rglob("*.xml"):
            if "vendor.lineage." in path.read_text(encoding="utf-8", errors="replace"):
                findings.append({"location": str(path.relative_to(root)),
                                 "kind": "lineage-vintf-declaration"})
    return findings


def audit(root=ROOT, product_out=None):
    report = {
        "description": "Identity surface audit; a marker is NOT proof of app visibility or integrity failure",
        "source": scan_source(root),
        "runtime_image_examined": bool(product_out),
        "build_properties": [],
        "packages_and_vintf": [],
    }
    if product_out is not None:
        product = Path(product_out)
        if not product.is_dir():
            raise ValueError("ANDROID_PRODUCT_OUT is not a directory")
        report["build_properties"] = scan_build_properties(product)
        report["packages_and_vintf"] = scan_packages_and_vintf(product)
    return report


if __name__ == "__main__":
    print(json.dumps(audit(product_out=os.environ.get("ANDROID_PRODUCT_OUT")),
                     ensure_ascii=False, indent=2))
