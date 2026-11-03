from copy import deepcopy
import numpy as np
import pytest
from reliability_lab.baseline import rms_score, predict_activity
from reliability_lab.config import default_config
from reliability_lab.corruption import apply_axis_freeze
from reliability_lab.signals import generate_reference
from reliability_lab.metrics import event_rmse, record_metrics


def test_hand_calculation_axis_means_global_rms_and_classification_error():
    x = np.zeros((3, 200), dtype=np.float64)
    # 100 zeroes, 100 twos; x-axis mean 1, deviations -1/+1;
    # y,z are constant and do not contribute to centered RMS.
    x[0, 100:] = 2.0
    x[1] = 10.0
    x[2] = -7.0
    means = [1.0, 10.0, -7.0]
    assert np.allclose(x.mean(axis=1), means, atol=1e-12, rtol=0)
    expected = np.sqrt(200.0 / 600.0)
    assert abs(rms_score(x) - expected) <= 1e-12
    assert predict_activity(x) == 1
    cfg = default_config()
    row = record_metrics("rest", 0, x, x.copy(), cfg)
    assert row["pred_ref"] == row["pred_obs"] == 1
    assert row["error_ref"] == row["error_obs"] == 1
    assert row["delta_S_m_s2"] == 0.0
    assert row["rmse_event_m_s2"] == 0.0


def test_hand_calculation_event_rmse_not_divided_by_mask_size():
    x = np.zeros((3, 200), dtype=np.float64)
    obs = x.copy()
    obs[0, 60:90] = 2.0
    expected = np.sqrt((30.0 * 4.0) / 60.0)
    assert abs(event_rmse(x, obs, default_config()) - expected) <= 1e-12


def test_threshold_is_fixed_and_inclusive():
    x = np.zeros((3, 200), dtype=np.float64)
    x[0, 100:] = 2.0
    assert predict_activity(x) == 1
    with pytest.raises(ValueError):
        predict_activity(x, threshold_m_s2=0.3)


@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0])
def test_record_metrics_are_consistent(alpha):
    cfg = default_config()
    cfg["corruption"]["alpha"] = alpha
    ref, labels, _ = generate_reference(cfg)
    for i, name in enumerate(("rest", "walk")):
        obs, mask = apply_axis_freeze(ref[i], cfg)
        row = record_metrics(name, labels[i], ref[i], obs, cfg)
        assert row["alpha"] == alpha
        assert row["error_ref"] == int(row["pred_ref"] != labels[i])
        assert row["error_obs"] == int(row["pred_obs"] != labels[i])
        assert row["delta_S_m_s2"] == row["S_obs_m_s2"] - row["S_ref_m_s2"]
        if alpha == 0.0:
            assert row["S_ref_m_s2"] == row["S_obs_m_s2"]
            assert row["delta_S_m_s2"] == row["rmse_event_m_s2"] == 0.0
            assert row["pred_ref"] == row["pred_obs"]
            assert not mask.any()
        else:
            assert mask.sum() == 60


def test_reference_numbers_for_alpha_one_tolerance_1e_minus_9():
    cfg = default_config()
    x_ref, labels, _ = generate_reference(cfg)
    expected = [
        (0.030236726394, 0.039481271255, 0.105545200200, 0, 0, 0, 0),
        (0.404957682970, 0.385989699825, 0.741924644698, 1, 1, 0, 0),
    ]
    for i, name in enumerate(("rest", "walk")):
        x_obs, _ = apply_axis_freeze(x_ref[i], cfg)
        row = record_metrics(name, int(labels[i]), x_ref[i], x_obs, cfg)
        sr, so, rmse, pr, po, er, eo = expected[i]
        assert abs(row["S_ref_m_s2"] - sr) <= 1e-9
        assert abs(row["S_obs_m_s2"] - so) <= 1e-9
        assert abs(row["rmse_event_m_s2"] - rmse) <= 1e-9
        assert (row["pred_ref"], row["pred_obs"], row["error_ref"], row["error_obs"]) == (pr, po, er, eo)
