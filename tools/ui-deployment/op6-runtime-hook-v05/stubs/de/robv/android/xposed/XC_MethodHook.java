package de.robv.android.xposed;
public class XC_MethodHook {
    protected void beforeHookedMethod(MethodHookParam p) throws Throwable {}
    protected void afterHookedMethod(MethodHookParam p) throws Throwable {}
    public static class MethodHookParam {
        public Object thisObject;
        public Object[] args;
        public void setResult(Object result) {}
        public Object getResult() { return null; }
        public boolean hasThrowable() { return false; }
        public Throwable getThrowable() { return null; }
    }
}
