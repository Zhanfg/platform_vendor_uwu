package cc.axymorrsen.uwu.hotfix;

import android.content.Context;
import android.content.ContentResolver;
import android.database.ContentObserver;
import android.graphics.Canvas;
import android.graphics.Outline;
import android.graphics.drawable.Drawable;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;
import android.util.Log;
import android.view.View;
import android.view.ViewOutlineProvider;
import android.view.WindowManager;
import android.widget.ImageView;
import java.lang.ref.WeakReference;
import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

/**
 * A narrowly scoped runtime workaround for the existing, platform-signed
 * Android 17 uwuAOSP SystemUI, not a fake SystemUI APK replacement.
 *
 * The system gesture nav view/insets are never resized or disabled.
 * Hook-only, opt-in via LSPosed scope. No process-kill or resident daemon.
 */
public final class SystemUiHook implements IXposedHookLoadPackage {
    private static final String TAG = "uwuSysUiFix";
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    private static final ThreadPoolExecutor ICON_WORKER = new ThreadPoolExecutor(
            0, 1, 20, TimeUnit.SECONDS, new ArrayBlockingQueue<Runnable>(16),
            r -> { Thread t = new Thread(r, "uwu-SysUI-Icons"); t.setDaemon(true); return t; },
            new ThreadPoolExecutor.DiscardOldestPolicy());
    private static final Map<Object, Integer> GENERATIONS =
            Collections.synchronizedMap(new WeakHashMap<>());
    private static final Map<Object, Cache> ENABLED =
            Collections.synchronizedMap(new WeakHashMap<>());
    private static final ThreadLocal<Boolean> IN_TOUCH = new ThreadLocal<>();
    private static final Map<View, Boolean> HANDLE_VIEWS =
            Collections.synchronizedMap(new WeakHashMap<>());
    private static volatile boolean HIDE_HANDLE = true;
    private static volatile boolean HANDLE_OBSERVER_STARTED;
    private static final Map<Class<?>, Boolean> TICK_HOOKS =
            Collections.synchronizedMap(new WeakHashMap<>());

    private static final class Cache {
        long at;
        boolean enabled;
    }

    private static void log(String message, Throwable e) {
        Log.w(TAG, message, e);
        XposedBridge.log(TAG + ": " + message + " (" + e.getClass().getSimpleName() + ")");
    }

    @Override public void handleLoadPackage(XC_LoadPackage.LoadPackageParam p) {
        if (!"com.android.systemui".equals(p.packageName)) return;
        // Never install hooks on an unverified ROM OTA or another device.
        // DEX class/method compatibility was checked against the installed
        // OnePlus 6 API 37 / CP2A.260605.016 SystemUI.apk baseline.
        if (Build.VERSION.SDK_INT != 37
                || !"CP2A.260605.016".equals(Build.ID)
                || !("OnePlus6".equalsIgnoreCase(Build.DEVICE)
                        || "enchilada".equalsIgnoreCase(Build.DEVICE))) {
            XposedBridge.log(TAG + ": unknown ROM baseline; hooks not installed");
            return;
        }
        try { hookHandle(p.classLoader); }
        catch (Throwable t) { log("Gesture-handle hook unavailable", t); }
        try { hookClock(p.classLoader); }
        catch (Throwable t) { log("Clock lifecycle hook unavailable", t); }
        try { hookMomentArc(p.classLoader); }
        catch (Throwable t) { log("MomentArc hook unavailable", t); }
    }

    // Read SettingsProvider only on initialization or setting changes.
    // Doing a Binder read on every navigation handle onDraw() would
    // introduce jank/ANR risk into the exact path this module must fix.
    private static void trackHandle(View view) {
        HANDLE_VIEWS.put(view, true);
        if (HANDLE_OBSERVER_STARTED) return;
        synchronized (HANDLE_VIEWS) {
            if (HANDLE_OBSERVER_STARTED) return;
            HANDLE_OBSERVER_STARTED = true;
            try {
                final ContentResolver resolver = view.getContext().getContentResolver();
                final ContentObserver watcher = new ContentObserver(MAIN) {
                    @Override public void onChange(boolean selfChange) {
                        try {
                            // Independent from v0.1–v0.3's legacy flag:
                            // older hotfix uninstalls may have restored that to
                            // zero, although the user still wants the bar hidden.
                            // Default hidden; explicit 0 opt-out remains possible.
                            HIDE_HANDLE = Settings.Secure.getInt(
                                    resolver, "uwu_hotfix_hide_pill", 1) == 1;
                            synchronized (HANDLE_VIEWS) {
                                for (View tracked : HANDLE_VIEWS.keySet()) {
                                    if (tracked != null) tracked.postInvalidate();
                                }
                            }
                        } catch (RuntimeException error) {
                            HIDE_HANDLE = false;
                            log("Cannot refresh gesture-handle setting", error);
                        }
                    }
                };
                watcher.onChange(false);
                resolver.registerContentObserver(Settings.Secure.getUriFor(
                        "uwu_hotfix_hide_pill"), false, watcher);
            } catch (Throwable e) {
                HIDE_HANDLE = false; // fail open to the stock renderer
                log("Could not observe gesture handle preference", e);
            }
        }
    }

    private static void hookHandle(ClassLoader cl) {
        String base = "com.android.systemui.navigationbar.gestural.";
        for (String name : new String[] {"NavigationHandle", "QuickswitchOrientedNavHandle"}) {
            Class<?> clazz = XposedHelpers.findClassIfExists(base + name, cl);
            if (clazz == null) continue;
            XposedBridge.hookAllMethods(clazz, "onDraw", new XC_MethodHook() {
                @Override protected void beforeHookedMethod(MethodHookParam param) {
                    try {
                        View v = (View) param.thisObject;
                        trackHandle(v);
                        // Only paint is skipped; nav view, gesture touch insets and
                        // accessibility stay unchanged.
                        if (HIDE_HANDLE) param.setResult(null);
                    } catch (Throwable t) {
                        // Fail open: a broken settings service must never crash
                        // SystemUI while rendering the navigation bar.
                        log("Gesture-handle drawing hook failed", t);
                    }
                }
            });
        }
    }

    private static void hookClock(ClassLoader cl) {
        Class<?> clock = XposedHelpers.findClassIfExists(
                "com.android.systemui.statusbar.policy.Clock", cl);
        if (clock == null) return;
        XposedBridge.hookAllMethods(clock, "onAttachedToWindow", new XC_MethodHook() {
            @Override protected void afterHookedMethod(MethodHookParam p) {
                try {
                    Object runnable = XposedHelpers.getObjectField(p.thisObject, "mSecondTick");
                    if (runnable == null) return;
                    Class<?> cls = runnable.getClass();
                    synchronized (TICK_HOOKS) {
                        if (TICK_HOOKS.containsKey(cls)) return;
                        XposedBridge.hookAllMethods(cls, "run", new XC_MethodHook() {
                            @Override protected void beforeHookedMethod(MethodHookParam tick) {
                                try {
                                    Object owner = XposedHelpers.getObjectField(tick.thisObject,
                                            "this$0");
                                    if (owner == null ||
                                            XposedHelpers.getObjectField(owner,
                                                    "mSecondsHandler") == null) {
                                        tick.setResult(null);
                                    }
                                } catch (Throwable e) {
                                    // Do not add exceptions to clock run path.
                                    log("Seconds tick guard unavailable", e);
                                }
                            }
                        });
                        TICK_HOOKS.put(cls, true);
                    }
                } catch (Throwable t) { log("Could not arm seconds guard", t); }
            }
        });
    }

    private static int nextGeneration(Object controller) {
        synchronized (GENERATIONS) {
            Integer previous = GENERATIONS.get(controller);
            int next = (previous == null ? 0 : previous) + 1;
            GENERATIONS.put(controller, next);
            return next;
        }
    }

    private static int generation(Object controller) {
        synchronized (GENERATIONS) {
            Integer value = GENERATIONS.get(controller);
            return value == null ? 0 : value;
        }
    }

    private static void hookMomentArc(ClassLoader cl) {
        final Class<?> arc = XposedHelpers.findClassIfExists(
                "com.android.systemui.moment.arc.MomentArcController", cl);
        if (arc == null) return;

        // Installed 17.0.101 APK has no declared Controller.onTouchCoordinates:
        // R8 inlined that source method into the gesture BroadcastReceiver.
        // Scope caching and failure containment to the actual DEX entrypoint.
        final Class<?> receiver = XposedHelpers.findClassIfExists(
                "com.android.systemui.moment.arc.MomentArcStartable$gestureReceiver$1", cl);
        if (receiver != null) {
            XposedBridge.hookAllMethods(receiver, "onReceive", new XC_MethodHook() {
                private final ThreadLocal<Boolean> scopedTouch = new ThreadLocal<>();
                @Override protected void beforeHookedMethod(MethodHookParam p) {
                    android.content.Intent intent = p.args.length > 1
                            && p.args[1] instanceof android.content.Intent
                            ? (android.content.Intent) p.args[1] : null;
                    boolean update = intent != null
                            && "com.android.systemui.action.UPDATE_MOMENT_ARC_TOUCH"
                                    .equals(intent.getAction());
                    scopedTouch.set(update);
                    if (update) IN_TOUCH.set(true);
                }
                @Override protected void afterHookedMethod(MethodHookParam p) {
                    boolean update = Boolean.TRUE.equals(scopedTouch.get());
                    scopedTouch.remove();
                    if (update) IN_TOUCH.remove();
                    if (!p.hasThrowable()
                            || !(p.getThrowable() instanceof RuntimeException)) return;
                    android.content.Intent intent = p.args.length > 1
                            && p.args[1] instanceof android.content.Intent
                            ? (android.content.Intent) p.args[1] : null;
                    String action = intent == null ? null : intent.getAction();
                    if (action == null || !action.startsWith("com.android.systemui.action.")
                            || !action.endsWith("_MOMENT_ARC")
                            && !action.endsWith("_MOMENT_ARC_TOUCH")) return;
                    log("MomentArc broadcast failure contained", p.getThrowable());
                    p.setResult(null);
                    MAIN.post(() -> {
                        try {
                            Object startable = XposedHelpers.getObjectField(
                                    p.thisObject, "this$0");
                            if (startable != null) safeHide(
                                    XposedHelpers.getObjectField(startable, "controller"));
                        } catch (Throwable e) { log("MomentArc safe hide unavailable", e); }
                    });
                }
            });
        }

        XposedBridge.hookAllMethods(arc, "hide", new XC_MethodHook() {
            private final ThreadLocal<Object> beforeView = new ThreadLocal<>();
            @Override protected void beforeHookedMethod(MethodHookParam p) {
                nextGeneration(p.thisObject);
                try { beforeView.set(XposedHelpers.getObjectField(p.thisObject, "overlayView")); }
                catch (Throwable ignored) { beforeView.remove(); }
            }
            @Override protected void afterHookedMethod(MethodHookParam p) {
                Object viewObject = beforeView.get();
                beforeView.remove();
                if (!(viewObject instanceof View)) return;
                final WeakReference<View> weakView = new WeakReference<>((View) viewObject);
                final WeakReference<Object> weakController = new WeakReference<>(p.thisObject);
                MAIN.postDelayed(() -> {
                    View view = weakView.get();
                    Object controller = weakController.get();
                    if (view == null || controller == null || !view.isAttachedToWindow()) return;
                    try {
                        WindowManager wm = (WindowManager) XposedHelpers.getObjectField(
                                controller, "windowManager");
                        wm.removeViewImmediate(view);
                    } catch (Throwable e) { log("MomentArc stale overlay cleanup failed", e); }
                }, 700);
            }
        });

        // Only cache during high-frequency coordinate broadcasts. Normal
        // SHOW calls and ContentObserver callbacks retain immediate reads.
        XposedBridge.hookAllMethods(arc, "isMomentArcEnabled", new XC_MethodHook() {
            @Override protected void beforeHookedMethod(MethodHookParam p) {
                if (!Boolean.TRUE.equals(IN_TOUCH.get())) return;
                synchronized (ENABLED) {
                    Cache c = ENABLED.get(p.thisObject);
                    if (c != null && SystemClock.uptimeMillis() - c.at < 160) {
                        p.setResult(c.enabled);
                    }
                }
            }
            @Override protected void afterHookedMethod(MethodHookParam p) {
                if (!Boolean.TRUE.equals(IN_TOUCH.get()) || p.hasThrowable()) return;
                Object value = p.getResult();
                if (!(value instanceof Boolean)) return;
                synchronized (ENABLED) {
                    Cache cache = new Cache();
                    cache.enabled = (Boolean) value;
                    cache.at = SystemClock.uptimeMillis();
                    ENABLED.put(p.thisObject, cache);
                }
            }
        });

        // Original createIconView calls LauncherApps and PackageManager Binder
        // synchronously up to 12 times on the SYSTEM UI MAIN THREAD.
        // Return a non-intercepting placeholder immediately, load the actual
        // icon using a single bounded, idle-expiring worker.
        XposedBridge.hookAllMethods(arc, "createIconView", new XC_MethodHook() {
            @Override protected void beforeHookedMethod(MethodHookParam p) {
                try {
                    final Object controller = p.thisObject;
                    final Object target = p.args[0];
                    final Context context =
                            (Context) XposedHelpers.getObjectField(controller, "context");
                    final ImageView image = new ImageView(context);
                    image.setImageDrawable(context.getPackageManager().getDefaultActivityIcon());
                    image.setOutlineProvider(new ViewOutlineProvider() {
                        @Override public void getOutline(View v, Outline outline) {
                            int size = Math.min(v.getWidth(), v.getHeight());
                            if (size <= 0) { outline.setEmpty(); return; }
                            int left = (v.getWidth() - size) / 2;
                            int top = (v.getHeight() - size) / 2;
                            outline.setRoundRect(left, top, left + size, top + size, size / 2f);
                        }
                    });
                    image.setClipToOutline(true);
                    final int currentGeneration = generation(controller);
                    WeakReference<ImageView> weakImage = new WeakReference<>(image);
                    WeakReference<Object> weakController = new WeakReference<>(controller);
                    try {
                        ICON_WORKER.execute(() -> {
                            Object owner = weakController.get();
                            if (owner == null || generation(owner) != currentGeneration) return;
                            Drawable result;
                            try {
                                result = (Drawable) XposedHelpers.callMethod(owner, "loadIcon",
                                        target);
                            } catch (Throwable error) {
                                // Uninstalled app/missing shortcuts are normal; placeholder stays.
                                return;
                            }
                            if (result == null) return;
                            MAIN.post(() -> {
                                ImageView v = weakImage.get();
                                Object c = weakController.get();
                                if (v == null || c == null ||
                                        generation(c) != currentGeneration) return;
                                if (v.isAttachedToWindow()) v.setImageDrawable(result);
                            });
                        });
                    } catch (RejectedExecutionException ignored) {
                        // Saturation must never delay or crash SystemUI.
                    }
                    p.setResult(image);
                } catch (Throwable t) {
                    // Preserve the ROM's original renderer if this optional
                    // integration is not compatible with the installed class.
                    log("Async icon replacement unavailable", t);
                }
            }
        });
    }

    private static void safeHide(Object controller) {
        try { XposedHelpers.callMethod(controller, "hide"); }
        catch (Throwable t) { log("MomentArc hide failed", t); }
    }
}
