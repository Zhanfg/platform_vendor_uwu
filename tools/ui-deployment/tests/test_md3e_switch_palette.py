"""MD3E Switch override must retain wallpaper palette and a11y semantics.
This test runs against the pinned uwu-sdk checkout AFTER applying patch.
"""
from pathlib import Path
import unittest
S=Path("uwu-sdk/uwuCompose/src/org/uwuaosp/compose/settingslib/SettingsSwitch.kt")
P=Path("tools/ui-deployment/patches/uwu-sdk-md3e-switch-contrast.patch")

class ExpressiveSwitch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=S.read_text(encoding="utf-8")
        cls.patch=P.read_text(encoding="utf-8")
    def test_off_border_matches_tonal_track(self):
        self.assertIn("uncheckedTrackColor = surfaceHighest",self.src)
        self.assertIn("uncheckedBorderColor = surfaceHighest",self.src)
        self.assertIn("disabledUncheckedBorderColor = surfaceHighest",self.src)
        self.assertNotIn("uncheckedBorderColor = outline",self.src)
    def test_thumb_contrast_and_dynamic_palette(self):
        self.assertIn("MaterialTheme.colorScheme.onSurfaceVariant",self.src)
        self.assertIn("uncheckedThumbColor = offThumb",self.src)
        self.assertNotIn("val outline = MaterialTheme.colorScheme.outline",self.src)
    def test_all_switch_rows_share_same_component(self):
        for name in ("MainSwitchPreference","SwitchPreferenceRow","PrimarySwitchPreferenceRow"):
            self.assertIn("fun "+name+"(",self.src)
        self.assertEqual(self.src.count("private fun SettingsSwitch("),1)
        self.assertIn("role = Role.Switch",self.src)
    def test_no_runtime_hooks_or_signature_changing(self):
        for s in ("XposedBridge","LSPosed","System.loadLibrary","Settings.Secure.put"):
            self.assertNotIn(s,self.patch)
if __name__=="__main__":
    unittest.main()
