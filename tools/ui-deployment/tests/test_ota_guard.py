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
TARGETS = tuple(
    f"/system/system_ext/priv-app/{name}/{name}.apk"
    for name in ("SystemUI", "Settings", "Launcher3QuickStep",
                 "uwuSettingsExt", "ThemePicker")
)

class BootGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mod = self.root / "module"
        self.mod.mkdir()
        shutil.copyfile(SOURCE, self.mod / "post-fs-data.sh")
        (self.mod / "module.prop").write_text("id=uwu-ui-live-hotfix\n")
        mountify = self.root / "rom/data/adb/modules/mountify"
        mountify.mkdir(parents=True)
        (mountify / "metamount.sh").write_text("#!/system/bin/sh\n")
        config = self.root / "rom/data/adb/mountify"
        config.mkdir(parents=True)
        (config / "config.sh").write_text("mountify_mounts=2\n")
        (self.mod / "target.properties").write_text(
            "device=OnePlus6\nsdk=37\nbuild_id=CP2A.260605.016\n"
        )
        self.apks = {}
        self.original = {}
        self.staged = {}
        for target in TARGETS:
            original = self.root / "rom" / target.lstrip("/")
            original.parent.mkdir(parents=True, exist_ok=True)
            content = b"known-good-original-apk:" + target.encode()
            original.write_bytes(content)
            self.apks[target] = original
            self.original[target] = content
            staged = self.mod / target.lstrip("/")
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(b"new-original-signer-build:" + target.encode())
            self.staged[target] = staged
        self.apk = self.apks[TARGET]
        # A preserved product overlay is a release dependency of the
        # independently signed ThemePicker package (not a UI settings toggle).
        self.prism = self.root / "rom/system/product/overlay/uwuPrism__uwu_enchilada__auto_generated_rro_product.apk"
        self.prism.parent.mkdir(parents=True,exist_ok=True)
        # Preimage for actual ROM hash is not supplied to the synthetic test.
        # A fixture needs a real hash from the exact bytes, so patch the
        # pinned value only in the TEMPORARY test script, never in sources.
        self.prism.write_bytes(b"ROM101-Prism-test-fixture")
        guard=(self.mod / "post-fs-data.sh")
        text=guard.read_text().replace(
            "f328d25307f9426677ed009ef234b5e9772a9a7473fdb4b6dc22d9d4d9d4fa8b",
            hashlib.sha256(self.prism.read_bytes()).hexdigest(),
        )
        guard.write_text(text)
        (self.mod / "base-apks.sha256").write_text(
            "".join(f"{path}|{hashlib.sha256(self.original[path]).hexdigest()}\n"
                    for path in TARGETS)
        )
        (self.mod / "payload-apks.sha256").write_text(
            "".join(f"{path}|{hashlib.sha256(self.staged[path].read_bytes()).hexdigest()}\n"
                    for path in TARGETS)
        )
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
        self.apk.write_bytes(self.original[TARGET])
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
        (config / "modules.txt").write_text("uwu-ui-live-hotfix\n")
        self.assertTrue(self.run_guard().startswith("COMPATIBLE:"))

    def test_mountify_disabled_blocks(self):
        (self.root / "rom/data/adb/modules/mountify/disable").touch()
        self.assertIn("Mountify disabled", self.run_guard())

    def test_prism_overlay_hash_drift_blocks_system_mount(self):
        self.prism.write_bytes(b"conflicting-theme-overlay")
        self.assertIn("Prism baseline differs", self.run_guard())
        self.assertTrue((self.mod / "skip_mount").exists())

    def test_missing_prism_overlay_blocks(self):
        self.prism.unlink()
        self.assertIn("ThemePicker color overlay missing", self.run_guard())

    def test_removed_component_refuses_mount(self):
        self.staged[TARGETS[-1]].unlink()
        self.assertIn("staged signed APK missing", self.run_guard())

    def test_incomplete_base_manifest_refuses_mount(self):
        p=self.mod/"base-apks.sha256"
        p.write_text("\n".join(p.read_text().splitlines()[:-1])+"\n")
        self.assertIn("incomplete five-component baseline manifest", self.run_guard())

    def test_duplicate_original_entry_refuses_mount(self):
        p=self.mod/"base-apks.sha256"
        p.write_text(p.read_text()+p.read_text().splitlines()[0]+"\n")
        self.assertIn("duplicate baseline APK target", self.run_guard())

    def test_duplicate_payload_entry_refuses_mount(self):
        p=self.mod/"payload-apks.sha256"
        p.write_text(p.read_text()+p.read_text().splitlines()[0]+"\n")
        self.assertIn("duplicate payload APK target", self.run_guard())

    def test_incomplete_payload_manifest_refuses_mount(self):
        p=self.mod/"payload-apks.sha256"
        p.write_text("\n".join(p.read_text().splitlines()[:-1])+"\n")
        self.assertIn("incomplete five-component payload manifest", self.run_guard())

    def test_unknown_target_blocks(self):
        (self.mod / "base-apks.sha256").write_text("/system/etc/passwd|abc\n")
        self.assertIn("PAUSED: unexpected target path", self.run_guard())

if __name__ == "__main__":
    unittest.main()
