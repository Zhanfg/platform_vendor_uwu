"""Host-side test for a single Mountify ZIP with multiple components.

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
        for filename in ("module.prop", "post-fs-data.sh", "late-load.sh", "action.sh"):
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

    def test_two_components_are_in_one_zip_without_duplicate_payloads(self):
        self.apk("SystemUI.apk")
        self.apk("Settings.apk")
        result = self.run_pack()
        self.assertEqual(result.returncode, 0, result.stderr)
        files = list((self.tree / "out").glob("*.zip"))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "uwu-ui-hotfix-oneplus6.zip")
        with ZipFile(files[0]) as z:
            names = z.namelist()
            self.assertIn("id=uwu-ui-hotfix\n", z.read("module.prop").decode())
            for comp in ("SystemUI", "Settings"):
                self.assertEqual(sum(n.endswith(f"/{comp}.apk") for n in names), 1)
            self.assertEqual(len(z.read("base-apks.sha256").splitlines()), 2)
            self.assertIn("action.sh", names)
            self.assertIn("late-load.sh", names)
            self.assertFalse(any(n.startswith("payload/") for n in names))

    def test_unchanged_apk_is_not_packaged(self):
        self.apk("SystemUI.apk")
        self.apk("Settings.apk")
        (self.tree / "staging/built/Settings.apk").write_bytes(b"BASELINE-APKS")
        result = self.run_pack()
        self.assertEqual(result.returncode, 0, result.stderr)
        with ZipFile(self.tree / "out/uwu-ui-hotfix-oneplus6.zip") as z:
            self.assertFalse(any(n.endswith("/Settings.apk") for n in z.namelist()))
            self.assertEqual(len(z.read("base-apks.sha256").splitlines()), 1)

    def test_all_unchanged_fails_closed(self):
        self.apk("Settings.apk")
        (self.tree / "staging/built/Settings.apk").write_bytes(b"BASELINE-APKS")
        result = self.run_pack()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.tree / "out/uwu-ui-hotfix-oneplus6.zip").exists())

    def test_component_toggle_moves_bytes_without_duplication(self):
        self.apk("SystemUI.apk")
        self.apk("Settings.apk")
        result = self.run_pack()
        self.assertEqual(result.returncode, 0, result.stderr)
        mod = self.base / "installed_module"
        mod.mkdir()
        with ZipFile(self.tree / "out/uwu-ui-hotfix-oneplus6.zip") as z:
            z.extractall(mod)
        path = Path("system_ext/priv-app/Settings/Settings.apk")
        live = mod / "system" / path
        inactive = mod / "inactive/system" / path
        self.assertTrue(live.is_file())
        toggle = lambda: subprocess.run(
            ["sh", str(mod / "action.sh")],
            input="2\n", capture_output=True, text=True
        )
        self.assertEqual(toggle().returncode, 0)
        self.assertFalse(live.exists())
        self.assertTrue(inactive.is_file())
        self.assertEqual(toggle().returncode, 0)
        self.assertTrue(live.is_file())
        self.assertFalse(inactive.exists())

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
