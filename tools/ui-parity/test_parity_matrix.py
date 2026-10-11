"""Keep SystemUI stability tasks and OEM dependency caveats visible."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
DOC=(ROOT/"tools/ui-parity/ROM_PARITY_STABILITY_MATRIX_zh.md").read_text(encoding="utf-8")

class ParityMatrixTests(unittest.TestCase):
    def test_two_reference_roms_and_actual_oneplus_device_tree(self):
        for name in ("crdroidandroid/crdroid_features","evolution-x.org/features",
                     "android_device_oneplus_sdm845-common"):
            self.assertIn(name,DOC)

    def test_stability_and_power_gates_cannot_disappear(self):
        for item in ("MomentArc","SystemUI","CLOCK_SECONDS","主线程",
                     "Mountify TMPFS","全量编译","上游 OTA"):
            if item=="CLOCK_SECONDS":
                self.assertIn("clock_seconds",DOC)
            else:
                self.assertIn(item,DOC)

    def test_not_all_marketing_features_faked(self):
        for item in ("OnePlusDoze","KeyHandler","UDFPS","VRR","HAL","不制造"):
            self.assertIn(item,DOC)

if __name__ == "__main__":
    unittest.main()
