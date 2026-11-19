import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import numpy as np
from explorations.repair_dynamics import core as c, run as r


def fixture_with_gap(x, y):
    ref = np.zeros((3, 300), dtype=np.float64)
    s, L = 256, len(x)
    ref[0,s:s+L] = x
    q = tuple(range(300))
    obs, z = c.inject(ref,q,s,L)
    out = c.assemble(obs,q,z,s,L,np.array(y,dtype=np.float64))
    return c.metrics(ref,out,q,q,z,s,L)


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = r.generate_fixture()
        cls.bundle = r.make_bundle()

    def test_execution_mode(self):
        expected = int(os.environ.get("EXPECTED_OPTIMIZE",str(sys.flags.optimize)))
        self.assertEqual(sys.flags.optimize,expected)
        self.assertIn(expected,(0,1))

    def test_authentic_fixture_and_sources(self):
        x,q=r.load_bundle(self.bundle)
        self.assertEqual(x.shape,(3,r.N))
        self.assertEqual(q[0],10000)
        self.assertEqual(r.sha(self.original),r.FIXTURE_SHA)
        self.assertFalse(x.flags.writeable)
        self.assertEqual(set(r.check_sources()),set(r.PINS))
        self.assertEqual(r.check_config((r.HERE/"config.json").read_bytes()),r.CONFIG)

    def test_byte_and_self_rehashed_tamper(self):
        lines=self.original.splitlines(keepends=True)
        # Change exactly one digit in the first amplitude.
        row=lines[1].split(b",")
        v=bytearray(row[4])
        v[-1]=ord("0") if v[-1]!=ord("0") else ord("1")
        row[4]=bytes(v)
        lines[1]=b",".join(row)
        bad=b"".join(lines)
        self.assertEqual(len(bad),len(self.original))
        self.assertEqual(sum(a!=b for a,b in zip(bad,self.original)),1)
        for claimed in (r.FIXTURE_SHA,r.sha(bad)):
            with self.subTest(claimed=claimed), self.assertRaises(c.InvalidExecution):
                r.load_bundle(r.make_bundle(bad,claimed))
        with self.assertRaises(c.InvalidExecution):
            r.load_bundle(r.make_bundle(self.original,"0"*64))

    def test_missing_duplicate_unexpected_member(self):
        for names in ([], [r.MEMBER], [r.MEMBER,r.MEMBER,"manifest.json"],
                      [r.MEMBER,"manifest.json","extra"]):
            with self.subTest(names=names):
                f=io.BytesIO()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore",UserWarning)
                    with zipfile.ZipFile(f,"w") as z:
                        for n in names:
                            z.writestr(n,self.original if n==r.MEMBER else b"{}")
                with self.assertRaises(c.InvalidExecution):
                    r.load_bundle(f.getvalue())

    def test_invalid_schema_subject_activity_source_line_q_finite_length(self):
        source=self.original.decode().splitlines()
        cases=[]
        cases.append(["bad,activity,source_line,q,x,y,z"]+source[1:])
        cases.append(source[:-1])
        for column,value in [(0,"1601"),(1,"B"),(2,"9"),(3,"1e4"),(3,"10000"),(4,"nan"),(5,"inf")]:
            changed=source.copy()
            fields=changed[2].split(","); fields[column]=value
            changed[2]=",".join(fields); cases.append(changed)
        for i,lines in enumerate(cases):
            bad=("\n".join(lines)+"\n").encode()
            with self.subTest(i=i),self.assertRaises(c.InvalidExecution):
                r.parse_fixture(bad)
            with self.assertRaises(c.InvalidExecution):
                r.load_bundle(r.make_bundle(bad,r.sha(bad)))

    def test_invalid_config_and_authorizations(self):
        for key,value in [("ar_order",9),("ar_context",255),("starts",[399]),("lengths",[7]),
                          ("axis",1),("evaluation_authorized",True),("subject",1601),
                          ("sign_tau",0.),("seed",1),("ar_order",10.0)]:
            with self.subTest(key=key,value=value),self.assertRaises(c.InvalidExecution):
                r.check_config(r.dump(r.CONFIG|{key:value}).encode())
        with self.assertRaises(c.InvalidExecution):
            r.read_json(b'{"axis":0,"axis":1}')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in r.PINS:
                p=root/rel; p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r.ROOT/rel).read_bytes())
            self.assertEqual(set(r.check_sources(root)),set(r.PINS))
            p=root/r.ADMISSION
            obj=json.loads(p.read_bytes());obj["evaluation_authorized"]=True
            p.write_text(json.dumps(obj))
            with self.assertRaises(c.InvalidExecution):
                r.check_sources(root)

    def test_invalid_bounds_and_outside(self):
        ref,q=r.load_bundle(self.bundle)
        for s,L in [(255,5),(3400,1),(400,-1),(400,3001),(400.0,1)]:
            with self.assertRaises(c.InvalidExecution):
                c.inject(ref,q,s,L)
        obs,z=c.inject(ref,q,400,5)
        for a,i in [(0,399),(0,405),(1,401),(2,401)]:
            bad=obs.copy();bad[a,i]+=1
            with self.assertRaises(c.InvalidExecution):
                c.metrics(ref,bad,q,q,z,400,5)
        with self.assertRaises(c.InvalidExecution):
            c.metrics(ref,obs,q,q[:-1]+(q[-1]+1,),z,400,5)
        badz=z.copy();badz[0,400]=False
        with self.assertRaises(c.InvalidExecution):
            c.assemble(obs,q,badz,400,5,np.ones(5))

    def test_fatal_output_policy_and_nonempty(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            for name,kw in [("bad_config",{"config_bytes":b"{}"}),
                            ("bad_bundle",{"bundle":r.make_bundle(self.original+b"!",r.FIXTURE_SHA)})]:
                out=base/name
                status=r.execute(out,**kw)
                self.assertEqual(status["status"],"INVALID_EXECUTION")
                self.assertEqual(status["completed_plan_status"],"INVALID_EXECUTION")
                self.assertEqual({p.name for p in out.iterdir()},{"validation.json","provenance.json"})
                self.assertEqual(json.loads((out/"provenance.json").read_bytes())["status"],"INVALID_EXECUTION")
            existing=base/"existing";existing.mkdir();p=existing/"keep";p.write_text("keep")
            with self.assertRaises(c.InvalidExecution):
                r.execute(existing)
            self.assertEqual(p.read_text(),"keep")
            self.assertEqual(list(existing.iterdir()),[p])
            # CLI refuses nonempty output with nonzero exit, including under -O.
            cmd=[sys.executable]+(["-O"] if sys.flags.optimize else [])+[
                "-m","explorations.repair_dynamics.run","--output-dir",str(existing)]
            proc=subprocess.run(cmd,cwd=r.ROOT,capture_output=True,text=True,check=False)
            self.assertEqual(proc.returncode,2,proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["status"],"INVALID_EXECUTION")

    def test_output_forgery_external_pin(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); target=p/"results.csv";target.write_bytes(b"original\n")
            trusted=r.output_hashes(p)
            r.write_json(p/"provenance.json",{"files_sha256":trusted})
            r.verify_files(p,trusted)
            target.write_bytes(b"forged\n")
            r.write_json(p/"provenance.json",{"files_sha256":r.output_hashes(p)})
            with self.assertRaises(c.InvalidExecution):
                r.verify_files(p,trusted)


class MethodTests(unittest.TestCase):
    def test_hold_linear_exact_ramp_and_no_injection(self):
        x=np.tile(np.arange(3401,dtype=np.float64),(3,1))
        q=tuple(range(3401))
        obs,z=c.inject(x,q,400,20)
        p=c.packet(obs,400,20)
        hold,_=c.reconstruct("Hold",p)
        linear,_=c.reconstruct("Linear",p)
        self.assertTrue(np.array_equal(hold,obs[0,400:420]))
        self.assertTrue(np.array_equal(linear,x[0,400:420]))
        for m in c.METHODS:
            o,z=c.inject(x,q,400,0)
            g,_=c.reconstruct(m,c.packet(o,400,0))
            result=c.assemble(o,q,z,400,0,g)
            self.assertTrue(np.array_equal(result,x))
            self.assertEqual(c.metrics(x,result,q,q,z,400,0)["D_reason"],"NO_INJECTION")

    def test_ar_constant_rank_deficiency_and_design(self):
        h=np.full(256,2.,dtype=np.float64)
        a,t=c.ar_design(h)
        self.assertEqual(a.shape,(246,11))
        self.assertEqual(t.shape,(246,))
        p=c.Packet(h,500.,20)
        out,meta=c.reconstruct("AR(10)",p)
        self.assertTrue(np.allclose(out,2.,rtol=1e-10,atol=1e-10))
        self.assertLess(meta["rank"],11)
        self.assertEqual(len(meta["singular_values"]),11)
        a,t=c.ar_design(np.arange(256,dtype=np.float64))
        np.testing.assert_array_equal(a[0],np.r_[1.,np.arange(10)])
        np.testing.assert_array_equal(a[-1],np.r_[1.,np.arange(245,255)])
        self.assertEqual(t[-1],255)

    def test_recursive_oldest_newest_and_hidden_reference_independence(self):
        beta=np.zeros(11);beta[0]=1;beta[1]=.3;beta[-1]=.2
        h=np.arange(10,dtype=np.float64)
        manual=h.tolist()
        for _ in range(25):
            manual.append(1+.3*manual[-10]+.2*manual[-1])
        np.testing.assert_allclose(c.recursive(beta,h,25),manual[10:],atol=1e-12,rtol=1e-12)
        ref,q=r.load_bundle(r.make_bundle())
        hidden=ref.copy();hidden[0,400:420]+=123
        o1,z1=c.inject(ref,q,400,20)
        o2,z2=c.inject(hidden,q,400,20)
        self.assertTrue(np.array_equal(o1,o2))
        other=ref.copy();other[0,420]+=10
        o3,_=c.inject(other,q,400,20)
        for method in c.METHODS:
            a,_=c.reconstruct(method,c.packet(o1,400,20))
            b,_=c.reconstruct(method,c.packet(o2,400,20))
            d,_=c.reconstruct(method,c.packet(o3,400,20))
            np.testing.assert_array_equal(a,b)
            self.assertEqual(np.array_equal(a,d),method!="Linear")
            self.assertFalse(a.flags.writeable)
            # A different scenario cannot mutate or warm-start the current one.
            alt,z=c.inject(ref,q,800,80)
            c.reconstruct(method,c.packet(alt,800,80))
            b,_=c.reconstruct(method,c.packet(o1,400,20))
            np.testing.assert_array_equal(a,b)
            output=c.assemble(o1,q,z1,400,20,a)
            np.testing.assert_array_equal(output[~z1],ref[~z1])

    def test_solver_and_nonfinite_failure_no_fallback(self):
        p=c.Packet(np.ones(256),0.,20)
        with patch.object(np.linalg,"lstsq",side_effect=np.linalg.LinAlgError("fixture failure")):
            with self.assertRaises(c.NumericFailure):
                c.reconstruct("AR(10)",p)
        with patch.object(np.linalg,"lstsq",return_value=(np.full(11,np.inf),None,1,np.ones(11))):
            with self.assertRaises(c.NumericFailure):
                c.reconstruct("AR(10)",p)


class MetricTests(unittest.TestCase):
    def test_manual_counterexample(self):
        x=[0,1,0,1]
        p=fixture_with_gap(x,[.25,.75,.25,.75]);q=fixture_with_gap(x,[1,2,1,2])
        self.assertEqual((p["E"],p["A"],p["B"],p["D"]),(.25,.5,1.,.5))
        self.assertEqual((q["E"],q["D"]),(1.,0.))
        self.assertLess(p["E"],q["E"]);self.assertGreater(p["D"],q["D"])
        self.assertEqual((p["left_error"],p["right_error"]),(.25,.25))
        self.assertAlmostEqual(p["V"],.25)

    def test_exact_constant_short_and_zero_reference(self):
        m=fixture_with_gap([0,1,0,1],[0,1,0,1])
        self.assertEqual((m["E"],m["D"],m["V"]),(0.,0.,1.))
        m=fixture_with_gap([0,1,0,1],[7]*4)
        self.assertEqual((m["D"],m["V"]),(1.,0.))
        m=fixture_with_gap([2],[3])
        self.assertEqual(m["E"],1.)
        self.assertEqual(m["D_reason"],"INSUFFICIENT_PAIRS")
        self.assertEqual(m["V_reason"],"INSUFFICIENT_PAIRS")
        self.assertIsNone(m["A"]);self.assertIsNone(m["B"]);self.assertEqual(m["n_pairs"],0)
        for y,flag in [([2]*4,"A_ZERO"),([1,2,1,2],"A_POSITIVE")]:
            m=fixture_with_gap([2]*4,y)
            self.assertIsNone(m["D"]);self.assertEqual(m["B"],0.)
            self.assertEqual(m["D_reason"],"ZERO_REFERENCE_DIFFERENCES")
            self.assertEqual(m["A_B_zero_flag"],flag)
            self.assertEqual(m["V_reason"],"ZERO_REFERENCE_VARIANCE")
        m=fixture_with_gap([],[])
        self.assertIsNone(m["E"]);self.assertEqual(m["E_reason"],"NO_INJECTION")

    def test_small_positive_b_and_scaled_rms(self):
        m=fixture_with_gap([0,1e-300,0,1e-300],[0]*4)
        self.assertGreater(m["B"],0.);self.assertEqual(m["D"],1.)
        self.assertEqual(c.rms(np.array([1e300,-1e300])),1e300)
        self.assertEqual(c.rms(np.array([1e-300,-1e-300])),1e-300)
        with self.assertRaises(c.NumericFailure):
            fixture_with_gap([-1e308,1e308],[1e308,-1e308])

    def test_sign_ties_exact_agreement(self):
        self.assertEqual([c.sign(x) for x in [-1.05e-10,-1e-10,0,1e-10,1.05e-10,None]],
                         ["-","tie","tie","tie","+","undefined"])
        c.compare_evidence({"value":-1.05e-10,"sign":"-"},{"value":-0.95e-10,"sign":"-"})
        with self.assertRaises(c.InvalidExecution):
            c.compare_evidence({"value":-1.05e-10,"sign":"-"},{"value":-0.95e-10,"sign":"tie"})
        for a,b in [(8,7),(None,0),("COMPLETE_PLAN","INCOMPLETE_PLAN"),(True,1)]:
            with self.assertRaises(c.InvalidExecution):
                c.compare_evidence(a,b)

    def test_delta_discrete_evidence_type_confusion(self):
        c.compare_evidence({"n_valid":8,"rank":10,"s":400,"E":1.0,"D":None},
                           {"n_valid":8,"rank":10,"s":400,"E":1.0000000001,"D":None})
        c.compare_evidence({"rank":None,"joint_discordance":True},
                           {"rank":None,"joint_discordance":True})
        for key,a,b in [
            ("n_valid",8,8.0000000001), ("n_valid",0,5e-11), ("n_valid",8,8.0),
            ("n_valid",8.0,8), ("n_valid",8.0,8.0), ("n_valid",True,True),
            ("rank",10,10.0), ("rank",10.0,10.0), ("rank",None,0),
            ("s",400,400.0), ("e",405,406), ("source_first_line",1,1.0),
            ("E_tie",0,0.0), ("joint_count",1,1.00000000001),
            ("joint_discordance",True,1), ("D",None,0.0),
            ("status","OK","UNDEFINED"), ("sign_E","-","tie"),
            ("completed_plan_status","COMPLETE_PLAN","INCOMPLETE_PLAN"),
        ]:
            with self.subTest(key=key,a=a,b=b), self.assertRaises(c.InvalidExecution):
                c.compare_evidence({"rows":[{key:a}]},{"rows":[{key:b}]})
        for a,b in [(1.0,1.001),(float("inf"),float("inf")),
                    (float("nan"),float("nan"))]:
            with self.assertRaises(c.InvalidExecution):
                c.compare_evidence(a,b)

    def test_delta_pair_requires_complete_typed_record_identity(self):
        base=dict(subject="SYNTHETIC",run="fixture-1",source_first_line=1,
                  source_last_line=3401,s=400,e=405,L=5,status="OK",E=1.,D=2.)
        a=base|dict(method="AR(10)")
        b=base|dict(method="Linear",E=2.,D=1.)
        p=c.pair(a,b)
        self.assertEqual((p["delta_E"],p["delta_D"],p["joint_discordance"]),(-1.,1.,True))
        self.assertEqual((p["source_first_line"],p["source_last_line"]),(1,3401))
        for bad in [
            b|{"subject":"OTHER"}, b|{"run":"other"},
            b|{"source_first_line":2}, b|{"source_last_line":3402},
            b|{"s":800,"e":805}, b|{"L":20,"e":420},
            b|{"e":406}, b|{"s":400.0}, b|{"L":True},
            b|{"source_last_line":3401.0}, b|{"method":"AR(10)"},
            b|{"method":"UNKNOWN"}, {k:v for k,v in b.items() if k!="source_last_line"},
        ]:
            with self.subTest(bad=bad), self.assertRaises(c.InvalidExecution):
                c.pair(a,bad)
        with self.assertRaises(c.InvalidExecution):
            c.pair(a|{"e":406},b|{"e":406})
        with self.assertRaises(c.InvalidExecution):
            c.pair(a|{"subject":1},b|{"subject":True})
        with self.assertRaises(c.InvalidExecution):
            c.pair(b,a)

    def test_delta_summary_rejects_mixed_records_lengths_and_labels(self):
        methods=[];pairs=[]
        for s in c.STARTS:
            base=dict(subject="SYNTHETIC",run="fixture-1",source_first_line=1,
                      source_last_line=3401,s=s,e=s+5,L=5,status="OK",E=1.,D=2.)
            a=base|dict(method="AR(10)")
            b=base|dict(method="Linear",E=2.,D=1.)
            methods.append(a);pairs.append(c.pair(a,b))
        self.assertEqual(c.method_summary(methods)["n_total"],8)
        self.assertEqual(c.paired_summary(pairs)["n_valid"],8)
        for rows,func,key,other in [(methods,c.method_summary,"method","Hold"),
                                    (pairs,c.paired_summary,"pair","AR(10) - Hold")]:
            for change in [{"subject":"OTHER"},{"run":"other"},{"source_first_line":2},
                           {"source_last_line":3402},{"L":20,"e":rows[0]["s"]+20},
                           {"e":rows[0]["e"]+1},{key:other},{"s":400.0}]:
                with self.subTest(key=key,change=change), self.assertRaises(c.InvalidExecution):
                    func([rows[0]|change]+rows[1:])

    def test_paired_denominators_and_decision_precedence(self):
        rows=[]
        for s in c.STARTS:
            base=dict(s=s,e=s+200,L=200,subject="SYNTHETIC",run="f",status="OK",
                      source_first_line=1,source_last_line=3401)
            ar=base|dict(method="AR(10)",E=1.,D=2.)
            lin=base|dict(method="Linear",E=2.,D=1.)
            rows.append(c.pair(ar,lin))
        p=c.paired_summary(rows)
        self.assertEqual((p["n_valid"],p["joint_count"],p["delta_E_primary_paired"],p["delta_D_primary_paired"]),(8,8,-1.,1.))
        self.assertEqual(c.decision(p,True)["completed_plan_status"],"TARGET_DISCORDANCE_OBSERVED")
        self.assertEqual(c.decision(p,False)["completed_plan_status"],"INCOMPLETE_PLAN")
        self.assertEqual(c.decision(p,False,True)["primary_status"],"INVALID_EXECUTION")
        p2=dict(p,aggregate_sign_D="tie")
        self.assertEqual(c.decision(p2,True)["primary_status"],"TARGET_DISCORDANCE_NOT_OBSERVED")
        p2=dict(p,joint_count=0)
        self.assertEqual(c.decision(p2,True)["primary_status"],"TARGET_DISCORDANCE_NOT_OBSERVED")
        row=rows[0].copy();row.update(delta_D=None,sign_D="undefined",joint_discordance=None,status="UNDEFINED")
        p=c.paired_summary([row]+rows[1:])
        self.assertEqual((p["n_valid"],p["n_valid_E"],p["D_undefined"]),(7,8,1))
        self.assertEqual(c.decision(p,True)["primary_status"],"INCONCLUSIVE_PRIMARY")
        all_undefined=[dict(row,s=s,e=s+200) for s in c.STARTS]
        absent=c.paired_summary(all_undefined)
        self.assertIsNone(absent["delta_D_primary_paired"])
        self.assertEqual(absent["n_valid"],0)
        self.assertEqual(absent["mean_delta_E_all"],-1.)


class FullFixtureTests(unittest.TestCase):
    def test_full_plan_independent_metric_and_status_check(self):
        ref,q=r.load_bundle(r.make_bundle())
        frozen,scenarios=r.compute(ref,q)
        results,pairs=r.evaluate(ref,q,frozen)
        sm,sp,decision=r.summarize(results,pairs)
        self.assertEqual((len(scenarios),len(results),len(pairs)),(32,96,96))
        self.assertEqual(len(sm),12);self.assertEqual(len(sp),12)
        expected={}
        for item in frozen:
            s,L=item["s"],item["L"]; e=s+L
            xx=ref[0,s:e].tolist()
            for method in c.METHODS:
                out,_,err=item["outputs"][method]
                self.assertIsNone(err)
                yy=out[0,s:e].tolist()
                E=math.sqrt(sum((a-b)**2 for a,b in zip(xx,yy))/L)
                dx=[b-a for a,b in zip(xx,xx[1:])]
                dy=[b-a for a,b in zip(yy,yy[1:])]
                A=math.sqrt(sum((a-b)**2 for a,b in zip(dx,dy))/(L-1))
                B=math.sqrt(sum(a*a for a in dx)/(L-1))
                D=A/B if B else None
                def variance(v):
                    m=sum(v)/len(v)
                    return sum((x-m)**2 for x in v)/len(v)
                V=variance(yy)/variance(xx) if variance(xx) else None
                expected[(s,L,method)]=(E,D)
                row=next(v for v in results if (v["s"],v["L"],v["method"])==(s,L,method))
                c.compare_evidence({"E":row["E"],"A":row["A"],"B":row["B"],"D":row["D"],"V":row["V"]},
                                   {"E":E,"A":A,"B":B,"D":D,"V":V})
                self.assertEqual(row["status"],"OK")
                self.assertEqual(row["n_pairs"],L-1)
                self.assertEqual(row["outside_max"],0.)
                self.assertTrue(row["outside_identical"])
        def independent_sign(v):
            return "undefined" if v is None else "-" if v< -1e-10 else "+" if v>1e-10 else "tie"
        for row in pairs:
            a,b=row["pair"].split(" - ")
            ea,da=expected[(row["s"],row["L"],a)]
            eb,db=expected[(row["s"],row["L"],b)]
            de=ea-eb;dd=None if da is None or db is None else da-db
            se,sd=independent_sign(de),independent_sign(dd)
            c.compare_evidence({"delta_E":row["delta_E"],"delta_D":row["delta_D"],"sign_E":row["sign_E"],
                                "sign_D":row["sign_D"],"joint":row["joint_discordance"]},
                               {"delta_E":de,"delta_D":dd,"sign_E":se,"sign_D":sd,
                                "joint":None if dd is None else se=="-" and sd=="+"})
        prim=[p for p in pairs if p["L"]==200 and p["pair"]=="AR(10) - Linear"]
        de=sum(p["delta_E"] for p in prim)/8;dd=sum(p["delta_D"] for p in prim)/8
        h=de< -1e-10 and dd>1e-10 and any(p["joint_discordance"] for p in prim)
        self.assertEqual(decision["primary_status"],"TARGET_DISCORDANCE_OBSERVED" if h else "TARGET_DISCORDANCE_NOT_OBSERVED")
        self.assertEqual(decision["plan_completeness"],"COMPLETE_PLAN")

    def test_numeric_failure_preserved_and_plan_nonzero(self):
        ref,q=r.load_bundle(r.make_bundle())
        original=c.reconstruct
        def failure(method,p):
            if method=="AR(10)" and p.L==5:
                raise c.NumericFailure("forced synthetic failure")
            return original(method,p)
        with tempfile.TemporaryDirectory() as td, patch.object(c,"reconstruct",side_effect=failure):
            out=Path(td)/"out"
            result=r.execute(out)
            self.assertEqual(result["status"],"INCOMPLETE_PLAN")
            rows=json.loads((out/"results.json").read_bytes())
            bad=[a for a in rows if a["status"]=="NUMERIC_FAILURE"]
            self.assertEqual(len(rows),96);self.assertEqual(len(bad),8)
            self.assertTrue(all(x["E"] is None and x["D"] is None for x in bad))
            d=json.loads((out/"decision.json").read_bytes())
            self.assertEqual(d["plan_completeness"],"INCOMPLETE_PLAN")
            self.assertEqual(d["completed_plan_status"],"INCOMPLETE_PLAN")
            self.assertEqual(d["evaluation_authorized"],False)
            # CLI status mapping must not promote incomplete execution.
            with patch.object(r,"execute",return_value=result), patch("sys.stdout",new=io.StringIO()):
                self.assertEqual(r.main(["--output-dir",str(Path(td)/"not_run")]),2)


if __name__=="__main__":
    unittest.main()
