"""Frozen mathematical protocol, §§3–6. No real-data loader or detector."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

STARTS = (400, 800, 1200, 1600, 2000, 2400, 2800, 3200)
LENGTHS = (5, 20, 80, 200)
METHODS = ("Hold", "Linear", "AR(10)")
PAIRS = (("AR(10)", "Linear"), ("AR(10)", "Hold"), ("Linear", "Hold"))
P, C, TAU = 10, 256, 1e-10


class InvalidExecution(ValueError):
    """An invariant failed; no scientific decision is permissible."""


class NumericFailure(ArithmeticError):
    """A numerical reconstruction or metric cannot be represented."""


def require(ok, detail):
    if not ok:
        raise InvalidExecution(detail)


def finite_scalar(value):
    v = float(value)
    if not math.isfinite(v):
        raise NumericFailure("nonfinite numeric result")
    return v


def finite_vector(x):
    if not np.isfinite(x).all():
        raise NumericFailure("nonfinite numeric array")
    return x


def readonly(x):
    result = np.array(x, copy=True)
    result.setflags(write=False)
    return result


def validate_reference(x, q):
    require(isinstance(x, np.ndarray) and x.dtype == np.float64
            and x.ndim == 2 and x.shape[0] == 3, "reference must be 3 x N float64")
    require(np.isfinite(x).all(), "nonfinite reference")
    require(type(q) is tuple and len(q) == x.shape[1]
            and all(type(v) is int for v in q), "q must be exact integer tuple")
    require(all(a < b for a, b in zip(q, q[1:])), "non-increasing q")


def bounds(n, s, L):
    require(type(s) is int and type(L) is int and L >= 0
            and C <= s < n and s + L < n, "invalid gap bounds")


def inject(x, q, s, L):
    validate_reference(x, q)
    bounds(x.shape[1], s, L)
    obs = x.copy()
    obs[0, s:s+L] = x[0, s-1]
    z = np.zeros(x.shape, dtype=bool)
    z[0, s:s+L] = True
    outside(x, q, obs, q, z)
    return readonly(obs), readonly(z)


def outside(ref, q, output, output_q, z):
    require(isinstance(output, np.ndarray) and output.shape == ref.shape
            and output.dtype == np.float64 and np.isfinite(output).all(),
            "invalid reconstructed shape/dtype/finite")
    require(isinstance(z, np.ndarray) and z.dtype == bool and z.shape == ref.shape,
            "invalid assigned mask")
    require(q == output_q and type(output_q) is tuple, "q changed")
    require(np.array_equal(ref[~z], output[~z]), "changed outside assigned mask")
    return 0.0


@dataclass(frozen=True)
class Packet:
    history: np.ndarray
    right: float
    L: int


def packet(obs, s, L):
    bounds(obs.shape[1], s, L)
    require(obs.ndim == 2 and obs.shape[0] == 3 and obs.dtype == np.float64,
            "invalid observation")
    require(np.isfinite(obs).all(), "nonfinite observation")
    return Packet(readonly(obs[0, s-C:s]), float(obs[0, s+L]), L)


def ar_design(h):
    require(isinstance(h, np.ndarray) and h.shape == (C,) and
            h.dtype == np.float64 and np.isfinite(h).all(), "invalid AR history")
    a = np.ones((C-P, P+1), dtype=np.float64)
    for j in range(P, C):
        a[j-P, 1:] = h[j-P:j]
    return a, h[P:].copy()


def recursive(beta, history, L):
    h = list(map(float, history))
    out = []
    for _ in range(L):
        with np.errstate(over="raise", invalid="raise"):
            y = finite_scalar(beta[0] + np.dot(beta[1:], h[-P:]))
        out.append(y)
        h.append(y)
    return np.asarray(out, dtype=np.float64)


def reconstruct(method, p):
    """Only the oracle packet is accessible; no true/hidden samples or other axes."""
    require(method in METHODS and isinstance(p, Packet), "unknown method/packet")
    h, L = p.history, p.L
    require(type(L) is int and L >= 0 and h.shape == (C,)
            and h.dtype == np.float64 and np.isfinite(h).all()
            and math.isfinite(p.right), "bad packet")
    meta = dict(rank=None, singular_values=None, condition=None,
                condition_reason="NOT_AR")
    if L == 0:
        return readonly(np.empty(0, dtype=np.float64)), meta
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            if method == "Hold":
                out = np.full(L, h[-1], dtype=np.float64)
            elif method == "Linear":
                out = np.linspace(h[-1], p.right, L+2, dtype=np.float64)[1:-1]
            else:
                a, target = ar_design(h)
                beta, _, rank, sv = np.linalg.lstsq(a, target, rcond=None)
                finite_vector(beta)
                finite_vector(sv)
                cond = None if sv[-1] == 0 else finite_scalar(sv[0]/sv[-1])
                meta = dict(rank=int(rank), singular_values=sv.tolist(), condition=cond,
                            condition_reason="SINGULAR" if cond is None else None)
                out = recursive(beta, h[-P:], L)
            finite_vector(out)
    except (np.linalg.LinAlgError, FloatingPointError, OverflowError) as exc:
        raise NumericFailure(str(exc)) from exc
    return readonly(out), meta


def assemble(obs, q, z, s, L, gap):
    bounds(obs.shape[1], s, L)
    expected = np.zeros(obs.shape, dtype=bool)
    expected[0, s:s+L] = True
    require(np.array_equal(z, expected), "wrong assigned mask")
    require(isinstance(gap, np.ndarray) and gap.dtype == np.float64
            and gap.shape == (L,), "bad prediction shape/dtype")
    finite_vector(gap)
    out = obs.copy()
    out[0, s:s+L] = gap
    outside(obs, q, out, q, z)
    return readonly(out)


def rms(v):
    finite_vector(v)
    require(v.size > 0, "empty RMS")
    m = float(np.max(np.abs(v)))
    if m == 0:
        return 0.0
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        r = finite_scalar(m * math.sqrt(float(np.mean((v/m)**2))))
    if r == 0:
        raise NumericFailure("positive RMS not representable")
    return r


def stable_sd(v):
    # Shift before scaling to preserve differences at large common levels.
    # If that subtraction overflows, explicitly normalize first.
    if np.all(v == v[0]):
        return 0.0
    with np.errstate(over="ignore", invalid="ignore"):
        d = v-v[0]
    if np.isfinite(d).all():
        m = float(np.max(np.abs(d)))
        u = d/m
    else:
        m = float(np.max(np.abs(v)))
        u = v/m
    sd = finite_scalar(m * rms(u - np.mean(u)))
    if sd == 0:
        raise NumericFailure("positive standard deviation not representable")
    return sd


def metrics(ref, output, q, output_q, z, s, L):
    """Evaluator only; boundaries are not part of the first-difference endpoint."""
    validate_reference(ref, q)
    bounds(ref.shape[1], s, L)
    outside(ref, q, output, output_q, z)
    expected = np.zeros(ref.shape, dtype=bool)
    expected[0, s:s+L] = True
    require(np.array_equal(z, expected), "evaluation mask differs from assigned I")
    e = s+L
    row = dict(E=None, E_reason=None, A=None, B=None, D=None, D_reason=None,
               V=None, V_reason=None, A_B_zero_flag=None,
               n_pairs=max(0, L-1), left_error=None, right_error=None,
               outside_max=0.0, outside_identical=True)
    if L == 0:
        row.update(E_reason="NO_INJECTION", D_reason="NO_INJECTION",
                   V_reason="NO_INJECTION")
        return row
    x, y = ref[0, s:e], output[0, s:e]
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            residual = y-x
            row.update(E=rms(residual), left_error=finite_scalar(residual[0]),
                       right_error=finite_scalar(-residual[-1]))
            if L == 1:
                row.update(D_reason="INSUFFICIENT_PAIRS", V_reason="INSUFFICIENT_PAIRS")
                return row
            dx, dy = np.diff(x), np.diff(y)
            A, B = rms(dy-dx), rms(dx)
            row.update(A=A, B=B)
            if np.all(dx == 0):
                row.update(D_reason="ZERO_REFERENCE_DIFFERENCES",
                           A_B_zero_flag="A_ZERO" if A == 0 else "A_POSITIVE")
            else:
                row["D"] = finite_scalar(A/B)
                if A > 0 and row["D"] == 0:
                    raise NumericFailure("positive D not representable")
            if np.all(x == x[0]):
                row["V_reason"] = "ZERO_REFERENCE_VARIANCE"
            else:
                sy, sx = stable_sd(y), stable_sd(x)
                ratio = finite_scalar(sy/sx)
                row["V"] = finite_scalar(ratio*ratio)
                if sy > 0 and row["V"] == 0:
                    raise NumericFailure("positive V not representable")
    except (FloatingPointError, OverflowError) as exc:
        raise NumericFailure(str(exc)) from exc
    return row


def sign(x):
    if x is None:
        return "undefined"
    return "+" if x > TAU else "-" if x < -TAU else "tie"


def pair(a, b):
    require((a["s"], a["L"]) == (b["s"], b["L"]), "unpaired windows")
    E1, E2, D1, D2 = a["E"], b["E"], a["D"], b["D"]
    ok = a["status"] == b["status"] == "OK"
    de = finite_scalar(E1-E2) if ok and E1 is not None and E2 is not None else None
    dd = finite_scalar(D1-D2) if ok and D1 is not None and D2 is not None else None
    return dict(subject=a["subject"], run=a["run"], s=a["s"], L=a["L"], e=a["e"],
                pair=a["method"]+" - "+b["method"], E_left=E1, E_right=E2,
                D_left=D1, D_right=D2, delta_E=de, delta_D=dd,
                sign_E=sign(de), sign_D=sign(dd),
                joint_discordance=(sign(de) == "-" and sign(dd) == "+")
                if de is not None and dd is not None else None,
                status="NUMERIC_FAILURE" if not ok else
                "OK" if de is not None and dd is not None else "UNDEFINED")


def avg(v):
    return finite_scalar(math.fsum(x/len(v) for x in v)) if v else None


def stats(v):
    if not v:
        return dict(mean=None, min=None, max=None, median=None)
    u = sorted(v)
    n = len(u)
    med = u[n//2] if n%2 else avg(u[n//2-1:n//2+1])
    return dict(mean=avg(v), min=u[0], max=u[-1], median=med)


def paired_summary(rows):
    require(len(rows) == 8 and tuple(r["s"] for r in rows) == STARTS,
            "incomplete or misordered paired grid")
    both = [r for r in rows if r["delta_E"] is not None and r["delta_D"] is not None]
    er = [r["delta_E"] for r in rows if r["delta_E"] is not None]
    dr = [r["delta_D"] for r in rows if r["delta_D"] is not None]
    es, ds = stats([r["delta_E"] for r in both]), stats([r["delta_D"] for r in both])
    return dict(subject=rows[0]["subject"], run=rows[0]["run"], L=rows[0]["L"],
                pair=rows[0]["pair"], n_total=len(rows), n_valid=len(both),
                n_valid_E=len(er), n_valid_D=len(dr),
                mean_delta_E_all=avg(er), mean_delta_D_all=avg(dr),
                delta_E_primary_paired=es["mean"], delta_D_primary_paired=ds["mean"],
                **{"paired_E_"+k:v for k,v in es.items()},
                **{"paired_D_"+k:v for k,v in ds.items()},
                **{f"E_{flag}":sum(r["sign_E"]==flag for r in rows) for flag in ("+","-","tie","undefined")},
                **{f"D_{flag}":sum(r["sign_D"]==flag for r in rows) for flag in ("+","-","tie","undefined")},
                joint_count=sum(r["joint_discordance"] is True for r in rows),
                numeric_failures=sum(r["status"]=="NUMERIC_FAILURE" for r in rows),
                aggregate_sign_E=sign(es["mean"]), aggregate_sign_D=sign(ds["mean"]))


def method_summary(rows):
    require(len(rows)==8 and tuple(r["s"] for r in rows)==STARTS, "bad method grid")
    e = [r["E"] for r in rows if r["E"] is not None]
    d = [r["D"] for r in rows if r["D"] is not None]
    return dict(subject=rows[0]["subject"], run=rows[0]["run"], L=rows[0]["L"],
                method=rows[0]["method"], n_total=8, n_valid_E=len(e),
                n_valid_D=len(d), mean_E=avg(e), mean_D=avg(d),
                numeric_failures=sum(r["status"]=="NUMERIC_FAILURE" for r in rows))


def decision(primary, complete, invalid=False):
    # Primary completeness and full-plan completeness are distinct; invalid wins.
    if invalid:
        return dict(primary_status="INVALID_EXECUTION", plan_completeness="INVALID_EXECUTION",
                    completed_plan_status="INVALID_EXECUTION")
    plan = "COMPLETE_PLAN" if complete else "INCOMPLETE_PLAN"
    if primary["n_valid"] != 8:
        status = "INCONCLUSIVE_PRIMARY"
    elif primary["aggregate_sign_E"] == "-" and primary["aggregate_sign_D"] == "+" and primary["joint_count"] > 0:
        status = "TARGET_DISCORDANCE_OBSERVED"
    else:
        status = "TARGET_DISCORDANCE_NOT_OBSERVED"
    return dict(primary_status=status, plan_completeness=plan,
                completed_plan_status=status if complete else "INCOMPLETE_PLAN")


def compare_evidence(a, b):
    """Independent comparison gate: numeric tolerance AND exact discrete evidence."""
    if type(a) is float or type(b) is float:
        require(type(a) in (int,float) and type(b) in (int,float)
                and math.isfinite(a) and math.isfinite(b), "numeric type/finite mismatch")
        require(abs(a-b) <= 1e-10 + 1e-10*max(abs(a),abs(b)), "numeric tolerance mismatch")
    elif isinstance(a, dict):
        require(isinstance(b,dict) and a.keys()==b.keys(), "schema mismatch")
        for k in a:
            compare_evidence(a[k], b[k])
    elif isinstance(a, list):
        require(isinstance(b,list) and len(a)==len(b), "length mismatch")
        for x,y in zip(a,b):
            compare_evidence(x,y)
    else:
        require(type(a) is type(b) and a==b, "exact integer/status/sign/undefined mismatch")
