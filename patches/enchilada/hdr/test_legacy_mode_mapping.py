"""Compile the *patched source expression* against conservative OnePlus 6 mode fixtures.

This validates only mapping predicates. It does not build Qualcomm HWC, check
binary ABI, or prove real HDR display functionality.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: test_legacy_mode_mapping.py PATH_TO_PATCHED_HWC_DISPLAY_CPP")

source = Path(sys.argv[1]).read_text()
match = re.search(
    r"const bool op6_legacy_standard\s*=\s*(.*?);\s*if \(int_render_intent",
    source,
    re.DOTALL,
)
if not match:
    raise SystemExit("Legacy compatibility expression missing from patched HWC")

expression = match.group(1).strip()
cpp = r"""
#include <string>
#include <vector>
#include <iostream>
using std::string;
const string kNative = "native", kSrgb = "srgb", kDcip3 = "dcip3";
const string kBt2020 = "bt2020", kSdr = "sdr", kSt2084 = "st2084";
const string kHlg = "hlg", kStandard = "standard";
struct Sample {
    string name, gamut, range, quality, transfer;
    int render_intent;
    bool expected;
};
int main() {
    const std::vector<Sample> cases = {
        {"CTS", "native", "sdr", "standard", "", -1, true},
        {"SRGB", "srgb", "sdr", "standard", "", -1, true},
        {"DCI_P3", "dcip3", "sdr", "standard", "", -1, true},
        {"bt2020_pq", "bt2020", "", "standard", "st2084", -1, true},
        {"bt2020_hlg", "bt2020", "", "standard", "hlg", -1, true},
        {"advance_native", "srgb", "sdr", "standard", "", -1, false},
        {"advance_srgb", "srgb", "sdr", "standard", "", -1, false},
        {"advance_p3", "srgb", "sdr", "standard", "", -1, false},
        {"SRGB", "srgb", "sdr", "enhanced", "", -1, false},
        {"SRGB", "srgb", "sdr", "standard", "", 1, false},
        {"bt2020_pq", "bt2020", "", "standard", "hlg", -1, false},
        {"bt2020_hlg", "bt2020", "", "standard", "st2084", -1, false},
        {"FAKE", "srgb", "sdr", "standard", "", -1, false},
        {"CTS", "dcip3", "sdr", "standard", "", -1, false},
        // Real QDCM profiles that must NOT become Android standard modes.
        {"hal_hdr", "dcip3", "hdr", "standard", "", -1, false},
        {"zhal_native", "srgb", "sdr", "standard", "", -1, false},
        {"fod_native", "srgb", "sdr", "standard", "", -1, false},
        {"sharpness-70", "srgb", "sdr", "standard", "", -1, false},
        {"sharpness0", "srgb", "sdr", "standard", "", -1, false},
        {"bt2020_pq", "bt2020", "", "enhanced", "st2084", -1, false},
    };
    for (const auto& test : cases) {
        const string& mode_string = test.name;
        const string& color_gamut = test.gamut;
        const string& dynamic_range = test.range;
        const string& pic_quality = test.quality;
        const string& transfer = test.transfer;
        const int int_render_intent = test.render_intent;
        const bool op6_legacy_standard = __EXPRESSION__;
        const bool selected = int_render_intent == -1 &&
                              pic_quality == kStandard && op6_legacy_standard;
        if (selected != test.expected) {
            std::cerr << "Mismatch: " << test.name << std::endl;
            return 1;
        }
    }
    std::cout << "20 exact color-mode mappings passed" << std::endl;
    return 0;
}
"""
cpp = cpp.replace("__EXPRESSION__", expression)
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    (td / "test.cpp").write_text(cpp)
    subprocess.run(
        ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
         str(td / "test.cpp"), "-o", str(td / "test")],
        check=True,
    )
    subprocess.run([str(td / "test")], check=True)
