# Repair dynamics — LAB-041 / Issue #38

**Synthetic-only implementation, not independent acceptance, not target evaluation.**
Protocol: docs/specs/REPAIR_DYNAMICS_PROTOCOL_v1.md §§3–8, approved LAB-038.
LAB-041 enables only fixture gate. The already audited LAB-040 manifest is
pinned by Git blob from main and read as metadata only; historical closed
flags remain unchanged. No raw loader, network acquisition, detector, tuning,
fallback or target amplitudes. Full G2 NOT GO, G3 CLOSED.

## Run from checkout root (Linux x86_64, Python 3.13.5)

    python -m pip install --only-binary=:all: -r explorations/repair_dynamics/requirements.txt
    export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    EXPECTED_OPTIMIZE=0 python -m unittest discover -s explorations/repair_dynamics/tests -v
    EXPECTED_OPTIMIZE=1 python -O -m unittest discover -s explorations/repair_dynamics/tests -v
    python -m explorations.repair_dynamics.run --output-dir dynamics_fixture
    python -O -m explorations.repair_dynamics.run --output-dir dynamics_fixture_O

Pinned NumPy 2.3.5/scipy-openblas 0.3.30, Matplotlib 3.10.8. BLAS/thread
identity explicitly checked; Linux-only reproducibility scope. Do not switch
environment to obtain a desired sign. Numeric tolerance plus exact discrete
evidence required. Output directories must be new or empty. Exit 0 means
PASS_SYNTHETIC_FIXTURE only; invalid input/config/identity/outside is exit 2
with failure validation/provenance and no success output (existing nonempty
directories untouched). Numeric failure retains null/failure rows, no fallback,
incomplete plan exit 2. Primary status and plan completeness separate; invalid
execution takes precedence. No real evaluation even if config is edited.

## Fixture and outputs

One fixed deterministic synthetic 3-axis record N=3401, artificial integer q,
no randomness; X combines integer triangular waveforms with predetermined
amplitude variation and a bounded modular term. Values are arbitrary units,
not WISDM or calibrated measurements. Compiled fixture SHA-256 independent of
mutable bundle manifest. Tests exercise malformed member/schema and rehashed
substitution. Grid unchanged: starts 400..3200 step 400; lengths 5,20,80,200;
Hold, Linear, AR(10). Same oracle mask, Linear uses future boundary; Hold/AR
do not. All reconstructions frozen before evaluation. Outside X mask,
other axes and integer q unchanged. Arrays share common unchanged obs_y/z/q;
only reconstructed X method-specific. Failure reconstruction literal null.

E = masked amplitude RMS; A = RMS internal first-difference residual;
B = RMS reference first differences; D=A/B without epsilon; V=variance ratio
descriptive only. Boundary residuals separate. Undefined values include reasons.
Outputs include 32 scenarios/arrays, 96 method and 96 paired rows, AR
diagnostics, all effects, exact signs/ties/undefined, counts, methods/paired
summaries and decisions. Paired means restricted to common valid windows;
all available E also retained. No pooled RMSE, independent-window inference,
p-values or scientific novelty. Synthetic TARGET_* strings exercise the rule,
not a real target result. Fixed plots s=1200 L=20 and 200, comparison E/D and
paired primary scatter, actual validation/provenance hashes, source and
environment recorded. The approved historical manifest is copied unchanged as
metadata only. CI stores actual logs, exits, normal and optimized artifacts.

Next: 05 independent implementation audit on exact HEAD, then separate 00
decision; no real target access or merge by 04.
