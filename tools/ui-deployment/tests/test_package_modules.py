"""Native v0.6 KSU packager: fail-closed tests with synthetic APKs.

Fake apksigner exercises control flow ONLY, not genuine Android signing.
A successful flashable ZIP requires actual ROM-matching signed APK binaries.
"""
from pathlib import Path
import os, shutil, subprocess, tempfile, unittest

ROOT=Path(__file__).resolve().parents[1]
COMPONENTS=("SystemUI.apk","Settings.apk","Launcher3QuickStep.apk","uwuSettingsExt.apk")

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
        )
        signer.chmod(0o755)
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

    def test_four_mock_signed_components_still_fail_exact_apk_hash(self):
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
