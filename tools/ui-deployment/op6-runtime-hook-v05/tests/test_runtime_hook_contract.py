"""Static checks only: runtime APK and on-device LSPosed integration still need QA."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/"src/cc/axymorrsen/uwu/hotfix/SystemUiHook.java").read_text()
BUILD=(ROOT/"build.sh").read_text()
MANIFEST=(ROOT/"AndroidManifest.xml").read_text()

class RuntimeFixContract(unittest.TestCase):
    def test_scope_and_version(self):
        self.assertIn('com.android.systemui',SRC)
        self.assertIn('com.android.systemui', (ROOT/"res/values/arrays.xml").read_text())
        self.assertIn('xposedmodule', MANIFEST)
        self.assertEqual(
            (ROOT/"assets/xposed_init").read_text().strip(),
            'cc.axymorrsen.uwu.hotfix.SystemUiHook',
        )
    def test_pill_only_skip_paint(self):
        self.assertIn('QuickswitchOrientedNavHandle', SRC)
        self.assertIn('uwu_hide_gesture_handle', SRC)
        self.assertIn('param.setResult(null);', SRC)
        self.assertNotIn('setVisibility(View.GONE)', SRC)
        self.assertNotIn('wm density', SRC)
    def test_draw_uses_observer_not_binder_on_every_frame(self):
        self.assertIn('new ContentObserver(MAIN)', SRC)
        self.assertIn('resolver.registerContentObserver(', SRC)
        paint=SRC.split('private static void hookHandle(ClassLoader cl)', 1)[1].split(
            'private static void hookClock(ClassLoader cl)',1)[0]
        self.assertIn('if (HIDE_HANDLE) param.setResult(null)', paint)
        self.assertNotIn('Settings.Secure.getInt(', paint)

    def test_only_actual_installed_moment_entrypoints_hooked(self):
        self.assertIn('MomentArcStartable$gestureReceiver$1', SRC)
        self.assertIn('XposedBridge.hookAllMethods(receiver, "onReceive"', SRC)
        self.assertIn('UPDATE_MOMENT_ARC_TOUCH', SRC)
        self.assertNotIn('XposedBridge.hookAllMethods(arc, "onTouchCoordinates"', SRC)
        self.assertIn('XposedBridge.hookAllMethods(arc, "createIconView"', SRC)
        self.assertIn('XposedBridge.hookAllMethods(arc, "hide"', SRC)

    def test_rom_ota_fail_closed(self):
        self.assertIn('Build.VERSION.SDK_INT != 37', SRC)
        self.assertIn('CP2A.260605.016', SRC)
        self.assertIn('"OnePlus6".equalsIgnoreCase(Build.DEVICE)',SRC)

    def test_clock_null_guard(self):
        self.assertIn('mSecondsHandler', SRC)
        self.assertIn('"mSecondTick"', SRC)
        self.assertIn('tick.setResult(null)', SRC)
    def test_moment_ipc_off_main(self):
        self.assertIn('new ThreadPoolExecutor(', SRC)
        self.assertIn('new ArrayBlockingQueue<Runnable>(16)', SRC)
        self.assertIn('XposedHelpers.callMethod(owner, "loadIcon"', SRC)
        self.assertIn('ICON_WORKER.execute', SRC)
        self.assertIn('new WeakReference<>(image)', SRC)
        self.assertIn('if (v.isAttachedToWindow())', SRC)
    def test_no_process_restart_or_signature_spoofing(self):
        for bad in ('pkill ', 'killall ', 'resetprop ', 'ro.build.fingerprint',
                    'ro.boot.verifiedbootstate', 'removeViewImmediate(systemUiRoot)'):
            self.assertNotIn(bad,SRC)
        self.assertIn('xposed-api-compile-only.jar', BUILD)
        self.assertIn('apksigner', BUILD.lower()) if False else self.assertIn('APKSIGNER', BUILD.upper())
    def test_minimum_recovery_and_limits(self):
        desc=(ROOT/"README_CN.txt").read_text()
        for term in ('LSPosed','SystemUI','真机','风险','平台签名'):
            self.assertIn(term,desc)
if __name__=='__main__':unittest.main()
