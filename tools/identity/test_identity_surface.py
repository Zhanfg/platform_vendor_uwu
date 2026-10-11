"""Source/fixture validation for the read-only ROM identity audit."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/identity/audit_identity_surface.py"
spec = importlib.util.spec_from_file_location("rom_identity_audit", TOOL)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class IdentityAuditTests(unittest.TestCase):
    def test_sdk_image_uses_actual_project_identity(self):
        p = ROOT / "build/target/product/source.properties"
        s = p.read_text(encoding="utf-8")
        self.assertIn("SystemImage.TagId=uwu", s)
        self.assertIn("SystemImage.TagDisplay=uwuAOSP", s)
        self.assertNotIn("SystemImage.TagId=lineage", s)

    def test_protected_hal_contract_retained(self):
        r = audit.scan_source(ROOT)
        found = {f["id"]: f for f in r}
        self.assertTrue(found["lineage_hal_contract"]["matched"])
        self.assertTrue(found["lineage_permission_contract"]["matched"])
        self.assertTrue(found["lineage_plugin_allowlist"]["matched"])
        self.assertTrue(found["insecure_adb_on_nonuser"]["matched"])
        self.assertEqual(found["sdk_image_tag"]["scope"], "build-only")

    def test_fixture_reports_runtime_properties_and_vintf_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p=root/"system/build.prop"
            p.parent.mkdir(parents=True)
            p.write_text("ro.lineage.version=test\nro.build.type=userdebug\nro.adb.secure=0\n")
            xml=root/"vendor/etc/vintf/manifest.xml"
            xml.parent.mkdir(parents=True)
            xml.write_text("<manifest>vendor.lineage.livedisplay</manifest>")
            package=root/"system_ext/priv-app/LineageParts"
            package.mkdir(parents=True)
            props=audit.scan_build_properties(root)
            pkg=audit.scan_packages_and_vintf(root)
            self.assertEqual({x["kind"] for x in props},
                             {"lineage-property", "generic-build-identity",
                              "adb-authentication-review"})
            self.assertEqual({x["kind"] for x in pkg},
                             {"lineage-vintf-declaration","package-filename-hint"})
            self.assertEqual(p.read_text().splitlines()[0],"ro.lineage.version=test")
            self.assertEqual(json.dumps(audit.audit(ROOT, root)) is not None, True)

    def test_read_only_and_requires_actual_image_to_claim_runtime(self):
        s=TOOL.read_text(encoding="utf-8")
        self.assertNotIn("setprop", s)
        self.assertNotIn("settings put ", s)
        report=audit.audit(ROOT)
        self.assertFalse(report["runtime_image_examined"])
        self.assertEqual(report["build_properties"], [])

if __name__=="__main__":
    unittest.main()
