# Repair pilot — v1 (exploratory; pending audit)

WISDM subject 1600, Walking/A, 3574 X observations. Frozen protocol in SPEC.md; 8 starts × 4 lengths × 3 methods; one oracle-mask artificial freeze per scenario. No held-out test, no new method, no downstream ML. G2 NOT GO, G3 CLOSED.

Original local evidence: results.csv, summary.csv and provenance.json. The Git transfer preserves the local protocol, run.py and numerical tables; binary PNGs are generated on rerun rather than committed. The initial local run passed 6 tests. The alternate reference-CSV route is a new reproduction adapter, not a claim of a second raw run or independent audit.

## Reproduce from the original supplied raw ZIP

From this directory:

```sh
python -m pip install -r requirements.txt
python -m unittest -v
python run.py /path/to/G2_RAW_FOR_AUDIT_05.zip
```

Use a working copy: run.py writes results.csv, summary.csv, PNGs and provenance.json in its own directory. Raw ZIP is not committed. It must contain the exact member and digest in config.json.

## Reproduce from previously committed reference.csv (without raw ZIP)

From repository root:

```sh
python -m pip install -r explorations/repair_pilot/requirements.txt
python explorations/repair_pilot/reproduce_reference.py --out /tmp/repair-pilot-reproduction
```

The adapter checks the already committed g23 reference Git blob, runs the identical numerical methods, compares all 96 rows and 12 summary rows within tolerance to local measured results, writes separate reproduction files (including plots), and records reference-based provenance. This route does not verify the raw member. GitHub Actions runs tests and this independent-of-raw-ZIP reproduction; an independent 05 audit is still required.

Source: Gary M. Weiss (2019), UCI WISDM 507, DOI https://doi.org/10.24432/C5HK59, CC BY 4.0.
