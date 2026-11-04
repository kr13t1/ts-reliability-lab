"""Separate evaluator: assigned labels are forbidden in detector."""
import numpy as np


def positive_intervals(z):
    a = np.flatnonzero(np.diff(np.pad(z.astype(np.int8), (1, 1))))
    return [(int(a[i]), int(a[i + 1])) for i in range(0, len(a), 2)]


def evaluate_mask(predicted: np.ndarray, assigned: np.ndarray) -> dict:
    for name, x in (("predicted", predicted), ("assigned", assigned)):
        if not isinstance(x, np.ndarray) or x.ndim != 1 or x.dtype != np.uint8 or not len(x) or not np.isin(x, (0, 1)).all():
            raise ValueError(f'{name}: expected nonempty 1-D binary uint8')
    if predicted.shape != assigned.shape:
        raise ValueError('shape mismatch')
    p, z = predicted.astype(bool), assigned.astype(bool)
    tp, fp, fn, tn = (int(np.count_nonzero(q)) for q in (p & z, p & ~z, ~p & z, ~p & ~z))
    n = len(p)
    assert tp + fp + fn + tn == n
    def ratio(num, den, why):
        return (num / den, None) if den else (None, why)
    precision, precision_reason = ratio(tp, tp + fp, 'NO_PREDICTED_POSITIVES')
    recall, recall_reason = ratio(tp, tp + fn, 'NO_INJECTED_POSITIVES')
    fpr, fpr_reason = ratio(fp, fp + tn, 'NO_INJECTION_NEGATIVES')
    specificity, specificity_reason = ratio(tn, fp + tn, 'NO_INJECTION_NEGATIVES')
    truth_events, predicted_events = positive_intervals(assigned), positive_intervals(predicted)
    overlap = lambda a, b: max(a[0], b[0]) < min(a[1], b[1])
    true_hit = [any(overlap(t, p_) for p_ in predicted_events) for t in truth_events]
    nonoverlap = sum(not any(overlap(t, p_) for t in truth_events) for p_ in predicted_events)
    return dict(N=n, TP=tp, FP=fp, FN=fn, TN=tn, n_true=tp + fn, n_pred=tp + fp,
                precision=precision, precision_null_reason=precision_reason,
                recall=recall, recall_null_reason=recall_reason,
                FPR=fpr, FPR_null_reason=fpr_reason,
                specificity=specificity, specificity_null_reason=specificity_reason,
                true_events=truth_events, predicted_events=predicted_events,
                true_event_overlap=true_hit, predicted_nonoverlap_events=nonoverlap,
                event_overlap_fraction=(sum(true_hit) / len(true_hit)) if true_hit else None)
