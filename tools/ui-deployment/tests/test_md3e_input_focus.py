"""Pinned uwuCompose MD3E search and dialog field palette contract.

Run after applying patches to the exact locked uwu-sdk checkout. This is
source-level; platform Compose compilation is a separate release gate.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SDK = ROOT / "uwu-sdk/uwuCompose/src/org/uwuaosp/compose/settingslib"
PREPARE = ROOT / "tools/ui-deployment/prepare_native_sources.sh"

class TonalInputFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.search = (SDK / "SettingsSearchField.kt").read_text()
        cls.dialog = (SDK / "TextInputPreferenceDialog.kt").read_text()

    def test_focus_is_state_driven_not_polling(self):
        src=self.search
        self.assertIn("remember { MutableInteractionSource() }",src)
        self.assertIn("collectIsFocusedAsState().value",src)
        self.assertIn("interactionSource = searchInteractionSource",src)
        self.assertNotIn("while (",src)
        self.assertNotIn("Handler(",src)

    def test_shared_dynamic_tonal_fill(self):
        self.assertIn("color = MaterialTheme.colorScheme.surfaceContainerHigh",self.search)
        self.assertIn(".background(MaterialTheme.colorScheme.surfaceContainerHigh)",self.dialog)
        self.assertNotIn("color = MaterialTheme.colorScheme.surfaceContainerLowest",self.search)

    def test_search_focus_accessibility(self):
        self.assertIn("if (isFocused) MaterialTheme.colorScheme.primary",self.search)
        self.assertIn("else MaterialTheme.colorScheme.outlineVariant",self.search)
        self.assertIn("clearContentDescription",self.search)
        self.assertIn("singleLine = true",self.search)

    def test_dialog_has_same_unfocused_border_tone(self):
        self.assertIn("else -> MaterialTheme.colorScheme.outlineVariant",self.dialog)
        self.assertIn("focused -> MaterialTheme.colorScheme.primary",self.dialog)
        self.assertIn("isError -> MaterialTheme.colorScheme.error",self.dialog)

    def test_native_patch_covered_by_source_gate(self):
        self.assertIn("uwu-sdk-md3e-input-tonal-focus.patch",PREPARE.read_text())

if __name__=="__main__":
    unittest.main()
