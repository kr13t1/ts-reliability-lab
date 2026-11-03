"""Single offline CLI for the approved G1 synthetic demonstration."""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess

import matplotlib
import numpy as np

from .config import read_config, validate_config, write_config
from .signals import generate_reference
from .corruption import corrupt_both
from .metrics import CSV_FIELDS, record_metrics
from .visualization import plot_signals, plot_mask


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git_commit(project_root: Path) -> str | None:
    if not (project_root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=3, check=True,
        )
        return result.stdout.strip() or None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def execute(config: dict, output_dir: Path, *, project_root: Path = PROJECT_ROOT) -> list[dict]:
    """Produce all obligatory G1 artifacts; return exactly two per-record rows."""
    config = validate_config(config)
    expected_numpy = config["generator"]["expected_numpy_version"]
    if np.__version__ != expected_numpy:
        raise RuntimeError(f"NumPy {np.__version__} != pinned {expected_numpy}; control numbers cannot be certified")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    x_ref, labels, time_s = generate_reference(config)
    x_obs, mask = corrupt_both(x_ref, config)
    rows = [
        record_metrics(record_id, int(labels[i]), x_ref[i], x_obs[i], config)
        for i, record_id in enumerate(config["experiment"]["record_ids"])
    ]

    np.savez(output_dir / "g1_arrays.npz", x_ref=x_ref, x_obs=x_obs, mask=mask,
             labels=labels, time_s=time_s)
    with (output_dir / "results.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        # repr(float) in Python 3 uses enough precision to round-trip binary64,
        # exceeding the required 12 significant decimal digits.
        writer.writerows(rows)

    plot_signals(x_ref, x_obs, time_s, config, output_dir / "signal_comparison.png")
    plot_mask(mask, config, output_dir / "mask.png")
    write_config(config, output_dir / "config.json")

    spec_path = project_root / "contract" / "G1_SPEC.md"
    output_names = ["g1_arrays.npz", "results.csv", "signal_comparison.png",
                    "mask.png", "config.json"]
    metadata = {
        "experiment_id": "G1",
        "experiment_scope": "синтетическая демонстрация, без оценки научного качества",
        "specification": "G1_SPEC.md v1.0, approved for implementation by coordinator 00",
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "matplotlib_version": matplotlib.__version__,
        "git_commit_sha": _git_commit(project_root),
        "spec_sha256": _digest(spec_path) if spec_path.is_file() else None,
        "inputs": "fully synthetic; no external data files; one PRNG draw; corruption deterministic",
        "record_order": ["rest", "walk"],
        "mask_semantics": "assigned injection locations at alpha>0, not detection",
        "source_artifact_sha256": {name: _digest(output_dir / name) for name in output_names},
        "limitations": [
            "two invented records, not a statistical population",
            "RMS heuristic classifies activity, not sensor faults",
            "no training, detection, restoration, or independent test dataset",
            "no scientific novelty or real-world performance claims",
        ],
    }
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline G1 fixed-contract demonstration")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs" / "g1.json")
    parser.add_argument("--alpha", type=float, default=None,
                        help="Approved injection strength in [0,1], default 1.0")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "results")
    args = parser.parse_args(argv)
    config = read_config(args.config)
    if args.alpha is not None:
        config["corruption"]["alpha"] = args.alpha
    parser.error("invalid alpha; must be in [0,1]") if not (
        isinstance(config["corruption"]["alpha"], (int, float))
        and 0 <= config["corruption"]["alpha"] <= 1
    ) else None
    rows = execute(config, args.output_dir)
    print(f"G1 synthetic demonstration | alpha={config['corruption']['alpha']:g}")
    print("record | S_ref     | S_obs     | ΔS        | E_event   | pred ref->obs | err ref->obs")
    for row in rows:
        print(f"{row['record_id']:6} | {row['S_ref_m_s2']:.9f} | {row['S_obs_m_s2']:.9f} | "
              f"{row['delta_S_m_s2']:+.9f} | {row['rmse_event_m_s2']:.9f} | "
              f"{row['pred_ref']}->{row['pred_obs']}           | "
              f"{row['error_ref']}->{row['error_obs']}")
    print(f"Artifacts: {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
