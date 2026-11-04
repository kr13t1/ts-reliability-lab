# G2.4: fixed exact constant-run baseline A — Issue #20 / LAB-027

Status: READY_FOR_INDEPENDENT_05_AUDIT only when the PR is frozen. This is an **educational** sanity-check, NOT G2.4 technical GO, not full G2 GO and not G3. No learning, repair, classifier or scientific novelty.

Mathematical contract: docs/g2/G24_CONSTANT_RUN_BASELINE_SPEC.md v0.1. The historical header says PROPOSED; LAB-026 and LAB-027 separately authorize this narrowly scoped implementation. 0-branch and the Standing negative control have **no project-injected error**, not verified healthy hardware.

## Exact local commands

From the existing repository root, Python 3.13.5 (pinned in g24/.python-version); NumPy 2.3.5 and Matplotlib 3.10.8 are pinned in g24/requirements.txt. Python 3.12 compatibility is plausible but not independently verified for this run.

    python -m pip install -r g24/requirements.txt
    python -m unittest discover -s g24/tests -v
    python -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir /tmp/g24-first
    python -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir /tmp/g24-second

Replace /tmp paths with **new empty directories** under Windows. The repository provides the previously audited g23/example CSV outputs. The command uses unchanged g2.readonly and g23.freeze modules. The original raw TXT must be extracted by the user from the already verified G2_RAW_FOR_AUDIT_05.zip; no raw files or the 310 MB UCI archive are committed and no network/paid services are required at runtime.

Required transport ZIP SHA-256: 7aca931a3af368bae0ac932140aff270f9cd5f0c6c783e393c83c1672628f503.
Original data_1600_accel_phone.txt: SHA-256 40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f, size 3,451,789 bytes. Standing/E 1600 segment source lines 14292..17863, N=3572, SHA-256 50edfd731735d54cd76fe4c0a38da914fca7b567ae4e3b3d389f2d687fadb61d. Full remote original UCI ZIP authenticity UNVERIFIED.

## Frozen single experiment: three cases

| Case | source | assigned mask |
| --- | --- | --- |
| 1600_A_alpha_0 | G2.3 Walking/A 1600, original lines 1..3574 | all zero |
| 1600_A_alpha_1 | G2.3 Walking/A 1600, alpha1 | x[1191:2382] = 1 |
| 1600_E_raw | original Standing/E 1600, original lines 14292..17863 | all zero, no project injection |

Detector receives **only observed_x** as float64 vector and L=3. It marks every point of each maximal exact equality run of length >=3, with epsilon=0, without knowledge of assigned Z, X_ref, alpha, activity, q, a/b or origin. **Predictions for all three cases are computed before the evaluator reads G2.3 assigned Z.** An observed anchor preceding the injected interval remains eligible as a predicted positive and must not be manually adjusted.

evaluate_mask(predicted, assigned) calculates x-only TP/FP/FN/TN, precision/recall/FPR/specificity and explicit null reasons. The denominator is N, not 3N. Event overlaps are descriptive, not a matched-event precision. On absent injected positives, recall is null (NO_INJECTED_POSITIVES), not zero or 100%. No physical time conversion, q is preserved verbatim as integer and source lines are unchanged.

CLI creates per-case masks.csv: i, source_line, q, obs_x, Zhat_x, Z_x; detection.png with observed trace and both masks; also results.csv, events.json, config.json, validation.json, provenance.json with SHA-256 hashes, versions and source status. A bad/missing SHA, altered config, different Standing segment or existing nonempty output is a controlled refusal (exit 2); no fake successful outputs. Tests without raw skip integration checks; tests on the verified raw exercise the full pipeline.

## Actual author execution (NOT independent audit)

Python 3.13.5, NumPy 2.3.5, Matplotlib 3.10.8 on Linux; 26 tests passed with verified raw, two real-byte CLI runs PASS_DEMO; 10/10 non-provenance outputs byte-identical, including PNGs. G23 local scratch CSV reconstructions were byte-identical to accepted repository g23/example hashes; temporary compatible parser adapters were used outside the PR and **are not misrepresented as actual repository integration testing**. The role 05 reviewer must rerun with the original, unchanged g2 and g23 modules. See g24/reports/EXECUTION_REPORT.md.

| Case | TP | FP | FN | TN | Precision | Recall | injection-relative FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Walking alpha0 | 0 | 0 | 0 | 3574 | null | null | 0 |
| Walking alpha1 | 1191 | 1 | 0 | 2382 | 1191/1192 | 1 | 1/2383 |
| Standing raw | 0 | 0 | 0 | 3572 | null | null | 0 |

The frozen predictor flags x[1190:2382), while assigned injection is x[1191:2382): **one boundary FP** at anchor i=1190. On both negative controls no run of length 3 was detected; this is **not** a real sensor false-alarm-rate result. All three cases are from one subject and do not yield independent trials, generalizable accuracies, confidence intervals or latency claims. Unknown: whether any natural sensor faults exist; session identities, physical q units and remote UCI checksums.

The author's reproducibility bundle with full sample CSV and PNG is G24_ISSUE20_IMPLEMENTATION_v1.zip (shared with the user for 05). PR stores source and factual summaries; per-sample files can be recreated with the four commands above. No merge until 05 read-only audit on frozen SHA and separate 00 decision.
