"""Offline shell-path regression tests. Not a substitute for a KernelSU device install."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class HotfixTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.mod = self.root / "module"
        shutil.copytree(ROOT, self.mod, ignore=shutil.ignore_patterns("tests", "out", "*.zip"))
        bindir = self.root / "bin"
        bindir.mkdir()
        getprop = bindir / "getprop"
        getprop.write_text(
            '#!/bin/sh\ncase "$1" in\n'
            'ro.product.device) echo "${TEST_DEVICE:-OnePlus6}";;\n'
            'ro.build.version.sdk) echo "${TEST_SDK:-37}";;\n'
            'sys.boot_completed) echo 1;;\nesac\n'
        )
        getprop.chmod(0o755)
        settings = bindir / "settings"
        settings.write_text(
            '#!/usr/bin/env python3\n'
            'import os,json,sys\n'
            'from pathlib import Path\n'
            'p=Path(os.environ["TEST_DB"])\n'
            'd=json.loads(p.read_text())\n'
            'a=sys.argv[1:]\n'
            'if a[:2]==["--user","0"]:a=a[2:]\n'
            'assert a[1]=="secure",a\n'
            'op,_,key=a[:3]\n'
            'if op=="get": print(d.get(key,"null"))\n'
            'elif op=="put":\n'
            '  if os.environ.get("FAIL_PUT")==key:sys.exit(3)\n'
            '  d[key]=a[3];p.write_text(json.dumps(d))\n'
            'elif op=="delete":d.pop(key,None);p.write_text(json.dumps(d))\n'
        )
        settings.chmod(0o755)
        self.db = self.root / "db.json"
        self.db.write_text(json.dumps({"clock_seconds": "0", "uwu_hide_gesture_handle": "0"}))
        self.state = self.root / "state"
        self.env = os.environ | {
            "UWU_HOTFIX_TESTING": "1",
            "UWU_HOTFIX_TEST_PATH": str(bindir),
            "UWU_HOTFIX_TEST_STATE_DIR": str(self.state),
            "UWU_HOTFIX_TEST_MAX_WAIT": "0",
            "TEST_DB": str(self.db),
            "PATH": str(bindir) + ":" + os.environ["PATH"],
        }

    def run_script(self, name, expect=0):
        result = subprocess.run(["sh", str(self.mod / name)],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, expect, result.stderr + result.stdout)

    def value(self, key):
        return json.loads(self.db.read_text()).get(key)

    def change(self, key, value):
        d=json.loads(self.db.read_text())
        d[key]=value
        self.db.write_text(json.dumps(d))

    def test_first_apply(self):
        self.run_script("apply.sh")
        self.assertEqual(self.value("clock_seconds"), "1")
        self.assertEqual(self.value("uwu_hide_gesture_handle"), "1")
        self.assertEqual((self.state / "original_clock_seconds").read_text().strip(), "0")

    def test_repeat_apply_preserves_original(self):
        self.run_script("apply.sh")
        self.run_script("apply.sh")
        self.assertEqual((self.state / "original_clock_seconds").read_text().strip(), "0")

    def test_uninstall_restores(self):
        self.run_script("apply.sh")
        self.run_script("restore.sh")
        self.assertEqual(self.value("clock_seconds"), "0")
        self.assertEqual(self.value("uwu_hide_gesture_handle"), "0")

    def test_user_override(self):
        self.run_script("apply.sh")
        self.change("clock_seconds", "0")
        self.run_script("apply.sh")
        self.assertEqual(self.value("clock_seconds"), "0")
        self.assertTrue((self.state / "user_override_clock_seconds").exists())

    def test_provider_failure_retried(self):
        self.env["FAIL_PUT"] = "clock_seconds"
        self.run_script("apply.sh")
        self.assertIn("PARTIAL_FAILURE", (self.state / "last_status.txt").read_text())
        self.assertTrue((self.state / "pending_clock_seconds").exists())
        del self.env["FAIL_PUT"]
        self.run_script("apply.sh")
        self.assertEqual(self.value("clock_seconds"), "1")

    def test_v01_upgrade_preserves_original(self):
        self.state.mkdir()
        (self.state / "original_clock_seconds").write_text("0\n")
        self.change("clock_seconds", "1")
        self.run_script("apply.sh")
        self.assertTrue((self.state / "managed_clock_seconds").exists())
        self.run_script("restore.sh")
        self.assertEqual(self.value("clock_seconds"), "0")

    def test_manual_off_survives_boot(self):
        self.run_script("apply.sh")
        self.run_script("action.sh")
        self.run_script("apply.sh")
        self.assertEqual(self.value("uwu_hide_gesture_handle"), "0")
        self.assertTrue((self.state / "manual_off_uwu_hide_gesture_handle").exists())

    def test_manual_off_survives_upgrade_default(self):
        self.run_script("apply.sh")
        self.run_script("action.sh")
        (self.mod / "options.conf").write_text("clock_seconds=1\nhide_gesture_handle=1\n")
        self.run_script("apply.sh")
        self.assertEqual(self.value("uwu_hide_gesture_handle"), "0")
        self.run_script("action.sh")
        self.assertEqual(self.value("uwu_hide_gesture_handle"), "1")

    def test_failed_action_does_not_flip_config(self):
        self.run_script("apply.sh")
        self.env["FAIL_PUT"] = "uwu_hide_gesture_handle"
        self.run_script("action.sh", expect=1)
        self.assertIn("hide_gesture_handle=1", (self.mod / "options.conf").read_text())

    def test_new_api_pauses(self):
        self.env["TEST_SDK"] = "38"
        self.run_script("apply.sh")
        self.assertEqual(self.value("clock_seconds"), "0")

    def test_module_id_persistent_and_no_system_payload(self):
        prop=(self.mod / "module.prop").read_text()
        self.assertIn("name=uwuAOSP hotfix v0.2", prop)
        self.assertIn("id=uwu-ui-live-hotfix", prop)
        self.assertFalse((self.mod / "system").exists())

    def test_produces_installer_zip(self):
        result = subprocess.run(["sh", str(self.mod / "package.sh")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = self.mod / "out" / "uwuAOSP hotfix v0.2.zip"
        with zipfile.ZipFile(out) as z:
            self.assertEqual(len(z.namelist()), 10)
            self.assertEqual(len(z.namelist()), len(set(z.namelist())))
            self.assertTrue(all("/" not in name for name in z.namelist()))
            self.assertIsNone(z.testzip())


if __name__ == "__main__":
    unittest.main()
