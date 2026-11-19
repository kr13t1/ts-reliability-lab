"""LAB-041 fixture-only runner. The real-data entry point is deliberately absent."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
from . import core as c

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CONTRACT = "docs/specs/REPAIR_DYNAMICS_PROTOCOL_v1.md"
ADMISSION = "data/provenance/REPAIR_DYNAMICS_ELIGIBILITY_MANIFEST_LAB040.json"
PINS = {CONTRACT: "7d5c0f21bbe63575ff3f7302460589791b03d7b5",
        ADMISSION: "393902a5dc113fb599932f2627593e1c295fc3e8"}
N = 3401
FIXTURE_SHA = "365757ca56a5486da6834450d44332921a31ff4741658de5a5c1cc6b930c34ea"
MEMBER = "synthetic/fixture.csv"
HEADER = ["subject","activity","source_line","q","x","y","z"]
CONFIG = dict(scope="SYNTHETIC_ONLY", evaluation_authorized=False, subject="SYNTHETIC",
              activity="A", axis=0, starts=list(c.STARTS), lengths=list(c.LENGTHS),
              ar_order=c.P, ar_context=c.C, methods=list(c.METHODS), seed=None,
              mask="oracle", primary_pair="AR(10) - Linear", primary_L=200,
              sign_tau=1e-10, fixture_sha256=FIXTURE_SHA)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git_blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+"\n"


def write_json(path,obj):
    path.write_bytes(dump(obj).encode("utf-8"))


def read_json(b):
    def pairs(items):
        out={}
        for k,v in items:
            c.require(k not in out,"duplicate JSON key")
            out[k]=v
        return out
    def bad_constant(value):
        raise c.InvalidExecution("nonfinite JSON constant: "+value)
    return json.loads(b, object_pairs_hook=pairs, parse_constant=bad_constant)


def check_pinned(path, blob):
    b = path.read_bytes()
    c.require(git_blob(b)==blob, "pinned source/admission identity mismatch: "+path.name)
    return b


def check_sources(root=ROOT):
    result={}
    for rel, pin in PINS.items():
        b=check_pinned(root/rel,pin)
        result[rel]={"git_blob_sha":pin,"sha256":sha(b)}
        if rel==ADMISSION:
            m=read_json(b)
            c.require(m.get("evaluation_authorized") is False and
                      m.get("fixture_gate_authorized") is False and
                      m.get("runner_authorized") is False,
                      "historical authorization flags changed")
    return result


def check_config(b):
    candidate=read_json(b)
    c.require(dump(candidate)==dump(CONFIG),"frozen config differs")
    return candidate


def generate_fixture():
    # Exact, deterministic integer waveform. No randomness or real measurements.
    def tri(i,p):
        return 4*abs(i%p-p//2)-p
    rows=[",".join(HEADER)+"\n"]
    for i in range(N):
        x=13*tri(i,40)+7*tri(i+3,14)+2*(i//200%4)*tri(i,26)+(i*73+19)%101-50
        y=5*tri(i,18)
        z=1000+3*tri(i+1,30)
        rows.append(f"SYNTHETIC,A,{i+1},{10000+7*i},{x/1000:.3f},{y/1000:.3f},{z/1000:.3f}\n")
    data="".join(rows).encode("ascii")
    c.require(sha(data)==FIXTURE_SHA,"compiled synthetic fixture identity mismatch")
    return data


def make_bundle(data=None, claimed=None):
    data=generate_fixture() if data is None else data
    f=io.BytesIO()
    with zipfile.ZipFile(f,"w",compression=zipfile.ZIP_STORED) as z:
        for name, b in [(MEMBER,data),("manifest.json",dump({"scope":"SYNTHETIC_ONLY",
                       "member":MEMBER,"sha256":claimed or sha(data)}).encode())]:
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0))
            z.writestr(info,b)
    return f.getvalue()


def parse_fixture(data):
    text=data.decode("ascii")
    reader=csv.reader(io.StringIO(text,newline=""),strict=True)
    c.require(next(reader,None)==HEADER,"incorrect fixture schema")
    axes=[]; q=[]
    for row in reader:
        i=len(q)+1
        c.require(len(row)==len(HEADER),"incorrect record width")
        subject, activity, line, stamp, *v=row
        c.require(subject=="SYNTHETIC" and activity=="A","wrong subject/activity/contiguity")
        c.require(line==str(i),"incorrect physical source row")
        c.require(re.fullmatch(r"[0-9]+",stamp) is not None,"malformed q")
        q.append(int(stamp))
        xyz=[float(a) for a in v]
        c.require(all(np.isfinite(xyz)),"NaN/Inf input")
        axes.append(xyz)
    c.require(len(q)==N and len(q)>=3401,"fixture truncated or extended")
    x=np.array(axes,dtype=np.float64).T.copy()
    c.validate_reference(x,tuple(q))
    return c.readonly(x),tuple(q)


def load_bundle(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names=z.namelist()
        c.require(len(names)==2 and sorted(names)==sorted([MEMBER,"manifest.json"]),
                  "missing/duplicate/unexpected member")
        c.require(z.getinfo(MEMBER).file_size<=200_000 and
                  z.getinfo("manifest.json").file_size<=4096,"fixture member too large")
        data=z.read(MEMBER)
        m=read_json(z.read("manifest.json"))
    c.require(m=={"scope":"SYNTHETIC_ONLY","member":MEMBER,"sha256":FIXTURE_SHA},
              "unapproved claimed SHA or fixture metadata")
    c.require(sha(data)==FIXTURE_SHA,"fixture bytes differ from independent compiled pin")
    return parse_fixture(data)


def csv_bytes(rows):
    c.require(bool(rows),"no rows")
    f=io.StringIO(newline="")
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow({k:"null" if v is None else json.dumps(v,allow_nan=False) if
                    isinstance(v,(list,dict,bool)) else v for k,v in row.items()})
    return f.getvalue().encode("utf-8")


def write_csv(path, header, rows):
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def frozen_prediction(obs,q,z,s,L,method):
    try:
        gap, meta=c.reconstruct(method,c.packet(obs,s,L))
        output=c.assemble(obs,q,z,s,L,gap)
        return output,meta,None
    except c.NumericFailure as exc:
        return None,dict(rank=None,singular_values=None,condition=None,
                         condition_reason="NUMERIC_FAILURE"),str(exc)


def compute(ref,q):
    c.validate_reference(ref,q)
    c.require(ref.shape==(3,N),"wrong fixture shape")
    frozen=[]
    scenarios=[]
    # Phase 1: each prediction receives only an observed context, right boundary,
    # length and fixed algorithm. No metrics/references supplied to method.
    for L in c.LENGTHS:
        for s in c.STARTS:
            obs,z=c.inject(ref,q,s,L)
            record=dict(s=s,L=L,e=s+L,obs=obs,z=z,outputs={})
            for method in c.METHODS:
                record["outputs"][method]=frozen_prediction(obs,q,z,s,L,method)
            frozen.append(record)
            scenarios.append(dict(subject="SYNTHETIC",run="fixture-1",s=s,e=s+L,L=L,
                                  n_assigned=int(z.sum()),n_changed=int(np.count_nonzero(obs!=ref)),
                                  source_first_line=1,source_last_line=N))
    return frozen,scenarios


def evaluate(ref,q,frozen):
    results=[]; pairs=[]
    for item in frozen:
        s,L,e=item["s"],item["L"],item["e"]
        obs,z=item["obs"],item["z"]
        c.outside(ref,q,obs,q,z)
        rr={}
        for method in c.METHODS:
            out,meta,error=item["outputs"][method]
            row=dict(subject="SYNTHETIC",run="fixture-1",source_first_line=1,
                     source_last_line=N,s=s,e=e,L=L,method=method,status="OK",failure_reason=None)
            common=dict(E=None,E_reason="NUMERIC_FAILURE",A=None,B=None,D=None,
                        D_reason="NUMERIC_FAILURE",V=None,V_reason="NUMERIC_FAILURE",
                        A_B_zero_flag=None,n_pairs=L-1,left_error=None,right_error=None,
                        outside_max=None,outside_identical=None)
            if error is None:
                try:
                    common=c.metrics(ref,out,q,q,z,s,L)
                except c.NumericFailure as exc:
                    error=str(exc)
            if error is not None:
                row.update(status="NUMERIC_FAILURE",failure_reason=error)
            row.update(common)
            row.update(meta)
            results.append(row)
            rr[method]=row
        for a,b in c.PAIRS:
            pairs.append(c.pair(rr[a],rr[b]))
    return results,pairs


def summarize(results,pairs):
    sm=[];sp=[]
    for L in c.LENGTHS:
        for m in c.METHODS:
            sm.append(c.method_summary([r for r in results if r["L"]==L and r["method"]==m]))
        for a,b in c.PAIRS:
            sp.append(c.paired_summary([r for r in pairs if r["L"]==L and r["pair"]==a+" - "+b]))
    primary=next(r for r in sp if r["L"]==200 and r["pair"]=="AR(10) - Linear")
    d=c.decision(primary,all(r["status"]=="OK" for r in results))
    return sm,sp,dict(scope="SYNTHETIC_ONLY",evaluation_authorized=False,
                      hypothetical_rule_only=True,**d)


def plots(out,ref,frozen,summary,pairs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for L in (20,200):
        item=next(r for r in frozen if r["s"]==1200 and r["L"]==L)
        s,e=item["s"],item["e"]
        idx=np.arange(s-15,e+16)
        fig,ax=plt.subplots(figsize=(10,4.2))
        ax.plot(idx,ref[0,idx],color="#202632",lw=2,label="Reference")
        ax.plot(idx,item["obs"][0,idx],color="#999999",lw=1.2,ls=":",label="Frozen observation")
        for m,color in zip(c.METHODS,("#D18732","#2878B5","#1A9274")):
            x,_,err=item["outputs"][m]
            if err is None:
                ax.plot(idx,x[0,idx],label=m,color=color,lw=1.4,ls="--" if m=="Hold" else "-")
            else:
                ax.plot([],[],label=m+" FAILURE",color=color)
        ax.axvspan(s-.5,e-.5,color="#F4B860",alpha=.14,label="Assigned gap")
        ax.set(xlabel="Sample index (not seconds)",ylabel="Synthetic amplitude",
               title=f"SYNTHETIC FIXTURE ONLY | s=1200, L={L}")
        ax.legend(ncol=3,fontsize=8)
        ax.grid(alpha=.18)
        fig.tight_layout()
        fig.savefig(out/f"repair_s1200_L{L}.png",dpi=150)
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for method,color in zip(c.METHODS,("#D18732","#2878B5","#1A9274")):
        rr=[r for r in summary if r["method"]==method]
        for ax,key in zip(axes,("mean_E","mean_D")):
            ax.plot([r["L"] for r in rr],[r[key] for r in rr],marker="o",label=method,color=color)
    for ax,title in zip(axes,("Mean masked RMSE E","Mean first-difference error D")):
        ax.set(xlabel="Gap length (samples)",title=title)
        ax.set_xticks(c.LENGTHS)
        ax.grid(alpha=.2)
    axes[0].legend()
    fig.suptitle("Synthetic fixture only — descriptive means, 8 dependent starts")
    fig.tight_layout()
    fig.savefig(out/"comparison.png",dpi=150)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4.8))
    ax.axhline(0,color=".6");ax.axvline(0,color=".6")
    primary=[r for r in pairs if r["L"]==200 and r["pair"]=="AR(10) - Linear"]
    for r in primary:
        if r["delta_E"] is not None and r["delta_D"] is not None:
            ax.scatter(r["delta_E"],r["delta_D"],color="#2878B5")
            ax.annotate(str(r["s"]),(r["delta_E"],r["delta_D"]),fontsize=8,xytext=(4,4),textcoords="offset points")
    ax.set(xlabel="E_AR − E_Linear",ylabel="D_AR − D_Linear",
           title="Synthetic L=200: paired discrepancies\nupper left = lower RMSE, higher dynamics error")
    ax.grid(alpha=.15)
    fig.tight_layout()
    fig.savefig(out/"paired_L200.png",dpi=150)
    plt.close(fig)


def verify_files(out,expected):
    # expected lives outside the edited output manifest (trusted in-memory generation
    # or independently re-executed reference); a self-declared digest is insufficient.
    actual={p.relative_to(out).as_posix():sha(p.read_bytes()) for p in out.rglob("*")
            if p.is_file() and p.name!="provenance.json"}
    c.require(actual==expected,"output substitution or missing/extra artifact")


def output_hashes(out):
    return {p.relative_to(out).as_posix():sha(p.read_bytes()) for p in out.rglob("*")
            if p.is_file() and p.name!="provenance.json"}


def evidence():
    import matplotlib
    buf=io.StringIO()
    from contextlib import redirect_stdout
    with redirect_stdout(buf):
        np.show_config()
    try:
        head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,
                            text=True,check=True,timeout=3).stdout.strip()
    except (OSError,subprocess.SubprocessError):
        head=None
    return dict(scope="SYNTHETIC_ONLY",evaluation_authorized=False,seed=None,
                argv=sys.argv,python=platform.python_version(),numpy=np.__version__,
                matplotlib=matplotlib.__version__,platform=platform.platform(),
                blas=buf.getvalue(),threads={k:os.environ.get(k) for k in
                 ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS")},
                optimize=sys.flags.optimize,git_sha=head,
                source_sha256={p.name:sha(p.read_bytes()) for p in sorted(HERE.glob("*.py"))})


def execute(out,bundle=None,config_bytes=None,root=ROOT):
    if out.exists():
        c.require(out.is_dir() and not any(out.iterdir()),"output must be new or empty")
    out.mkdir(parents=True,exist_ok=True)
    prov=evidence()
    try:
        c.require(np.__version__=="2.3.5" and prov["matplotlib"]=="3.10.8" and
                  prov["python"]=="3.13.5","environment differs from pinned versions")
        prov["pinned_inputs"]=check_sources(root)
        cfg=check_config((HERE/"config.json").read_bytes() if config_bytes is None else config_bytes)
        data=make_bundle() if bundle is None else bundle
        ref,q=load_bundle(data)
        prov.update(fixture_sha256=FIXTURE_SHA,fixture_bundle_sha256=sha(data))
        frozen,scenarios=compute(ref,q)
        # Verify the no-injection path separately; never add a 97th method row.
        obs,z=c.inject(ref,q,400,0)
        noinj=c.metrics(ref,obs,q,q,z,400,0)
        # Predictions for every scenario are frozen before evaluation.
        results,pairs=evaluate(ref,q,frozen)
        sm,sp,d=summarize(results,pairs)
        c.require(len(results)==len(pairs)==96 and len(scenarios)==32,"plan cardinality mismatch")
        valid=dict(status="PASS_SYNTHETIC_FIXTURE" if d["plan_completeness"]=="COMPLETE_PLAN"
                   else "INCOMPLETE_PLAN",scope="SYNTHETIC_ONLY",no_injection=noinj,
                   n_scenarios=32,n_method_rows=96,n_paired_rows=96,evaluation_authorized=False)
        write_json(out/"config.json",cfg)
        (out/"frozen_admission_manifest.json").write_bytes(check_pinned(root/ADMISSION,PINS[ADMISSION]))
        (out/"fixture.csv").write_bytes(generate_fixture())
        write_csv(out/"reference.csv",["i","source_line","q","x","y","z"],
                  ((i,i+1,q[i],*ref[:,i]) for i in range(N)))
        for item in frozen:
            s,L=item["s"],item["L"]
            obs,z=item["obs"],item["z"]
            p=out/"arrays"
            p.mkdir(exist_ok=True)
            values=[item["outputs"][m][0] for m in c.METHODS]
            write_csv(p/f"L{L}_s{s}.csv",
                      ["i","source_line","q","obs_x","obs_y","obs_z","Z_x","Z_y","Z_z",
                       "Hold_x","Linear_x","AR10_x"],
                      ((i,i+1,q[i],*obs[:,i],*map(int,z[:,i]),
                        *("null" if v is None else v[0,i] for v in values)) for i in range(N)))
        for name,rows in [("scenarios",scenarios),("results",results),("paired",pairs),
                          ("summary_methods",sm),("summary_paired",sp)]:
            (out/(name+".csv")).write_bytes(csv_bytes(rows))
            write_json(out/(name+".json"),rows)
        write_json(out/"decision.json",d)
        # No scientific result; image generation is a view of the frozen arrays.
        plots(out,ref,frozen,sm,pairs)
        write_json(out/"validation.json",valid)
        expected=output_hashes(out)
        verify_files(out,expected)
        prov["files_sha256"]=expected
        prov["status"]=valid["status"]
        write_json(out/"provenance.json",prov)
        return valid
    except (c.InvalidExecution,c.NumericFailure,OSError,ValueError,TypeError,KeyError,
            csv.Error,zipfile.BadZipFile,UnicodeError,StopIteration) as exc:
        # New output folder belongs to this run; remove partial success outputs.
        import shutil
        for p in out.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        valid=dict(status="INVALID_EXECUTION",detail=str(exc),scope="SYNTHETIC_ONLY",
                   evaluation_authorized=False,**c.decision({},False,invalid=True))
        write_json(out/"validation.json",valid)
        prov.update(status=valid["status"],files_sha256=output_hashes(out))
        write_json(out/"provenance.json",prov)
        return valid


def main(argv=None):
    parser=argparse.ArgumentParser(description="SYNTHETIC ONLY; no real-data evaluation entry point")
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        r=execute(args.output_dir)
    except (c.InvalidExecution,OSError) as exc:
        r={"status":"INVALID_EXECUTION","detail":str(exc)}
    print(json.dumps(r,ensure_ascii=False,allow_nan=False))
    return 0 if r["status"]=="PASS_SYNTHETIC_FIXTURE" else 2


if __name__=="__main__":
    raise SystemExit(main())
