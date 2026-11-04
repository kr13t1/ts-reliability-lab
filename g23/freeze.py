"""Single authorized freeze experiment. Reuses the unchanged G2.2 validator."""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import re
import sys
import numpy as np
from g2 import readonly as ro

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {"contract": "LAB-023; G2_REAL_SIGNAL_SPEC §7", "axis": 0,
          "a": 1191, "b": 2382, "alphas": [0, 1], "seed": None, "baseline": "identity"}
REFERENCE_SHA = "8bf61ee71f68e0648ead7bc8eb8b6c44414e28411bd6de65e5f9dadf9c28eb38"
APPROVAL_COMMIT = "1fc3f053a8260bb5d869bd904522fdbb72b5215f"


def check_array(x):
    if not isinstance(x, np.ndarray) or x.dtype != np.float64 or x.ndim != 2 or x.shape[0] != 3 or not np.isfinite(x).all():
        raise ValueError("expected finite float64 array of shape (3,N)")


def freeze(x, alpha, a, b):
    """Return new observed array and ASSIGNED mask, without mutating x."""
    check_array(x)
    if type(alpha) is not int or alpha not in (0, 1):
        raise ValueError("alpha must be integer 0 or 1")
    if type(a) is not int or type(b) is not int or not 1 <= a < b < x.shape[1]:
        raise ValueError("require 1 <= a < b < N")
    observed = x.copy()
    mask = np.zeros(x.shape, dtype=bool)
    if alpha == 1:
        observed[0, a:b] = x[0, a-1]
        mask[0, a:b] = True
    return observed, mask


def metrics(reference, observed, mask, a, b):
    """Identity baseline; empty-mask RMSE is undefined, represented by None."""
    check_array(reference)
    check_array(observed)
    if observed.shape != reference.shape or mask.shape != reference.shape or mask.dtype != bool:
        raise ValueError("array/mask shape or dtype mismatch")
    if not 1 <= a < b < reference.shape[1] or not (~mask).any():
        raise ValueError("invalid interval or empty complement")
    delta = observed - reference
    rms = lambda v: math.sqrt(math.fsum(float(t)**2 for t in v) / len(v))
    count = int(mask.sum())
    return {"D_I": rms(delta[0, a:b]), "D_Z": rms(delta[mask]) if count else None,
            "D_Z_status": "DEFINED" if count else "NOT_APPLICABLE",
            "L_out": float(np.max(np.abs(delta[~mask]))),
            "n_assigned": count, "n_changed": int(np.count_nonzero(observed != reference)),
            "outside_identical": bool(np.array_equal(reference[~mask], observed[~mask]))}


def plot(path, reference, observed, mask, alpha):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    i = np.arange(reference.shape[1])
    fig, axes = plt.subplots(4, 1, figsize=(13, 9), sharex=True,
                             gridspec_kw={"height_ratios": [1,1,1,.55]})
    for c, ax in enumerate(axes[:3]):
        ax.plot(i, reference[c], color="#4076a9", lw=.65, label="Исходная запись")
        ax.plot(i, observed[c], color="#d44b35", lw=.65, alpha=.85, label="После вмешательства")
        ax.set_ylabel("xyz"[c]+" (м/с²*)")
        ax.grid(alpha=.2)
    axes[0].legend(loc="upper right", ncol=2)
    axes[0].set_title(f"WISDM 1600/A · строки 1–3574 · α={alpha}\n"
                      + ("Искусственная заморозка x: [1191,2382)" if alpha else "Контроль: вмешательство отключено"))
    for c in range(3):
        axes[3].step(i, mask[c].astype(int), where="mid", lw=1.2, label="Z_"+"xyz"[c])
    axes[3].set_ylim(-.1,1.2)
    axes[3].set_yticks([0,1]); axes[3].set_ylabel("Маска Z")
    axes[3].legend(loc="upper right", ncol=3)
    axes[3].set_xlabel("Индекс отсчёта (не секунды; единица timestamp неизвестна)")
    fig.text(.02,.012,"* По документации WISDM. Исходная запись не гарантированно безошибочна; Z обозначает назначенную инъекцию.",fontsize=8)
    fig.tight_layout(rect=(0,.035,1,1))
    fig.savefig(path,dpi=125); plt.close(fig)


def write_arrays(path, rows, observed, mask):
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,lineterminator="\n")
        w.writerow(["i","source_line","q","ref_x","ref_y","ref_z","obs_x","obs_y","obs_z","Z_x","Z_y","Z_z"])
        for i,r in enumerate(rows):
            w.writerow([i,r.line,str(r.q),*r.axes_tokens,*[repr(float(v)) for v in observed[:,i]],*[int(v) for v in mask[:,i]]])


def execute(raw_path, output, config_path, source_commit=None, invocation=None):
    if output.exists() and any(output.iterdir()):
        raise ro.Refusal("OUTPUT_NOT_EMPTY", "output must be new or empty")
    output.mkdir(parents=True,exist_ok=True)
    evidence={"status":"PENDING", "command_argv": invocation,
              "declared_source_commit":source_commit,
              "source_commit_evidence":"Caller-supplied identifier; compare source hashes with GitHub (not automatic attestation)",
              "approval_commit":APPROVAL_COMMIT, "approved_spec_commit_sha":ro.APPROVED_SPEC_COMMIT_SHA,
              "timestamp_unit":"UNKNOWN", "session_id":None, "physical_continuity":"UNKNOWN",
              "full_remote_attestation":"UNVERIFIED", "seed":None,
              "attribution":{"author":"Gary M. Weiss", "dataset":"WISDM 2019, UCI 507",
                             "doi":"10.24432/C5HK59","license":"CC BY 4.0 (UCI metadata)",
                             "modification":"Artificial freeze of x only; alpha=0 and alpha=1"},
              "source_sha256":{p:ro.sha_file(ROOT/p) for p in ["g23/freeze.py","g23/configs/freeze.json","g23/requirements.txt","g2/readonly.py","g2/configs/g2_readonly.json","docs/g2/G2_REAL_SIGNAL_SPEC.md"]},
              "versions":{"python":sys.version.split()[0],"numpy":np.__version__}, **ro.git_state()}
    try:
        try:
            config=json.loads(config_path.read_bytes())
        except (OSError,ValueError) as e:
            raise ro.Refusal("REJECTED_CONFIG","unreadable/invalid config") from e
        ro.json_write(output/"config.json",config if isinstance(config,dict) else {"rejected_value":config})
        if json.dumps(config,sort_keys=True)!=json.dumps(CONFIG,sort_keys=True):
            raise ro.Refusal("REJECTED_CONFIG","frozen configuration changed")
        if source_commit is not None and not re.fullmatch(r"[0-9a-f]{40}",source_commit):
            raise ro.Refusal("REJECTED_CONFIG","source commit must be a full SHA")
        try:
            raw=raw_path.read_bytes()
        except OSError as e:
            raise ro.Refusal("BLOCKED_INPUT","raw unavailable") from e
        evidence["input_sha256"]=ro.sha256(raw)
        evidence["input_size_bytes"]=len(raw)
        pre_path=ROOT/"data/provenance/G2_MULTI_SUBJECT_PRECHECK.json"
        try:
            pre_bytes=pre_path.read_bytes(); pre=json.loads(pre_bytes)
        except (OSError,ValueError) as e:
            raise ro.Refusal("REJECTED_INPUT","precheck unavailable or invalid") from e
        ro.validate_precheck_shape(pre)
        evidence["precheck_sha256"]=ro.sha256(pre_bytes)
        if evidence["precheck_sha256"] != ro.PINNED_PRECHECK_SHA256:
            raise ro.Refusal("BLOCKED_IDENTITY","precheck hash differs")
        rows,selection=ro.validate_source(raw,ro.load_config(ROOT/"g2/configs/g2_readonly.json"),pre)
        # Validate the precise accepted reference serialization BEFORE publishing outputs.
        import io
        buf=io.StringIO(newline=""); w=csv.writer(buf,lineterminator="\n")
        w.writerow(("i","source_line","subject","activity","q","x","y","z"))
        for i,r in enumerate(rows): w.writerow((i,r.line,r.subject,r.activity,str(r.q),*r.axes_tokens))
        ref_bytes=buf.getvalue().encode()
        if ro.sha256(ref_bytes)!=REFERENCE_SHA:
            raise ro.Refusal("REPORT_MISMATCH","reference serialization differs from accepted G2.2")
        x=np.array([r.axes for r in rows],dtype=np.float64).T
        original=x.copy(); results=[]
        # Compute and check both branches before writing any successful plot/data.
        outputs=[]
        for alpha in CONFIG["alphas"]:
            obs,z=freeze(x,alpha,CONFIG["a"],CONFIG["b"])
            m=metrics(x,obs,z,CONFIG["a"],CONFIG["b"])
            if not m["outside_identical"] or m["L_out"]!=0 or not np.array_equal(x,original):
                raise ro.Refusal("INVARIANT_FAILURE","unintended changes")
            results.append({"alpha":alpha,**m}); outputs.append((alpha,obs,z))
        (output/"reference.csv").write_bytes(ref_bytes)
        ro.json_write(output/"selection.json",selection)
        for alpha,obs,z in outputs:
            dest=output/f"alpha_{alpha}";dest.mkdir()
            write_arrays(dest/"arrays.csv",rows,obs,z)
            plot(dest/"comparison.png",x,obs,z,alpha)
        with (output/"results.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(results[0]),lineterminator="\n");w.writeheader()
            for m in results:w.writerow({k:("null" if v is None else v) for k,v in m.items()})
        ro.json_write(output/"results.json",{"results":results})
        status={"status":"PASS_DEMO","checks":{"raw_identity":"PASS","reference_identity":"PASS","both_modes":"PASS","outside_mask_unchanged":"PASS","reference_unchanged":"PASS"}}
        evidence["reference_sha256"]=ro.sha256(ref_bytes)
        import matplotlib
        evidence["versions"]["matplotlib"]=matplotlib.__version__
    except ro.Refusal as e:
        status={"status":e.status,"detail":str(e)}
    ro.json_write(output/"validation.json",status)
    evidence["status"]=status["status"]
    evidence["files_sha256"]={str(p.relative_to(output)):ro.sha_file(p) for p in sorted(output.rglob("*")) if p.is_file()}
    ro.json_write(output/"provenance.json",evidence)
    return status


def main(argv=None):
    p=argparse.ArgumentParser(description="LAB-023 bounded G2.3 freeze demo")
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--config",type=Path,default=ROOT/"g23/configs/freeze.json")
    p.add_argument("--source-commit",help="full source SHA, recorded as declared, not automatically authenticated")
    args_list=list(sys.argv[1:] if argv is None else argv);args=p.parse_args(args_list)
    try:
        status=execute(args.input,args.output_dir,args.config,args.source_commit,[sys.executable,"-m","g23.freeze",*args_list])
    except ro.Refusal as e: status={"status":e.status,"detail":str(e)}
    print(json.dumps(status));return 0 if status["status"]=="PASS_DEMO" else 2

if __name__=="__main__": raise SystemExit(main())
