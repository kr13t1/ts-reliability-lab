"""Read-only numerical audit of saved G1 artifacts, without importing implementation.

Recompute baseline scores and event errors with scalar Python math.fsum,
independently of the NumPy implementation that wrote results.csv.
"""
import csv
import json
import math
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "rest": (0.030236726394, 0.039481271255, 0.105545200200),
    "walk": (0.404957682970, 0.385989699825, 0.741924644698),
}


def score(x):
    means = [math.fsum(float(v) for v in x[c]) / 200 for c in range(3)]
    return math.sqrt(math.fsum((float(x[c, i]) - means[c]) ** 2
                               for c in range(3) for i in range(200)) / 600)


def verify(directory):
    with np.load(directory / "g1_arrays.npz", allow_pickle=False) as arrays:
        ref = arrays["x_ref"]
        obs = arrays["x_obs"]
        mask = arrays["mask"]
        labels = arrays["labels"]
        time = arrays["time_s"]
    cfg = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    alpha = cfg["corruption"]["alpha"]
    with (directory / "results.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    assert np.array_equal(labels, np.array([0, 1]))
    assert np.array_equal(time, np.arange(200) / 20)
    assert ref.shape == obs.shape == mask.shape == (2, 3, 200)
    for j, (name, y) in enumerate((('rest', 0), ('walk', 1))):
        row = rows[j]
        assert row["record_id"] == name and int(row["y"]) == y
        expected_mask = np.zeros((3, 200), dtype=np.uint8)
        if alpha > 0:
            expected_mask[0, 60:120] = 1
        assert np.array_equal(mask[j], expected_mask)
        expected_obs = ref[j].copy()
        if alpha > 0:
            expected_obs[0, 60:120] = ((1 - alpha) * ref[j, 0, 60:120]
                                           + alpha * ref[j, 0, 59])
        assert np.array_equal(obs[j], expected_obs)
        sref = score(ref[j])
        sobs = score(obs[j])
        error = math.sqrt(math.fsum((float(obs[j, 0, i]) - float(ref[j, 0, i])) ** 2
                                    for i in range(60, 120)) / 60)
        computed = {
            "S_ref_m_s2": sref, "S_obs_m_s2": sobs,
            "delta_S_m_s2": sobs - sref,
            "rmse_event_m_s2": error,
            "pred_ref": int(sref >= 0.20), "pred_obs": int(sobs >= 0.20),
        }
        computed["error_ref"] = int(computed["pred_ref"] != y)
        computed["error_obs"] = int(computed["pred_obs"] != y)
        for key, value in computed.items():
            tolerance = 1e-12 if isinstance(value, float) else 0
            assert abs(float(row[key]) - value) <= tolerance, (alpha, name, key)
        if alpha == 1:
            for actual, expected in zip((sref, sobs, error), EXPECTED[name]):
                assert abs(actual - expected) <= 1e-9
        print(f"alpha={alpha:g} {name}: S_ref={sref:.15f}, S_obs={sobs:.15f}, "
              f"delta={sobs-sref:+.15f}, E_event={error:.15f} "
              f"mask_sum={int(mask[j].sum())} pred={computed['pred_ref']}->{computed['pred_obs']} "
              f"error={computed['error_ref']}->{computed['error_obs']}")


if __name__ == "__main__":
    for d in [ROOT / "results", ROOT / "results/controls/alpha_0",
              ROOT / "results/controls/alpha_0_5"]:
        verify(d)
    print("INDEPENDENT CHECK: PASS (scalar fsum vs saved CSV/NPZ, three alpha values)")
