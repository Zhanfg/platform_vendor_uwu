"""Fail-closed source contracts for OnePlus 6 17.0.101 native KSU hotfix.
This does not compile/simulate all Android platform APIs or prove boot.
"""
from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/"ksu-hotfix"
PKG=(ROOT/"package_ui_hotfix.sh").read_text()
VERIFY=(ROOT/"verify_apk_signatures.sh").read_text()
GUARD=(MOD/"post-fs-data.sh").read_text()
SERVICE=(MOD/"service.sh").read_text()
INSTALL=(MOD/"customize.sh").read_text()
LOCK=(ROOT/"MD3E_NATIVE_SOURCE_LOCK.txt").read_text()

class NativeHotfixContract(unittest.TestCase):
    def test_module_id_and_only_one_mount_channel(self):
        p=(MOD/"module.prop").read_text()
        self.assertIn("id=uwu-ui-live-hotfix",p)
        self.assertIn("name=uwuAOSP hotfix v0.6",p)
        self.assertIn("Mountify",GUARD)
        self.assertNotIn("LSPosed",SERVICE)
        self.assertNotIn("XposedHelpers",PKG)

    def test_all_four_signed_apps_required_no_partial_zip(self):
        self.assertIn('count" -eq 4',PKG)
        self.assertIn('sh "$ROOT/verify_apk_signatures.sh"',PKG)
        self.assertIn("BLOCKED signer mismatch",VERIFY)
        self.assertIn("apksigner verify --print-certs",VERIFY)
        for f in ("SystemUI.apk","Settings.apk","Launcher3QuickStep.apk","uwuSettingsExt.apk"):
            self.assertIn(f,PKG)
        self.assertIn("payload-apks.sha256",PKG)
        self.assertIn("base-apks.sha256",PKG)

    def test_exact_source_commit_locks(self):
        for sha in (
            "ccaa206b36db45ed6add3eec3e2b4812f31b00c0",
            "c3cfe7b63318bb17f6e8e542f4a7e33e1b38f94d",
            "601c7068193663506e154f1333f7dcc070f7fb49",
            "289a20b44e68ce8b3836335b32793bbfd243213c"
        ):
            self.assertIn(sha,LOCK)
        self.assertIn("420",LOCK)

    def test_installed_rom_guard_at_boot(self):
        self.assertIn("CP2A.260605.016",SERVICE)
        self.assertIn('getprop ro.build.id',GUARD)
        self.assertIn('expected_id',GUARD)
        self.assertIn("Mountify",GUARD)
        self.assertIn("sha256sum",GUARD)
        self.assertIn('block ',GUARD)
        self.assertIn("uwu-ui-hotfix",INSTALL)
        self.assertIn("Conflicting retired",INSTALL)

    def test_no_legacy_unverified_ui_flags(self):
        self.assertIn('sysui_ok=0',SERVICE)
        self.assertIn('payload-apks.sha256',SERVICE)
        self.assertIn('if [ "$sysui_ok" = 1 ]',SERVICE)
        self.assertIn("v06_ui_flags_applied",SERVICE)
        self.assertIn("v06_density_written",SERVICE)
        self.assertIn("wm density 420",SERVICE)
        self.assertNotIn("pkill",SERVICE)
        self.assertNotIn("killall",SERVICE)

    def test_all_posix_shell_scripts_parse(self):
        for f in [ROOT/"package_ui_hotfix.sh",ROOT/"verify_apk_signatures.sh",*MOD.glob("*.sh")]:
            r=subprocess.run(["sh","-n",str(f)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,f"{f}: {r.stderr}")

    def test_missing_real_apks_cannot_build_release(self):
        # Calling the packager against an unpopulated staging directory
        # must always fail. Do NOT turn absent binaries into fake modules.
        p=subprocess.run(["sh",str(ROOT/"package_ui_hotfix.sh")],
                         cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((ROOT/"out"/"uwuAOSP hotfix v0.6.zip").exists())

if __name__=="__main__": unittest.main()
