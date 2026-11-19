"""Exact LAB-042 comparison; audited numerical functions are imported unchanged."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
from explorations.repair_dynamics import core as c, run as r
from . import adapter as a, gate

HERE=Path(__file__).resolve().parent
CONFIG={"scope":"LAB042_FIXED_REAL_RECORDING","evaluation_authorized_by":"LAB-042","subject":1601,"activity":"A","N":4512,"source_first_line":1,"source_last_line":4512,"axis":0,"starts":[400,800,1200,1600,2000,2400,2800,3200],"lengths":[5,20,80,200],"ar_order":10,"ar_context":256,"methods":["Hold","Linear","AR(10)"],"seed":None,"mask":"oracle","primary_pair":"AR(10) - Linear","primary_L":200,"sign_tau":1e-10,"member_sha256":"cafe0c35079ce96909ad6a42b8a65af7349cd416350fe4d0aa78354bb68b20ff","view_sha256":"61f5cdd0f23ae5d3200b45109dbe5ef2a78bac498fc5815faa1341bd6a8bac0b","private_exposure_history":"UNKNOWN"}


def check_config(data):
    config=r.read_json(data)
    c.require(r.dump(config)==r.dump(CONFIG),"real configuration differs from frozen LAB-042 plan")
    return config


def compute(record):
    ref,q=record.ref,record.q
    c.validate_reference(ref,q)
    c.require(ref.shape==(3,record.pins.n),"wrong admitted shape")
    identity=record.metadata
    frozen=[]
    scenarios=[]
    # Phase 1: each prediction receives only an observed context, right boundary,
    # length and fixed algorithm. No metrics/references supplied to method.
    for L in c.LENGTHS:
        for s in c.STARTS:
            obs,z=c.inject(ref,q,s,L)
            item=dict(s=s,L=L,e=s+L,obs=obs,z=z,outputs={})
            for method in c.METHODS:
                item["outputs"][method]=r.frozen_prediction(obs,q,z,s,L,method)
            frozen.append(item)
            scenarios.append(dict(**identity,s=s,e=s+L,L=L,
                                  n_assigned=int(z.sum()),n_changed=int(np.count_nonzero(obs!=ref))))
    return frozen,scenarios


def evaluate(record,frozen):
    ref,q=record.ref,record.q
    results=[]; pairs=[]
    for item in frozen:
        s,L,e=item["s"],item["L"],item["e"]
        obs,z=item["obs"],item["z"]
        c.outside(ref,q,obs,q,z)
        rr={}
        for method in c.METHODS:
            out,meta,error=item["outputs"][method]
            row=dict(**record.metadata,s=s,e=e,L=L,method=method,status="OK",failure_reason=None)
            common=dict(E=None,E_reason="NUMERIC_FAILURE",A=None,A_reason="NUMERIC_FAILURE",
                        B=None,B_reason="NUMERIC_FAILURE",D=None,
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
    return sm,sp,d


def freeze_digest(frozen):
    h=hashlib.sha256()
    for item in frozen:
        h.update(r.dump({k:item[k] for k in ("s","e","L")}).encode())
        for field in ("obs","z"):
            c.require(not item[field].flags.writeable,"unfrozen observed/mask array")
            h.update(item[field].tobytes())
        for method in c.METHODS:
            output,meta,error=item["outputs"][method]
            h.update(r.dump([method,meta,error]).encode())
            if output is not None:
                c.require(not output.flags.writeable,"unfrozen prediction")
                h.update(output.tobytes())
    return h.hexdigest()


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
        ax.set(xlabel="Sample index (not seconds)",ylabel="Acceleration (m/s²)",
               title=f"WISDM 1601/A — controlled X freeze | s=1200, L={L}")
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
    fig.suptitle("WISDM 1601/A — one recording, 8 dependent starts")
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
           title="WISDM 1601/A, L=200: paired discrepancies\nupper left = lower RMSE, higher dynamics error")
    ax.grid(alpha=.15)
    fig.tight_layout()
    fig.savefig(out/"paired_L200.png",dpi=150)
    plt.close(fig)



def guard_before_io(gate_dir):
    proof=gate.verify(gate_dir)
    config=check_config((HERE/"config.json").read_bytes())
    return proof,config


def safe_out(out):
    c.require(not out.exists() or (out.is_dir() and not any(out.iterdir())),
              "output must be new or empty")
    out.mkdir(parents=True,exist_ok=True)


def status_for_error(exc):
    return "BLOCKED_IDENTITY" if isinstance(exc,a.IdentityError) else "INVALID_EXECUTION"


def execute(out,archive,gate_dir,receipt):
    safe_out(out)
    prov=dict(scope=CONFIG["scope"],status="INVALID_EXECUTION",seed=None,
              argv=sys.argv,private_exposure_history="UNKNOWN",limitation=a.LIMITATION,
              attribution=a.ATTRIBUTION,evaluation_authorized_by="LAB-042")
    try:
        proof,config=guard_before_io(gate_dir)
        acquisition=r.read_json(receipt.read_bytes())
        a.identity(acquisition.get("url")==a.URL and acquisition.get("http_status")==200
                   and acquisition.get("bytes_received")==a.ARCHIVE.outer_size and
                   acquisition.get("outer_sha256")==a.ARCHIVE.outer_sha,
                   "missing or inconsistent official acquisition receipt")
        env=gate.current()
        prov.update(env=env,gate_sha256=r.sha((gate_dir/"gate.json").read_bytes()),
                    pinned_inputs=a.check_sources(),acquisition=acquisition)
        record=a.load_archive(archive)
        p=record.pins
        prov["record_identity"]=dict(**record.metadata,member_sha256=p.member_sha,
              member_size_bytes=p.member_size,member_crc32=p.member_crc,
              raw_run_sha256=p.run_sha,raw_run_bytes=p.run_size,
              canonical_view_sha256=p.view_sha,canonical_view_bytes=p.view_size,
              outer_sha256=a.ARCHIVE.outer_sha,inner_sha256=a.ARCHIVE.inner_sha,
              q_first=str(p.q_first),q_last=str(p.q_last),timestamp_unit="UNKNOWN",
              reference_is_observed_not_guaranteed_fault_free=True)
        frozen,scenarios=compute(record)
        frozen_hash=freeze_digest(frozen)
        # First evaluation occurs only after all 96 predictions are frozen.
        results,pairs=evaluate(record,frozen)
        c.require(frozen_hash==freeze_digest(frozen),"prediction altered during evaluation")
        sm,sp,d=summarize(results,pairs)
        c.require(len(results)==len(pairs)==96 and len(scenarios)==32,"wrong frozen grid cardinality")
        ref,q=record.ref,record.q
        obs,z=c.inject(ref,q,400,0)
        noinj=c.metrics(ref,obs,q,q,z,400,0)
        decision=dict(scope=CONFIG["scope"],**record.metadata,**d,
                      private_exposure_history="UNKNOWN",limitation=a.LIMITATION,
                      independent_audit="PENDING_05")
        valid=dict(status="PASS_FIXED_COMPARISON" if d["plan_completeness"]=="COMPLETE_PLAN" else "INCOMPLETE_PLAN",
                   n_scenarios=32,n_method_rows=96,n_paired_rows=96,
                   no_injection=noinj,scope=CONFIG["scope"],
                   private_exposure_history="UNKNOWN",limitation=a.LIMITATION,
                   prediction_sha256_before_and_after_evaluation=frozen_hash,
                   identity_verified=True,independent_audit="PENDING_05")
        r.write_json(out/"config.json",config)
        (out/"frozen_admission_manifest.json").write_bytes((a.ROOT/r.ADMISSION).read_bytes())
        (out/"reference.csv").write_bytes(record.view)
        c.require(r.sha((out/"reference.csv").read_bytes())==p.view_sha,"written view pin mismatch")
        arrays=out/"arrays";arrays.mkdir()
        for item in frozen:
            s,L=item["s"],item["L"]
            obs,z=item["obs"],item["z"]
            values=[item["outputs"][m][0] for m in c.METHODS]
            r.write_csv(arrays/f"L{L}_s{s}.csv",
                       ["i","source_line","q","obs_x","obs_y","obs_z","Z_x","Z_y","Z_z",
                        "Hold_x","Linear_x","AR10_x"],
                       ((i,p.first+i,q[i],*obs[:,i],*map(int,z[:,i]),
                        *("null" if v is None else v[0,i] for v in values)) for i in range(p.n)))
        for name,rows in [("scenarios",scenarios),("results",results),("paired",pairs),
                          ("summary_methods",sm),("summary_paired",sp)]:
            (out/(name+".csv")).write_bytes(r.csv_bytes(rows))
            r.write_json(out/(name+".json"),rows)
        r.write_json(out/"decision.json",decision)
        plots(out,ref,frozen,sm,pairs)
        (out/"ATTRIBUTION.txt").write_text(a.ATTRIBUTION+"\n"+a.LIMITATION+
            "\nPrivate audit artifact only. Real recorded reference, artificial freeze, known oracle mask.\n"
            "Linear uses the right boundary; Hold and AR do not. No physical fault or population claims.\n"
            "q: original integer; unit/epoch UNKNOWN. Gap length and x-axis are indices, not seconds.\n",
            encoding="utf-8")
        r.write_json(out/"validation.json",valid)
        expected=r.output_hashes(out)
        r.verify_files(out,expected)
        prov.update(status=valid["status"],prediction_sha256=frozen_hash,files_sha256=expected)
        r.write_json(out/"provenance.json",prov)
        return valid
    except (c.InvalidExecution,c.NumericFailure,OSError,ValueError,TypeError,KeyError,
            zipfile.BadZipFile,UnicodeError,RuntimeError,OverflowError,subprocess.SubprocessError) as exc:
        for p in out.iterdir():
            shutil.rmtree(p) if p.is_dir() else p.unlink()
        valid=dict(status=status_for_error(exc),error=str(exc),scope=CONFIG["scope"],
                   **c.decision({},False,invalid=True),private_exposure_history="UNKNOWN")
        r.write_json(out/"validation.json",valid)
        prov.update(status=valid["status"],files_sha256=r.output_hashes(out))
        r.write_json(out/"provenance.json",prov)
        return valid


def main(argv=None):
    parser=argparse.ArgumentParser(description="LAB-042 fixed real-recording execution")
    sub=parser.add_subparsers(dest="command",required=True)
    for name in ("acquire","run"):
        subp=sub.add_parser(name)
        subp.add_argument("--archive",type=Path,required=True)
        subp.add_argument("--gate-dir",type=Path,required=True)
        subp.add_argument("--receipt",type=Path,required=True)
        if name=="run":
            subp.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=="acquire":
            guard_before_io(args.gate_dir)
            c.require(not args.receipt.exists(),"acquisition receipt already exists")
            info=a.acquire(args.archive)
            r.write_json(args.receipt,info)
            print(r.dump(info))
            return 0
        result=execute(args.output_dir,args.archive,args.gate_dir,args.receipt)
    except (c.InvalidExecution,OSError,ValueError,TypeError,KeyError,RuntimeError,zipfile.BadZipFile,subprocess.SubprocessError) as exc:
        # Acquisition failure cannot be interpreted as a comparison.
        result=dict(status=status_for_error(exc),error=str(exc),scope=CONFIG["scope"])
        if args.command=="acquire" and not args.receipt.exists():
            r.write_json(args.receipt,result)
    print(r.dump(result))
    return 0 if result.get("status")=="PASS_FIXED_COMPARISON" else 2


if __name__=="__main__":
    raise SystemExit(main())
