import csv
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
import pytest
from reliability_lab.config import default_config
from reliability_lab.run import execute
from reliability_lab.metrics import CSV_FIELDS, record_metrics


@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0])
def test_real_artifacts_and_provenance(tmp_path, alpha):
    c = default_config()
    c["corruption"]["alpha"] = alpha
    target = tmp_path / f"alpha_{alpha}"
    rows = execute(c, target)
    expected_files = ["g1_arrays.npz", "results.csv", "signal_comparison.png",
                      "mask.png", "config.json", "metadata.json"]
    assert all((target / name).is_file() and (target / name).stat().st_size > 0 for name in expected_files)
    arrays = np.load(target / "g1_arrays.npz", allow_pickle=False)
    assert set(arrays.files) == {"x_ref", "x_obs", "mask", "labels", "time_s"}
    assert arrays["x_ref"].shape == arrays["x_obs"].shape == arrays["mask"].shape == (2, 3, 200)
    assert arrays["x_ref"].dtype == arrays["x_obs"].dtype == np.float64
    assert arrays["mask"].dtype == np.uint8
    assert arrays["labels"].tolist() == [0, 1]
    assert np.isfinite(arrays["x_ref"]).all()
    with (target / "results.csv").open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == CSV_FIELDS
        csv_rows = list(reader)
    assert [row["record_id"] for row in csv_rows] == ["rest", "walk"]
    for i, name in enumerate(["rest", "walk"]):
        recomputed = record_metrics(name, int(arrays["labels"][i]), arrays["x_ref"][i],
                                    arrays["x_obs"][i], c)
        for field in CSV_FIELDS:
            if field == "record_id":
                assert csv_rows[i][field] == name
            else:
                assert float(csv_rows[i][field]) == float(recomputed[field])
    for img in ["signal_comparison.png", "mask.png"]:
        assert (target / img).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    metadata = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["numpy_version"] == "2.3.5"
    assert metadata["spec_sha256"] is not None
    assert metadata["git_commit_sha"] is None or len(metadata["git_commit_sha"]) == 40
    for name, digest in metadata["source_artifact_sha256"].items():
        assert sha256((target / name).read_bytes()).hexdigest() == digest
    assert json.loads((target / "config.json").read_text(encoding="utf-8")) == c
    assert all(row["alpha"] == alpha for row in rows)
    if alpha == 0:
        assert not arrays["mask"].any()
        assert np.array_equal(arrays["x_ref"], arrays["x_obs"])
    else:
        assert arrays["mask"].sum() == 120


def test_identical_two_runs_array_equal_and_identical_numeric_outputs(tmp_path):
    c = default_config()
    first = execute(c, tmp_path / "a")
    second = execute(c, tmp_path / "b")
    assert first == second
    with np.load(tmp_path / "a" / "g1_arrays.npz") as a, np.load(tmp_path / "b" / "g1_arrays.npz") as b:
        for key in a.files:
            assert np.array_equal(a[key], b[key])
    assert (tmp_path / "a" / "results.csv").read_bytes() == (tmp_path / "b" / "results.csv").read_bytes()
