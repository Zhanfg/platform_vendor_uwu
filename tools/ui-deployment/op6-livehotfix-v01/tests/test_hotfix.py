"""Host simulation; never writes Android settings on the test runner."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LiveHotfixTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.mod = self.root / "module"
        shutil.copytree(ROOT, self.mod, ignore=shutil.ignore_patterns("*.zip"))
        bindir = self.root / "bin"
        bindir.mkdir()
        props = bindir / "getprop"
        props.write_text(
            '#!/bin/sh\ncase "$1" in\n'
            'ro.product.device) echo "${UWU_TEST_DEVICE:-OnePlus6}";;\n'
            'ro.build.version.sdk) echo "${UWU_TEST_SDK:-37}";;\n'
            'sys.boot_completed) echo 1;;\nesac\n'
        )
        props.chmod(0o755)
        script = bindir / "settings"
        script.write_text(
            '#!/usr/bin/env python3\n'
            'import json,os,pathlib,sys\n'
            'p=pathlib.Path(os.environ["SETTINGS_STORE"])\n'
            'a=json.loads(p.read_text()) if p.exists() else {}\n'
            'args=sys.argv[1:]\n'
            'if args[:2]==["--user","0"]:args=args[2:]\n'
            'assert len(args)>=3 and args[1]=="secure",args\n'
            'cmd,_,key=args[:3]\n'
            'if cmd=="get":print(a.get(key,"null"))\n'
            'elif cmd=="put":a[key]=args[3];p.write_text(json.dumps(a))\n'
            'elif cmd=="delete":a.pop(key,None);p.write_text(json.dumps(a))\n'
            'else:raise RuntimeError(args)\n'
        )
        script.chmod(0o755)
        self.store = self.root / "settings.json"
        self.store.write_text(json.dumps({
            "clock_seconds": "0", "uwu_hide_gesture_handle": "0"
        }))
        self.state = self.root / "state"
        self.env = os.environ | {
            "UWU_HOTFIX_TEST_PATH": str(bindir),
            "UWU_HOTFIX_TEST_STATE_DIR": str(self.state),
            "UWU_HOTFIX_TEST_MAX_WAIT": "0",
            "SETTINGS_STORE": str(self.store),
        }

    def run_script(self, name):
        run = subprocess.run(
            ["sh", str(self.mod / name)], env=self.env,
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
        return run

    def values(self):
        return json.loads(self.store.read_text())

    def test_applies_and_saves_original(self):
        self.run_script("apply.sh")
        self.assertEqual(self.values(), {
            "clock_seconds": "1", "uwu_hide_gesture_handle": "1"
        })
        self.assertEqual(
            (self.state / "original_clock_seconds").read_text().strip(), "0"
        )

    def test_repeat_boot_keeps_original(self):
        self.run_script("apply.sh")
        self.run_script("apply.sh")
        self.assertEqual(
            (self.state / "original_uwu_hide_gesture_handle").read_text().strip(), "0"
        )

    def test_restore(self):
        self.run_script("apply.sh")
        self.run_script("restore.sh")
        self.assertEqual(self.values(), {
            "clock_seconds": "0", "uwu_hide_gesture_handle": "0"
        })

    def test_missing_original_is_deleted_after_uninstall(self):
        self.store.write_text("{}")
        self.run_script("apply.sh")
        self.run_script("restore.sh")
        self.assertEqual(self.values(), {})

    def test_new_api_pauses(self):
        self.env["UWU_TEST_SDK"] = "38"
        self.run_script("apply.sh")
        self.assertEqual(self.values()["clock_seconds"], "0")
        self.assertIn("PAUSED", (self.state / "last_status.txt").read_text())

    def test_wrong_device_pauses(self):
        self.env["UWU_TEST_DEVICE"] = "PJZ110"
        self.run_script("apply.sh")
        self.assertEqual(self.values()["clock_seconds"], "0")

    def test_pill_toggle_disabled_via_config(self):
        (self.mod / "options.conf").write_text(
            "clock_seconds=1\nhide_gesture_handle=0\n"
        )
        self.run_script("apply.sh")
        self.assertEqual(self.values()["uwu_hide_gesture_handle"], "0")

    def test_no_system_payload_or_background_daemon(self):
        self.assertFalse((self.mod / "system").exists())
        source = (self.mod / "apply.sh").read_text()
        for command in ("pkill ", "killall ", "reboot ", "setprop "):
            self.assertNotIn(command, source)

if __name__ == "__main__":
    unittest.main()
