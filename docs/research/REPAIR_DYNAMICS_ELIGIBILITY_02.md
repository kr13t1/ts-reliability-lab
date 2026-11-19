# LAB-038 / Issue #34 — independent recording eligibility: evidence (02)

Date: 2026-11-19. **BLOCKED_NO_ELIGIBLE_DATA**; manifest is a blocked precheck, not a frozen usable evaluation input. Review by 05 pending; no authorization for runner/evaluation. [Machine-readable inventory](../../data/provenance/REPAIR_DYNAMICS_ELIGIBILITY_MANIFEST_v1.json).

## Contract and inventory

[Issue #34](https://github.com/kr13t1/ts-reliability-lab/issues/34), [LAB-038](../DECISIONS.md), [protocol §2](../specs/REPAIR_DYNAMICS_PROTOCOL_v1.md), accepted PR #33 HEAD `9bbed1f030ddf556d92aa72c7c5aa130e4700925`, merge `9bd5168b1a8fb1922a9ef3bde626ca52c7c66ab5`, exact document blob `7d5c0f21bbe63575ff3f7302460589791b03d7b5`. Historical PROPOSED header does not supersede LAB-038. Read current NEXT_ACTION and project state; the latter retains older LAB-036 header, so controlling authority is LAB-038 and Issue #34.

Official [UCI 507](https://archive.ics.uci.edu/dataset/507/wisdm%2Bsmartphone%2B), Gary M. Weiss (2019), DOI [10.24432/C5HK59](https://doi.org/10.24432/C5HK59), CC BY 4.0: documented 51 subjects 1600–1650, one raw file per subject for each sensor/device. The complete official archive inventory could not be read. The complete *accessible transport* inventory has three subject TXT members, activity_key.txt and PROVENANCE_MANIFEST.json. Search of accessible Project/Library titles for original and fresh ZIP yielded no full archive; no complete ZIP in mounted inputs. Therefore log all 51 documented IDs; 1603–1650 are **unavailable here**, not asserted absent in UCI. No alternative dataset, activity, partial run or fallback to subject 1600.

## Direct byte check, not a JSON-only review

Actually read `G2_RAW_FOR_AUDIT_05.zip`: 4,373,638 bytes, SHA-256 `7aca931a3af368bae0ac932140aff270f9cd5f0c6c783e393c83c1672628f503`; all ZIP CRCs passed, digest unchanged before/after. All three members independently rehashed; all sizes, counts, boundaries, q endpoints and digests agreed with previous precheck JSON (local bytes SHA-256 `f534d093b003327019dec214c1c332e95c1d413ad25efd7943df4082422e8a57`, corresponding to repo blob `ea9d48a2c3ee2896c860a9a474b595fbcec8b1a2`). Actual activity_key SHA and mapping A=Walking in manifest. Processing allowed solely for format, finite values, q, length and view hashes; no amplitude summaries, plots, equality-run analysis, outcomes or quality-based exclusion.

| Subject | Physical TXT lines | Maximal A-run (1-based) | N | Format/finite/integer q, strict q inside A, N≥3401 | Eligibility |
|---|---:|---|---:|---|---|
| 1600 | 64311 | 1–3574 | 3574 | PASS | EXCLUDED: design/pilot (entire subject) |
| 1601 | 81457 | 1–4512 | 4512 | PASS | BLOCKED: independent official member identity and full exposure history not confirmed |
| 1602 | 84890 | 1–3572 | 3572 | PASS | BLOCKED: same reasons |
| 1603–1650 | unknown | unknown | unknown | NOT CHECKED | unavailable in accessible inputs; history/source unverified |

Each of the three has exactly one A-run, starting at physical line 1 and immediately followed by B. The candidate ordering is numeric subject ID then physical start line; 1601/A is the first **structurally qualifying non-design** candidate, not selected and not eligible yet. No candidate is fully eligible. Distinct ID is subject-disjoint grouping only, not statistical independence or verified physical session. Unknown q units/epoch/collector, missing physical events, potential natural faults and physical session continuity retained; no Hz or seconds computed.

## Independent source gate — NOT SATISFIED

On 2026-11-19 opened the official UCI listing and followed its download link:
`https://archive.ics.uci.edu/static/public/507/wisdm%2Bsmartphone%2Band%2Bsmartwatch%2Bactivity%2Band%2Bbiometrics%2Bdataset.zip`.
Web retrieval refused oversized binary (>4 MiB limit); container curl failed DNS resolution; direct download tool failed. No bytes of a second complete download were obtained. Limited search for official checksum (UCI page, WISDM 507 / wisdm-dataset.zip SHA-256 searches) did not identify a trusted published checksum. Not proof no such checksum exists. Historical external/inner ZIP hashes and sizes in manifest are **reported** not recomputed today. Previous 151,511,010-byte prefix match is not proof of identity of selected members or full remote ZIP. See [LAB-016 evidence](../../data/provenance/G2_PROVENANCE_EVIDENCE_LAB016.json), [prefix check](../../data/provenance/G2_UCI_PARTIAL_PREFIX_CHECK.json), [LAB-017 review](../G2_AUDIT_REVIEW_00_LAB017.md). Local transport CRC and SHA cannot independently authenticate official acquisition. MAJOR-01 for full G2 remains open even if one member is attested later.

## Exposure gate — limited history, no positive clearance

Repository main tree enumerated, available PR list #1–33 and titles/descriptions checked; read historical data card, G2 specification, decisions, project state, prior precheck and pilot SPEC/config/provenance. [Pilot #31 independent audit](https://github.com/kr13t1/ts-reliability-lab/pull/31#issuecomment-6995524630) and frozen pilot config identify **1600/A only**; G2.2/2.3/2.4 and viewer/Habr history used 1600/A and/or E. Local archived `G2_MULTI_SUBJECT_REVIEW_02.zip` parser read and checked: numeric axes parsed only for finite validation; reports concern counts, q and identity. Available prior project conversations corroborate metadata-only use of 1601/1602. No evidence of shape inspection, dynamics statistics, trial outcomes or amplitude-based design for 1601/1602 found in inspected sources; historical q comparisons were metadata, not repair. Search of GitHub indexed text returned no matches even for known terms, so not treated as proof of absence. Not every private/local execution, historical branch, or unrecorded human inspection is accessible. Full exposure history is therefore **UNVERIFIED** for these two subjects, rather than falsely asserted zero prior exposure. No new target amplitudes disclosed to roles 03/04. The current 02 operation parsed bytes mechanically, printed only metadata and hashes.

## Reproduction of current metadata check

Standard Python 3, only hashlib/zipfile/re/math/csv/io (no numerical methods). This is the exact operation in descriptive form; not a runner or fixture-only gate:

1. Read original transport in binary and SHA-256 before opening. Open ZIP read-only, call testzip; require no duplicate member names. Read exactly the three manifest-listed raw TXT members and activity key; compare hash, byte size, CRC with manifest. Independently compare against recorded precheck.
2. Split raw bytes with `splitlines(keepends=True)`; enumerate physical lines from 1, ASCII, remove only trailing CR/LF and the one terminal semicolon; split on commas, six nonempty fields. Require subject decimal digits matching filename, one activity in A–M/O–S, signed decimal integer q; require decimal/scientific number grammar for all three original axis tokens, finite float64 values. No sorting/dropping. Read q as integer, not float.
3. Scan maximal constant-activity runs in physical order (subject checked for all lines). For each A-run check strict q increase and N≥3401, record endpoints and neighboring codes. For raw-run SHA concatenate original line bytes including their original line endings. No amplitude-based selection.
4. Canonical view hash: build an in-memory `io.StringIO(newline="")` with `csv.writer(..., lineterminator="\n")`, header `i,source_line,subject,activity,q,x,y,z`; row for each source line `[i, physical_line_number, *original_six_field_tokens]` (i 0-based). Hash UTF-8 bytes; retain only digest and byte length, not view. Match previous G2.2 accepted 1600/A view SHA as serialization control. New candidate view hashes in JSON are *local evidence*, not yet independently official-attested pins. Rehash original transport after reading; no writes to any source.
5. Apply exclusions and provenance/exposure gates **before selection**. All three read-only checks completed but zero eligible targets. Manifest has null selected subject/run/hash; inactive planned grid §3, 32 scenarios, no computed outcomes.

## Handoff

**BLOCKED_NO_ELIGIBLE_DATA** is the required stop result, not an empirical negative about methods. No repair metrics or runner, no new masks/split/plots, no edits to raw or pilot. One next action: 05 independently review this frozen PR and reproduce metadata using existing transport (no manual archive handoff); report source/exposure blockers to 00. Subsequent official-source re-acquisition/equivalent trusted member attestation and completion of exposure evidence require coordinator decision; no fixture gate or evaluation until separate permission. Full G2 NOT GO; G3 CLOSED.
