#!/usr/bin/env python3
"""Reject a false 'SystemUI fully fixed' release when only resource overlays are built.

No parameters. Statically validates the next KernelSU resource-only package plan.
This does not verify signer private keys, APKs or real-device overlay activation.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def validate(data):
    errors = []
    module = data["module"]
    if module["id"] != "uwu-ui-live-hotfix":
        errors.append("KSU module ID changed; in-place upgrade would break")
    if module["name_prefix"] != "uwuAOSP hotfix":
        errors.append("nonstandard module display name")
    if module["uses_lsp"] or module["auto_restart_systemui"]:
        errors.append("runtime hook or background SystemUI restart not permitted")
    if module["delivery"] != "single_ksu_zip":
        errors.append("deliver one KernelSU ZIP")
    if data["device"] != "OnePlus6" or data["sdk"] != 37:
        errors.append("target device/API mismatch")
    if data["density"] != 420:
        errors.append("DPI must be 420")
    if data["build_id"] != "CP2A.260605.016":
        errors.append("ROM baseline changed without review")
    certs = []
    for name in ("SystemUI.apk", "Settings.apk"):
        app = data["originals"].get(name)
        if not app or not re.fullmatch(r"[0-9a-f]{64}", app["sha256"]):
            errors.append("missing original APK checksum: " + name)
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", app["cert_sha256"]):
            errors.append("invalid certificate fingerprint: " + name)
        certs.append(app["cert_sha256"])
    if len(certs) == 2 and certs[0] != certs[1]:
        errors.append("SystemUI and Settings platform signing chain diverged")
    owners = set()
    statuses = {}
    for item in data["changes"]:
        ident, owner, route, ship = (item["id"], item["owner"], item["route"],
                                    item["ship_in_current_zip"])
        if ident in statuses:
            errors.append("duplicate patch id: " + ident)
        statuses[ident] = item["status"]
        owners.add(owner)
        if ship and route not in ("rro", "configuration"):
            errors.append("blocked: cannot ship unsigned code/HAL patch: " + ident)
        if route == "privileged_apk_code":
            if not item.get("requires_matching_signer"):
                errors.append("missing signer requirement for " + ident)
            if ship:
                errors.append("privileged APK code cannot be added without a signed build: " + ident)
        if route == "rro" and not item.get("needs_runtime_overlay_verification"):
            errors.append("RRO must be tested by real idmap/OverlayManager: " + ident)
    required = {"SystemUI", "Settings", "Launcher3QuickStep", "uwuSettingsExt",
                "framework-res", "vendor HAL"}
    if not required.issubset(owners):
        errors.append("MD3E/capability scope omitted: " + str(required - owners))
    if statuses.get("momentarc_thread_and_cleanup") != "source_pr_7_uncompiled":
        errors.append("do not claim integrated SystemUI ANR fix shipped")
    return errors

if __name__ == "__main__":
    plan = json.loads((ROOT / "patch_plan.json").read_text(encoding="utf-8"))
    errors = validate(plan)
    for message in errors:
        print("BLOCKED:", message)
    if errors:
        raise SystemExit(1)
    included = [x["id"] for x in plan["changes"] if x["ship_in_current_zip"]]
    blocked = [x["id"] for x in plan["changes"] if not x["ship_in_current_zip"]]
    print("KSU RESOURCE-ONLY PLAN VALID. Shippable entries:", ", ".join(included))
    print("NOT SHIPPED / NOT VERIFIED:", ", ".join(blocked))
    print("No claim of successful runtime fix until Android 17 device verification.")
