# G2.4 Issue #20 — author execution, not independent audit 05

Status: READY_FOR_INDEPENDENT_05_AUDIT after freezing PR HEAD. LAB-027 narrow implementation GO, not technical G2.4 acceptance, not full G2 GO, G3–G6 closed.

Environment: Linux Python 3.13.5, NumPy 2.3.5, Matplotlib 3.10.8.
Source: attached verified transport G2_RAW_FOR_AUDIT_05.zip SHA-256 7aca931a3af368bae0ac932140aff270f9cd5f0c6c783e393c83c1672628f503; member data_1600_accel_phone.txt SHA-256 40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f; original Standing segment source lines 14292..17863 SHA-256 50edfd731735d54cd76fe4c0a38da914fca7b567ae4e3b3d389f2d687fadb61d.

## Actual local execution

The code was run in an **isolated workspace**. Because private GitHub HTTPS clone credentials were unavailable, the standalone local sandbox used compatible small *temporary* adapters for g2.readonly and g23.freeze interfaces. They are not committed as changes. The G2.3 reference.csv, alpha_0/arrays.csv, alpha_1/arrays.csv, config.json and selection.json were reconstructed from the exact verified raw under the published G2.3 contract; **all five computed hashes equal the accepted hashes in the repository**. This demonstrates byte-identical G2.3 **inputs**, but is **not** a full integration test with actual unchanged modules checked out via Git. Audit 05 must independently rerun on the original repository.

Commands that actually ran:

    python local_prepare_input.py
    python -m unittest discover -s g24/tests -v
    python -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir g24/results/local_run_A
    python -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir g24/results/local_run_B

Results: 26 tests passed (including real-byte integration); both CLI calls PASS_DEMO / exit 0. 10/10 *non-provenance* outputs including sample CSVs and PNGs have exactly the same SHA between runs. Provenance files can differ by command/output dir. Standalone source git_sha=null; an immutable PR HEAD identifies the published code, not automatic local checkout attestation.

| case | N | TP | FP | FN | TN | n_true | n_pred | precision | recall | injection-relative FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1600/A alpha0 | 3574 | 0 | 0 | 0 | 3574 | 0 | 0 | null | null | 0 |
| 1600/A alpha1 | 3574 | 1191 | 1 | 0 | 2382 | 1191 | 1192 | 0.9991610738255033 | 1.0 | 0.000419639110365086 |
| 1600/E raw | 3572 | 0 | 0 | 0 | 3572 | 0 | 0 | null | null | 0 |

Predicted event alpha1 [1190,2382); assigned injection [1191,2382). Boundary FP at anchor i=1190 must not be adjusted. Walking alpha0 and raw Standing have empty predicted and true masks; precision and recall null for zero denominator. Pointwise FPR for these no-injection controls is **not** a physical false-alarm estimate.

No source or prior accepted G1/G2.2/G2.3 files modified in this PR. No raw TXT/ZIP committed. Full per-sample Zhat/Z CSV with original q/source lines and illustrative PNG from actual local run shipped in separate user-provided audit ZIP G24_ISSUE20_IMPLEMENTATION_v1.zip; PR code reproducibly regenerates it from the documented verified raw. No training, tuning, timed latency, confidence intervals or independent-subject claims. Future gate: 05 read-only audit on frozen PR SHA, separate 00 decision; no merge by 04.
