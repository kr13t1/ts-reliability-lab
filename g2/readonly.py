"""WISDM G2.2: source-preserving selection and plotting of one observed run.

Only G2_REAL_SIGNAL_SPEC sections 2–6,8 are implemented. No corruption,
resampling, inference, model, or assumed physical timestamp conversion.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

CONTRACT = "LAB-020 G2_REAL_SIGNAL_SPEC §§2–6,8"
APPROVED_SPEC_COMMIT_SHA = "ae612e338df6a25eb94281cc2b3969cd39824d44"
PINNED_PRECHECK_SHA256 = "f534d093b003327019dec214c1c332e95c1d413ad25efd7943df4082422e8a57"
EXPECTED = {
    "mode": "reference_only",
    "approved_spec_commit_sha": APPROVED_SPEC_COMMIT_SHA,
    "source_member": "wisdm-dataset/raw/phone/accel/data_1600_accel_phone.txt",
    "subject": 1600,
    "activity": "A",
    "expected_file_sha256": "40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f",
    "expected_file_size": 3451789,
    "expected_file_lines": 64311,
    "expected_start_line": 1,
    "expected_end_line": 3574,
    "expected_n": 3574,
    "expected_q_first": "252207666810782",
    "expected_q_last": "252387581668153",
    "expected_next_activity": "B",
    "expected_delta_count": 3573,
    "expected_delta_min": "50331507",
    "expected_delta_median": "50354004",
    "expected_delta_max": "50378589",
    "timestamp_unit": "UNKNOWN",
    "session_id": None,
    "seed": None,
    "full_remote_attestation": "UNVERIFIED",
    "physical_continuity": "UNKNOWN",
}
REQUIRED = set(EXPECTED) | {"contract", "precheck_path"}
INT = re.compile(r"[+-]?[0-9]+\Z")


class Refusal(ValueError):
    """The code refuses to silently repair, substitute, or reinterpret input."""

    def __init__(self, status: str, detail: str):
        super().__init__(detail)
        self.status = status


@dataclass(frozen=True)
class Row:
    line: int
    subject: int
    activity: str
    q: int
    axes_tokens: tuple[str, str, str]
    axes: tuple[float, float, float]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_row(raw: bytes, line: int) -> Row:
    try:
        s = raw.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise Refusal("REJECTED_INPUT", f"line {line}: non-UTF-8 input") from exc
    if not s or not s.endswith(";") or s.count(";") != 1:
        raise Refusal("REJECTED_INPUT", f"line {line}: expected one trailing semicolon")
    fields = [f.strip() for f in s[:-1].split(",")]
    if len(fields) != 6 or any(not f for f in fields):
        raise Refusal("REJECTED_INPUT", f"line {line}: expected six nonempty fields")
    if not INT.fullmatch(fields[0]) or not INT.fullmatch(fields[2]):
        raise Refusal("REJECTED_INPUT", f"line {line}: subject and timestamp must be integers")
    if len(fields[1]) != 1 or not fields[1].isalpha():
        raise Refusal("REJECTED_INPUT", f"line {line}: invalid activity code")
    try:
        axis = tuple(float(x) for x in fields[3:6])
    except ValueError as exc:
        raise Refusal("REJECTED_INPUT", f"line {line}: invalid numeric axis") from exc
    if any(not math.isfinite(x) for x in axis):
        raise Refusal("REJECTED_INPUT", f"line {line}: non-finite axis")
    return Row(line, int(fields[0]), fields[1], int(fields[2]),
               tuple(fields[3:6]), axis)  # type: ignore[arg-type]


def parse_file(raw: bytes) -> list[Row]:
    lines = raw.splitlines()
    if not lines:
        raise Refusal("REJECTED_INPUT", "empty raw input")
    return [parse_row(line, i) for i, line in enumerate(lines, 1)]


def contiguous_runs(rows: Sequence[Row]) -> list[tuple[int, int, int, str]]:
    if not rows:
        return []
    result: list[tuple[int, int, int, str]] = []
    start = 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or (rows[i].subject, rows[i].activity) != (rows[start].subject, rows[start].activity):
            result.append((rows[start].line, rows[i - 1].line,
                           rows[start].subject, rows[start].activity))
            start = i
    return result


def validate_precheck_shape(precheck: Any) -> None:
    """Reject malformed metadata with a controlled error before source selection.

    The full pinned SHA is checked separately. This shape validation is solely
    to distinguish invalid reports from valid-but-unauthorized report changes.
    """
    if not isinstance(precheck, dict) or not isinstance(precheck.get("subjects"), dict):
        raise Refusal("REJECTED_INPUT", "precheck must contain a subjects object")
    for sid, info in precheck["subjects"].items():
        if not isinstance(sid, str) or not sid.isdecimal() or not isinstance(info, dict):
            raise Refusal("REJECTED_INPUT", "precheck has invalid subject entry")
        runs = info.get("all_contiguous_runs_in_original_order")
        if not isinstance(runs, list):
            raise Refusal("REJECTED_INPUT", f"subject {sid}: runs must be a list")
        for run in runs:
            if not isinstance(run, dict):
                raise Refusal("REJECTED_INPUT", f"subject {sid}: run must be an object")
            if not isinstance(run.get("activity"), str) or len(run["activity"]) != 1:
                raise Refusal("REJECTED_INPUT", f"subject {sid}: invalid run activity")
            start, end = run.get("start_line_1_based"), run.get("end_line_1_based")
            if type(start) is not int or type(end) is not int or start < 1 or end < start:
                raise Refusal("REJECTED_INPUT", f"subject {sid}: invalid run line boundaries")


def select_from_precheck(precheck: dict[str, Any]) -> tuple[int, str, int, int]:
    validate_precheck_shape(precheck)
    options = []
    for sid, info in precheck["subjects"].items():
        for run in info["all_contiguous_runs_in_original_order"]:
            if run["activity"] in ("A", "E"):
                options.append((int(sid), 0 if run["activity"] == "A" else 1,
                                int(run["start_line_1_based"]), int(run["end_line_1_based"])))
    if not options:
        raise Refusal("REPORT_MISMATCH", "precheck contains no A/E runs")
    selected = min(options)
    return selected[0], "A" if selected[1] == 0 else "E", selected[2], selected[3]


def load_config(path: Path) -> dict[str, Any]:
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refusal("REJECTED_CONFIG", f"invalid config: {exc}") from exc
    if not isinstance(o, dict) or set(o) != REQUIRED:
        raise Refusal("REJECTED_CONFIG", "config key set differs from frozen LAB-020 contract")
    if o["contract"] != "G2_REAL_SIGNAL_SPEC §§2–6,8; LAB-020":
        raise Refusal("REJECTED_CONFIG", "wrong contract")
    if o["precheck_path"] != "data/provenance/G2_MULTI_SUBJECT_PRECHECK.json":
        raise Refusal("REJECTED_CONFIG", "changed pinned precheck path")
    if any(type(o[key]) is not type(v) or o[key] != v for key, v in EXPECTED.items()):
        raise Refusal("REJECTED_CONFIG", "contract constants changed; requires 00 approval")
    return o


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_source(raw: bytes, config: dict[str, Any], precheck: dict[str, Any]) -> tuple[list[Row], dict[str, Any]]:
    digest = sha256(raw)
    if digest != config["expected_file_sha256"]:
        raise Refusal("BLOCKED_IDENTITY", f"SHA-256 mismatch: {digest}")
    if len(raw) != config["expected_file_size"]:
        raise Refusal("REPORT_MISMATCH", "raw byte size differs from pinned report")
    selected = select_from_precheck(precheck)
    expected = (config["subject"], config["activity"],
                config["expected_start_line"], config["expected_end_line"])
    if selected != expected:
        raise Refusal("REPORT_MISMATCH", f"precheck selection {selected} != {expected}")
    subject_report = precheck["subjects"].get(str(config["subject"]))
    if not isinstance(subject_report, dict) or any(k not in subject_report for k in ("file_sha256", "size_bytes", "line_count")):
        raise Refusal("REJECTED_INPUT", "selected subject is missing required identity metadata")
    if subject_report["file_sha256"] != digest or subject_report["size_bytes"] != len(raw):
        raise Refusal("REPORT_MISMATCH", "precheck file identity differs")
    rows = parse_file(raw)
    if len(rows) != config["expected_file_lines"] or subject_report["line_count"] != len(rows):
        raise Refusal("REPORT_MISMATCH", "file line count mismatch")
    if any(r.subject != config["subject"] for r in rows):
        raise Refusal("REJECTED_INPUT", "foreign subject ID in source file")
    runs = contiguous_runs(rows)
    if (expected[2], expected[3], expected[0], expected[1]) not in runs:
        raise Refusal("REPORT_MISMATCH", "selected activity is not an entire contiguous run")
    subset = rows[expected[2] - 1:expected[3]]
    q = [r.q for r in subset]
    deltas = [b - a for a, b in zip(q[:-1], q[1:])]
    if any(x <= 0 for x in deltas):
        raise Refusal("REJECTED_INPUT", "selected run has non-increasing timestamps")
    sd = sorted(deltas)
    if len(sd) % 2 == 0:
        raise Refusal("REPORT_MISMATCH", "median rank expected odd count")
    next_code = rows[expected[3]].activity if expected[3] < len(rows) else None
    stats = {
        "file_sha256": digest,
        "file_size_bytes": len(raw),
        "file_lines": len(rows),
        "member": config["source_member"],
        "subject": config["subject"], "activity": config["activity"],
        "start_line": expected[2], "end_line": expected[3], "n": len(subset),
        "next_activity": next_code,
        "q_first": str(q[0]), "q_last": str(q[-1]),
        "delta_count": len(deltas),
        "delta_min": str(sd[0]), "delta_median": str(sd[len(sd)//2]),
        "delta_max": str(sd[-1]), "delta_sum": str(sum(deltas)),
        "timestamp_unit": "UNKNOWN", "physical_continuity": "UNKNOWN",
        "session_id": None,
    }
    pins = {
        "expected_n": "n", "expected_q_first": "q_first", "expected_q_last": "q_last",
        "expected_next_activity": "next_activity", "expected_delta_count": "delta_count",
        "expected_delta_min": "delta_min", "expected_delta_median": "delta_median",
        "expected_delta_max": "delta_max",
    }
    if any(stats[target] != config[pin] for pin, target in pins.items()):
        raise Refusal("REPORT_MISMATCH", "selected run disagrees with frozen precheck")
    if stats["delta_sum"] != str(q[-1] - q[0]):
        raise Refusal("REPORT_MISMATCH", "exact integer delta telescoping failed")
    return subset, stats


def json_write(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_reference(path: Path, rows: Sequence[Row]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(("i", "source_line", "subject", "activity", "q", "x", "y", "z"))
        for i, r in enumerate(rows):
            writer.writerow((i, r.line, r.subject, r.activity, str(r.q), *r.axes_tokens))


def write_plot(path: Path, rows: Sequence[Row]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x_idx = list(range(len(rows)))
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    for col, ax in enumerate(axes):
        ax.plot(x_idx, [r.axes[col] for r in rows], linewidth=0.65)
        ax.set_ylabel(f"{('x', 'y', 'z')[col]} (м/с²*)")
        ax.grid(alpha=0.22)
    axes[0].set_title("WISDM 2019 | subject 1600 | Walking (A) | строки 1–3574\n"
                      "Наблюдаемые измерения, не подтверждённый эталон без ошибок")
    axes[-1].set_xlabel("Индекс отсчёта i (НЕ секунды; timestamp unit = UNKNOWN)")
    fig.text(0.01, 0.005, "* Амплитуда в м/с² по документации WISDM; калибровка не проверена", fontsize=8)
    fig.tight_layout(rect=(0, .015, 1, 1))
    fig.savefig(path, dpi=140)
    plt.close(fig)


def git_state() -> dict[str, Any]:
    try:
        root = Path(__file__).resolve().parents[1]
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=2, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=2, check=True).stdout.strip())
        return {"git_sha": sha, "git_dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"git_sha": None, "git_dirty": None}


def execute(raw_path: Path, out: Path, config_path: Path, precheck_path: Path,
            invocation: Sequence[str] | None = None) -> dict[str, Any]:
    if out.exists() and any(out.iterdir()):
        raise Refusal("OUTPUT_NOT_EMPTY", "choose a fresh, empty output directory")
    out.mkdir(parents=True, exist_ok=True)
    try:
        config = load_config(config_path)
        json_write(out / "config.json", config)
        if not raw_path.is_file():
            raise Refusal("BLOCKED_INPUT", "expected local raw TXT is unavailable")
        if not precheck_path.is_file():
            raise Refusal("BLOCKED_INPUT", "pinned precheck JSON unavailable")
        raw = raw_path.read_bytes()
        try:
            precheck_bytes = precheck_path.read_bytes()
            precheck = json.loads(precheck_bytes.decode("utf-8"))
        except (ValueError, OSError, UnicodeDecodeError) as exc:
            raise Refusal("REJECTED_INPUT", "invalid precheck JSON") from exc
        validate_precheck_shape(precheck)
        if sha256(precheck_bytes) != PINNED_PRECHECK_SHA256:
            raise Refusal("BLOCKED_IDENTITY", "precheck SHA-256 differs from frozen LAB-020 report")
        rows, selection = validate_source(raw, config, precheck)
        json_write(out / "selection.json", selection)
        write_reference(out / "reference.csv", rows)
        write_plot(out / "reference.png", rows)
        checks = {"raw_sha256": "PASS", "raw_size_and_lines": "PASS", "subject_activity_run": "PASS",
                  "q_strict_integer_order": "PASS", "all_pinned_statistics": "PASS",
                  "signal_unchanged": "PASS", "physical_timestamp_unit": "UNKNOWN",
                  "remote_UCI_attestation": "UNVERIFIED"}
        json_write(out / "validation.json", {"status": "PASS_READ_ONLY", "checks": checks})
        files = ("config.json", "selection.json", "reference.csv", "reference.png", "validation.json")
        version = {"python": sys.version.split()[0]}
        try:
            import numpy, matplotlib
            version |= {"numpy": numpy.__version__, "matplotlib": matplotlib.__version__}
        except ImportError:
            pass
        provenance = {
            "status": "PASS_READ_ONLY", "contract": CONTRACT,
            "input_member": config["source_member"], "local_input_name": raw_path.name,
            "input_sha256": sha256(raw), "precheck_sha256": sha_file(precheck_path),
            "precheck_pinned_sha256": PINNED_PRECHECK_SHA256,
            "approved_spec_commit_sha": config["approved_spec_commit_sha"],
            "command_argv": list(invocation) if invocation is not None else None,
            "command_display": shlex.join(invocation) if invocation is not None else None,
            "command_origin": "CLI" if invocation is not None else "PYTHON_API",
            "attribution": {
                "dataset": "WISDM Smartphone and Smartwatch Activity and Biometrics Dataset (2019)",
                "repository": "UCI Machine Learning Repository",
                "doi": "10.24432/C5HK59",
                "url": "https://archive.ics.uci.edu/dataset/507/wisdm%2Bsmartphone%2B",
                "license": "CC BY 4.0 (as listed by UCI)",
            },
            "source_implementation_sha256": sha_file(Path(__file__)),
            "files_sha256": {name: sha_file(out / name) for name in files},
            "versions": version, "timestamp_unit": "UNKNOWN", "session_id": None,
            "physical_continuity": "UNKNOWN", "full_remote_attestation": "UNVERIFIED",
            "no_injection_or_ml": True,
            **git_state(),
        }
        json_write(out / "provenance.json", provenance)
        return {"status": "PASS_READ_ONLY", "selection": selection, "output": str(out)}
    except Refusal as exc:
        json_write(out / "validation.json", {"status": exc.status, "detail": str(exc),
                                              "signal_extracted": False, "reference_plot_created": False})
        return {"status": exc.status, "detail": str(exc), "output": str(out)}


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LAB-020: read-only WISDM G2.2 illustration")
    p.add_argument("--input", type=Path, required=True, help="original extracted data_1600_accel_phone.txt")
    p.add_argument("--output-dir", type=Path, required=True, help="new or empty output directory")
    p.add_argument("--config", type=Path, default=Path("g2/configs/g2_readonly.json"))
    p.add_argument("--precheck", type=Path, default=Path("data/provenance/G2_MULTI_SUBJECT_PRECHECK.json"))
    invoked_args = list(sys.argv[1:] if argv is None else argv)
    args = p.parse_args(invoked_args)
    try:
        command_argv = [sys.executable, "-m", "g2.readonly", *invoked_args]
        result = execute(args.input, args.output_dir, args.config, args.precheck,
                         invocation=command_argv)
    except Refusal as exc:
        result = {"status": exc.status, "detail": str(exc)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS_READ_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
