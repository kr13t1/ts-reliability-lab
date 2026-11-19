"""Entirely synthetic, do not fetch/open any real measurement."""
import io
import os
import sys
import tempfile
import unittest
import warnings
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
from explorations.repair_dynamics import core as c, run as r
from explorations.repair_dynamics_real import adapter as a, run, gate

P=a.RecordPins(99001,"synthetic/fixture.txt",118900,
                "c5f7cb0eb4f82137962ddd0c03a731324158491c8cfc6f134a8436bde0f96062",
                "3bb52dfd",3402,1,3401,3401,None,"B",100000,123800,118866,
                "2556a6fa1987d41a7d1d7e6c8fa16afec41f42dbddbf9cb145da4dc18fd0def5",
                147297,"6f895cefe7bfac5e678aeab6fe41882e8d65c8570288cce051fe25ab69134a22")
KEY=b"A,Walking\nB,Jogging\n"


def fixture():
    lines=[f"99001,A,{100000+7*i},{(i%41-20)/8:.3f},{(i%13-6)/4:.3f},1.000;\n"
           for i in range(3401)]
    lines.append("99001,B,123807,0.000,0.000,1.000;\n")
    return "".join(lines).encode("ascii")


def zipped(entries):
    buffer=io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",UserWarning)
        with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_STORED) as z:
            for name,data in entries:
                z.writestr(zipfile.ZipInfo(name,(1980,1,1,0,0,0)),data)
    return buffer.getvalue()


def bundle(entries=None,outer_entries=None):
    inner=zipped(entries if entries is not None else [(P.member,fixture()),("key.txt",KEY)])
    outer=zipped(outer_entries(inner) if outer_entries else [("inner.zip",inner)])
    ap=a.ArchivePins(len(outer),r.sha(outer),"inner.zip",len(inner),r.sha(inner),
                     a.crc(inner),"key.txt",len(KEY),r.sha(KEY),a.crc(KEY))
    return outer,ap


class FixtureAdapter(unittest.TestCase):
    def test_mode(self):
        self.assertEqual(sys.flags.optimize,int(os.environ["EXPECTED_OPTIMIZE"]))
        self.assertIn(sys.flags.optimize,(0,1))

    def test_manifest_and_frozen_config(self):
        # Only existing approved metadata, never source amplitudes.
        m=(a.ROOT/r.ADMISSION).read_bytes()
        self.assertEqual(a.check_manifest(m)["selected_subject"],1601)
        self.assertEqual(set(a.check_sources()),set(a.PINS))
        self.assertEqual(run.check_config((run.HERE/"config.json").read_bytes()),run.CONFIG)
        for key,value in [("subject",99001),("N",3401),("axis",1),("ar_order",11),
                          ("ar_context",255),("lengths",[200]),("sign_tau",0.0),
                          ("starts",[1200]),("seed",1),("private_exposure_history","CLEARED")]:
            with self.subTest(key=key),self.assertRaises(c.InvalidExecution):
                run.check_config(r.dump(run.CONFIG|{key:value}).encode())
        tampered=r.read_json(m)
        tampered["selected_run"]["N"]=3401
        with self.assertRaises(a.IdentityError):
            a.check_manifest(r.dump(tampered).encode())
        with self.assertRaises(a.IdentityError):
            a.check_manifest(m+b"\n")

    def test_positive_exact_member_run_view(self):
        rec=a.load_member(fixture(),P)
        self.assertEqual((rec.ref.shape,rec.q[0],rec.q[-1]),((3,3401),100000,123800))
        self.assertFalse(rec.ref.flags.writeable)
        self.assertEqual(r.sha(rec.view),P.view_sha)
        self.assertEqual(rec.metadata,dict(subject=99001,run="99001/A/1-3401",
                                           source_first_line=1,source_last_line=3401))
        np.testing.assert_array_equal(rec.ref[:,0],[-2.5,-1.5,1.0])

    def test_byte_tamper_and_self_rehash_member(self):
        good=fixture()
        bad=good.replace(b"-2.500",b"-2.501",1)
        self.assertEqual(sum(x!=y for x,y in zip(good,bad)),1)
        with self.assertRaises(a.IdentityError):
            a.load_member(bad,P)
        # Even if an upstream claimed raw-member digest is changed, independent
        # run and reference identity remain pinned; production cannot alter any pin.
        with self.assertRaisesRegex(a.IdentityError,"raw run pin"):
            a.load_member(bad,replace(P,member_sha=r.sha(bad),member_crc=a.crc(bad)))

    def test_run_and_view_pin_wrong(self):
        for p in (replace(P,run_sha="0"*64),replace(P,run_size=P.run_size+1),
                  replace(P,view_sha="0"*64),replace(P,view_size=P.view_size+1)):
            with self.assertRaises(a.IdentityError):
                a.load_member(fixture(),p)

    def test_structure_subject_q_activity_finite_and_contiguity(self):
        original=fixture().splitlines(keepends=True)
        changes=[original[:-1]]
        for col,new in [(0,"99002"),(1,"B"),(2,"100000"),(2,"1e5"),
                        (2,"100000.0"),(3,"NaN"),(4,"inf"),(5,"1e999"),(5,"")]:
            bad=original.copy()
            fields=bad[1].decode().rstrip(";\n").split(",");fields[col]=new
            bad[1]=(",".join(fields)+";\n").encode();changes.append(bad)
        bad=original.copy();bad[-1]=bad[-1].replace(b",B,",b",A,");changes.append(bad)
        bad=original.copy();bad[1]=bad[1][:-2]+b"\n";changes.append(bad)
        for i,rows in enumerate(changes):
            with self.subTest(i=i),self.assertRaises(a.IdentityError):
                a.decode_member(b"".join(rows),P)
        for p in (replace(P,n=3400),replace(P,following="C"),replace(P,q_last=123801)):
            with self.assertRaises(a.IdentityError):
                a.decode_member(fixture(),p)

    def test_nested_zip_positive_and_changed_outer(self):
        data,ap=bundle()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"outer.zip";path.write_bytes(data)
            rec=a.load_archive(path,P,ap)
            self.assertEqual(r.sha(rec.view),P.view_sha)
            self.assertEqual(path.read_bytes(),data)
            path.write_bytes(data[:-1]+bytes([data[-1]^1]))
            with self.assertRaisesRegex(a.IdentityError,"outer ZIP"):
                a.load_archive(path,P,ap)

    def test_missing_duplicate_or_rehashed_nested_member(self):
        good=fixture()
        bad=good.replace(b"-2.500",b"-2.501",1)
        cases=[bundle([("key.txt",KEY)]),
               bundle([(P.member,good),(P.member,good),("key.txt",KEY)]),
               bundle([(P.member,bad),("key.txt",KEY)]),
               bundle([(P.member,good),("key.txt",b"BAD")]),
               bundle(outer_entries=lambda inner:[("wrong.zip",inner)]),
               bundle(outer_entries=lambda inner:[("inner.zip",inner),("inner.zip",inner)])]
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"outer.zip"
            for i,(data,ap) in enumerate(cases):
                path.write_bytes(data)
                with self.subTest(i=i),self.assertRaises(a.IdentityError):
                    a.load_archive(path,P,ap)

    def test_isolated_hidden_samples_other_channels_and_right_boundary(self):
        rec=a.load_member(fixture(),P)
        s,L=400,20
        changed=rec.ref.copy();changed[0,s:s+L]+=123
        changed[1:]+=1000
        right=rec.ref.copy();right[0,s+L]+=7
        for m in c.METHODS:
            preds=[]
            for ref in (rec.ref,changed,right):
                obs,z=c.inject(ref,rec.q,s,L)
                out,_,error=r.frozen_prediction(obs,rec.q,z,s,L,m)
                self.assertIsNone(error);self.assertFalse(out.flags.writeable)
                np.testing.assert_array_equal(out[~z],ref[~z])
                preds.append(out[0,s:s+L])
            np.testing.assert_array_equal(preds[0],preds[1])
            self.assertEqual(np.array_equal(preds[0],preds[2]),m!="Linear")

    def test_full_synthetic_adapter_to_frozen_grid(self):
        rec=a.load_member(fixture(),P)
        frozen,scenarios=run.compute(rec)
        before=run.freeze_digest(frozen)
        rows,pairs=run.evaluate(rec,frozen)
        sm,sp,d=run.summarize(rows,pairs)
        self.assertEqual((len(scenarios),len(rows),len(pairs),len(sm),len(sp)),(32,96,96,12,12))
        self.assertEqual(before,run.freeze_digest(frozen))
        self.assertTrue(all(row["subject"]==P.subject and row["source_last_line"]==P.last
                            and row["outside_identical"] for row in rows))
        self.assertEqual(d["plan_completeness"],"COMPLETE_PLAN")
        self.assertEqual([row["method"] for row in rows[:3]],list(c.METHODS))

    def test_gate_missing_or_failed_blocks_all_real_io(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);out=p/"out"
            with patch.object(a,"load_archive",side_effect=RuntimeError("must not be called")) as load:
                v=run.execute(out,p/"missing.zip",p/"no_gate",p/"receipt")
                load.assert_not_called()
            self.assertEqual(v["status"],"INVALID_EXECUTION")
            self.assertEqual({f.name for f in out.iterdir()},{"provenance.json","validation.json"})
            gp=p/"failed_gate";gp.mkdir()
            r.write_json(gp/"gate.json",dict(status="INVALID_EXECUTION",scope="SYNTHETIC_ONLY"))
            with patch.object(a,"acquire",side_effect=RuntimeError("must not be called")) as acquire:
                code=run.main(["acquire","--archive",str(p/"missing.zip"),
                               "--gate-dir",str(gp),"--receipt",str(p/"receipt")])
                self.assertEqual(code,2);acquire.assert_not_called()

    def test_provenance_source_pin_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in a.PINS:
                target=root/rel;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((a.ROOT/rel).read_bytes())
            self.assertEqual(set(a.check_sources(root)),set(a.PINS))
            target=root/r.ADMISSION;target.write_bytes(target.read_bytes()+b"\n")
            with self.assertRaises(a.IdentityError):
                a.check_sources(root)

if __name__=="__main__":
    unittest.main()
