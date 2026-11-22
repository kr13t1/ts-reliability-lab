"""Issue #25: offline, read-only presentation of frozen G2.3/G2.4 outputs.

This module never reads WISDM raw, imports G2.4 detector, or generates predictions.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

CASE_IDS = ("1600_A_alpha_0", "1600_A_alpha_1", "1600_E_raw")
CASE_LABELS = ("Walking · α=0", "Walking · freeze α=1", "Standing · без инъекции")
G23_PINS = {
    "reference.csv": "8bf61ee71f68e0648ead7bc8eb8b6c44414e28411bd6de65e5f9dadf9c28eb38",
    "alpha_0/arrays.csv": "6cf2fd4d19da30d00be7a4878a979c2d3828554715377c3bda5aaf384801f7d5",
    "alpha_1/arrays.csv": "df34cf7dc715bf9e928560d26b6fb01f8299349a80e64a84c65f3f20807262f6",
}
RAW_SHA = "40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f"
E_SHA = "50edfd731735d54cd76fe4c0a38da914fca7b567ae4e3b3d389f2d687fadb61d"
G23_COLS = ("i", "source_line", "q", "ref_x", "ref_y", "ref_z", "obs_x", "obs_y", "obs_z", "Z_x", "Z_y", "Z_z")
MASK_COLS = ("i", "source_line", "q", "obs_x", "Zhat_x", "Z_x")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 8_000_000

# Trust anchors come from the frozen, independently audited source lineage, not
# from the user-supplied G2.4 provenance.json being checked below.
# Walking CSVs/results: byte-for-byte equal to committed accepted G2.4 Git blobs.
# Standing CSV: reproduced independently from the source raw TXT whose exact
# 1600/E segment SHA-256 is E_SHA; the source uses unchanged q and float64 x.
# PNGs: byte-specific display references from the frozen Linux Python 3.13.5 /
# Matplotlib 3.10.8 rendering. They are AUTHOR CANDIDATE fingerprints to be
# independently ratified by 05, not platform-independent semantic attestations.
# A different platform rendering must REFUSE instead of claiming to be verified.
G24_FIXED_PINS = {
    "results.csv": "abde1e1c95da63c0e7eb829defcc54babd34b7462053026f70ed3682269f83b4",
    "1600_A_alpha_0/masks.csv": "d582599adcb81efab436e5306bd68071741932dc750d222dbbe5bd3cb4d55438",
    "1600_A_alpha_1/masks.csv": "95ef70fe8330973c0dbbe4894b561ae8f9faf8861f40a41770394a2301c5b0a7",
    "1600_E_raw/masks.csv": "4c0bcdd6665c0dcf20697de66bdab128680a78f4059689f20824f8bb5ec10642",
    "1600_A_alpha_0/detection.png": "30925c8884bf1aaf4d3586b35c2d6b3e123ba2b424c7d5b90309d2690b2fb84a",
    "1600_A_alpha_1/detection.png": "633842cc5aeaa7a96926b3185468cf4d211cbe961885412af7e0207a7f0ea93d",
    "1600_E_raw/detection.png": "87d72ca4c9267268bae41973542beca4814a998962a464790bb1f594c4f928b8",
}


class InputError(ValueError):
    """Controlled refusal on unavailable, forged, or incompatible inputs."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise InputError(reason)


def read_bytes(path: Path) -> bytes:
    try:
        require(path.is_file(), f"Missing input: {path}. First run approved g24.demo; see visual_lab/README.md")
        require(path.stat().st_size <= MAX_BYTES, f"Input is unexpectedly large: {path}")
        return path.read_bytes()
    except OSError as exc:
        raise InputError(f"Cannot read input {path}: {exc}") from exc


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def read_json(path: Path) -> dict:
    try:
        obj = json.loads(read_bytes(path))
    except InputError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise InputError(f"Invalid JSON: {path}") from exc
    require(type(obj) is dict, f"Expected JSON object: {path}")
    return obj


def read_csv(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        content = read_bytes(path).decode("utf-8")
        reader = csv.DictReader(content.splitlines())
        require(reader.fieldnames is not None and all(c in reader.fieldnames for c in required),
                f"CSV header/scheme mismatch: {path}")
        require(len(set(reader.fieldnames)) == len(reader.fieldnames), f"Duplicate CSV header: {path}")
        rows = list(reader)
    except (UnicodeError, csv.Error, ValueError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError(f"Invalid CSV: {path}") from exc
    require(all(None not in row and None not in row.values() for row in rows), f"Malformed CSV cells: {path}")
    return rows


def integer(token: str, context: str) -> int:
    require(isinstance(token, str) and re.fullmatch(r"[0-9]+", token) is not None,
            f"Nonnegative integer required: {context}")
    return int(token)


def number(token: str, context: str) -> float:
    try:
        result = float(token)
    except (ValueError, TypeError, OverflowError) as exc:
        raise InputError(f"Numeric value required: {context}") from exc
    require(math.isfinite(result), f"Non-finite value: {context}")
    return result


def check_png(path: Path, sha: str, label: str) -> bytes:
    data = read_bytes(path)
    require(data.startswith(PNG_MAGIC), f"Not a PNG: {label}")
    require(digest(data) == sha, f"PNG checksum mismatch: {label}")
    return data


def segments(bits: list[int]) -> list[list[int]]:
    out: list[list[int]] = []
    start = None
    for i, bit in enumerate(bits + [0]):
        if bit and start is None:
            start = i
        elif not bit and start is not None:
            out.append([start, i]); start = None
    return out


def canonical_g24_files_sha(files: object) -> dict[str, str]:
    """Safely canonicalize Windows/POSIX G2.4 relative metadata keys.

    Metadata hashes still only attest what the untrusted metadata *claims*;
    accepted scientific outputs are also pinned independently below.
    """
    require(type(files) is dict, "G2.4 provenance.files_sha256 must be a JSON object")
    canonical: dict[str, str] = {}
    for raw_key, sha in files.items():
        require(type(raw_key) is str and type(sha) is str and
                re.fullmatch(r"[0-9a-f]{64}", sha) is not None,
                "G2.4 provenance invalid path or SHA-256")
        name = raw_key.replace("\\", "/")
        parts = name.split("/")
        require(all(part not in ("", ".", "..") and
                    re.fullmatch(r"[A-Za-z0-9_.-]+", part) is not None for part in parts),
                f"G2.4 provenance unsafe relative path: {raw_key!r}")
        require(name not in canonical,
                f"G2.4 provenance ambiguous/colliding path: {name}")
        canonical[name] = sha
    return canonical


def verified_inputs(g23: Path, g24: Path, g24_png_mode: str = "strict") -> tuple[dict, dict[str, str]]:
    """Check existing artifacts only. No detector, mutation, or raw file access."""
    require(g24_png_mode in ("strict", "omit"), "Invalid G2.4 PNG presentation mode")
    hashes: dict[str, str] = {}
    def tracked(path: Path, root: Path, prefix: str) -> bytes:
        data = read_bytes(path)
        hashes[f"{prefix}/{path.relative_to(root).as_posix()}"] = digest(data)
        return data
    p23 = read_json(g23 / "provenance.json")
    require(p23.get("status") == "PASS_DEMO" and isinstance(p23.get("files_sha256"), dict),
            "G2.3 has no accepted PASS_DEMO provenance hash map")
    for name in (*G23_PINS, "alpha_0/comparison.png", "alpha_1/comparison.png", "results.csv"):
        data = tracked(g23 / name, g23, "g23")
        expected = G23_PINS.get(name, p23["files_sha256"].get(name))
        require(isinstance(expected, str) and digest(data) == expected, f"G2.3 SHA mismatch: {name}")
        require(p23["files_sha256"].get(name) == expected, f"G2.3 provenance mismatch: {name}")
    require(p23.get("input_sha256") == RAW_SHA and p23.get("reference_sha256") == G23_PINS["reference.csv"],
            "G2.3 raw/reference identity mismatch")
    require(read_json(g23 / "validation.json").get("status") == "PASS_DEMO", "G2.3 validation failed")
    g23_result = read_csv(g23 / "results.csv", ("alpha", "D_I", "n_assigned"))
    require([r["alpha"] for r in g23_result] == ["0", "1"] and
            [integer(r["n_assigned"], "G2.3 n_assigned") for r in g23_result] == [0,1191],
            "G2.3 results must contain the two frozen alpha modes")
    g23_rows = {}
    for alpha in (0, 1):
        rows = read_csv(g23 / f"alpha_{alpha}/arrays.csv", G23_COLS)
        require(len(rows) == 3574, f"G2.3 alpha{alpha} must contain 3574 samples")
        for i, row in enumerate(rows):
            require(integer(row["i"], "G2.3 i") == i and
                    integer(row["source_line"], "G2.3 source_line") == i + 1,
                    f"G2.3 sample index mismatch alpha={alpha}, i={i}")
            require(re.fullmatch(r"[0-9]+", row["q"]) is not None, "G2.3 q must preserve integer text")
            for c in "xyz":
                number(row[f"ref_{c}"], "G2.3 reference")
                number(row[f"obs_{c}"], "G2.3 observation")
            expect_z = int(alpha == 1 and 1191 <= i < 2382)
            require(tuple(row[f"Z_{c}"] for c in "xyz") == (str(expect_z), "0", "0"),
                    f"G2.3 assigned mask mismatch alpha={alpha}, i={i}")
            if alpha == 0:
                require(all(number(row[f"ref_{c}"], "ref") == number(row[f"obs_{c}"], "obs")
                            for c in "xyz"), "Alpha0 must leave observations unchanged")
        g23_rows[alpha] = rows
    require(all(g23_rows[0][i]["q"] == g23_rows[1][i]["q"] and
                g23_rows[0][i]["ref_x"] == g23_rows[1][i]["ref_x"] for i in range(3574)),
            "G2.3 two alpha modes refer to different reference records")
    for a in (0, 1):
        tracked(g23 / f"alpha_{a}/comparison.png", g23, "g23")

    p24 = read_json(g24 / "provenance.json")
    v24 = read_json(g24 / "validation.json")
    require(p24.get("status") == "PASS_DEMO" and v24.get("status") == "PASS_DEMO",
            "G2.4 has no PASS_DEMO outputs; run approved g24.demo first")
    source_map = canonical_g24_files_sha(p24.get("files_sha256"))
    require(p24.get("standing_raw_sha256") == RAW_SHA and p24.get("standing_segment_sha256") == E_SHA,
            "G2.4 Standing/raw SHA identity mismatch")
    require(p24.get("g23_provenance_sha256") == digest(read_bytes(g23 / "provenance.json")),
            "G2.4 was run against different G2.3 provenance")
    g23_files = p24.get("g23_files_sha256")
    require(type(g23_files) is dict and
            g23_files.get("reference.csv") == G23_PINS["reference.csv"],
            "G2.4 G2.3 reference SHA mismatch")
    conf = read_json(g24 / "config.json")
    require(conf.get("axis") == "x" and type(conf.get("min_run_samples")) is int and
            conf["min_run_samples"] == 3 and type(conf.get("epsilon")) is int and
            conf["epsilon"] == 0 and conf.get("seed", "MISSING") is None and
            conf.get("cases") == list(CASE_IDS), "G2.4 config differs from frozen L=3/axis=x")
    require(conf.get("raw_sha256") == RAW_SHA and conf.get("standing_segment_sha256") == E_SHA,
            "G2.4 config source identity differs")
    required_files = ["results.csv", "events.json", "config.json", "validation.json"]
    for cid in CASE_IDS:
        required_files.append(f"{cid}/masks.csv")
        if g24_png_mode == "strict":
            required_files.append(f"{cid}/detection.png")
    images: dict[str, str] = {}
    for rel in required_files:
        data = tracked(g24 / rel, g24, "g24")
        require(isinstance(source_map.get(rel), str) and source_map[rel] == digest(data),
                f"G2.4 provenance/hash mismatch: {rel}")
        if rel.endswith(".png"):
            require(data.startswith(PNG_MAGIC), f"Bad G2.4 PNG: {rel}")
            images[rel] = base64.b64encode(data).decode("ascii")
    for a in (0, 1):
        data = read_bytes(g23 / f"alpha_{a}/comparison.png")
        require(data.startswith(PNG_MAGIC), f"Bad G2.3 PNG alpha{a}")
        images[f"g23_alpha_{a}"] = base64.b64encode(data).decode("ascii")
    tracked(g23 / "provenance.json", g23, "g23")
    tracked(g24 / "provenance.json", g24, "g24")

    results = read_csv(g24 / "results.csv", ("case_id", "subject", "activity", "alpha", "N", "L", "TP", "FP", "FN", "TN", "n_true", "n_pred", "precision", "recall"))
    require([r["case_id"] for r in results] == list(CASE_IDS), "Unexpected G2.4 cases/order")
    events = read_json(g24 / "events.json")
    require(set(events) == set(CASE_IDS), "G2.4 event case mismatch")
    data_by_case = {}
    for j, (case, metrics) in enumerate(zip(CASE_IDS, results)):
        mask_rows = read_csv(g24 / case / "masks.csv", MASK_COLS)
        count = 3572 if j == 2 else 3574
        source_line_start = 14292 if j == 2 else 1
        require(len(mask_rows) == count, f"Incorrect mask length: {case}")
        require(metrics["subject"] == "1600" and metrics["activity"] == ("E" if j == 2 else "A") and
                metrics["alpha"] == ("none" if j == 2 else str(j)) and
                integer(metrics["N"], "N") == count and integer(metrics["L"], "L") == 3,
                f"G2.4 result metadata mismatch: {case}")
        observed, predicted, assigned, q = [], [], [], []
        for i, row in enumerate(mask_rows):
            require(integer(row["i"], "mask index") == i and
                    integer(row["source_line"], "mask source_line") == i + source_line_start,
                    f"Mask/source row identity differs: {case}, i={i}")
            qt = row["q"]
            require(re.fullmatch(r"[0-9]+", qt) is not None, f"q not exact integer text: {case}, i={i}")
            if q:
                require(int(qt) > int(q[-1]), f"q not increasing within the raw activity: {case}")
            q.append(qt)
            value = number(row["obs_x"], "observed x")
            require(row["Zhat_x"] in ("0", "1") and row["Z_x"] in ("0", "1"),
                    f"Nonbinary mask: {case}, i={i}")
            observed.append(value); predicted.append(int(row["Zhat_x"])); assigned.append(int(row["Z_x"]))
            if j < 2:
                old = g23_rows[j][i]
                require(row["q"] == old["q"] and value == number(old["obs_x"], "G2.3 obs") and
                        row["Z_x"] == old["Z_x"], f"Mask differs from frozen G2.3: {case}, i={i}")
            else:
                require(row["Z_x"] == "0", f"Standing must have no project injection: i={i}")
        if j == 2:
            require((q[0], q[-1]) == ("241892286783982", "242072100924919"),
                    "Standing timestamp boundary identity mismatch")
        tp = sum(a and p for a, p in zip(assigned, predicted))
        fp = sum(not a and p for a, p in zip(assigned, predicted))
        fn = sum(a and not p for a, p in zip(assigned, predicted))
        tn = count - tp - fp - fn
        for field, val in {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "n_pred": tp + fp, "n_true": tp + fn}.items():
            require(integer(metrics[field], field) == val, f"G2.4 result/mask mismatch: {case}/{field}")
        expected_precision = tp / (tp + fp) if tp + fp else None
        expected_recall = tp / (tp + fn) if tp + fn else None
        for field, expected in (("precision", expected_precision), ("recall", expected_recall)):
            token = metrics[field]
            require((token == "null") if expected is None else math.isclose(number(token, field), expected, rel_tol=1e-12),
                    f"G2.4 {field} does not match masks: {case}")
        event = events[case]
        require(isinstance(event, dict) and event.get("true_events") == segments(assigned) and
                event.get("pred_events") == segments(predicted), f"G2.4 events/masks differ: {case}")
        # Fixed source-specific sanity gate, not a recomputed detector.
        expected_pred = [[1190, 2382]] if j == 1 else []
        expected_assigned = [[1191, 2382]] if j == 1 else []
        require(event["pred_events"] == expected_pred and event["true_events"] == expected_assigned,
                f"G2.4 fixed case disagrees with independently audited intervals: {case}")
        data_by_case[case] = {"metrics": metrics, "observed": observed, "pred": predicted,
                              "z": assigned, "image": images.get(f"{case}/detection.png")}
    # Only after all structural/semantic checks: compare against fixed source
    # references embedded in the viewer code, never mutable G2.4 provenance.
    for rel, expected in G24_FIXED_PINS.items():
        if rel.endswith(".png") and g24_png_mode == "omit":
            continue  # No trust claim and no image bytes loaded in portable mode.
        require(hashes.get(f"g24/{rel}") == expected,
                f"G2.4 independent fixed-source SHA mismatch: {rel}. "
                "PNG bytes may vary by platform; cannot approve an unverified image")
    return {"cases": data_by_case, "g23_rows": g23_rows, "images": images,
            "g23_report": g23_result,
            "g24_png_mode": g24_png_mode, "p24": p24}, hashes


def _path(values: list[float], left: int, right: int, y_min: float, y_max: float,
          width: int = 860, x0: int = 50, y0: int = 35, height: int = 145) -> str:
    scale = y_max - y_min or 1.0
    return " ".join(f"{'M' if i == left else 'L'}{x0 + width * (i-left+.5)/(right-left):.2f},{y0 + height*(1-(values[i]-y_min)/scale):.2f}"
                    for i in range(left, right))


def signal_svg(reference: list[float], observed: list[float], assigned: list[int],
               predicted: list[int], left: int, right: int, zoom: bool) -> str:
    lo, hi = min(reference[left:right] + observed[left:right]), max(reference[left:right] + observed[left:right])
    pad = (hi - lo) * .08 or .3; lo -= pad; hi += pad
    x0, w = 50, 860
    xpos = lambda idx: x0 + w * (idx-left)/(right-left)
    xi = lambda idx: x0 + w * (idx-left+.5)/(right-left)
    def mask_track(bits: list[int], y: int, color: str) -> str:
        return "".join(f'<rect x="{xpos(max(s,left)):.2f}" y="{y}" width="{xpos(min(e,right))-xpos(max(s,left)):.2f}" height="15" rx="2" fill="{color}"/>'
                       for s, e in segments(bits) if s < right and e > left)
    region_x = xpos(max(left, 1191)); region_w = max(0, xpos(min(right,2382)) - region_x)
    ticks = sorted(set([left, right] + ([1185,1190,1191,1195,1200,1210] if zoom else [0,1190,1191,2382,3574])))
    ticks = [t for t in ticks if left <= t <= right]
    grid = ''.join(f'<line x1="{xpos(t):.2f}" x2="{xpos(t):.2f}" y1="30" y2="270" stroke="#e0e6ee" stroke-width=".9"/><text x="{xpos(t):.2f}" y="297" fill="#596779" font-size="11" text-anchor="middle">{t}</text>' for t in ticks)
    marker = ''
    if left <= 1190 < right:
        marker = f'<rect x="{xpos(1190):.2f}" y="245" width="{xpos(1191)-xpos(1190):.2f}" height="44" fill="#ef4444" opacity=".92"/><line x1="{xi(1190):.2f}" x2="{xi(1190):.2f}" y1="27" y2="238" stroke="#ce3232" stroke-dasharray="4 3"/>'
        if zoom:
            marker += f'<text x="{xi(1190):.2f}" y="20" text-anchor="middle" font-size="12" font-weight="700" fill="#aa2222">i=1190 · FP</text>'
    return f'''<svg viewBox="0 0 930 318" role="img" aria-label="Reference and observed x; assigned and predicted masks, sample indices">
      <rect x="50" y="30" width="860" height="145" rx="8" fill="#fbfcfe" stroke="#e0e6ee"/>
      {grid}<rect x="{region_x:.2f}" y="30" width="{region_w:.2f}" height="145" fill="#45b99c" opacity=".11"/>
      <path d="{_path(reference,left,right,lo,hi)}" fill="none" stroke="#3373b9" stroke-width="{'2.2' if zoom else '1.1'}"/>
      <path d="{_path(observed,left,right,lo,hi)}" fill="none" stroke="#de7940" stroke-width="{'2.2' if zoom else '1.1'}"/>
      <text x="52" y="191" font-size="11" fill="#526478">значения x; индексы отсчётов, НЕ секунды</text>
      <text x="50" y="223" font-size="12" fill="#526478">Назначено Z</text>
      <rect x="50" y="231" width="860" height="15" rx="3" fill="#edf3ef"/>{mask_track(assigned,231,'#41a67d')}
      <text x="50" y="262" font-size="12" fill="#526478">Найдено Zhat</text>
      <rect x="50" y="270" width="860" height="15" rx="3" fill="#f1edf8"/>{mask_track(predicted,270,'#8466b4')}
      {marker}
    </svg>'''


def _rate(token: str) -> str:
    return "не определено" if token == "null" else f"{float(token)*100:.2f}%"


def _image_html(data: str, alt: str) -> str:
    return f'<img alt="{html.escape(alt, quote=True)}" src="data:image/png;base64,{data}" loading="lazy" decoding="async">'


def render(model: dict, hashes: dict[str,str]) -> str:
    cases = model["cases"]
    g23 = model["g23_rows"][1]
    ref = [float(r["ref_x"]) for r in g23]
    obs = cases["1600_A_alpha_1"]["observed"]
    true = cases["1600_A_alpha_1"]["z"]
    pred = cases["1600_A_alpha_1"]["pred"]
    overview = signal_svg(ref, obs, true, pred, 0, len(ref), False)
    boundary = signal_svg(ref, obs, true, pred, 1183, 1211, True)
    cards = []
    for key, label in zip(CASE_IDS, CASE_LABELS):
        m = cases[key]["metrics"]
        png_details = (
            f'<details><summary>Открыть проверенный график</summary>{_image_html(cases[key]["image"],label+" · observed x, Zhat, Z")}</details>'
            if cases[key]["image"] is not None else
            '<div class="minor">G2.4 PNG omitted / не проверялись и не встроены. '
            'Числа и SVG выше построены из независимо проверенных CSV.</div>'
        )
        cards.append(f'''<article class="mini">
          <div class="mini-title">{html.escape(label)}</div>
          <div class="counts">TP {m['TP']} <b>·</b> FP {m['FP']} <b>·</b> FN {m['FN']} <b>·</b> TN {m['TN']}</div>
          <div class="minor">{m['N']} отсчётов · precision {_rate(m['precision'])} · recall {_rate(m['recall'])}</div>
          {png_details}
        </article>''')
    images23 = ''.join(f'<details><summary>G2.3 · Walking α={alpha}, исходный и наблюдаемый сигналы</summary>{_image_html(model["images"][f"g23_alpha_{alpha}"], f"G2.3 comparison alpha={alpha}")}</details>' for alpha in (0,1))
    m = cases["1600_A_alpha_1"]["metrics"]
    source = html.escape(hashes["g24/results.csv"][:12])
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Лаборатория сигналов · G2.3 → G2.4</title>
    <style>
      :root{{--ink:#172b3d;--muted:#627083;--line:#dfe7ee;--blue:#3373b9;--orange:#de7940;--green:#41a67d;--purple:#8466b4}}
      *{{box-sizing:border-box}}body{{margin:0;background:#f2f5f8;color:var(--ink);font:15px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif}}
      .wrap{{max-width:1480px;margin:auto;padding:26px 28px 54px}}.heading{{display:flex;justify-content:space-between;align-items:start;gap:24px;margin-bottom:17px}}h1{{font-size:30px;line-height:1.15;margin:8px 0}}h2{{font-size:18px;margin:0 0 8px}}.sub{{margin:0;color:var(--muted);max-width:900px}}.tag{{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:#536b81;font-weight:700}}.pill{{border:1px solid #b7cad6;border-radius:99px;padding:8px 12px;font-size:12px;color:#496378;white-space:nowrap}}
      .layout{{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(360px,1fr);gap:16px}}.col{{display:grid;gap:16px;align-content:start}}.panel{{background:white;border:1px solid var(--line);border-radius:17px;padding:19px 20px;box-shadow:0 2px 9px rgba(20,43,64,.035);min-width:0}}
      .key{{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:13px;margin:8px 0}}.dot{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:middle}}svg{{display:block;width:100%;height:auto}}.large{{font-size:32px;font-weight:750;line-height:1.12}}.statrow{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0}}.stat{{background:#f4f7fa;border-radius:11px;padding:10px}}.stat small{{display:block;color:var(--muted);font-size:11px}}.stat strong{{font-size:25px}}.mini{{border-top:1px solid var(--line);padding:12px 0}}.mini:first-of-type{{border-top:0}}.mini-title{{font-weight:750}}.counts{{font-variant-numeric:tabular-nums;font-size:15px}}.counts b{{font-weight:400;color:#a5aebb;margin:0 3px}}.minor{{font-size:12px;color:var(--muted)}}.note{{background:#fff8e9;border:1px solid #f2dbab;border-radius:11px;padding:10px 12px;margin-top:10px;font-size:13px}}.hint{{font-size:13px;color:var(--muted)}}details{{border-top:1px solid var(--line);margin-top:10px;padding-top:7px}}summary{{cursor:pointer;color:#375d7a;font-size:13px;font-weight:650}}details img{{display:block;max-width:100%;height:auto;margin-top:10px;border-radius:8px}}.bottom{{margin-top:16px}}.fine{{font-size:12px;color:var(--muted)}}code{{font-family:ui-monospace,monospace}}a{{color:#276396}}@media(max-width:1050px){{.layout{{grid-template-columns:1fr}}.pill{{display:none}}}}@media(max-width:620px){{.wrap{{padding:15px 12px}}.panel{{padding:13px}}h1{{font-size:25px}}.statrow{{grid-template-columns:repeat(3,1fr)}}.stat strong{{font-size:20px}}}}
    </style></head><body><main class="wrap">
      <header class="heading"><div><div class="tag">WISDM · Subject 1600 · учебная offline-демонстрация</div><h1>Где алгоритм увидел замерзание оси?</h1><p class="sub">Реальная запись ходьбы → <b>искусственное</b> удержание x → известная маска назначения Z → ответ простого детектора Zhat. Все данные считаны из уже сохранённых G2.3/G2.4 файлов, здесь ничего не обучается и не обнаруживается заново.</p></div><div class="pill">G2.3 + G2.4 · presentation only</div></header>
      <div class="layout"><div class="col"><section class="panel"><h2>1. Исходный сигнал и сигнал после вмешательства</h2><p class="hint">Walking α=1 · [1191,2382) — назначенная заморозка x. Синий: исходное значение; оранжевый: наблюдаемое.</p><div class="key"><span><i class="dot" style="background:var(--blue)"></i>Reference</span><span><i class="dot" style="background:var(--orange)"></i>Observed</span><span><i class="dot" style="background:var(--green)"></i>Истинная Z</span><span><i class="dot" style="background:var(--purple)"></i>Предсказанная Zhat</span></div>{overview}</section>
      <section class="panel"><h2>2. Увеличение начала freeze: ошибка на границе</h2><p class="hint">Важны два соседних индекса: <b>1190</b> — опорное значение до вмешательства; <b>1191</b> — первая назначенная точка инъекции.</p>{boundary}<div class="note"><b>Один FP на i=1190.</b> Детектор видит одинаковое x уже в опорной точке и выделяет весь участок <code>[1190,2382)</code>. Но Z помечает только <code>[1191,2382)</code>. Мы не «поправляем» Zhat знанием правильной границы.</div></section></div>
      <aside class="col"><section class="panel"><div class="tag">Один заранее заданный пример · Walking α=1</div><div class="statrow"><div class="stat"><small>Назначено Z</small><strong>{m['n_true']}</strong></div><div class="stat"><small>Найдено Zhat</small><strong>{m['n_pred']}</strong></div><div class="stat"><small>FP на границе</small><strong>{m['FP']}</strong></div></div><p class="hint">Precision <b>{m['TP']}/{m['n_pred']}</b> ≈ {_rate(m['precision'])} · recall <b>{_rate(m['recall'])}</b>. Это совпадение с искусственной маской, а не измерение качества поиска реальных аппаратных отказов.</p></section>
      <section class="panel"><h2>3. Все три зафиксированных случая</h2>{''.join(cards)}<p class="fine">TP — верно отмечено; FP — отмечено без нашей инъекции; FN — пропущено; TN — верно не отмечено. При отсутствии назначенных положительных точек recall не определён.</p></section>
      <section class="panel"><h2>Чего эти картинки не доказывают</h2><p class="hint">Один испытуемый (1600), Walking и Standing не являются независимыми сессиями. <b>Z=0</b> означает лишь, что мы не добавляли дефект, а не то, что датчик исправен. Физическая единица timestamp q неизвестна. Нет независимого test, оценённой аппаратной частоты ложных тревог, нового метода или научной новизны.</p></section></aside></div>
      <section class="panel bottom"><h2>Оригинальные опубликованные сравнения G2.3</h2><p class="hint">Графики включены в HTML как исходные PNG, проверенные SHA-256. Никаких внешних ссылок, сети или сервера.</p>{images23}</section>
      <footer class="fine" style="margin-top:17px">Источник: WISDM 2019 (Gary M. Weiss), UCI 507, CC BY 4.0 · project synthetic freeze only. Offline viewer build; g24/results.csv SHA-256: <code>{source}…</code> · подробные SHA, версии и происхождение в <code>manifest.json</code> рядом с HTML. Full G2 NOT GO · G3 CLOSED.</footer>
    </main></body></html>'''


def _git_sha(root: Path) -> str | None:
    try:
        output = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=3)
        if output.returncode == 0 and re.fullmatch("[0-9a-f]{40}", output.stdout.strip()):
            return output.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def build(g23: Path, g24: Path, out: Path, g24_png_mode: str = "strict") -> dict:
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())),
            f"Output directory must be new/empty; existing files will not be overwritten: {out}")
    model, hashes = verified_inputs(g23, g24, g24_png_mode=g24_png_mode)
    page = render(model, hashes).encode("utf-8")
    manifest = {"status": "PRESENTATION_ONLY", "scope": "G2.3/G2.4 precomputed outputs; no detector run",
                "input_sha256": hashes, "html_sha256": digest(page),
                "g24_original_source_git_sha_reported": model["p24"].get("git_sha"),
                "viewer_git_sha": _git_sha(Path(__file__).resolve().parents[1]),
                "viewer_executed_source_sha256": digest(Path(__file__).resolve().read_bytes()),
                "g24_fixed_source_pins": G24_FIXED_PINS,
                "g24_png_mode": g24_png_mode,
                "g24_png_verified": g24_png_mode == "strict",
                "g24_png_embedded": g24_png_mode == "strict",
                "g24_png_attestation_scope": (
                    "G2.4 PNG excluded, not read, verified or embedded; SVG and metrics from pinned CSV"
                    if g24_png_mode == "omit" else
                    "Exact bytes only: Linux Python 3.13.5 / Matplotlib 3.10.8; independent 05 audit"
                ),
                "python": platform.python_version(), "seed": None,
                "external_services": False, "read_raw": False, "recomputed_detector": False,
                "g23_cases": ["alpha_0", "alpha_1"], "g24_cases": list(CASE_IDS),
                "scientific_validation": False, "upstream_remote_UCI_attestation": "UNVERIFIED",
                "source_document": "Issue #25; LAB-029"}
    encoded = (json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    out.mkdir(parents=True, exist_ok=True)
    try:
        (out / "index.html").write_bytes(page)
        (out / "manifest.json").write_bytes(encoded)
    except OSError:
        for name in ("index.html", "manifest.json"):
            (out / name).unlink(missing_ok=True)
        raise
    return {"status": "PASS_PRESENTATION", "output": str(out / "index.html"),
            "manifest": str(out / "manifest.json"), "html_sha256": digest(page)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue #25: offline viewer of accepted G2.3/G2.4 files only")
    parser.add_argument("--g23-dir", type=Path, default=Path("g23/example"))
    parser.add_argument("--g24-dir", type=Path, default=Path("output_g24"))
    parser.add_argument("--output-dir", type=Path, default=Path("visual_lab_out"))
    parser.add_argument("--g24-png-mode", choices=("strict", "omit"), default="strict",
                        help="strict: independently pinned Linux PNG bytes; omit: no G2.4 PNG read or display")
    args = parser.parse_args(argv)
    try:
        result = build(args.g23_dir, args.g24_dir, args.output_dir, g24_png_mode=args.g24_png_mode)
    except (InputError, OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "REJECTED_INPUT", "detail": str(exc)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS_PRESENTATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
