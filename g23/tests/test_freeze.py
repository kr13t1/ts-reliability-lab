import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from g23.freeze import freeze, metrics, execute, CONFIG, ROOT
from g2.readonly import Refusal

class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.x=np.array([[1,2,4,8,16,32],[6,5,4,3,2,1],[0,1,0,1,0,1]],dtype=np.float64)
    def test_identity_empty_mask(self):
        o,z=freeze(self.x,0,2,4);m=metrics(self.x,o,z,2,4)
        np.testing.assert_array_equal(o,self.x)
        self.assertEqual(m,dict(D_I=0.,D_Z=None,D_Z_status="NOT_APPLICABLE",L_out=0.,n_assigned=0,n_changed=0,outside_identical=True))
    def test_hand_calculated_freeze(self):
        o,z=freeze(self.x,1,2,4);m=metrics(self.x,o,z,2,4)
        np.testing.assert_array_equal(o[0],[1,2,2,2,16,32])
        self.assertAlmostEqual(m['D_I'],20**.5)
        self.assertEqual(m['D_Z'],m['D_I']);self.assertEqual(m['n_changed'],2)
        self.assertEqual(m['n_assigned'],2);self.assertEqual(m['L_out'],0)
    def test_input_and_other_axes_immutable(self):
        old=self.x.copy();o,z=freeze(self.x,1,2,4)
        np.testing.assert_array_equal(old,self.x)
        np.testing.assert_array_equal(o[1:],old[1:])
        self.assertFalse(np.shares_memory(o,self.x))
        self.assertFalse(z[:,:2].any());self.assertFalse(z[:,4:].any())
    def test_assigned_not_changed_on_constant_signal(self):
        x=np.ones((3,6),dtype=np.float64);o,z=freeze(x,1,2,4);m=metrics(x,o,z,2,4)
        self.assertEqual((m['n_assigned'],m['n_changed'],m['D_Z']),(2,0,0.))
    def test_metrics_detect_outside_change(self):
        o,z=freeze(self.x,1,2,4);o[2,5]+=7
        m=metrics(self.x,o,z,2,4);self.assertEqual(m['L_out'],7);self.assertFalse(m['outside_identical'])
    def test_invalid_parameters(self):
        for alpha,a,b in [(2,2,4),(True,2,4),(1,0,4),(1,2,6),(1,4,2),(1,2.,4)]:
            with self.subTest(params=(alpha,a,b)),self.assertRaises(ValueError):freeze(self.x,alpha,a,b)
    def test_nonfinite_input(self):
        self.x[0,0]=np.nan
        with self.assertRaises(ValueError):freeze(self.x,1,2,4)
    def test_wrong_mask(self):
        with self.assertRaises(ValueError):metrics(self.x,self.x,np.zeros((3,6),dtype=int),2,4)
    def test_determinism(self):
        a,z=freeze(self.x,1,2,4);b,w=freeze(self.x,1,2,4)
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(z,w)
    def test_production_mask(self):
        x=np.zeros((3,3574),dtype=np.float64);o,z=freeze(x,1,1191,2382)
        self.assertEqual(z.sum(),1191);self.assertTrue(z[0,1191:2382].all());self.assertFalse(z[1:].any())

class RefusalTests(unittest.TestCase):
    def run_case(self,raw=None,config=None):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);conf=p/'c.json';conf.write_text(json.dumps(CONFIG if config is None else config))
            inp=p/'raw.txt'
            if raw is not None:inp.write_bytes(raw)
            status=execute(inp,p/'out',conf)
            self.assertFalse(list((p/'out').rglob('*.png')))
            self.assertFalse(list((p/'out').rglob('*.csv')))
            self.assertEqual(json.loads((p/'out'/'provenance.json').read_text())['status'],status['status'])
            return status['status']
    def test_missing_raw(self):self.assertEqual(self.run_case(),'BLOCKED_INPUT')
    def test_wrong_raw(self):self.assertEqual(self.run_case(b'1600,A,1,1,2,3;\n'),'BLOCKED_IDENTITY')
    def test_changed_config(self):self.assertEqual(self.run_case(config={**CONFIG,'a':0}),'REJECTED_CONFIG')
    def test_malformed_config(self):self.assertEqual(self.run_case(config=[]),'REJECTED_CONFIG')
    def test_stale_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'old.png').write_bytes(b'old')
            with self.assertRaises(Refusal):execute(p/'raw',p,ROOT/'g23/configs/freeze.json')
            self.assertEqual((p/'old.png').read_bytes(),b'old')

if __name__=='__main__':unittest.main()
