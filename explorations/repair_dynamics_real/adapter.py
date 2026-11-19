"""LAB-042: byte-pinned adapter. No repair or selection by signal values."""
from __future__ import annotations

import csv
import hashlib
import io
import math
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from explorations.repair_dynamics import core as c, run as r

ROOT = r.ROOT
DECISIONS = "docs/DECISIONS.md"
BASE = "0406702c52b12f3e1bfcba2a313a5bfdeb6fb778"
ACCEPTED = "585c8ea4f4d8a3250e9d7cbb03c3ac23d6310da0"
PINS = {**r.PINS, DECISIONS: "dee2b1442fb0586899367c2917fa2e07d69ccf49",
        "explorations/repair_dynamics/core.py": "ddfd1503de8797086745b73cfa7b3d3817a1b103",
        "explorations/repair_dynamics/run.py": "fc5066ff195ead25da34f920f2584699649aeb37",
        "explorations/repair_dynamics/requirements.txt": "def132cbbdc1f2b65bc65dddf97bcff597a78faf"}
URL = "https://archive.ics.uci.edu/static/public/507/wisdm%2Bsmartphone%2Band%2Bsmartwatch%2Bactivity%2Band%2Bbiometrics%2Bdataset.zip"
LIMITATION = ("Private exposure history UNKNOWN. Subject-disjoint relative to documented "
              "design/pilot; no guarantee of untouched test, statistical independence, "
              "session independence, or population generalization.")
ATTRIBUTION = ("Gary M. Weiss (2019), WISDM Smartphone and Smartwatch Activity and "
               "Biometrics Dataset, UCI 507, DOI 10.24432/C5HK59, CC BY 4.0. "
               "Observed reference; controlled X freeze and oracle repair; not a physical fault test.")


class IdentityError(c.InvalidExecution):
    pass


def identity(ok, detail):
    if not ok:
        raise IdentityError(detail)


@dataclass(frozen=True)
class RecordPins:
    subject: int
    member: str
    member_size: int
    member_sha: str
    member_crc: str
    lines: int
    first: int
    last: int
    n: int
    preceding: str | None
    following: str | None
    q_first: int
    q_last: int
    run_size: int
    run_sha: str
    view_size: int
    view_sha: str


@dataclass(frozen=True)
class ArchivePins:
    outer_size: int
    outer_sha: str
    inner_name: str
    inner_size: int
    inner_sha: str
    inner_crc: str
    key_name: str
    key_size: int
    key_sha: str
    key_crc: str


REAL = RecordPins(1601, "wisdm-dataset/raw/phone/accel/data_1601_accel_phone.txt",
                  4405756, "cafe0c35079ce96909ad6a42b8a65af7349cd416350fe4d0aa78354bb68b20ff",
                  "0b298b7f", 81457, 1, 4512, 4512, None, "B",
                  265073308304101, 265253274644607, 244067,
                  "ec776464a6d72da9b568d1d6949dd0881a5bd1fd8949f2d185074da293b7d11f",
                  282497, "61f5cdd0f23ae5d3200b45109dbe5ef2a78bac498fc5815faa1341bd6a8bac0b")
ARCHIVE = ArchivePins(310292805, "6e0147f181d8f5275918db65eeb9dc842a0185d37cb6b2f30cbf74ee6e205469",
                      "wisdm-dataset.zip", 309713877,
                      "1cf32e8d3a0ecc101bd299fba22545273dcb7de1c9565e0b7844abdfbc6b1695", "83f86753",
                      "wisdm-dataset/activity_key.txt", 210,
                      "ddca4cfb34ea3c4642f73a22dc498e2d77f435be4e836f87f37c274ec5ee4c26", "3c56e5f5")


@dataclass(frozen=True)
class Record:
    pins: RecordPins
    ref: np.ndarray
    q: tuple
    view: bytes

    @property
    def metadata(self):
        p = self.pins
        return dict(subject=p.subject, run=f"{p.subject}/A/{p.first}-{p.last}",
                    source_first_line=p.first, source_last_line=p.last)


def check_manifest(data):
    identity(r.git_blob(data) == PINS[r.ADMISSION], "historical admission manifest pin")
    m = r.read_json(data)
    for k in ("admission_finalized", "runner_authorized", "fixture_gate_authorized",
              "evaluation_authorized"):
        identity(m[k] is False, "historical flags changed")
    a = m["selected_run"]
    p = REAL
    expected = dict(subject_id=p.subject, member_path=p.member, member_size_bytes=p.member_size,
                    member_sha256=p.member_sha, member_crc32=p.member_crc,
                    physical_line_count=p.lines, axis=0, activity="A",
                    start_line_1_based=p.first, end_line_1_based=p.last, N=p.n,
                    preceding_activity=p.preceding, following_activity=p.following,
                    q_first=str(p.q_first), q_last=str(p.q_last), raw_run_bytes=p.run_size,
                    raw_run_sha256=p.run_sha, canonical_view_bytes=p.view_size,
                    canonical_view_sha256=p.view_sha, private_exposure_history="UNKNOWN",
                    timestamp_unit="UNKNOWN")
    identity(m["selected_subject"] == p.subject and all(type(a[k]) is type(v) and a[k] == v
             for k,v in expected.items()), "frozen selected record differs")
    s = m["dataset"]["source_attestation"]
    identity(m["dataset"]["official_download_url"] == URL and
             s["outer"]["sha256"] == ARCHIVE.outer_sha and
             s["outer"]["size_bytes"] == ARCHIVE.outer_size and
             s["inner"]["path"] == ARCHIVE.inner_name and s["inner"]["sha256"] == ARCHIVE.inner_sha
             and s["inner"]["size_bytes"] == ARCHIVE.inner_size and s["inner"]["crc32"] == ARCHIVE.inner_crc
             and s["member"]["path"] == p.member and s["member"]["sha256"] == p.member_sha
             and s["member"]["size_bytes"] == p.member_size and s["member"]["crc32"] == p.member_crc
             and s["activity_key"]["path"] == ARCHIVE.key_name
             and s["activity_key"]["sha256"] == ARCHIVE.key_sha
             and s["activity_key"]["size_bytes"] == ARCHIVE.key_size
             and s["activity_key"]["crc32"] == ARCHIVE.key_crc, "frozen acquisition pins differ")
    plan = m["frozen_future_plan"]
    identity(plan["starts"] == list(c.STARTS) and plan["lengths"] == list(c.LENGTHS)
             and plan["ar_order"] == c.P and plan["ar_context"] == c.C and
             plan["methods"] == list(c.METHODS) and plan["axis"] == 0 and
             plan["seed"] is None and plan["mask"] == "oracle" and plan["active"] is False,
             "frozen plan differs")
    return m


def check_sources(root=ROOT):
    evidence={}
    for rel, blob in PINS.items():
        data=(root/rel).read_bytes()
        identity(r.git_blob(data)==blob, "source/authority pin: "+rel)
        if rel == r.ADMISSION:
            check_manifest(data)
        evidence[rel]=dict(git_blob_sha=blob,sha256=r.sha(data))
    return evidence


def crc(data):
    return format(zlib.crc32(data), "08x")


def check_bytes(data, size, digest, expected_crc, label):
    identity(len(data)==size and r.sha(data)==digest and crc(data)==expected_crc,
             label+" identity mismatch")


def file_digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def check_file(path,size,digest,label):
    identity(path.is_file() and path.stat().st_size==size and file_digest(path)==digest,
             label+" identity mismatch")


def unique(z,name,size,expected_crc):
    infos=[i for i in z.infolist() if i.filename==name]
    identity(len(infos)==1 and not infos[0].is_dir(),"missing or duplicate exact archive member")
    info=infos[0]
    identity(info.file_size==size and format(info.CRC,"08x")==expected_crc,
             "archive member size/CRC differs")
    return info


INT = re.compile(r"[+-]?[0-9]+")
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def decode_member(data,p):
    """Read physical source order, lossless field tokens, one exact maximal A-run.
    Separate parser for structural synthetic negative checks; production always
    goes through load_member, which validates independent bytes first.
    """
    lines=data.splitlines(keepends=True)
    identity(len(lines)==p.lines and p.last-p.first+1==p.n and p.n>=3401,
             "physical line count or selected length differs")
    activity=[]; stamps=[]; axes=[]; raw=[]; tokens=[]
    for number,line in enumerate(lines,1):
        try:
            text=line.rstrip(b"\r\n").decode("ascii")
        except UnicodeError as exc:
            raise IdentityError(f"invalid ASCII at physical line {number}") from exc
        identity(text.endswith(";"), f"missing terminal semicolon at line {number}")
        row=text[:-1].split(",")
        identity(len(row)==6 and all(row), f"bad schema at line {number}")
        sub,act,stamp,*v=row
        identity(sub==str(p.subject) and re.fullmatch(r"[A-MO-S]",act) is not None,
                 f"wrong subject/activity at line {number}")
        identity(INT.fullmatch(stamp) is not None and all(NUMBER.fullmatch(a) for a in v),
                 f"invalid numeric token at line {number}")
        xyz=[float(a) for a in v]
        identity(all(math.isfinite(a) for a in xyz),f"nonfinite value at line {number}")
        activity.append(act)
        if p.first<=number<=p.last:
            identity(act=="A", "selected run not contiguous A")
            stamps.append(int(stamp))
            axes.append(xyz);raw.append(line);tokens.append(row)
    # The admitted member has exactly this one maximal A-run, not a search by results.
    identity([i+1 for i,a in enumerate(activity) if a=="A"]==list(range(p.first,p.last+1)),
             "selected A-run not the fixed maximal run")
    left=activity[p.first-2] if p.first>1 else None
    right=activity[p.last] if p.last<len(activity) else None
    identity((left,right)==(p.preceding,p.following), "neighboring activity differs")
    identity(len(stamps)==p.n and stamps[0]==p.q_first and stamps[-1]==p.q_last
             and all(a<b for a,b in zip(stamps,stamps[1:])), "q endpoints/order differ")
    exact_run=b"".join(raw)
    identity(len(exact_run)==p.run_size and r.sha(exact_run)==p.run_sha, "raw run pin mismatch")
    stream=io.StringIO(newline="")
    w=csv.writer(stream,lineterminator="\n")
    w.writerow(["i","source_line","subject","activity","q","x","y","z"])
    for i,row in enumerate(tokens):
        w.writerow([i,p.first+i,*row])
    view=stream.getvalue().encode("utf-8")
    identity(len(view)==p.view_size and r.sha(view)==p.view_sha,"canonical view pin mismatch")
    ref=np.array(axes,dtype=np.float64).T.copy()
    q=tuple(stamps)
    c.validate_reference(ref,q)
    identity(ref.shape==(3,p.n),"decoded shape differs")
    return Record(p,c.readonly(ref),q,view)


def load_member(data,p):
    check_bytes(data,p.member_size,p.member_sha,p.member_crc,"raw member")
    return decode_member(data,p)


def load_archive(path,p=REAL,a=ARCHIVE):
    """Operational check of already accepted archive chain, no new provenance study."""
    check_file(path,a.outer_size,a.outer_sha,"official outer ZIP")
    with tempfile.TemporaryDirectory(prefix="lab042-inner-") as td:
        inner=Path(td)/"inner.zip"
        with zipfile.ZipFile(path) as z:
            inf=unique(z,a.inner_name,a.inner_size,a.inner_crc)
            with z.open(inf) as f, inner.open("xb") as out:
                shutil.copyfileobj(f,out,1048576)
        check_file(inner,a.inner_size,a.inner_sha,"nested ZIP")
        with zipfile.ZipFile(inner) as z:
            key=z.read(unique(z,a.key_name,a.key_size,a.key_crc))
            check_bytes(key,a.key_size,a.key_sha,a.key_crc,"activity key")
            member=z.read(unique(z,p.member,p.member_size,p.member_crc))
            rec=load_member(member,p)
    check_file(path,a.outer_size,a.outer_sha,"unchanged outer ZIP")
    return rec


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urllib.parse.urlsplit(newurl)
        identity(p.scheme=="https" and p.hostname=="archive.ics.uci.edu",
                 "redirect outside official HTTPS host")
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def acquire(path):
    """Called only after fixture gate in the real workflow. Never log amplitudes."""
    identity(not path.exists(),"archive path must not exist")
    opener=urllib.request.build_opener(SafeRedirect())
    req=urllib.request.Request(URL,headers={"User-Agent":"ts-reliability-lab LAB-042",
                                          "Accept-Encoding":"identity"})
    n=0
    with opener.open(req,timeout=40) as response, path.open("xb") as out:
        final=response.geturl(); u=urllib.parse.urlsplit(final)
        identity(response.status==200 and u.scheme=="https" and u.hostname=="archive.ics.uci.edu",
                 "not complete official HTTPS response")
        while block:=response.read(1048576):
            n+=len(block)
            identity(n<=ARCHIVE.outer_size,"official response exceeds frozen size")
            out.write(block)
    check_file(path,ARCHIVE.outer_size,ARCHIVE.outer_sha,"downloaded official ZIP")
    return dict(url=URL,final_url=final,http_status=200,bytes_received=n,
                outer_sha256=ARCHIVE.outer_sha)
