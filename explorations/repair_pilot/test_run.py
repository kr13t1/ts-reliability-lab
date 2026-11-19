import unittest
import numpy as np
from run import freeze, repair

class RepairTests(unittest.TestCase):
    def test_freeze(self):
        x=np.arange(12.,dtype=float); y=freeze(x,4,8)
        np.testing.assert_array_equal(x,np.arange(12.))
        np.testing.assert_array_equal(y[4:8],np.repeat(3.,4))
        np.testing.assert_array_equal(y[:4],x[:4]); np.testing.assert_array_equal(y[8:],x[8:])
    def test_linear_ramp(self):
        x=np.arange(300.,dtype=float); y=freeze(x,270,280)
        np.testing.assert_allclose(repair(y,270,280,'linear'),x)
    def test_hold(self):
        y=freeze(np.arange(300.),270,280)
        np.testing.assert_array_equal(repair(y,270,280,'hold'),y)
    def test_ar_constant(self):
        x=np.full(300,3.); y=freeze(x,270,280)
        np.testing.assert_allclose(repair(y,270,280,'ar10'),x,atol=1e-10)
    def test_no_inside_or_future_leak_ar(self):
        x=np.sin(np.arange(350)*.2); y=freeze(x,270,280); z=y.copy(); z[270:]=999
        np.testing.assert_array_equal(repair(y,270,280,'ar10')[270:280],repair(z,270,280,'ar10')[270:280])
    def test_outside_unchanged(self):
        y=freeze(np.sin(np.arange(350)*.2),270,280)
        for method in ['hold','linear','ar10']:
            z=repair(y,270,280,method)
            np.testing.assert_array_equal(z[:270],y[:270]); np.testing.assert_array_equal(z[280:],y[280:])
if __name__=='__main__': unittest.main()
