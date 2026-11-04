import unittest
import numpy as np
from g24.detector import detect_constant_runs
from g24.evaluator import evaluate_mask

class TestDetector(unittest.TestCase):
    def d(self,x):return detect_constant_runs(np.asarray(x,dtype=np.float64))
    def test_unique(self):self.assertEqual(int(self.d([1,2,3,4]).sum()),0)
    def test_lminus(self):self.assertEqual(int(self.d([1,2,2,3]).sum()),0)
    def test_l(self):np.testing.assert_array_equal(self.d([1,2,2,2,3]),[0,1,1,1,0])
    def test_two_adjacent(self):np.testing.assert_array_equal(self.d([1,1,1,2,2,2]),[1]*6)
    def test_short(self):self.assertEqual(int(self.d([4,4]).sum()),0)
    def test_first_last(self):np.testing.assert_array_equal(self.d([2,2,2,9,8,8,8]),[1,1,1,0,1,1,1])
    def test_zero_sign(self):np.testing.assert_array_equal(self.d([-0.,0.,0.,2.]),[1,1,1,0])
    def test_nonfinite(self):
        for x in ([1,np.nan,2],[1,np.inf,2],[1,-np.inf,2]):
            with self.assertRaises(ValueError):self.d(x)
    def test_invalid(self):
        for x in (np.array([1,1,1],dtype=np.int32),np.ones((1,3)),np.array([],dtype=np.float64)):
            with self.assertRaises(ValueError):detect_constant_runs(x)
        with self.assertRaises(ValueError):detect_constant_runs(np.array([1.,1.,1.]),L=2)
    def test_anchor(self):
        p=self.d([8,5,5,5,5,1]).astype(np.uint8)
        z=np.array([0,0,1,1,1,0],dtype=np.uint8)
        e=evaluate_mask(p,z)
        self.assertEqual((e['TP'],e['FP'],e['FN'],e['TN']),(3,1,0,2))
    def test_manual(self):
        p=self.d([2,4,4,4,9,1,1,1,7,8]);z=np.array([0,0,1,1,0,0,0,0,0,0],dtype=np.uint8)
        e=evaluate_mask(p,z)
        self.assertEqual((e['TP'],e['FP'],e['FN'],e['TN']),(2,4,0,4))
        self.assertEqual(e['precision'],1/3);self.assertEqual(e['recall'],1.);self.assertEqual(e['FPR'],.5)
        self.assertEqual(e['predicted_nonoverlap_events'],1)
    def test_alpha0(self):
        e=evaluate_mask(self.d([1,2,3]),np.zeros(3,dtype=np.uint8))
        self.assertIsNone(e['recall']);self.assertEqual(e['recall_null_reason'],'NO_INJECTED_POSITIVES')
    def test_standing_no_injection(self):
        e=evaluate_mask(self.d([7,7,7,4]),np.zeros(4,dtype=np.uint8))
        self.assertEqual(e['FP'],3);self.assertIsNone(e['recall'])
    def test_zero_numerical_effect(self):
        x=[0,5,5,5,1];p=self.d(x)
        e1=evaluate_mask(p,np.array([0,0,1,1,0],dtype=np.uint8))
        e0=evaluate_mask(p,np.zeros(5,dtype=np.uint8))
        self.assertEqual(e1['TP'],2);self.assertEqual(e0['FP'],3)
    def test_empty_positives_negatives(self):
        z=np.ones(3,dtype=np.uint8);p=np.ones(3,dtype=np.uint8)
        e=evaluate_mask(p,z);self.assertIsNone(e['FPR']);self.assertIsNone(e['specificity'])
        e=evaluate_mask(np.zeros(3,dtype=np.uint8),z)
        self.assertIsNone(e['precision']);self.assertEqual(e['recall'],0)
    def test_repeated(self):np.testing.assert_array_equal(self.d([1]*20),self.d([1]*20))
    def test_input_unchanged(self):
        x=np.array([1.,1.,1.]);orig=x.copy();self.d(x);np.testing.assert_array_equal(x,orig)
    def test_evaluator_validation(self):
        with self.assertRaises(ValueError):evaluate_mask(np.array([1,2],dtype=np.uint8),np.zeros(2,dtype=np.uint8))
        with self.assertRaises(ValueError):evaluate_mask(np.zeros(2,dtype=np.uint8),np.zeros(3,dtype=np.uint8))

if __name__=='__main__':unittest.main()
