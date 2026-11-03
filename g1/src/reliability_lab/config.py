"""Fixed approved G1 experiment. Only alpha in [0,1] is configurable."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


# An explicit immutable reference for the approved contract; inputs changing
# anything except corruption.alpha are rejected (no silent tuning).
CONTRACT_CONFIG: dict[str, Any] = {
    "contract": "G1_SPEC.md v1.0 (2026-11-01)",
    "experiment": {
        "kind": "synthetic demonstration",
        "record_ids": ["rest", "walk"],
        "labels": [0, 1],
        "record_count": 2,
        "axis_names": ["x", "y", "z"],
        "axis_count": 3,
        "unit": "m/s^2",
        "signal_description": "conditional dynamic acceleration with gravity removed",
        "training_or_split": None,
    },
    "generator": {
        "fs_hz": 20,
        "duration_s": 10.0,
        "samples": 200,
        "time_definition": "t_i = i / fs, i = 0,...,199",
        "dtype": "float64",
        "seed": 20261101,
        "random_bit_generator": "numpy.random.PCG64",
        "rng": "numpy.random.Generator(numpy.random.PCG64(seed))",
        "noise_draw": "one call standard_normal(size=(2,3,200), dtype=numpy.float64)",
        "noise_shape": [2, 3, 200],
        "expected_numpy_version": "2.3.5",
        "noise_sigma_m_s2": 0.03,
        "sine_frequency_hz": 2.0,
        "amplitudes_m_s2": [0.8, 0.5, 0.3],
        "phases_rad": ["0", "pi/3", "pi/2"],
        "reference_definitions": ["sigma * eps[0]", "A_c * sin(2*pi*f*t + phi_c) + sigma * eps[1]"],
        "filters_or_normalization": None,
    },
    "corruption": {
        "kind": "axis freeze to last pre-event value",
        "axis": 0,
        "start_s": 3.0,
        "end_s": 6.0,
        "start_idx": 60,
        "end_idx": 120,
        "anchor_idx": 59,
        "alpha": 1.0,
        "corruption_seed": None,
        "event_interval": "[60,120)",
        "formula": "(1-alpha)*X_ref[0,i] + alpha*X_ref[0,59]",
        "mask_definition": "Z[c,i] = int(alpha>0 and c==0 and 60<=i<120)",
        "mask_semantics": "assigned injection positions, not observed inequality or detector",
    },
    "baseline": {
        "name": "mean-centered tri-axial RMS activity heuristic",
        "threshold_m_s2": 0.20,
        "decision": "pred = int(S >= 0.20)",
        "score_formula": "sqrt(mean((X[c,i]-mean_i(X[c,i]))**2 over all c,i))",
        "training": None,
        "fault_detector": False,
    },
    "metrics": {
        "event_rmse": "sqrt(mean((X_obs[0,60:120]-X_ref[0,60:120])**2))",
        "event_denominator": 60,
        "event_rmse_defined_at_alpha_zero": True,
        "delta_score": "S_obs - S_ref",
        "classification_error": "int(pred != y)",
        "measurement_unit": "m/s^2",
    },
}


def default_config() -> dict[str, Any]:
    return deepcopy(CONTRACT_CONFIG)


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Reject deviations from every pinned field except the approved strength α."""
    if not isinstance(config, dict) or not isinstance(config.get("corruption"), dict):
        raise ValueError("Invalid configuration: missing corruption section")
    alpha = config["corruption"].get("alpha")
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be a finite number in [0, 1]")
    candidate = deepcopy(config)
    candidate["corruption"]["alpha"] = 1.0
    if candidate != CONTRACT_CONFIG:
        raise ValueError("Configuration differs from approved G1_SPEC.md v1.0 (only alpha may vary)")
    return deepcopy(config)


def read_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        return validate_config(json.load(file))


def write_config(config: dict[str, Any], path: str | Path) -> None:
    validate_config(config)
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")
