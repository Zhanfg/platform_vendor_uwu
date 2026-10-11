#!/usr/bin/env python3
"""Compile and run the REAL patched HWCColorMode::PopulateColorModes() method.

Method body is extracted from reference source AFTER patch application.
Mock only DisplayInterface. This is a host test, not a complete HAL build.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit("usage: test_real_populate_color_modes.py PATCHED_HWC_DISPLAY_CPP")
src = Path(sys.argv[1]).read_text()
begin_marker = "void HWCColorMode::PopulateColorModes() {"
end_marker = "\nvoid HWCColorMode::Dump("
assert src.count(begin_marker) == 1
start = src.index(begin_marker)
end = src.index(end_marker, start)
method = src[start:end].rstrip()
assert "op6_legacy_standard" in method
assert 'mode_string == "bt2020_hlg"' in method
assert 'mode_string == "bt2020_pq"' in method

header = r'''
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <string>
#include <utility>
#include <vector>
using std::string;
using AttrVal = std::map<string, string>;
using DisplayError = int;
constexpr DisplayError kErrorNone = 0;
constexpr int MAX_EXTENDED_RENDER_INTENT = 10;
const string kNative = "native", kSrgb = "srgb", kDcip3 = "dcip3";
const string kBt2020 = "bt2020", kSdr = "sdr", kHdr = "hdr";
const string kSt2084 = "st2084", kHlg = "hlg", kStandard = "standard";
const string kGamma2_2 = "gamma2.2", kEnhanced = "enhanced";
const string kColorGamutAttribute = "ColorGamut";
const string kDynamicRangeAttribute = "DynamicRange";
const string kPictureQualityAttribute = "PictureQuality";
const string kGammaTransferAttribute = "GammaTransfer";
const string kRenderIntentAttribute = "RenderIntent";
#define DLOGW(...) do {} while(0)
#define DLOGV_IF(...) do {} while(0)
const int kTagClient = 0;
enum class ColorMode { NATIVE, SRGB, DISPLAY_P3, BT2100_PQ, BT2100_HLG, DISPLAY_BT2020 };
enum class RenderIntent { COLORIMETRIC=0, ENHANCE=1 };
enum DynamicRangeType { kSdrType=0, kHdrType=1 };
using DynamicRangeMap = std::map<DynamicRangeType, string>;
using RenderIntentMap = std::map<RenderIntent, DynamicRangeMap>;
using ColorModeMap = std::map<ColorMode, RenderIntentMap>;
struct Mode {
  string name, gamut, range, quality, transfer;
  int intent=-1;
  bool has_attributes=true;
};
struct FakeDisplay {
  std::vector<Mode> modes;
  explicit FakeDisplay(std::vector<Mode> input): modes(std::move(input)) {}
  DisplayError GetColorModeCount(uint32_t *n) { *n = modes.size(); return 0; }
  DisplayError GetColorModes(uint32_t *n, std::vector<string>* output) {
    *n = std::min(*n, static_cast<uint32_t>(modes.size()));
    for (uint32_t i=0; i<*n; ++i) (*output)[i]=modes[i].name;
    return 0;
  }
  DisplayError GetColorModeAttr(const string& name, AttrVal *out) {
    for (const auto& m: modes) if (m.name == name) {
      if (m.has_attributes) {
        (*out)[kColorGamutAttribute] = m.gamut;
        (*out)[kDynamicRangeAttribute] = m.range;
        (*out)[kPictureQualityAttribute] = m.quality;
        if (!m.transfer.empty()) (*out)[kGammaTransferAttribute] = m.transfer;
        if (m.intent != -1) (*out)[kRenderIntentAttribute] = std::to_string(m.intent);
      }
      return 0;
    }
    return -1;
  }
  bool IsSupportSsppTonemap() const { return false; }
};
class HWCColorMode {
public:
  explicit HWCColorMode(FakeDisplay* display):display_intf_(display) {}
  void PopulateColorModes();
  ColorModeMap color_mode_map_;
private:
  FakeDisplay *display_intf_;
};
'''
footer = r'''
static void check(bool ok, const string &why) {
  if (!ok) { std::cerr << "FAIL: " << why << std::endl; std::exit(1); }
}
static string lookup(const HWCColorMode& hwc, ColorMode mode, DynamicRangeType dr) {
  auto m=hwc.color_mode_map_.find(mode);
  if (m == hwc.color_mode_map_.end()) return "";
  auto ri=m->second.find(RenderIntent::COLORIMETRIC);
  if (ri == m->second.end()) return "";
  auto d=ri->second.find(dr);
  return d == ri->second.end() ? "" : d->second;
}
int main() {
  std::vector<Mode> phone{
    {"CTS","native","sdr","standard","",-1},
    {"SRGB","srgb","sdr","standard","",-1},
    {"DCI_P3","dcip3","sdr","standard","",-1},
    {"advance_native","srgb","sdr","standard","",-1},
    {"advance_srgb","srgb","sdr","standard","",-1},
    {"advance_p3","srgb","sdr","standard","",-1},
    {"bt2020_pq","bt2020","","standard","st2084",-1},
    {"bt2020_hlg","bt2020","","standard","hlg",-1},
    {"hal_hdr","dcip3","hdr","standard","",-1},
    {"fod_native","srgb","sdr","standard","",-1},
    {"sharpness0","srgb","sdr","standard","",-1},
  };
  FakeDisplay display{phone};
  HWCColorMode hwc(&display);
  hwc.PopulateColorModes();
  check(hwc.color_mode_map_.size() == 5, "expected exactly five standard color modes");
  check(lookup(hwc,ColorMode::NATIVE,kSdrType) == "CTS", "NATIVE must select CTS");
  check(lookup(hwc,ColorMode::SRGB,kSdrType) == "SRGB", "advanced mode must not override SRGB");
  check(lookup(hwc,ColorMode::DISPLAY_P3,kSdrType) == "DCI_P3", "DCI_P3 mode");
  check(lookup(hwc,ColorMode::BT2100_PQ,kHdrType) == "bt2020_pq", "PQ must be HDR");
  check(lookup(hwc,ColorMode::BT2100_HLG,kHdrType) == "bt2020_hlg", "HLG must be HDR");
  check(lookup(hwc,ColorMode::SRGB,kHdrType).empty(), "SRGB must not be faked as HDR");
  FakeDisplay no_modes{std::vector<Mode>{}};
  HWCColorMode fallback(&no_modes);
  fallback.PopulateColorModes();
  check(fallback.color_mode_map_.size()==1, "native fallback missing");
  check(lookup(fallback,ColorMode::NATIVE,kSdrType) == "hal_native_identity", "fallback incorrect");
  FakeDisplay xml_only{{{"advance_native","srgb","sdr","standard","",-1},
                        {"hal_hdr","dcip3","hdr","standard","",-1},
                        {"fod_native","srgb","sdr","standard","",-1}}};
  HWCColorMode guard(&xml_only);
  guard.PopulateColorModes();
  check(guard.color_mode_map_.empty(), "uncalibrated xml-only modes must remain excluded");
  std::cout << "PASS: real HWC PopulateColorModes() compiled and executed (3 scenarios)" << std::endl;
}
'''
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    cpp = d / "hwc_method.cpp"
    cpp.write_text(header + "\n" + method + "\n" + footer)
    subprocess.run(
        ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
         "-Wno-unused-variable", str(cpp), "-o", str(d / "hwc_method")],
        check=True)
    subprocess.run([str(d / "hwc_method")], check=True)
