import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from g24 import demo

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/'data/raw/data_1600_accel_phone.txt'
G23=ROOT/'g23/example'

@unittest.skipUnless(INPUT.is_file() and (G23/'alpha_1/arrays.csv').is_file(),
                     'integration tests require verified raw and G2.3 accepted output')
class PipelineTests(unittest.TestCase):
    def test_pins(self):
        self.assertEqual(demo.sha_file(INPUT),demo.EXPECTED_CONFIG['raw_sha256'])
        self.assertEqual(demo.read_observed_only(G23/'alpha_1/arrays.csv').shape,(3574,))
        self.assertEqual(demo.validate_g23_metadata(G23,demo.EXPECTED_CONFIG)['g23_files_sha256']['reference.csv'],demo.EXPECTED_CONFIG['g23_reference_sha256'])
    def test_standing_verified_source_and_integer_q(self):
        a,e,digest=demo.read_raw_standing(INPUT,demo.EXPECTED_CONFIG)
        self.assertEqual((len(a),len(e),e[0].line,e[-1].line),(3574,3572,14292,17863))
        self.assertEqual(digest,demo.EXPECTED_CONFIG['standing_segment_sha256'])
        self.assertEqual((e[0].q,e[-1].q),(241892286783982,242072100924919))
    def test_prediction_does_not_see_mask(self):
        x=demo.read_observed_only(G23/'alpha_1/arrays.csv')
        pred=demo.detect_constant_runs(x)
        self.assertEqual(np.flatnonzero(pred)[0],1190)
        self.assertEqual(np.flatnonzero(pred)[-1],2381)
        a,_,_=demo.read_raw_standing(INPUT,demo.EXPECTED_CONFIG)
        obs,z=demo.validate_g23_arrays(G23/'alpha_1/arrays.csv',a,1,pred)
        self.assertTrue(np.array_equal(obs,x));self.assertEqual(np.flatnonzero(z)[0],1191)
    def test_three_cases_and_provenance_and_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            out1=Path(td)/'one';out2=Path(td)/'two'
            r1=demo.execute(G23,INPUT,out1,demo.CONFIG_PATH,axis='x',L=3)
            r2=demo.execute(G23,INPUT,out2,demo.CONFIG_PATH,axis='x',L=3)
            self.assertEqual((r1['status'],r2['status']),('PASS_DEMO','PASS_DEMO'))
            def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
            for p in out1.rglob('*'):
                if p.is_file() and p.name!='provenance.json':
                    self.assertEqual(digest(p),digest(out2/p.relative_to(out1)),p.name)
            with (out1/'results.csv').open(encoding='utf-8',newline='') as file:
                rows=list(csv.DictReader(file))
            self.assertEqual([(r['case_id'],r['TP'],r['FP'],r['FN'],r['TN']) for r in rows],
                  [('1600_A_alpha_0','0','0','0','3574'),('1600_A_alpha_1','1191','1','0','2382'),('1600_E_raw','0','0','0','3572')])
            self.assertEqual([r['recall'] for r in rows],['null','1.0','null'])
            for case, n in [('1600_A_alpha_0',3574),('1600_A_alpha_1',3574),('1600_E_raw',3572)]:
                with (out1/case/'masks.csv').open(encoding='utf-8') as file:
                    csv_rows=list(csv.DictReader(file))
                self.assertEqual(len(csv_rows),n)
                self.assertEqual(csv_rows[0]['source_line'],'14292' if case.endswith('raw') else '1')
                self.assertTrue((out1/case/'detection.png').is_file())
            prov=json.loads((out1/'provenance.json').read_text())
            self.assertEqual(prov['seed'],None)
            self.assertEqual(prov['standing_segment_sha256'],demo.EXPECTED_CONFIG['standing_segment_sha256'])
    def test_bad_missing_raw_and_wrong_sha(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'wrong.txt';path.write_bytes(b'1600,E,1,1,2,3;\n')
            out=Path(td)/'out';r=demo.execute(G23,path,out,demo.CONFIG_PATH)
            self.assertEqual(r['status'],'BLOCKED_IDENTITY')
            self.assertFalse((out/'results.csv').exists())
            missing=demo.execute(G23,Path(td)/'absent.txt',Path(td)/'missing',demo.CONFIG_PATH)
            self.assertEqual(missing['status'],'BLOCKED_INPUT')
    def test_bad_config_and_wrong_segment_identity(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'config.json'
            config=demo.EXPECTED_CONFIG|{'min_run_samples':2}
            bad.write_text(json.dumps(config))
            r=demo.execute(G23,INPUT,Path(td)/'bad',bad)
            self.assertEqual(r['status'],'REJECTED_CONFIG')
            # Explicit bad region pin: catches segment identity without reading injected mask.
            changed=demo.EXPECTED_CONFIG|{'standing_segment_sha256':'0'*64}
            with self.assertRaises(demo.Refusal) as cm:
                demo.read_raw_standing(INPUT,changed)
            self.assertEqual(cm.exception.status,'REPORT_MISMATCH')
    def test_reject_non_x_or_tuned_L(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(demo.execute(G23,INPUT,Path(td)/'a',demo.CONFIG_PATH,axis='y')['status'],'REJECTED_CONFIG')
            self.assertEqual(demo.execute(G23,INPUT,Path(td)/'b',demo.CONFIG_PATH,L=4)['status'],'REJECTED_CONFIG')
    def test_nonempty_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);(out/'existing.txt').write_text("do not change me")
            with self.assertRaises(demo.Refusal): demo.execute(G23,INPUT,out,demo.CONFIG_PATH)
            self.assertEqual((out/'existing.txt').read_text(),"do not change me")
if __name__=='__main__':unittest.main()
