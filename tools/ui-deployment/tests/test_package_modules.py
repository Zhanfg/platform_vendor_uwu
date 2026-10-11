"""Native v0.6 KSU packager: fail-closed tests with synthetic APKs.

Fake apksigner exercises control flow ONLY, not genuine Android signing.
A successful flashable ZIP requires actual ROM-matching signed APK binaries.
"""
from pathlib import Path
import os, shutil, subprocess, tempfile, unittest

ROOT=Path(__file__).resolve().parents[1]
COMPONENTS=("SystemUI.apk","Settings.apk","Launcher3QuickStep.apk","uwuSettingsExt.apk","ThemePicker.apk")

class PackagerTests(unittest.TestCase):
    def setUp(self):
        work=tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.base=Path(work.name)
        self.tree=self.base/"ui-deployment"
        for directory in ("staging/original","staging/built","ksu-hotfix"):
            (self.tree/directory).mkdir(parents=True,exist_ok=True)
        for name in ("package_ui_hotfix.sh","verify_apk_signatures.sh","MD3E_NATIVE_SOURCE_LOCK.txt"):
            shutil.copy(ROOT/name,self.tree/name)
        for src in (ROOT/"ksu-hotfix").glob("*"):
            if src.is_file():
                shutil.copy(src,self.tree/"ksu-hotfix"/src.name)
        (self.tree/"staging/target.properties").write_text(
            "device=OnePlus6\nsdk=37\nbuild_id=CP2A.260605.016\n"
        )
        self.bin=self.base/"bin"
        self.bin.mkdir()
        signer=self.bin/"apksigner"
        signer.write_text(
            '#!/bin/sh\nfor arg do apk="$arg"; done\n'
            'case "$(head -c 5 "$apk")" in\n'
            'WRONG*) hex="$(printf "%064d" 0)";;\n'
            '*) hex="$(printf "%064d" 1)";;\n'
            'esac\n'
            'echo "Signer #1 certificate SHA-256 digest: $hex"\n'
            'case "$(head -c 5 "$apk")" in MULTI*) echo "Signer #2 certificate SHA-256 digest: $hex";; TENXX*) echo "Signer #10 certificate SHA-256 digest: $hex";; esac\n'
        )
        signer.chmod(0o755)
        # Mock only the documented package-ID output, not an APK resource or
        # signer. Real release builds must use Android SDK aapt2.
        aapt2=self.bin/"aapt2"
        aapt2.write_text(
            '#!/bin/sh\n'
            '[ "$1" = dump ] && [ "$2" = packagename ] || exit 2\n'
            'apk="$3"\n'
            'case "$(head -c 5 "$apk")" in OTHER*) echo "com.example.unrelated"; exit 0;; BADPK*) exit 3;; esac\n'
            'case "${apk##*/}" in\n'
            'SystemUI.apk) echo "com.android.systemui";;\n'
            'Settings.apk) echo "com.android.settings";;\n'
            'Launcher3QuickStep.apk) echo "com.android.launcher3";;\n'
            'uwuSettingsExt.apk) echo "org.uwuaosp.settingsext";;\n'
            'ThemePicker.apk) echo "com.android.wallpaper";;\n'
            '*) exit 5;;\nesac\n'
        )
        aapt2.chmod(0o755)
        self.env=os.environ|{"PATH":str(self.bin)+":"+os.environ["PATH"]}

    def apk(self,name,bad=False,same=False):
        (self.tree/"staging/original"/name).write_bytes(b"BASELINE-FAKE")
        (self.tree/"staging/built"/name).write_bytes(
            b"BASELINE-FAKE" if same else (b"WRONG-SIGNER" if bad else b"PATCHED-FAKE")
        )

    def run_pack(self):
        return subprocess.run(["sh",str(self.tree/"package_ui_hotfix.sh")],
                              env=self.env,text=True,capture_output=True)

    def no_zip(self):
        self.assertEqual(list((self.tree/"out").rglob("*.zip")),[])

    def test_five_mock_signed_components_still_fail_exact_apk_hash(self):
        for name in COMPONENTS:
            self.apk(name)
        r=self.run_pack()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("not the locked 17.0.101 APK",r.stderr)
        self.no_zip()

    def test_incomplete_apk_set_never_yields_a_flashable_zip(self):
        self.apk(COMPONENTS[0])
        self.apk(COMPONENTS[1])
        r=self.run_pack()
        self.assertNotEqual(r.returncode,0)
        self.no_zip()

    def test_signer_mismatch_always_blocks(self):
        for name in COMPONENTS:
            self.apk(name,bad=(name==COMPONENTS[1]))
        r=self.run_pack()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("signer mismatch",r.stderr.lower())
        self.no_zip()

    def test_same_signer_but_wrong_android_package_is_blocked(self):
        for name in COMPONENTS:
            self.apk(name)
        # Signing authority and file placement are not sufficient: package
        # identity must match the installed original.
        (self.tree/"staging/built/SystemUI.apk").write_bytes(b"OTHER-PACKAGE")
        r=self.run_pack()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("package identity mismatch", r.stderr)
        self.no_zip()

    def test_bad_package_manifest_cannot_pass(self):
        for name in COMPONENTS:
            self.apk(name)
        (self.tree/"staging/built/Settings.apk").write_bytes(b"BADPK-MANIFEST")
        r=self.run_pack()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Cannot read package name", r.stderr)
        self.no_zip()

    def test_invalid_second_run_never_leaves_stale_release_zip(self):
        for name in COMPONENTS:
            self.apk(name)
        out=self.tree/"out";out.mkdir()
        stale=out/"uwuAOSP hotfix v0.7.zip"
        stale.write_bytes(b"STALE-OLD-BUILD")
        r=self.run_pack()
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(stale.exists())

    def test_same_first_signer_but_extra_second_signer_rejected(self):
        for name in COMPONENTS:
            self.apk(name)
        # Simulates an APK with the right first signer plus a second signer.
        # Android package identity would not be identical to the original.
        (self.tree/"staging/built/SystemUI.apk").write_bytes(b"MULTI-SIGNER")
        r=self.run_pack()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("Signature verification failed: built SystemUI.apk",r.stderr)
        self.no_zip()

    def test_tenth_signer_is_never_accepted_as_same_certificate(self):
        for name in COMPONENTS:
            self.apk(name)
        # Historically a [2-9] regex missed signer #10 and higher.
        (self.tree/"staging/built/SystemUI.apk").write_bytes(b"TENXX-SIGNER")
        r=self.run_pack()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("Signature verification failed: built SystemUI.apk",r.stderr)
        self.no_zip()

    def test_temp_zip_is_pid_unique(self):
        src=(ROOT/"package_ui_hotfix.sh").read_text()
        self.assertIn('.uwuAOSP-hotfix-v0.7.$.zip',src)

    def test_unknown_apk_is_not_accepted(self):
        self.apk("Unrecognized.apk")
        r=self.run_pack()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("Unrecognized APK",r.stderr)
        self.no_zip()

    def test_all_unchanged_blocks_zip(self):
        for name in COMPONENTS:
            self.apk(name,same=True)
        r=self.run_pack()
        self.assertNotEqual(r.returncode,0)
        self.no_zip()

    def test_atomic_action_does_not_toggle_single_apks(self):
        module=self.base/"installed"
        module.mkdir()
        shutil.copy(ROOT/"ksu-hotfix/action.sh",module/"action.sh")
        shutil.copy(ROOT/"ksu-hotfix/module.prop",module/"module.prop")
        (module/"system/system_ext/priv-app/SystemUI").mkdir(parents=True)
        (module/"system/system_ext/priv-app/SystemUI/SystemUI.apk").write_bytes(b"REAL_CODE_PLACEHOLDER")
        r=subprocess.run(["sh",str(module/"action.sh")],input="1\n",
                         text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue((module/"system/system_ext/priv-app/SystemUI/SystemUI.apk").exists())
        self.assertFalse((module/"inactive").exists())
        self.assertIn("toggle this single module",r.stdout)

if __name__=="__main__": unittest.main()
