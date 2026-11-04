# G2.3 execution report — Issue #12

Status: PASS_DEMO by implementation author; independent audit 05 PENDING. Full G2 NOT GO; G3 not opened. Authorization: LAB-023, main base `1fc3f053a8260bb5d869bd904522fdbb72b5215f`. Executed source commit: `bf0e6039a216d6d40c21016f8546aa5b1ae00050`. Artifact/report commit follows it without source changes.

## Execution and source identity

A GitHub API snapshot was used because ordinary HTTPS git clone did not authenticate. No substitute source or raw was used. Runtime git_sha/git_dirty are null; provenance's declared_source_commit is not presented as automatic authentication. The coordinator directly compared Git blob SHA-1 of local executed g23/freeze.py, freeze.json, requirements.txt, unchanged g2/readonly.py, g2 config, specification and pinned precheck against the recursive GitHub tree of the source commit: 7/7 equal. The exact SHA-256 of executed sources is also recorded in provenance.json. No reconstruction of Git metadata was performed.

Raw was extracted locally from the already attached G2_RAW_FOR_AUDIT_05.zip: member data_1600_accel_phone.txt, 3451789 bytes, SHA-256 40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f. This is verification of transported bytes, not full official UCI ZIP attestation. No raw TXT/ZIP is committed.

Commands from repository root:

```sh
python -m unittest discover -s g23/tests -v
python -m g23.freeze --input data/raw/data_1600_accel_phone.txt --output-dir g23/example --source-commit bf0e6039a216d6d40c21016f8546aa5b1ae00050
python -m g23.freeze --input data/raw/data_1600_accel_phone.txt --output-dir /workspace/scratch/51103f81b304/g23-repeat --source-commit bf0e6039a216d6d40c21016f8546aa5b1ae00050
```

Both CLI runs returned PASS_DEMO. Versions are in provenance (NumPy 2.3.5, Matplotlib 3.10.8). 15/15 unittest tests passed; log attached. Existing G2.2 pytest suite was NOT rerun: pytest is unavailable in this execution environment. The accepted G2.2 code was unchanged and its validator actually ran on the real raw in both CLI executions. GitHub CI is a separate status, not inferred from local success.

## Computed results

| alpha | n_assigned | n_changed | D_I | D_Z | L_out |
|---|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | null | 0 |
| 1 | 1191 | 1191 | 3.0753845270371265 | 3.0753845270371265 | 0 |

D_I and D_Z measure artificial change in documented acceleration units, not classification/detection/repair quality. Empty-mask D_Z is explicitly null, status NOT_APPLICABLE. Mask counts can differ from changed counts in general; a constant-signal fixture verifies that distinction.

A separate author check using only csv/math (without importing freeze/metrics) matched all 3574 rows of BOTH arrays.csv files directly against raw: source lines, q, all reference tokens, expected frozen values, every mask bit, unchanged coordinates and metrics. This is a cross-check by the same executor, NOT independent audit 05.

The repeat run produced byte-identical 10/10 non-provenance outputs, including both PNGs, CSVs, config, selection, results and validation. Provenance differs as expected in output-dir arguments. The accepted reference.csv SHA is unchanged: 8bf61ee71f68e0648ead7bc8eb8b6c44414e28411bd6de65e5f9dadf9c28eb38. Graph alpha=1 was visually inspected: the horizontal x segment aligns with Z_x; y/z remain overlaid; labels use indices, not physical time.

## Limits and handoff

Timestamp unit/epoch, physical session independence, full remote UCI provenance remain UNKNOWN/UNVERIFIED. X_ref is an observed record, not guaranteed clean truth. No resampling, classifier, detector, train/test, repair beyond identity, or new corruption type was introduced. Parameters and record were fixed before execution, not selected for visible effect.

Next: independent read-only audit 05 of the final PR SHA, using the original raw hash and source commit above; then decision 00. PR must not be merged by this executor. The old WORK_ORCHESTRATION/G2 README headers retain historical instructions; LAB-023 and Issue #12 explicitly authorize this narrowly scoped addition, while G2.2 remains unchanged.
