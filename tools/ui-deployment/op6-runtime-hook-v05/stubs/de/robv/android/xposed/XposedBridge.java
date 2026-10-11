package de.robv.android.xposed;
public final class XposedBridge {
    public static void hookAllMethods(Class<?> cls, String method, XC_MethodHook hook) {}
    public static void log(String line) {}
}
