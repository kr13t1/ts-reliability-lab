import argparse, csv, hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent

def load(archive,c):
    with zipfile.ZipFile(archive) as z:
        raw=z.read(c['raw_member'])
    assert hashlib.sha256(raw).hexdigest()==c['raw_sha256']
    rows=[r.rstrip(';').split(',') for r in raw.decode().splitlines() if r.strip()]
    assert all(len(r)==6 and r[0]==str(c['subject']) for r in rows)
    idx=[i for i,r in enumerate(rows) if r[1]==c['activity']]
    assert idx==list(range(idx[0],idx[-1]+1)) and len(idx)==3574
    assert all(int(rows[b][2])>int(rows[a][2]) for a,b in zip(idx,idx[1:]))
    x=np.array([float(rows[i][3+c['axis']]) for i in idx]); assert np.isfinite(x).all()
    return x

def freeze(x,s,e):
    y=x.copy(); y[s:e]=x[s-1]; return y

def repair(y,s,e,method,p=10,context=256):
    z=y.copy()
    if method=='hold': z[s:e]=y[s-1]
    elif method=='linear': z[s:e]=np.linspace(y[s-1],y[e],e-s+2)[1:-1]
    elif method=='ar10':
        h=y[s-context:s].copy(); assert len(h)==context
        A=np.column_stack([np.ones(len(h)-p),np.lib.stride_tricks.sliding_window_view(h,p)[:-1]])
        beta=np.linalg.lstsq(A,h[p:],rcond=None)[0]
        history=list(h[-p:])
        for i in range(s,e):
            z[i]=np.r_[1.,history[-p:]]@beta; history.append(z[i])
    else: raise ValueError(method)
    return z

def main(archive):
    c=json.loads((ROOT/'config.json').read_text()); x=load(archive,c); rows=[]; curves={}
    methods=['hold','linear','ar10']
    for L in c['lengths']:
        for s in c['starts']:
            e=s+L; y=freeze(x,s,e)
            for method in methods:
                z=repair(y,s,e,method,c['ar_order'],c['ar_context']); d=z[s:e]-x[s:e]
                assert np.isfinite(z).all() and np.array_equal(z[:s],x[:s]) and np.array_equal(z[e:],x[e:])
                rows.append(dict(start=s,length=L,method=method,mae=float(np.mean(abs(d))),rmse=float(np.sqrt(np.mean(d*d))),outside_max=0.0))
                if s==1200 and L in (20,200): curves[L,method]=z
    with (ROOT/'results.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    summary=[]
    for L in c['lengths']:
        hold=np.array([r['rmse'] for r in rows if r['length']==L and r['method']=='hold'])
        for m in methods:
            vals=[r for r in rows if r['length']==L and r['method']==m]; a=np.array([r['rmse'] for r in vals]); summary.append(dict(length=L,method=m,mean_rmse=float(a.mean()),mean_mae=float(np.mean([r['mae'] for r in vals])),wins_vs_hold=int(sum(a<hold)),windows=len(a)))
    with (ROOT/'summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
    for L in (20,200):
        s=1200;e=s+L; ix=np.arange(s-25,e+25); fig,ax=plt.subplots(figsize=(10,4));ax.plot(ix,x[ix],label='Reference',lw=1.7,color='#202832');ax.axvspan(s,e-1,color='#cbd5e1',alpha=.35,label='Oracle mask')
        for m in methods: ax.plot(ix,curves[L,m][ix],label=m,alpha=.85,lw=1.4)
        ax.set(xlabel='Sample index',ylabel='Acceleration X (m/s²)',title=f'WISDM 1600 | freeze length {L} | start {s}');ax.legend(ncol=3,frameon=False);fig.tight_layout();fig.savefig(ROOT/f'example_{L}.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5));
    for m in methods: ax.plot(c['lengths'],[q['mean_rmse'] for q in summary if q['method']==m],marker='o',label=m)
    ax.set(xscale='log',xticks=c['lengths'],xlabel='Freeze length (samples)',ylabel='Mean window RMSE (m/s²)',title='Exploratory comparison — one walking recording');ax.set_xticklabels(c['lengths']);ax.legend(frameon=False);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(ROOT/'comparison.png',dpi=160);plt.close(fig)
    (ROOT/'provenance.json').write_text(json.dumps({'python':sys.version,'numpy':np.__version__,'matplotlib':matplotlib.__version__,'raw_sha256':c['raw_sha256'],'config_sha256':hashlib.sha256((ROOT/'config.json').read_bytes()).hexdigest(),'spec_sha256':hashlib.sha256((ROOT/'SPEC.md').read_bytes()).hexdigest(),'run_sha256':hashlib.sha256((ROOT/'run.py').read_bytes()).hexdigest(),'archive_sha256':hashlib.sha256(Path(archive).read_bytes()).hexdigest()},indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('archive');main(ap.parse_args().archive)
