"""Negative tests for an unsafe release plan (no Android SDK required)."""
import copy
import json
import unittest
from pathlib import Path
from validate_patch_plan import validate

ROOT = Path(__file__).resolve().parent

class OneKsuPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "patch_plan.json").read_text())

    def test_current_resource_only_plan_is_valid(self):
        self.assertEqual(validate(self.data), [])

    def test_block_full_apk_code_without_valid_signature(self):
        plan = copy.deepcopy(self.data)
        for entry in plan["changes"]:
            if entry["id"] == "momentarc_thread_and_cleanup":
                entry["ship_in_current_zip"] = True
        self.assertTrue(any("cannot ship unsigned code" in x for x in validate(plan)))

    def test_block_claimed_rro_without_runtime_verification(self):
        plan = copy.deepcopy(self.data)
        for entry in plan["changes"]:
            if entry["id"] == "gesture_pill_resource":
                entry["needs_runtime_overlay_verification"] = False
        self.assertTrue(any("RRO must be tested" in x for x in validate(plan)))

    def test_block_lsp_and_restarting_systemui(self):
        plan = copy.deepcopy(self.data)
        plan["module"]["uses_lsp"] = True
        self.assertTrue(validate(plan))
        plan["module"]["uses_lsp"] = False
        plan["module"]["auto_restart_systemui"] = True
        self.assertTrue(validate(plan))

    def test_detect_omitted_md3e_settings_or_launcher(self):
        plan = copy.deepcopy(self.data)
        plan["changes"] = [x for x in plan["changes"] if x["owner"] != "Settings"]
        self.assertTrue(any("MD3E" in x for x in validate(plan)))

    def test_block_module_id_and_density_drift(self):
        plan = copy.deepcopy(self.data)
        plan["density"] = 480
        self.assertTrue(any("DPI" in x for x in validate(plan)))
        plan["density"] = 420
        plan["module"]["id"] = "new-ui-module"
        self.assertTrue(any("module ID" in x for x in validate(plan)))

if __name__ == "__main__":
    unittest.main()
