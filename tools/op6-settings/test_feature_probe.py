"""Prevent accidentally turning a read-only probe into a destructive script."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"tools/op6-settings/feature_probe.sh"
DOC=ROOT/"tools/op6-settings/FEATURE_PARITY_AUDIT_zh.md"
class ProbeReadOnlyTest(unittest.TestCase):
    def test_no_system_mutation(self):
        source=SCRIPT.read_text()
        for command in (
            "settings put ", "setprop ", "wm density ", "wm size ",
            "mount -o ", "svc power ", "cmd package install",
            "modprobe ", "insmod ", "reboot ", "su -c ", "pm uninstall ",
        ):
            self.assertNotIn(command,source)
        self.assertIn("settings get secure uwu_hide_gesture_handle",source)
        self.assertIn("OP6_Settings_Feature_Probe_",source)
    def test_capability_matrix_marks_unverified_features(self):
        source=DOC.read_text()
        for keyword in ("KeyHandler", "OnePlusDoze", "LiveDisplay",
                        "ProcStats", "OnePlusDiracGef", "SurfaceFlinger"):
            self.assertIn(keyword,source)
        self.assertIn("不能",source)
if __name__=="__main__": unittest.main()
