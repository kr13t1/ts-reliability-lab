import numpy as np
import pytest
from reliability_lab.config import default_config
from reliability_lab.signals import generate_reference
from reliability_lab.corruption import apply_axis_freeze, corrupt_both
from reliability_lab.metrics import event_rmse


@pytest.mark.parametrize("record", [0, 1])
def test_alpha_one_freezes_x_only_and_edges_unchanged(record):
    cfg = default_config()
    x_ref = generate_reference(cfg)[0][record]
    saved = x_ref.copy()
    x_obs, z = apply_axis_freeze(x_ref, cfg)
    assert np.array_equal(x_ref, saved)
    assert np.array_equal(x_obs[0, 60:120], np.full(60, x_ref[0, 59]))
    assert np.array_equal(x_obs[0, :60], x_ref[0, :60])
    assert np.array_equal(x_obs[0, 120:], x_ref[0, 120:])
    assert np.array_equal(x_obs[1:, :], x_ref[1:, :])
    assert x_obs[0, 59] == x_ref[0, 59] and x_obs[0, 120] == x_ref[0, 120]
    assert z.dtype == np.uint8 and z.shape == (3, 200)
    assert z.sum() == 60 and np.all(z[0, 60:120] == 1)
    assert z.sum(axis=1).tolist() == [60, 0, 0]
    assert np.all(z[0, :60] == 0) and np.all(z[0, 120:] == 0)


@pytest.mark.parametrize("record", [0, 1])
def test_half_strength_linear_formula_and_event_scaling(record):
    cfg = default_config()
    original = generate_reference(cfg)[0][record]
    obs_one, mask_one = apply_axis_freeze(original, cfg)
    cfg["corruption"]["alpha"] = 0.5
    obs_half, mask_half = apply_axis_freeze(original, cfg)
    expected = 0.5 * original[0, 60:120] + 0.5 * original[0, 59]
    assert np.array_equal(obs_half[0, 60:120], expected)
    assert np.array_equal(mask_one, mask_half) and mask_half.sum() == 60
    cfg_one = default_config()
    assert abs(event_rmse(original, obs_half, cfg) - 0.5 * event_rmse(original, obs_one, cfg_one)) <= 1e-12


@pytest.mark.parametrize("record", [0, 1])
def test_alpha_zero_mask_is_all_zero_even_with_planned_window(record):
    cfg = default_config()
    cfg["corruption"]["alpha"] = 0.0
    ref = generate_reference(cfg)[0][record]
    obs, mask = apply_axis_freeze(ref, cfg)
    assert np.array_equal(obs, ref)
    assert not mask.any()
    assert event_rmse(ref, obs, cfg) == 0.0


def test_mask_tracks_assigned_sites_even_if_reference_equals_anchor():
    cfg = default_config()
    ref = np.zeros((3, 200), dtype=np.float64)
    obs, mask = apply_axis_freeze(ref, cfg)
    assert np.array_equal(obs, ref)
    assert mask[0, 60:120].sum() == 60


def test_freeze_independently_on_both_records():
    cfg = default_config()
    ref, _, _ = generate_reference(cfg)
    obs, masks = corrupt_both(ref, cfg)
    assert obs.shape == masks.shape == (2, 3, 200)
    assert np.array_equal(obs[0, 0, 60:120], np.full(60, ref[0, 0, 59]))
    assert np.array_equal(obs[1, 0, 60:120], np.full(60, ref[1, 0, 59]))
    assert masks.sum() == 120
