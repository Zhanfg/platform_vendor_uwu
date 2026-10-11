"""Keep build labeling accurate without destroying legacy hardware ABI."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
class LineageCompatibilityBoundaryTests(unittest.TestCase):
    def test_sdk_image_tag_has_correct_brand(self):
        text=(ROOT/"build/target/product/source.properties").read_text()
        self.assertIn("SystemImage.TagId=uwuaosp",text)
        self.assertIn("SystemImage.TagDisplay=uwuAOSP",text)
        self.assertNotIn("SystemImage.TagId=lineage",text)
    def test_lineage_hardware_abi_preserved(self):
        root=ET.parse(ROOT/"config/framework_compatibility_matrix.xml").getroot()
        names={n.text for n in root.iter("name") if n.text}
        for name in ("vendor.lineage.health","vendor.lineage.powershare",
                     "vendor.lineage.livedisplay","vendor.lineage.touch"):
            self.assertIn(name,names)
        root=ET.parse(ROOT/"config/permissions/privapp-permissions-lineagehw.xml").getroot()
        for pkg in ("com.android.systemui","com.android.settings"):
            items=[c for c in root if c.get("package")==pkg]
            self.assertEqual(len(items),1)
            perms={p.get("name") for p in items[0] if p.tag=="permission"}
            self.assertIn("lineageos.permission.MANAGE_LIVEDISPLAY",perms)
            self.assertIn("lineageos.permission.HARDWARE_ABSTRACTION_ACCESS",perms)
    def test_audit_does_not_claim_to_hide_android_certification(self):
        text=(ROOT/"tools/los-compat/LOS_EXPOSURE_AUDIT_zh.md").read_text()
        for term in ("ro.build.fingerprint","Verified Boot","普通应用","OTA","不能"):
            self.assertIn(term,text)
if __name__=="__main__":unittest.main()
