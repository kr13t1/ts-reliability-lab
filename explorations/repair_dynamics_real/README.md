# LAB-042 / Issue #40 — fixed WISDM 1601/A comparison

**Only** the run authorized by LAB-042: subject 1601, maximal Walking A series,
physical rows 1–4512, axis X. Historical admission flags stay false in the
unchanged manifest; the separate LAB-042 decision is the authority. Private exposure
history UNKNOWN; documented subject-disjoint does not establish untouched test,
independent sessions or population inference. Full G2 NOT GO, G3 CLOSED.

The accepted LAB-041 core.py, run.py, requirements.txt, protocol, manifest,
and coordinator decision are independently pinned to exact Git blobs.
This package is separate: no changes to old numerical methods, fixture, pilot,
detector or lab. Only orchestration/generalized record metadata; compute all
predictions using the accepted frozen_prediction before the evaluator receives
reference truth. Each prediction has only an observed 256-sample context,
right boundary and L. Hold and AR use left only; Linear is offline/noncausal.
No tuning, fallback, data replacement or additional scenario.

## Controlled run
The private PR workflow fires on opening the designated same-repository PR (or one synchronize event following the pre-target failure at b7b5e0e).
It checks out the exact head, installs the accepted Linux x86_64 environment
(Python 3.13.5, NumPy 2.3.5, scipy-openblas 0.3.30 one thread, Matplotlib 3.10.8),
runs accepted and new synthetic test suites in separate normal and -O
processes, records actual exits/counts, and freezes source/config/environment
and pip freeze. The gate records full tracked status, requires the actual PR HEAD and verifies every tracked executable/package/test/config/authority byte against that HEAD, including the accepted fixture package. Only a successful gate allows acquisition. Failure blocks
the real step. The gate evidence is not independent authority against arbitrary
editing of trusted code; the approved decision pins and controlled workflow
supply authorization. Transitive dependencies recorded, not separately
hash-locked. The workflow intentionally does not run target evaluation on
every new push.

From the exact frozen checkout in a controlled environment, the workflow uses:

    python -m explorations.repair_dynamics_real.gate --output-dir "$E/gate"
    python -m explorations.repair_dynamics_real.run acquire --archive "$RUNNER_TEMP/lab042_source.zip" --gate-dir "$E/gate" --receipt "$E/acquisition.json"
    python -m explorations.repair_dynamics_real.run run --archive "$RUNNER_TEMP/lab042_source.zip" --gate-dir "$E/gate" --receipt "$E/acquisition.json" --output-dir "$E/normal"
    python -O -m explorations.repair_dynamics_real.run run --archive "$RUNNER_TEMP/lab042_source.zip" --gate-dir "$E/gate" --receipt "$E/acquisition.json" --output-dir "$E/optimized"

Second execution repeats identical fixed inputs solely for reproducibility;
not a new experiment. Official HTTPS source route and accepted outer/inner,
member/key size, SHA, CRC checked. Exact physical line count, one maximal A
run, q integers and increasing, finite XYZ, retained raw-run/view pin.
No alternate subject or archive selection. No raw or amplitude arrays in Git.
Private workflow artifact includes derived reference/view and arrays, all
32 scenario masks/counts and 96+96 method/paired rows, summaries, decisions,
validation/provenance, four fixed plots, gate/acquisition/logs/checksums.
Invalid input -> no success outputs; numeric failure retained and exit 2,
no successful completed-plan claim. Normal/-O copies checked for byte equality
except provenance and exact discrete evidence + numeric tolerance. If gate or
identity fails, no further computation and no substitute source.

## Attribution and scope
Gary M. Weiss (2019), WISDM Smartphone and Smartwatch Activity and Biometrics,
UCI 507, DOI [10.24432/C5HK59](https://doi.org/10.24432/C5HK59), CC BY 4.0.
Recorded reference (not guaranteed physically clean), artificial freeze
on X with known mask. Units m/s²; q unit/epoch UNKNOWN, sample index only.
All windows from one record, descriptive dependent comparisons. The primary
is AR−Linear at L=200: not a population hypothesis. V is only descriptive.
No Habr submission or public demo update; outputs for independent 05 audit
and subsequent 00 decision. No scientific claims before audit.
