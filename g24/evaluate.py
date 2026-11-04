"""Evaluator: called only *after* an observed-only prediction is frozen."""
from __future__ import annotations
import numpy as np


def _mask(mask: np.ndarray, label: str) -> np.ndarray:
    if not isinstance(mask, np.ndarray) or mask.ndim != 1 or mask.size < 1:
        raise ValueError(f'{label} must be nonempty one-dimensional numpy array')
    if mask.dtype == np.bool_:
        return mask
    if mask.dtype == np.uint8 and np.all((mask == 0) | (mask == 1)):
        return mask.astype(bool)
    raise ValueError(f'{label} must be bool or binary uint8 mask')


def intervals(mask: np.ndarray) -> list[list[int]]:
    bits = _mask(mask, 'mask')
    padded = np.r_[False, bits, False].astype(np.int8)
    starts = np.flatnonzero(np.diff(padded) == 1)
    ends = np.flatnonzero(np.diff(padded) == -1)
    return [[int(a), int(b)] for a, b in zip(starts, ends)]


def evaluate_mask(predicted: np.ndarray, assigned: np.ndarray) -> dict:
    """Pointwise counts on exactly one channel; None for zero denominator."""
    p, z = _mask(predicted, 'predicted'), _mask(assigned, 'assigned')
    if p.shape != z.shape:
        raise ValueError('masks must have equal shape')
    tp, fp = int(np.count_nonzero(p & z)), int(np.count_nonzero(p & ~z))
    fn, tn = int(np.count_nonzero(~p & z)), int(np.count_nonzero(~p & ~z))
    n = int(z.size)
    def safe(numerator: int, denominator: int, reason: str):
        return (numerator / denominator, None) if denominator else (None, reason)
    prec, prec_reason = safe(tp, tp + fp, 'NO_PREDICTED_POSITIVES')
    rec, rec_reason = safe(tp, tp + fn, 'NO_INJECTED_POSITIVES')
    fpr, fpr_reason = safe(fp, fp + tn, 'NO_INJECTION_NEGATIVES')
    specificity, spec_reason = safe(tn, fp + tn, 'NO_INJECTION_NEGATIVES')
    assert tp + fp + fn + tn == n
    true_events, pred_events = intervals(z), intervals(p)
    overlaps = lambda u, v: max(u[0], v[0]) < min(u[1], v[1])
    true_event_overlaps = [any(overlaps(t, d) for d in pred_events) for t in true_events]
    nonoverlap = sum(not any(overlaps(d, t) for t in true_events) for d in pred_events)
    return {
        'N': n, 'TP': tp, 'FP': fp, 'FN': fn, 'TN': tn,
        'n_true': tp + fn, 'n_pred': tp + fp,
        'precision': prec, 'precision_null_reason': prec_reason,
        'recall': rec, 'recall_null_reason': rec_reason,
        'FPR': fpr, 'FPR_null_reason': fpr_reason,
        'specificity': specificity, 'specificity_null_reason': spec_reason,
        'true_events': true_events, 'pred_events': pred_events,
        'true_event_overlaps': true_event_overlaps,
        'pred_events_without_true_overlap': int(nonoverlap),
        'true_event_overlap_fraction': (sum(true_event_overlaps) / len(true_events)) if true_events else None,
    }
