"""G2.2 unit tests: synthetic FIXTURES only; no claim of real WISDM testing."""
import csv
import hashlib
import json
from pathlib import Path

import pytest

from g2.readonly import (
    EXPECTED, Refusal, contiguous_runs, execute, load_config,
    parse_file, parse_row, select_from_precheck, sha256, validate_precheck_shape, validate_source,
    write_reference,
)


def raw(*rows: str) -> bytes:
    return ("\n".join(rows) + "\n").encode("utf-8")


def row(activity: str, q: int, subject: int = 1600) -> str:
    return f"{subject},{activity},{q},1.000,-2.500,3.250;"


def test_integer_q_not_float():
    q = 9007199254740993  # > 2**53 (would round if converted through float)
    p = parse_row(row("A", q).encode(), 1)
    assert p.q == q and isinstance(p.q, int)
    assert p.axes_tokens == ("1.000", "-2.500", "3.250")


def test_lf_crlf_parsing_same_rows():
    src = raw(row("A", 10), row("B", 20))
    assert parse_file(src) == parse_file(src.replace(b"\n", b"\r\n"))


def test_trailing_line_ending_not_record():
    assert len(parse_file(raw(row("A", 1)))) == 1


@pytest.mark.parametrize("problem", [
    b"", b"1600,A,5,1,2,3", b"1600,A,5,1,2,3;;", b"1600,A,5,1,2;",
    b"1600,A,5,1,2,3,4;", b"1600,A,5,1,,3;",
    b"1600,A,1.5,1,2,3;", b"x,A,5,1,2,3;",
    b"1600,A,5,nan,2,3;", b"1600,A,5,inf,2,3;",
    b"1600,A,5,no,2,3;", b"1600,A,5,1,2,3;\n\n",
    b"\x00\xff", b"1600,AA,5,1,2,3;",
])
def test_bad_input_rejected(problem):
    with pytest.raises(Refusal) as exc:
        parse_file(problem)
    assert exc.value.status == "REJECTED_INPUT"


def test_A_B_A_are_two_A_runs():
    r = parse_file(raw(row("A", 1), row("B", 2), row("A", 3)))
    assert contiguous_runs(r) == [(1, 1, 1600, "A"), (2, 2, 1600, "B"), (3, 3, 1600, "A")]


def test_changes_in_subject_are_boundaries_even_with_same_activity():
    r = parse_file(raw(row("A", 1, 1600), row("A", 2, 1601)))
    assert contiguous_runs(r) == [(1, 1, 1600, "A"), (2, 2, 1601, "A")]


def test_selection_uses_numeric_subject_then_A_then_line():
    p = {"subjects": {
        "1602": {"all_contiguous_runs_in_original_order": [
            {"activity": "A", "start_line_1_based": 5, "end_line_1_based": 7}]},
        "1600": {"all_contiguous_runs_in_original_order": [
            {"activity": "E", "start_line_1_based": 1, "end_line_1_based": 5},
            {"activity": "A", "start_line_1_based": 6, "end_line_1_based": 8}]},
        "1601": {"all_contiguous_runs_in_original_order": [
            {"activity": "A", "start_line_1_based": 1, "end_line_1_based": 3}]},
    }}
    assert select_from_precheck(p) == (1600, "A", 6, 8)


def test_nonmatching_activity_precheck_fails():
    with pytest.raises(Refusal, match="no A/E runs"):
        select_from_precheck({"subjects": {"1600": {"all_contiguous_runs_in_original_order": [
            {"activity": "B", "start_line_1_based": 1, "end_line_1_based": 3}]}}})


def test_reference_csv_preserves_q_and_original_axis_tokens(tmp_path):
    q = 12345678901234567890123
    p = tmp_path / "ref.csv"
    write_reference(p, parse_file(raw(row("A", q))))
    with p.open(encoding="utf-8", newline="") as f:
        values = list(csv.DictReader(f))
    assert values == [{"i": "0", "source_line": "1", "subject": "1600", "activity": "A",
                       "q": str(q), "x": "1.000", "y": "-2.500", "z": "3.250"}]


def test_sha256_matches_hashlib():
    data = raw(row("A", 4))
    assert sha256(data) == hashlib.sha256(data).hexdigest()


def test_validate_fails_no_fallback_on_wrong_hash():
    cfg = dict(EXPECTED)
    with pytest.raises(Refusal) as exc:
        validate_source(raw(row("A", 1)), cfg, {})
    assert exc.value.status == "BLOCKED_IDENTITY"


def test_config_frozen(tmp_path):
    path = tmp_path / "config.json"
    cfg = {"contract": "G2_REAL_SIGNAL_SPEC §§2–6,8; LAB-020",
           "precheck_path": "data/provenance/G2_MULTI_SUBJECT_PRECHECK.json", **EXPECTED}
    path.write_text(json.dumps(cfg))
    assert load_config(path) == cfg
    cfg["expected_n"] = 4
    path.write_text(json.dumps(cfg))
    with pytest.raises(Refusal, match="constants changed"):
        load_config(path)


def test_execute_missing_raw_yields_blocked_input_without_plot(tmp_path):
    cfg = {"contract": "G2_REAL_SIGNAL_SPEC §§2–6,8; LAB-020",
           "precheck_path": "data/provenance/G2_MULTI_SUBJECT_PRECHECK.json", **EXPECTED}
    conf = tmp_path / "config_in.json"
    conf.write_text(json.dumps(cfg))
    precheck = tmp_path / "precheck.json"
    precheck.write_text('{"subjects": {}}')
    out = tmp_path / "results"
    result = execute(tmp_path / "missing.txt", out, conf, precheck)
    assert result["status"] == "BLOCKED_INPUT"
    assert not (out / "reference.png").exists()
    assert not (out / "reference.csv").exists()
    assert (out / "config.json").is_file()
    assert json.loads((out / "validation.json").read_text())["status"] == "BLOCKED_INPUT"


def test_execute_hash_failure_yields_no_fabricated_outputs(tmp_path):
    cfg = {"contract": "G2_REAL_SIGNAL_SPEC §§2–6,8; LAB-020",
           "precheck_path": "data/provenance/G2_MULTI_SUBJECT_PRECHECK.json", **EXPECTED}
    conf = tmp_path / "config_in.json"
    conf.write_text(json.dumps(cfg))
    input_file = tmp_path / "data.txt"
    input_file.write_bytes(raw(row("A", 1)))
    precheck = tmp_path / "precheck.json"
    precheck.write_text('{"subjects": {}}')
    out = tmp_path / "results"
    result = execute(input_file, out, conf, precheck)
    assert result["status"] == "BLOCKED_IDENTITY"
    assert not (out / "reference.png").exists()
    assert not (out / "reference.csv").exists()


def test_output_directory_must_be_empty(tmp_path):
    out = tmp_path / "results"
    out.mkdir()
    (out / "stale-reference.png").write_bytes(b"fake")
    with pytest.raises(Refusal) as exc:
        execute(tmp_path / "missing.txt", out, tmp_path / "config.json", tmp_path / "p.json")
    assert exc.value.status == "OUTPUT_NOT_EMPTY"


def test_q_delta_is_exact_for_very_large_integer():
    q = 10**30
    r = parse_file(raw(row("A", q), row("A", q + 99)))
    assert r[1].q - r[0].q == 99


def test_immutable_row_objects():
    r = parse_row(row("A", 1).encode(), 1)
    with pytest.raises(Exception):
        r.q = 100


@pytest.mark.parametrize("bad_report", [
    {}, {"subjects": None}, {"subjects": []},
    {"subjects": {"1600": {}}},
    {"subjects": {"1600": {"all_contiguous_runs_in_original_order": None}}},
    {"subjects": {"1600": {"all_contiguous_runs_in_original_order": [{}]}}},
    {"subjects": {"1600": {"all_contiguous_runs_in_original_order": [
        {"activity": "A", "start_line_1_based": 2, "end_line_1_based": 1}]}}},
])
def test_invalid_precheck_structure_returns_rejected_input(bad_report, tmp_path):
    cfg = {"contract": "G2_REAL_SIGNAL_SPEC §§2–6,8; LAB-020",
           "precheck_path": "data/provenance/G2_MULTI_SUBJECT_PRECHECK.json", **EXPECTED}
    conf = tmp_path / "config_in.json"
    conf.write_text(json.dumps(cfg))
    input_file = tmp_path / "data.txt"
    input_file.write_bytes(raw(row("A", 1)))
    precheck_path = tmp_path / "precheck.json"
    precheck_path.write_text(json.dumps(bad_report))
    out = tmp_path / "results"
    result = execute(input_file, out, conf, precheck_path)
    assert result["status"] == "REJECTED_INPUT"
    assert json.loads((out / "validation.json").read_text())["status"] == "REJECTED_INPUT"
    assert not (out / "reference.png").exists()
    assert not (out / "reference.csv").exists()


def test_well_formed_but_unpinned_precheck_is_blocked(tmp_path):
    cfg = {"contract": "G2_REAL_SIGNAL_SPEC §§2–6,8; LAB-020",
           "precheck_path": "data/provenance/G2_MULTI_SUBJECT_PRECHECK.json", **EXPECTED}
    conf = tmp_path / "config_in.json"
    conf.write_text(json.dumps(cfg))
    precheck_path = tmp_path / "precheck.json"
    precheck_path.write_text(json.dumps({"subjects": {"1600": {
        "all_contiguous_runs_in_original_order": [
            {"activity": "A", "start_line_1_based": 1, "end_line_1_based": 1}
        ]
    }}}))
    raw_path = tmp_path / "raw.txt"
    raw_path.write_bytes(raw(row("A", 1)))
    out = tmp_path / "results"
    r = execute(raw_path, out, conf, precheck_path)
    assert r["status"] == "BLOCKED_IDENTITY"
    assert json.loads((out / "validation.json").read_text())["status"] == "BLOCKED_IDENTITY"
    assert not (out / "reference.csv").exists()


def test_pinned_provenance_fields_after_real_execution(tmp_path):
    from g2.readonly import APPROVED_SPEC_COMMIT_SHA, PINNED_PRECHECK_SHA256
    project_root = Path(__file__).resolve().parents[2]
    raw_path = project_root / "data/raw/data_1600_accel_phone.txt"
    precheck = project_root / "data/provenance/G2_MULTI_SUBJECT_PRECHECK.json"
    if not raw_path.is_file():
        pytest.skip("real raw file is not distributed with Git")
    out = tmp_path / "results"
    invocation = ["python", "-m", "g2.readonly", "--input", "data/raw/data_1600_accel_phone.txt"]
    result = execute(raw_path, out, project_root / "g2/configs/g2_readonly.json",
                     precheck, invocation=invocation)
    assert result["status"] == "PASS_READ_ONLY"
    config = json.loads((out / "config.json").read_text())
    provenance = json.loads((out / "provenance.json").read_text())
    assert config["approved_spec_commit_sha"] == APPROVED_SPEC_COMMIT_SHA
    assert provenance["approved_spec_commit_sha"] == APPROVED_SPEC_COMMIT_SHA
    assert provenance["command_argv"] == invocation
    assert provenance["attribution"]["doi"] == "10.24432/C5HK59"
    assert "CC BY 4.0" in provenance["attribution"]["license"]
    assert provenance["precheck_sha256"] == PINNED_PRECHECK_SHA256
