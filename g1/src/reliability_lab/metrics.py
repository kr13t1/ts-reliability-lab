"""Only the observation and per-record baseline metrics defined by G1_SPEC."""
from __future__ import annotations
import numpy as np
from .baseline import rms_score, predict_activity


CSV_FIELDS = [
    "record_id", "y", "seed", "fs_hz", "alpha", "axis", "start_idx", "end_idx",
    "S_ref_m_s2", "S_obs_m_s2", "delta_S_m_s2", "pred_ref", "pred_obs",
    "error_ref", "error_obs", "rmse_event_m_s2",
]


def event_rmse(x_ref: np.ndarray, x_obs: np.ndarray, config: dict) -> float:
    """Always over the predetermined 60 samples; never over mask.sum()."""
    p = config["corruption"]
    d = x_obs[p["axis"], p["start_idx"]:p["end_idx"]] - x_ref[
        p["axis"], p["start_idx"]:p["end_idx"]]
    return float(np.sqrt(np.mean(d ** 2)))


def record_metrics(record_id: str, y: int, x_ref: np.ndarray, x_obs: np.ndarray,
                   config: dict) -> dict:
    s_ref = rms_score(x_ref)
    s_obs = rms_score(x_obs)
    threshold = config["baseline"]["threshold_m_s2"]
    pred_ref = predict_activity(x_ref, threshold_m_s2=threshold)
    pred_obs = predict_activity(x_obs, threshold_m_s2=threshold)
    p = config["corruption"]
    return {
        "record_id": record_id,
        "y": int(y),
        "seed": config["generator"]["seed"],
        "fs_hz": config["generator"]["fs_hz"],
        "alpha": float(p["alpha"]),
        "axis": p["axis"],
        "start_idx": p["start_idx"],
        "end_idx": p["end_idx"],
        "S_ref_m_s2": s_ref,
        "S_obs_m_s2": s_obs,
        "delta_S_m_s2": s_obs - s_ref,
        "pred_ref": pred_ref,
        "pred_obs": pred_obs,
        "error_ref": int(pred_ref != y),
        "error_obs": int(pred_obs != y),
        "rmse_event_m_s2": event_rmse(x_ref, x_obs, config),
    }
