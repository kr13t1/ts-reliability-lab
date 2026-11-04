# G2.4 branch 04 — observed local execution, 2026-11-04

**Input:** `G2_RAW_FOR_AUDIT_05.zip` sha256 `7aca931a3af368bae0ac932140aff270f9cd5f0c6c783e393c83c1672628f503`; actual member TXT SHA `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`; actual Standing segment SHA `50edfd731735d54cd76fe4c0a38da914fca7b567ae4e3b3d389f2d687fadb61d`. All calculated from bytes. Raw ZIP not modified.

**G2.3 inputs:** local reserialization using frozen accepted G2.3 formula (NOT an original G2.3 program execution). Git blob SHA of local `alpha_0/arrays.csv`: `6ff11a30f79dab8febb465004954109e74cfb341`; accepted repository `g23/example/alpha_0/arrays.csv` same SHA and 334278 bytes. Local alpha_1 blob `f075db8916c8be0f892f77eb511fc801e13748f6`; accepted artifact same SHA and 334445 bytes. Thus **the inputs are byte-identical to already audited G2.3 output**. Input reconstruction is included for provenance, **not part of the algorithm or deployable `g24/`**.

Commands actually run from the artifact's parent directory:

```sh
python -m unittest discover -s g24/tests -v
python prepare_verified_g23_input.py
python -m g24.demo --g23-dir g23_reconstructed --standing-input raw/data_1600_accel_phone.txt --output-dir run_1
python -m g24.demo --g23-dir g23_reconstructed --standing-input raw/data_1600_accel_phone.txt --output-dir run_2
```

Observed `READY_FOR_INDEPENDENT_05_AUDIT` for both CLI invocations. Deterministic results.csv/results.json and all three per-case masks are byte-identical across runs (PNG platform portability not asserted). Test suite passes in the recorded local environment. No algorithmic tuning performed.

| Case | N | TP | FP | FN | TN | n_pred | recall | precision | FPR injection-relative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Walking alpha0 | 3574 | 0 | 0 | 0 | 3574 | 0 | null | null | 0 |
| Walking alpha1 | 3574 | 1191 | 1 | 0 | 2382 | 1192 | 1 | 0.9991610738255033 | 0.000419639110365086 |
| Standing no injection | 3572 | 0 | 0 | 0 | 3572 | 0 | null | null | 0 |

The predicted alpha1 run starts at **1190** (frozen anchor), rather than assigned injection at 1191: exactly one boundary FP. No natural exact constant run of length 3 was reported in either no-injection control; neither is certified healthy.

**Status:** READY_FOR_INDEPENDENT_05_AUDIT (not accepted); full G2 NOT GO / G3 CLOSED. No statistical generalization or scientific novelty.
