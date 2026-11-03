"""Two deterministic synthetic tri-axial signals, per G1_SPEC §2."""
from __future__ import annotations
import numpy as np


def generate_reference(config: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (X_ref[rest,walk;axis;sample], labels, time_s)."""
    g = config["generator"]
    fs = g["fs_hz"]
    n = g["samples"]
    rng = np.random.Generator(np.random.PCG64(g["seed"]))
    # Exactly one draw in exactly this order and dtype. Never split RNG calls.
    eps = rng.standard_normal(size=(2, 3, 200), dtype=np.float64)
    time_s = np.arange(n, dtype=np.float64) / fs
    amplitudes = np.asarray(g["amplitudes_m_s2"], dtype=np.float64)
    # These analytic phases are fixed by the contract, not rounded decimals.
    phases = np.array([0.0, np.pi / 3.0, np.pi / 2.0], dtype=np.float64)
    sigma = g["noise_sigma_m_s2"]
    freq = g["sine_frequency_hz"]
    rest = sigma * eps[0]
    walk = (amplitudes[:, None]
            * np.sin(2.0 * np.pi * freq * time_s[None, :] + phases[:, None])
            + sigma * eps[1])
    x_ref = np.stack((rest, walk), axis=0)
    labels = np.array(config["experiment"]["labels"], dtype=np.int64)
    return x_ref, labels, time_s
