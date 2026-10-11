#!/usr/bin/env python3
"""Conservative post-build vendor Composer ABI and patch-presence gate.

Usage on a Linux HOST build machine:
  python3 verify_composer_abi.py /private/stock-composer /path/to/built-composer

The original (proprietary) binary is never copied or uploaded. This gate does
not authorize device installation; VINTF, SELinux, rollback, and display
testing remain separate requirements.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path


def abort(message):
    print("ABI BLOCKED:", message, file=sys.stderr)
    raise SystemExit(1)


def readelf(path, flags):
    proc = subprocess.run(
        ["readelf", "-W", *flags, str(path)],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode:
        abort("readelf failed for " + str(path) + ": " + proc.stderr.strip())
    return proc.stdout


def analyse(path):
    raw = path.read_bytes()
    if len(raw) < 64 or raw[:4] != b"\x7fELF":
        abort(str(path) + ": not an ELF binary")
    if raw[4] != 2 or raw[5] != 1 or int.from_bytes(raw[18:20], "little") != 183:
        abort(str(path) + ": expected ELF64 little-endian AArch64")
    h = readelf(path, ["-h"])
    if not re.search(r"Type:\s+DYN\b", h):
        abort(str(path) + ": not a PIE/DYN executable")
    d = readelf(path, ["-d"])
    needed = frozenset(re.findall(r"\(NEEDED\).*?\[(.*?)\]", d))
    if not needed or "libsdmcore.so" not in needed:
        abort(str(path) + ": no expected Qualcomm SDM dependencies")
    if "TEXTREL" in d or "(RPATH)" in d or "(RUNPATH)" in d:
        abort(str(path) + ": text relocations or search-path override")
    n = readelf(path, ["-n"])
    build_ids = re.findall(r"Build ID:\s+([0-9a-f]+)", n)
    if len(build_ids) != 1:
        abort(str(path) + ": missing or ambiguous ELF Build ID")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "needed": needed,
        "build_id": build_ids[0],
        "has_legacy_patch_marker": b"Legacy color mode" in raw,
    }


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    old, new = map(Path, sys.argv[1:])
    if not old.is_file() or not new.is_file():
        abort("stock and candidate files must both exist")
    baseline = analyse(old)
    candidate = analyse(new)
    print("Stock Build ID:", baseline["build_id"])
    print("Candidate Build ID:", candidate["build_id"])
    if baseline["sha256"] == candidate["sha256"]:
        abort("candidate is byte-identical to stock; no repair was built")
    if baseline["build_id"] == candidate["build_id"]:
        abort("candidate Build ID unchanged; build provenance ambiguous")
    missing = sorted(baseline["needed"] - candidate["needed"])
    added = sorted(candidate["needed"] - baseline["needed"])
    if missing or added:
        abort("DT_NEEDED mismatch; missing=" + repr(missing) + " extra=" + repr(added))
    if not candidate["has_legacy_patch_marker"]:
        abort("candidate missing the legacy color-mode patch diagnostic string")
    print("PASS: AArch64 ELF, SDM deps identical, Build ID changed, patch marker present.")
    print("NOTICE: this is necessary but NOT sufficient for safe boot or HDR output.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
