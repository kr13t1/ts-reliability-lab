"""Frozen G2.4 constant-run detection; no access to assignment/labels."""
import numpy as np


def detect_constant_runs(observed_x: np.ndarray, L: int = 3) -> np.ndarray:
    """Mark all samples of maximal *exactly equal* runs of length >= L."""
    if type(L) is not int or L != 3:
        raise ValueError('G2.4 contract requires L=3')
    if not isinstance(observed_x, np.ndarray) or observed_x.dtype != np.float64 or observed_x.ndim != 1 or not len(observed_x) or not np.isfinite(observed_x).all():
        raise ValueError('expected nonempty, finite 1-D float64 observed_x')
    n = len(observed_x)
    predicted = np.zeros(n, dtype=np.uint8)
    start = 0
    for end in range(1, n + 1):
        if end == n or observed_x[end] != observed_x[start]:
            if end - start >= L:
                predicted[start:end] = 1
            start = end
    return predicted
