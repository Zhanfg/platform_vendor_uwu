"""Portable mock-device tests for v0.3. CI does not require root or Android."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class StableHotfixCI(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        self.root=Path(td.name); self.mod=self.root/'mod'
        shutil.copytree(ROOT,self.mod,ignore=shutil.ignore_patterns('out','tests'))
        self.bin=self.root/'bin';self.bin.mkdir()
        def exe(name,data):
            p=self.bin/name;p.write_text(data);p.chmod(0o755)
        exe('getprop',"#!/bin/sh\ncase \"$1\" in\nro.product.device) echo \"${TEST_DEVICE:-OnePlus6}\";;\nro.build.version.sdk) echo \"${TEST_API:-37}\";;\nsys.boot_completed) echo 1;;\nesac\n")
        exe('settings', '''#!/usr/bin/env python3
import os,json,sys
from pathlib import Path
p=Path(os.environ['TEST_DB']);d=json.loads(p.read_text());a=sys.argv[1:]
if a[:2]==['--user','0']:a=a[2:]
x,_,key=a[:3]
if x=='get':print(d.get(key,'null'))
elif x=='put':d[key]=a[3];p.write_text(json.dumps(d))
elif x=='delete':d.pop(key,None);p.write_text(json.dumps(d))
''')
        exe('wm', '''#!/usr/bin/env python3
import os,sys
from pathlib import Path
p=Path(os.environ['TEST_DPI'])
if os.environ.get('FAIL_WM')=='1':sys.exit(1)
if sys.argv[1:]==['density']:print('Physical density: 499\\nOverride density: '+p.read_text())
else:
 with open(os.environ['TEST_WRITES'],'a') as f:f.write(sys.argv[-1]+'\\n')
 p.write_text(sys.argv[-1])
''')
        self.db=self.root/'db.json';self.db.write_text(json.dumps({'clock_seconds':'1','uwu_hide_gesture_handle':'1'}))
        self.dpi=self.root/'dpi';self.dpi.write_text('420')
        self.writes=self.root/'writes';self.writes.write_text('')
        self.state=self.root/'state';self.state.mkdir()
        self.env=os.environ|{'UWU_HOTFIX_TESTING':'1','UWU_HOTFIX_TEST_BIN':str(self.bin),'UWU_HOTFIX_TEST_STATE':str(self.state),'TEST_DB':str(self.db),'TEST_DPI':str(self.dpi),'TEST_WRITES':str(self.writes)}
    def runsh(self,name='apply.sh'):
        p=subprocess.run(['sh',str(self.mod/name)],env=self.env,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
    def original(self,key,value='0'):
        (self.state/('original_'+key)).write_text(value+'\n')
    def current(self,key):return json.loads(self.db.read_text()).get(key)
    def test_old_settings_restored_safely(self):
        self.original('clock_seconds');self.original('uwu_hide_gesture_handle')
        self.runsh();self.assertEqual(self.current('clock_seconds'),'0')
        self.assertEqual(self.current('uwu_hide_gesture_handle'),'0')
    def test_user_override_is_kept(self):
        self.original('clock_seconds');(self.state/'user_override_clock_seconds').touch()
        self.runsh();self.assertEqual(self.current('clock_seconds'),'1')
    def test_no_original_no_guess(self):
        self.runsh();self.assertEqual(self.current('clock_seconds'),'1')
    def test_density420_no_write(self):
        self.runsh();self.assertEqual(self.writes.read_text(),'')
    def test_density_drift_one_write_only(self):
        self.dpi.write_text('460');self.runsh();self.assertEqual(self.writes.read_text(),'420\n')
        self.dpi.write_text('480');self.runsh();self.assertEqual(self.writes.read_text(),'420\n')
    def test_failed_wm_skips_without_override(self):
        self.env['FAIL_WM']='1';self.runsh();self.assertEqual(self.writes.read_text(),'')
    def test_mismatch_api_pauses(self):
        self.original('clock_seconds');self.env['TEST_API']='38';self.runsh()
        self.assertEqual(self.current('clock_seconds'),'1')
    def test_action_explicitly_sets_420(self):
        self.dpi.write_text('480');self.runsh('action.sh');self.assertEqual(self.current('clock_seconds'),'1')
        self.assertEqual(self.writes.read_text(),'420\n')
if __name__=='__main__':unittest.main()
