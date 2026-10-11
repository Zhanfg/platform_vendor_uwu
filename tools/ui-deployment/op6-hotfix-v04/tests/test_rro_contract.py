"""RRO must hide only painted geometry and preserve system navigation."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
A="{http://schemas.android.com/apk/res/android}"
class GesturePillRRO(unittest.TestCase):
    def test_manifest_targets_systemui(self):
        m=ET.parse(ROOT/"rro/AndroidManifest.xml").getroot()
        overlay=m.find("overlay")
        self.assertEqual(overlay.attrib[A+"targetPackage"],"com.android.systemui")
        self.assertEqual(overlay.attrib[A+"resourcesMap"],"@xml/overlays")
    def test_radius_zero_only_and_no_touch_insets(self):
        resources=ET.parse(ROOT/"rro/res/values/dimens.xml").getroot()
        values={c.attrib["name"]:c.text for c in resources}
        self.assertEqual(values,{
            "navigation_handle_radius":"0dp",
            "navigation_home_handle_additional_height_for_animation":"0dp",
        })
        mapping=ET.parse(ROOT/"rro/res/xml/overlays.xml").getroot()
        self.assertEqual(len(mapping.findall("item")),2)
        self.assertTrue(all(x.get("target","").startswith("dimen/") for x in mapping))
    def test_kernelsu_same_id_and_no_binary_systemui(self):
        prop=(ROOT/"module/module.prop").read_text()
        self.assertIn("id=uwu-ui-live-hotfix",prop)
        self.assertIn("name=uwuAOSP hotfix v0.4",prop)
        script=(ROOT/"module/customize.sh").read_text()
        self.assertIn("47e4e849e99a695b3c698566fb451cf3cd671ddb17f3e5844d15b2b35188f841",script)
        self.assertIn("rm -f \"$MODPATH/skip_mount\"",script)
        text=(ROOT/"build.sh").read_text()
        self.assertNotIn("SystemUI.apk",text)
    def test_script_never_modifies_touch_dimensions(self):
        for p in (ROOT/"module").glob("*.sh"):
            src=p.read_text()
            for forbidden in ("navigation_bar_height", "system_gesture_inset", "pkill ",
                              "killall ", "pm disable com.android.systemui"):
                self.assertNotIn(forbidden,src)
if __name__=="__main__":
    unittest.main()
