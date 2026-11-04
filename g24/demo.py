"""G2.4 only: verified WISDM 1600/A and 1600/E, offline exact constant-run."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import platform
import numpy as np
from .detector import detect_constant_runs
from .evaluator import evaluate_mask

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / 'config.json').read_text(encoding='utf-8'))

class Refusal(ValueError):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code


def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def read_raw(path):
    try: raw = path.read_bytes()
    except OSError as exc: raise Refusal('BLOCKED_INPUT', 'raw file missing') from exc
    if sha(raw) != CONFIG['raw_sha256']:
        raise Refusal('BLOCKED_IDENTITY', 'full raw SHA mismatch')
    lines = raw.splitlines(keepends=True)
    if len(lines) != 64311:
        raise Refusal('BLOCKED_IDENTITY', 'wrong physical line count')
    segment = b''.join(lines[14291:17863])
    if sha(segment) != CONFIG['standing_segment_sha256']:
        raise Refusal('BLOCKED_IDENTITY', 'Standing contiguous segment SHA mismatch')
    def parse(lo, hi, activity):
        result=[]
        for lineno in range(lo,hi+1):
            try:
                line=lines[lineno-1].decode('ascii').rstrip('\r\n')
                if not line.endswith(';') or line.count(';') != 1: raise ValueError('terminator')
                fields=line[:-1].split(',')
                if len(fields)!=6 or fields[0]!='1600' or fields[1]!=activity: raise ValueError('record identity')
                if not fields[2].isdigit(): raise ValueError('integer timestamp')
                xyz=np.array([float(s) for s in fields[3:]],dtype=np.float64)
                if not np.isfinite(xyz).all(): raise ValueError('nonfinite')
                result.append((lineno, fields[2], xyz, fields[3:]))
            except (ValueError,UnicodeDecodeError) as exc:
                raise Refusal('REJECTED_INPUT', f'malformed source line {lineno}') from exc
        q=[int(r[1]) for r in result]
        if any(q[i+1]<=q[i] for i in range(len(q)-1)):
            raise Refusal('BLOCKED_IDENTITY','nonincreasing q within run')
        return result
    # Explicit gates; adjacent boundaries must NOT be silently joined.
    if b',A,' not in lines[0] or b',B,' not in lines[3574] or b',D,' not in lines[14290] or b',F,' not in lines[17863]:
        raise Refusal('BLOCKED_IDENTITY','source activity boundaries differ')
    walking=parse(1,3574,'A')
    standing=parse(14292,17863,'E')
    if (walking[0][1],walking[-1][1]) != ('252207666810782','252387581668153') or (standing[0][1],standing[-1][1]) != ('241892286783982','242072100924919'):
        raise Refusal('BLOCKED_IDENTITY','source q boundaries differ')
    return raw, walking, standing


def read_g23(path, reference, alpha):
    filename=path/f'alpha_{alpha}'/'arrays.csv'
    try:
        with filename.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise Refusal('BLOCKED_INPUT',f'G2.3 arrays.csv missing or unreadable ({alpha})') from exc
    expected={'i','source_line','q','ref_x','ref_y','ref_z','obs_x','obs_y','obs_z','Z_x','Z_y','Z_z'}
    if len(rows)!=len(reference) or not rows or set(rows[0])!=expected:
        raise Refusal('BLOCKED_IDENTITY','G2.3 CSV shape/header mismatch')
    observed=np.empty((3,len(rows)),dtype=np.float64)
    assigned=np.empty(len(rows),dtype=np.uint8)
    try:
        for i,(item, ref) in enumerate(zip(rows,reference)):
            if int(item['i'])!=i or int(item['source_line'])!=ref[0] or item['q']!=ref[1]:
                raise ValueError('source id/q changed')
            if [item[k] for k in ('ref_x','ref_y','ref_z')] != ref[3]:
                raise ValueError('reference original tokens changed')
            for c,axis in enumerate('xyz'):
                observed[c,i]=float(item['obs_'+axis])
                if not np.isfinite(observed[c,i]): raise ValueError('nonfinite observed')
                if int(item['Z_'+axis])!= (int(alpha==1 and c==0 and 1191<=i<2382)):
                    raise ValueError('assigned mask differs from accepted G2.3')
            assigned[i]=int(item['Z_x'])
        x=np.stack([r[2] for r in reference],axis=1)
        expected_obs=x.copy()
        if alpha==1: expected_obs[0,1191:2382]=x[0,1190]
        if not np.array_equal(observed,expected_obs): raise ValueError('observed not accepted G2.3 freeze')
        if not np.array_equal(observed[1:],x[1:]): raise ValueError('y/z changed')
    except (ValueError,TypeError,KeyError,IndexError) as exc:
        raise Refusal('BLOCKED_IDENTITY','G2.3 source/values/masks mismatch: '+str(exc)) from exc
    return observed,assigned


def save_plot(path, observed_x, pred, z, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes=plt.subplots(2,1,figsize=(12,5),sharex=True,gridspec_kw={'height_ratios':[3,1]})
    axes[0].plot(np.arange(len(observed_x)),observed_x,lw=.7)
    axes[0].set_ylabel('Observed x (WISDM units)')
    axes[0].set_title(title)
    axes[1].step(np.arange(len(pred)),pred,label='Zhat / predicted',where='mid')
    axes[1].step(np.arange(len(z)),z,label='Z / assigned injection',where='mid',alpha=.7)
    axes[1].set_ylim(-.1,1.2);axes[1].legend(loc='upper right');axes[1].set_ylabel('Mask')
    axes[1].set_xlabel('Index in original activity run (samples, not seconds)')
    fig.tight_layout();fig.savefig(path,dpi=110);plt.close(fig)


def run(g23_dir, standing_input, output, config_path, axis, L):
    if output.exists() and any(output.iterdir()):
        raise Refusal('OUTPUT_NOT_EMPTY','require new/empty output directory')
    output.mkdir(parents=True,exist_ok=True)
    try:
        try: config=json.loads(config_path.read_text(encoding='utf-8'))
        except (OSError,ValueError) as exc: raise Refusal('REJECTED_CONFIG','unreadable config') from exc
        if config!=CONFIG or axis!='x' or type(L) is not int or L!=3:
            raise Refusal('REJECTED_CONFIG','frozen configuration, axis x and L=3 required')
        raw, walking, standing = read_raw(standing_input)
        cases=[]
        for alpha in (0,1):
            obs,z=read_g23(g23_dir, walking, alpha)
            cases.append((f'walking_alpha_{alpha}','A',str(alpha),walking,obs,z))
        sx=np.stack([r[2] for r in standing],axis=1)
        cases.append(('standing_no_injection','E','none',standing,sx,np.zeros(len(standing),dtype=np.uint8)))
        # Only observed_x enters the detector. No assignment/metadata in inference.
        predictions=[detect_constant_runs(obs[0].copy(),L=3) for _,_,_,_,obs,_ in cases]
        evaluations=[evaluate_mask(p,z) for p,(*_,z) in zip(predictions,cases)]
        write_json(output/'config.json',config)
        summaries=[]
        for (name,activity,alpha,rows,obs,z),pred,ev in zip(cases,predictions,evaluations):
            dest=output/name;dest.mkdir()
            with (dest/'masks.csv').open('w',newline='',encoding='utf-8') as f:
                writer=csv.writer(f,lineterminator='\n');writer.writerow(('i','source_line','q','observed_x','Zhat_x','Z_x'))
                for i,r in enumerate(rows): writer.writerow((i,r[0],r[1],repr(float(obs[0,i])),int(pred[i]),int(z[i])))
            save_plot(dest/'comparison.png',obs[0],pred,z,f'WISDM 1600 / {activity} / {name} (not physical fault labels)')
            write_json(dest/'events.json',{k:ev[k] for k in ('true_events','predicted_events','true_event_overlap','predicted_nonoverlap_events','event_overlap_fraction')})
            summaries.append({'case':name,'source_id':'1600','activity':activity,'alpha':alpha,'L':3,**{k:v for k,v in ev.items() if k not in ('true_events','predicted_events','true_event_overlap','predicted_nonoverlap_events','event_overlap_fraction')}})
        with (output/'results.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(summaries[0]),lineterminator='\n');writer.writeheader()
            for row in summaries: writer.writerow({k:'null' if v is None else v for k,v in row.items()})
        write_json(output/'results.json',summaries)
        status={'status':'READY_FOR_INDEPENDENT_05_AUDIT','cases':len(cases),'no_training':True,'no_remote_attestation':True}
        write_json(output/'validation.json',status)
        import matplotlib
        provenance={'raw_sha256':sha(raw),'input_g23_sha256':{f'alpha_{a}/arrays.csv':sha((g23_dir/f'alpha_{a}'/'arrays.csv').read_bytes()) for a in (0,1)},'standing_segment_sha256':CONFIG['standing_segment_sha256'],'source_sha256':{p.name:sha(p.read_bytes()) for p in sorted(HERE.glob('*.py'))},'spec':'G24_CONSTANT_RUN_BASELINE_SPEC.md v0.1 / LAB-027','git_sha':None,'seed':None,'timestamp_unit':'UNKNOWN','session_id':None,'full_UCI_remote_attestation':'UNVERIFIED','versions':{'python':platform.python_version(),'numpy':np.__version__,'matplotlib':matplotlib.__version__},'limitations':'Only injection-relative FP/FPR; one subject, not independent observations; not hardware validation','output_sha256':{str(p.relative_to(output)):sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}}
        write_json(output/'provenance.json',provenance)
        return status
    except Refusal as exc:
        status={'status':exc.code,'reason':str(exc)}
        write_json(output/'validation.json',status)
        return status


def main(argv=None):
    parser=argparse.ArgumentParser(description='LAB-027 G2.4 frozen constant-run baseline')
    parser.add_argument('--g23-dir',required=True,type=Path)
    parser.add_argument('--standing-input',required=True,type=Path,help='verified full unmodified data_1600_accel_phone.txt (Standing segment extracted read-only)')
    parser.add_argument('--axis',default='x')
    parser.add_argument('--min-run-samples',type=int,default=3)
    parser.add_argument('--config',type=Path,default=HERE/'config.json')
    parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        status=run(args.g23_dir,args.standing_input,args.output_dir,args.config,args.axis,args.min_run_samples)
    except Refusal as exc: status={'status':exc.code,'reason':str(exc)}
    print(json.dumps(status,ensure_ascii=False))
    return 0 if status['status']=='READY_FOR_INDEPENDENT_05_AUDIT' else 2

if __name__=='__main__':raise SystemExit(main())
