import unittest
import numpy as np
from g24.detector import detect_constant_runs
from g24.evaluate import evaluate_mask, intervals

class DetectorTests(unittest.TestCase):
    def m(self, xs, L=3):
        return detect_constant_runs(np.array(xs,dtype=np.float64),L).astype(int).tolist()
    def test_all_unique(self):
        self.assertEqual(self.m([0,1,2,3,4]),[0]*5)
    def test_L_minus_one(self):
        self.assertEqual(self.m([0,1,1,2]),[0]*4)
    def test_exact_L(self):
        self.assertEqual(self.m([0,1,1,1,2]),[0,1,1,1,0])
    def test_longer_L(self):
        self.assertEqual(self.m([5,5,5,5]),[1]*4)
    def test_adjacent_distinct_runs(self):
        self.assertEqual(self.m([2,2,2,1,1,1,9]),[1,1,1,1,1,1,0])
    def test_first_and_last(self):
        self.assertEqual(self.m([7,7,7,0,3,3,3]),[1,1,1,0,1,1,1])
    def test_shorter_than_L(self):
        self.assertEqual(self.m([7,7]),[0,0])
    def test_plus_minus_zero(self):
        self.assertEqual(self.m([0.,-0.,0.,1.]),[1,1,1,0])
    def test_new_array_and_determinism(self):
        x=np.array([1.,2.,2.,2.,4.],dtype=np.float64);original=x.copy()
        a=detect_constant_runs(x);b=detect_constant_runs(x)
        self.assertTrue(np.array_equal(a,b) and np.array_equal(x,original))
        self.assertFalse(np.shares_memory(x,a))
    def test_reject_invalid(self):
        for x in [[],[1.,float('nan'),1.],[1.,float('inf'),1.]]:
            with self.subTest(x=x),self.assertRaises(ValueError):self.m(x)
        for bad in [np.array([1,1,1]),np.array([[1.,1.,1.]]),[1.,1.,1.]]:
            with self.subTest(bad=str(bad)),self.assertRaises(ValueError):detect_constant_runs(bad)
        for bad in [0,-1,2.0,True,None]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):detect_constant_runs(np.array([1.]),bad)

class EvaluatorTests(unittest.TestCase):
    def test_manual_A(self):
        pred=np.array([0,1,1,1,0,1,1,1,0,0],dtype=np.uint8)
        z=np.array([0,0,1,1,0,0,0,0,0,0],dtype=np.uint8)
        m=evaluate_mask(pred,z)
        self.assertEqual(tuple(m[k] for k in ('TP','FP','FN','TN')),(2,4,0,4))
        self.assertEqual(m['precision'],1/3)
        self.assertEqual(m['recall'],1.0)
        self.assertEqual(m['FPR'],0.5)
        self.assertEqual(m['true_events'],[[2,4]])
        self.assertEqual(m['pred_events'],[[1,4],[5,8]])
        self.assertEqual(m['true_event_overlaps'],[True])
        self.assertEqual(m['pred_events_without_true_overlap'],1)
    def test_boundary_fp(self):
        p=detect_constant_runs(np.array([5.,4.,4.,4.,9.],dtype=np.float64))
        z=np.array([0,0,1,1,0],dtype=np.uint8)
        self.assertEqual(tuple(evaluate_mask(p,z)[k] for k in ('TP','FP','FN','TN')),(2,1,0,2))
    def test_alpha0_null_recall_and_precision(self):
        m=evaluate_mask(np.zeros(5,dtype=bool),np.zeros(5,dtype=bool))
        self.assertIsNone(m['precision']);self.assertEqual(m['precision_null_reason'],'NO_PREDICTED_POSITIVES')
        self.assertIsNone(m['recall']);self.assertEqual(m['recall_null_reason'],'NO_INJECTED_POSITIVES')
        self.assertEqual(m['FPR'],0.0);self.assertEqual(m['specificity'],1.0)
    def test_no_pred_true_pos(self):
        m=evaluate_mask(np.zeros(5,dtype=bool),np.array([0,1,1,0,0],dtype=np.uint8))
        self.assertIsNone(m['precision']);self.assertEqual(m['recall'],0.0)
    def test_no_negatives(self):
        m=evaluate_mask(np.ones(4,dtype=bool),np.ones(4,dtype=bool))
        self.assertIsNone(m['FPR']);self.assertIsNone(m['specificity'])
        self.assertEqual(m['FPR_null_reason'],'NO_INJECTION_NEGATIVES')
    def test_zero_effect_unidentifiable(self):
        x=np.array([0.,5.,5.,5.,1.])
        p=detect_constant_runs(x)
        control=np.zeros(5,dtype=np.uint8)
        injected=np.array([0,0,1,1,0],dtype=np.uint8)
        self.assertTrue(np.array_equal(p,detect_constant_runs(x)))
        self.assertEqual(evaluate_mask(p,control)['FP'],3)
        self.assertEqual(evaluate_mask(p,injected)['TP'],2)
    def test_events_empty(self):
        self.assertEqual(intervals(np.zeros(3,dtype=bool)),[])
    def test_reject_masks(self):
        bad=[np.array([0,2,0],dtype=np.uint8),np.array([0.,1.,0.]),np.array([[0,1]],dtype=np.uint8),np.array([],dtype=bool)]
        for x in bad:
            with self.subTest(x=x), self.assertRaises(ValueError):evaluate_mask(x,np.zeros(3,dtype=bool))
        with self.assertRaises(ValueError):evaluate_mask(np.ones(2,dtype=bool),np.zeros(3,dtype=bool))
if __name__=='__main__':unittest.main()
