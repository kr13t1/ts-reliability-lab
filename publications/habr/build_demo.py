"""Rebuild the fixed offline publication HTML from versioned presentation inputs.

Reconstructed 2026-11-16 from the already-published PR #30 HTML blob.
This is NOT the original historical raw-WISDM build_demo.py and does not
assert independent authentication of the WISDM raw recording.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
TEMPLATE = SOURCE / "template.html"
PAYLOAD = SOURCE / "payload.json"
DEFAULT_OUT = ROOT / "demo" / "index.html"
PLACEHOLDER = "__EMBEDDED_WISDM_PAYLOAD_JSON__"
EXPECTED_SHA256 = "9d45b2f740415f19d8857beafa0cffd6150748571eb94841744cb085c200a684"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_mask(x: list[float], min_length: int = 3) -> list[bool]:
    result = [False] * len(x)
    start = 0
    for stop in range(1, len(x) + 1):
        if stop == len(x) or x[stop] != x[start]:
            if stop - start >= min_length:
                result[start:stop] = [True] * (stop - start)
            start = stop
    return result


def validate(payload: dict) -> None:
    if set(payload) != {"walking", "standing", "facts", "provenance"}:
        raise ValueError("Unexpected source payload fields")
    for name, n in (("walking", 3574), ("standing", 3572)):
        rows = payload[name]
        if len(rows) != n or any(len(row) != 3 for row in rows):
            raise ValueError(f"Unexpected {name} shape")
        if any(type(v) not in (int, float) or not math.isfinite(v)
               for row in rows for v in row):
            raise ValueError(f"Invalid {name} values")
    facts = payload["facts"]
    if facts["subject"] != 1600 or facts["freeze"] != [1191, 2382]:
        raise ValueError("Not the frozen demonstration")
    if facts["pred"] != [1190, 2382]:
        raise ValueError("Frozen detector interval differs")
    if payload["provenance"]["browser_detector_executed"] is not False:
        raise ValueError("Client-side detector claim differs")
    for case, rows in (("clean", payload["walking"]),
                       ("freeze", payload["walking"]),
                       ("standing", payload["standing"])):
        x = [row[0] for row in rows]
        expected = [False] * len(x)
        if case == "freeze":
            x[1191:2382] = [x[1190]] * 1191
            expected[1191:2382] = [True] * 1191
        mask = run_mask(x)
        counts = dict(tp=0, fp=0, fn=0, tn=0)
        for truth, pred in zip(expected, mask):
            counts[("tp" if pred else "fn") if truth else ("fp" if pred else "tn")] += 1
        if counts != facts["metrics"][case]:
            raise ValueError(f"Mask count mismatch: {case}")
        if case == "freeze":
            detected = [i for i, v in enumerate(mask) if v]
            if detected != list(range(1190, 2382)):
                raise ValueError("Detector interval mismatch")


def build() -> bytes:
    raw = PAYLOAD.read_bytes()
    payload = json.loads(raw)
    validate(payload)
    template = TEMPLATE.read_bytes()
    marker = PLACEHOLDER.encode("ascii")
    if template.count(marker) != 1:
        raise ValueError("Template must have precisely one data marker")
    rendered = template.replace(marker, raw)
    if digest(rendered) != EXPECTED_SHA256:
        raise ValueError("Reconstructed HTML differs from audited snapshot")
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true",
                        help="Compare rebuilt HTML to checked-in artifact; do not write")
    args = parser.parse_args()
    generated = build()
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != generated:
            parser.error("checked-in HTML does not equal reconstructed HTML")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(generated)
    print(f"PASS presentation snapshot SHA256={digest(generated)}")


if __name__ == "__main__":
    main()
