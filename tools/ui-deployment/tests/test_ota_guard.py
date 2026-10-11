"""No-root host tests of the KernelSU pre-mount OTA compatibility guard."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "ksu-hotfix" / "post-fs-data.sh"
TARGET = "/system/system_ext/priv-app/Settings/Settings.apk"

class BootGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mod = self.root / "module"
        self.mod.mkdir()
        shutil.copyfile(SOURCE, self.mod / "post-fs-data.sh")
        (self.mod / "module.prop").write_text("id=uwu-ui-hotfix-settings\n")
        mountify = self.root / "rom/data/adb/modules/mountify"
        mountify.mkdir(parents=True)
        (mountify / "metamount.sh").write_text("#!/system/bin/sh\n")
        config = self.root / "rom/data/adb/mountify"
        config.mkdir(parents=True)
        (config / "config.sh").write_text("mountify_mounts=2\n")
        (self.mod / "target.properties").write_text(
            "device=OnePlus6\nsdk=37\nbuild_id=CP2A.260605.016\n"
        )
        self.apk = self.root / "rom" / TARGET.lstrip("/")
        self.apk.parent.mkdir(parents=True)
        self.apk.write_bytes(b"known-good-original-apk")
        digest = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        (self.mod / "base-apks.sha256").write_text(f"{TARGET}|{digest}\n")
        bindir = self.root / "bin"
        bindir.mkdir()
        self.props = bindir / "getprop"
        self.props.write_text(
            '#!/bin/sh\ncase "$1" in\n'
            'ro.product.device) echo OnePlus6;;\n'
            'ro.build.version.sdk) echo 37;;\n'
            'ro.build.id) echo CP2A.260605.016;;\n'
            "esac\n"
        )
        self.props.chmod(0o755)
        self.env = os.environ | {
            "PATH": f"{bindir}:{os.environ['PATH']}",
            "UWU_GUARD_TEST_ROOT": str(self.root / "rom"),
        }

    def run_guard(self):
        r = subprocess.run(
            ["sh", str(self.mod / "post-fs-data.sh")],
            env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return (self.mod / "last_guard_status.txt").read_text().strip()

    def test_matching_rom_enables(self):
        self.assertTrue(self.run_guard().startswith("COMPATIBLE:"))
        self.assertFalse((self.mod / "skip_mount").exists())

    def test_ota_hash_change_blocks(self):
        self.apk.write_bytes(b"new-upstream-ROM")
        self.assertIn("PAUSED: baseline APK hash mismatch", self.run_guard())
        self.assertTrue((self.mod / "skip_mount").exists())

    def test_build_id_change_blocks(self):
        self.props.write_text(
            self.props.read_text().replace("CP2A.260605.016", "NEXT_BUILD")
        )
        self.assertIn("PAUSED: different ROM build ID", self.run_guard())

    def test_previous_pause_is_sticky(self):
        self.apk.write_bytes(b"changed")
        self.run_guard()
        self.apk.write_bytes(b"known-good-original-apk")
        self.assertIn("COMPATIBLE BUT PAUSED", self.run_guard())
        self.assertTrue((self.mod / "skip_mount").exists())

    def test_without_metamodule_handler_blocks(self):
        (self.root / "rom/data/adb/modules/mountify/metamount.sh").unlink()
        self.assertIn("Mountify metamodule handler not found", self.run_guard())
        self.assertTrue((self.mod / "skip_mount").exists())

    def test_manual_mode_without_our_module_blocks(self):
        config = self.root / "rom/data/adb/mountify"
        (config / "config.sh").write_text("mountify_mounts=1\n")
        (config / "modules.txt").write_text("some-other-module\n")
        self.assertIn("Mountify manual list excludes this module", self.run_guard())

    def test_manual_mode_with_module_id_allows(self):
        config = self.root / "rom/data/adb/mountify"
        (config / "config.sh").write_text("mountify_mounts=1\n")
        (config / "modules.txt").write_text("uwu-ui-hotfix-settings\n")
        self.assertTrue(self.run_guard().startswith("COMPATIBLE:"))

    def test_mountify_disabled_blocks(self):
        (self.root / "rom/data/adb/modules/mountify/disable").touch()
        self.assertIn("Mountify disabled", self.run_guard())

    def test_unknown_target_blocks(self):
        (self.mod / "base-apks.sha256").write_text("/system/etc/passwd|abc\n")
        self.assertIn("PAUSED: unexpected target path", self.run_guard())

if __name__ == "__main__":
    unittest.main()
