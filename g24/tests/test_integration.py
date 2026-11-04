import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from g24 import demo

BASE=Path(__file__).resolve().parents[2]
RAW=BASE/'raw/data_1600_accel_phone.txt' if (BASE/'raw/data_1600_accel_phone.txt').is_file() else BASE/'data/raw/data_1600_accel_phone.txt'
G23=BASE/'g23_reconstructed' if (BASE/'g23_reconstructed').is_dir() else BASE/'g23/example'

@unittest.skipUnless(RAW.is_file() and G23.is_dir(), 'verified raw input is not installed; do not fabricate execution')
class TestIntegration(unittest.TestCase):
    def test_input_identity(self):
        raw,w,s=demo.read_raw(RAW)
        self.assertEqual((len(w),len(s)),(3574,3572))
        self.assertEqual(w[0][0],1)
        self.assertEqual(s[0][0],14292)
        for alpha in (0,1):
            o,z=demo.read_g23(G23,w,alpha)
            self.assertEqual(int(z.sum()),1191 if alpha else 0)
            self.assertEqual(o.shape,(3,3574))
    def test_missing(self):
        with tempfile.TemporaryDirectory() as td:
            r=demo.run(G23,Path(td)/'missing.txt',Path(td)/'out',demo.HERE/'config.json','x',3)
            self.assertEqual(r['status'],'BLOCKED_INPUT')
    def test_wrong_sha(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'wrong.txt';bad.write_text('not WISDM')
            r=demo.run(G23,bad,Path(td)/'out',demo.HERE/'config.json','x',3)
            self.assertEqual(r['status'],'BLOCKED_IDENTITY')
    def test_wrong_segment(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'mutated.txt';raw=RAW.read_bytes()
            bad.write_bytes(raw.replace(b'1600,E,241892286783982',b'1600,E,241892286783983',1))
            self.assertEqual(demo.run(G23,bad,Path(td)/'out',demo.HERE/'config.json','x',3)['status'],'BLOCKED_IDENTITY')
    def test_wrong_config(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'config.json';c=copy.deepcopy(demo.CONFIG);c['min_run_samples']=2
            bad.write_text(json.dumps(c))
            self.assertEqual(demo.run(G23,RAW,Path(td)/'out',bad,'x',3)['status'],'REJECTED_CONFIG')
    def test_wrong_g23(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(demo.run(Path(td),RAW,Path(td)/'out',demo.HERE/'config.json','x',3)['status'],'BLOCKED_INPUT')
    def test_same_results(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            for i in (1,2):
                self.assertEqual(demo.run(G23,RAW,out/str(i),demo.HERE/'config.json','x',3)['status'],'READY_FOR_INDEPENDENT_05_AUDIT')
            for name in ('results.csv','results.json','standing_no_injection/masks.csv','walking_alpha_1/masks.csv'):
                self.assertEqual(hashlib.sha256((out/'1'/name).read_bytes()).digest(),hashlib.sha256((out/'2'/name).read_bytes()).digest())

if __name__=='__main__':unittest.main()
