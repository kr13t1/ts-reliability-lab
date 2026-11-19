"""Fixture gate and source/environment freeze. No real-data I/O."""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from explorations.repair_dynamics import core as c, run as r
from . import adapter as a

HERE=Path(__file__).resolve().parent
PKG="explorations/repair_dynamics_real"
SUITES={"accepted":"explorations/repair_dynamics/tests","adapter":PKG+"/tests"}


def git(*args):
    return subprocess.run(["git",*args],cwd=a.ROOT,check=True,
                          capture_output=True,text=True,timeout=10).stdout.strip()


def current():
    e=r.evidence()
    c.require(e["python"]=="3.13.5" and e["numpy"]=="2.3.5" and
              e["matplotlib"]=="3.10.8" and sys.platform=="linux" and
              e["blas_identity"].get("name")=="scipy-openblas" and
              e["blas_identity"].get("version")=="0.3.30" and
              all(v=="1" for v in e["threads"].values()) and
              __import__("platform").machine()=="x86_64", "environment differs from accepted LAB-041")
    head=git("rev-parse","HEAD")
    expected=os.environ.get("LAB042_EXPECTED_HEAD")
    c.require(expected is not None and head==expected,"checkout is not the exact PR head")
    # Existing repository files unrelated to this experiment may be modified
    # by the runner. Record status (do not claim a wholly clean checkout).
    # Fail closed on EVERY executable/package/test/config/authority byte
    # against HEAD, including all accepted fixture paths, not a global boolean.
    status=git("status","--porcelain","--untracked-files=no")
    paths=git("ls-files",PKG,"explorations/repair_dynamics",
              "explorations/__init__.py",".github/workflows/repair-dynamics-real.yml").splitlines()
    c.require(Path(c.__file__).resolve()==a.ROOT/"explorations/repair_dynamics/core.py"
              and Path(r.__file__).resolve()==a.ROOT/"explorations/repair_dynamics/run.py"
              and Path(a.__file__).resolve()==HERE/"adapter.py",
              "unexpected imported implementation path")
    c.require(PKG+"/adapter.py" in paths and PKG+"/run.py" in paths
              and PKG+"/tests/test_adapter.py" in paths and PKG+"/config.json" in paths,
              "not a frozen implementation checkout")
    sources={}
    for rel in sorted(set(paths)|set(a.PINS)):
        b=(a.ROOT/rel).read_bytes()
        c.require(r.git_blob(b)==git("rev-parse","HEAD:"+rel),"working source differs from HEAD")
        sources[rel]=r.sha(b)
    a.check_sources()
    pip=subprocess.run([sys.executable,"-m","pip","freeze"],check=True,
                       capture_output=True,text=True,timeout=30).stdout
    return dict(git_sha=head,sources_sha256=sources,tracked_status=status,
                environment={k:e[k] for k in ("python","numpy","matplotlib","platform",
                                               "blas_identity","threads","blas")},
                pip_freeze=pip)


def gate_status(log):
    m=re.search(r"^Ran ([0-9]+) tests? in ",log,re.M)
    c.require(m is not None and re.search(r"^OK$",log,re.M) is not None and
              not re.search(r"(?i)\b(skipped|expected failures|unexpected successes)\b",log),
              "mandatory tests failed, skipped or absent")
    return int(m.group(1))


def execute(out):
    c.require(not out.exists(),"fixture evidence directory already exists")
    out.mkdir(parents=True)
    frozen=current()
    evidence={}
    success=True
    for mode in (0,1):
        for name,path in SUITES.items():
            cmd=[sys.executable]+(["-O"] if mode else [])+[
                "-m","unittest","discover","-s",path,"-v"]
            proc=subprocess.run(cmd,cwd=a.ROOT,env=os.environ|{"EXPECTED_OPTIMIZE":str(mode)},
                                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=False)
            log=proc.stdout
            filename=f"{name}_{mode}.log"
            (out/filename).write_text(log,encoding="utf-8")
            print(filename,flush=True); print(log,flush=True)
            count=None
            try:
                count=gate_status(log)
                c.require(count >= (23 if name=="accepted" else 10),"test count smaller than required")
            except c.InvalidExecution:
                success=False
            success=success and proc.returncode==0
            evidence[filename]=dict(exit=proc.returncode,count=count,mode=mode,
                                    sha256=r.sha((out/filename).read_bytes()),argv=cmd)
    c.require(current()==frozen,"source/environment changed across fixture gate")
    report=dict(status="PASS_PRE_TARGET_FIXTURE_GATE" if success else "INVALID_EXECUTION",
                scope="SYNTHETIC_ONLY",**frozen,tests=evidence)
    r.write_json(out/"gate.json",report)
    print(r.dump({k:report[k] for k in ("status","git_sha","tests")}),flush=True)
    return 0 if success else 2


def verify(out):
    proof=r.read_json((out/"gate.json").read_bytes())
    c.require(proof["status"]=="PASS_PRE_TARGET_FIXTURE_GATE" and proof["scope"]=="SYNTHETIC_ONLY",
              "pre-target gate not passed")
    c.require(all(proof[k]==v for k,v in current().items()),"gate does not match frozen source/environment")
    expected={f"{name}_{mode}.log" for name in SUITES for mode in (0,1)}
    c.require(set(proof["tests"])==expected,"missing gate evidence")
    for filename in expected:
        info=proof["tests"][filename]
        b=(out/filename).read_bytes()
        mode=int(filename[-5])
        c.require(type(info["exit"]) is int and info["exit"]==0 and
                  type(info["mode"]) is int and info["mode"]==mode and
                  type(info["count"]) is int and info["count"]==gate_status(b.decode()) and
                  info["count"] >= (23 if filename.startswith("accepted") else 10) and
                  info["sha256"]==r.sha(b),"invalid gate evidence")
    return proof


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output-dir",type=Path,required=True)
    raise SystemExit(execute(p.parse_args().output_dir))
