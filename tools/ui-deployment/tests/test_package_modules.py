"""Host-side test for independently staged Mountify modules.

Uses a fake apksigner solely to test control flow; it DOES NOT validate real APKs.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]

class PackagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.tree = self.base / "ui-deployment"
        (self.tree / "staging/original").mkdir(parents=True)
        (self.tree / "staging/built").mkdir(parents=True)
        (self.tree / "ksu-hotfix").mkdir()
        for filename in ("package_ui_hotfix.sh", "verify_apk_signatures.sh"):
            shutil.copy(ROOT / filename, self.tree / filename)
        for filename in ("module.prop", "post-fs-data.sh", "late-load.sh"):
            shutil.copy(ROOT / "ksu-hotfix" / filename, self.tree / "ksu-hotfix" / filename)
        (self.tree / "staging/target.properties").write_text(
            "device=OnePlus6\nsdk=37\nbuild_id=CP2A.260605.016\n"
        )
        self.bin = self.base / "bin"
        self.bin.mkdir()
        signer = self.bin / "apksigner"
        signer.write_text(
            '#!/bin/sh\n'
            'for arg do apk="$arg"; done\n'
            'case "$(head -c 7 "$apk")" in\n'
            '  WRONG*) hex="$(printf "%064d" 0)";;\n'
            '  *) hex="$(printf "%064d" 1)";;\n'
            'esac\n'
            'echo "Signer #1 certificate SHA-256 digest: $hex"\n'
        )
        signer.chmod(0o755)
        self.env = os.environ | {"PATH": str(self.bin) + ":" + os.environ["PATH"]}

    def apk(self, name, bad_signer=False):
        (self.tree / "staging/original" / name).write_bytes(b"BASELINE-APKS")
        (self.tree / "staging/built" / name).write_bytes(
            b"WRONGxx-APKS" if bad_signer else b"PATCHED-APKS"
        )

    def run_pack(self):
        return subprocess.run(
            ["sh", str(self.tree / "package_ui_hotfix.sh")],
            env=self.env, text=True, capture_output=True
        )

    def test_two_components_are_independent_zip_modules(self):
        self.apk("SystemUI.apk")
        self.apk("Settings.apk")
        result = self.run_pack()
        self.assertEqual(result.returncode, 0, result.stderr)
        releases = list((self.tree / "out").glob("release.*"))
        self.assertEqual(len(releases), 1)
        files = sorted(p.name for p in releases[0].glob("*.zip"))
        self.assertEqual(files, [
            "uwu-ui-hotfix-settings.zip", "uwu-ui-hotfix-systemui.zip",
        ])
        for comp, name in (("settings", "Settings.apk"), ("systemui", "SystemUI.apk")):
            with ZipFile(releases[0] / f"uwu-ui-hotfix-{comp}.zip") as z:
                self.assertIn(f"id=uwu-ui-hotfix-{comp}", z.read("module.prop").decode())
                self.assertIn(name, " ".join(z.namelist()))
                self.assertEqual(len(z.read("base-apks.sha256").splitlines()), 1)
                self.assertIn("late-load.sh", z.namelist())

    def test_signature_mismatch_blocks_package(self):
        self.apk("Settings.apk", bad_signer=True)
        result = self.run_pack()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("signer mismatch", result.stderr.lower())
        self.assertEqual(list((self.tree / "out").rglob("*.zip")), [])

    def test_unknown_apk_blocks_package(self):
        self.apk("Unrecognized.apk")
        result = self.run_pack()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unrecognized APK", result.stderr)

if __name__ == "__main__":
    unittest.main()
