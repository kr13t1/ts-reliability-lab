# G2.4 — constant-run baseline A (Issue #20, LAB-027)

**Status: READY_FOR_INDEPENDENT_05_AUDIT, NOT G2.4 GO.** No ML, repair, resampling, seconds or novelty claim. One subject 1600, activities A (Walking) and E (Standing), same subject and **not independent sessions**. `Z` means only an **assigned project injection**, not labels for actual hardware faults; any FP/FPR is *injection-relative only*.

Python 3.13.5, `numpy==2.3.5`, `matplotlib==3.10.8`. Offline exact float64 `==`, `L=3`, `epsilon=0`; returns complete maximal equal runs. Detector consumes **only observed x**. Evaluation independently receives truth afterwards. A G2.3 freeze copies the preceding anchor, so the anchor may be a boundary FP and must never be edited based on ground truth.

## Run in full repository

From repository root, with **the previously verified** raw WISDM `data_1600_accel_phone.txt` in `data/raw/` (not committed):

```sh
python -m pip install -r g24/requirements.txt
python -m unittest discover -s g24/tests -v
python -m g23.freeze --input data/raw/data_1600_accel_phone.txt --output-dir output_g23 --source-commit 3140c28fa7e93fc804a3fe26a6aa23dc48484717
python -m g24.demo --g23-dir output_g23 --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir output_g24
```

Both output directories must be absent or empty. The accepted repository's `g23/example/` may substitute for `output_g23` when source identity is independently checked. `g24.demo` verifies SHA256 of full TXT, Standing segment, immutable original row/float/q identity, G2.3 assigned masks and frozen formula before detection. Wrong SHA, identity, config or missing inputs return exit code `2`. No paid services. Original raw is CC BY 4.0 (WISDM / UCI 507, DOI 10.24432/C5HK59); provenance of remote original UCI ZIP remains UNVERIFIED.

Output: `results.csv`, `results.json`, per-case `masks.csv` (q as literal integer text, original source_line, Zhat and Z), `events.json`, `comparison.png`, frozen config, validation/provenance including output hashes. Metrics per case and **x-axis samples only**: TP, FP, FN, TN, precision, recall, FPR, specificity. Empty denominators emit JSON `null` with explicit reason, CSV `null`. Event intersection is descriptive only, not event precision.

The local `g23_reconstructed/` input in the companion execution ZIP was reconstructed from verified raw solely to exercise the new runner; **its two files' Git blob SHAs were compared with the accepted `g23/example/alpha_0/arrays.csv` and `alpha_1/arrays.csv`, and both match exactly**, thereby establishing input byte identity. This is not a claim that an original G2.3 CLI was rerun by branch 04. The outputs in `run_1/` and `run_2/` are actual new G2.4 CLI runs on the byte-identical input, not predictions fabricated from the spec.

## Limitations

No injections were made in raw Standing. Both no-injection controls have `Z=0`; this **does not imply that sensor hardware was defect-free**. Physical timestamp units, sessions and original UCI ZIP chain-of-custody remain unknown; no FPR for real-world faults, no statistical confidence intervals, no independent subject evaluation. The 3574 samples of A are correlated, not 3574 independent trials. G3 is closed. Only coordinator 00 may decide acceptance after an independent read-only audit 05.
