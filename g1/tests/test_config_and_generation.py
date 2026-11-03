from copy import deepcopy
import numpy as np
import pytest

from reliability_lab.config import default_config, read_config, validate_config
from reliability_lab.signals import generate_reference


def test_config_matches_contract_file():
    assert read_config("configs/g1.json") == default_config()


def test_generator_shape_seed_order_and_finiteness():
    cfg = default_config()
    x, y, t = generate_reference(cfg)
    xx, yy, tt = generate_reference(cfg)
    assert x.shape == (2, 3, 200) and x.dtype == np.float64
    assert y.shape == (2,) and y.tolist() == [0, 1]
    assert t.shape == (200,) and t[0] == 0.0 and t[-1] == 9.95
    assert np.array_equal(x, xx)
    assert np.array_equal(y, yy)
    assert np.array_equal(t, tt)
    assert np.isfinite(x).all()
    rng = np.random.Generator(np.random.PCG64(20261101))
    eps = rng.standard_normal(size=(2, 3, 200), dtype=np.float64)
    assert np.array_equal(x[0], 0.03 * eps[0])
    amp = np.array([0.8, 0.5, 0.3])
    phases = np.array([0.0, np.pi / 3, np.pi / 2])
    expected_walk = amp[:, None] * np.sin(2 * np.pi * 2 * t[None, :] + phases[:, None]) + 0.03 * eps[1]
    assert np.array_equal(x[1], expected_walk)


@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0, 0.1234])
def test_only_alpha_is_adjustable(alpha):
    c = default_config()
    c["corruption"]["alpha"] = alpha
    assert validate_config(c) == c


@pytest.mark.parametrize("invalid_alpha", [-0.1, 1.0001, float("nan"), float("inf"), "0.5", True])
def test_invalid_strength_rejected(invalid_alpha):
    c = default_config()
    c["corruption"]["alpha"] = invalid_alpha
    with pytest.raises(ValueError):
        validate_config(c)


def test_no_other_parameter_or_label_can_be_changed():
    c = default_config()
    c["baseline"]["threshold_m_s2"] = 0.25
    with pytest.raises(ValueError):
        validate_config(c)
    c = default_config()
    c["generator"]["seed"] += 1
    with pytest.raises(ValueError):
        validate_config(c)
    c = default_config()
    c["experiment"]["labels"] = [1, 0]
    with pytest.raises(ValueError):
        validate_config(c)
