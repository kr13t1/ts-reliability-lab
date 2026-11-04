"""LAB-027: three predetermined G2.4 cases, verified WISDM raw + G2.3 outputs.

Predictor stage receives only float64 observed_x. Assigned Z and reference
columns are opened by the evaluator after predictions have been completed.
No tuning, training, resampling, units of time, or source modification.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from g2 import readonly as ro  # accepted G2.2 parser; not copied or changed
from g23 import freeze as g23  # accepted G2.3 frozen pins; no new injection
from .detector import detect_constant_runs
from .evaluate import evaluate_mask

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'g24/configs/g24.json'
EXPECTED_MODE_SHA = {
    0: '6cf2fd4d19da30d00be7a4878a979c2d3828554715377c3bda5aaf384801f7d5',
    1: 'df34cf7dc715bf9e928560d26b6fb01f8299349a80e64a84c65f3f20807262f6',
}
EXPECTED_CONFIG_SHA = '889aa3940b23ab05e9c9a7abfa84810a9566f8b7466ef948c366d62431a0b463'
EXPECTED_SELECTION_SHA = 'ded1e5b64ad4dc054ed7fdeed426f295ff9daeb49a9430a931efe6e945ea80c7'
EXPECTED_RAW_SIZE = 3451789
EXPECTED_RAW_LINES = 64311
EXPECTED_A_LINES = (1,3574)
EXPECTED_E_LINES = (14292,17863)
G23_HEADER = ['i','source_line','q','ref_x','ref_y','ref_z','obs_x','obs_y','obs_z','Z_x','Z_y','Z_z']
RESULT_FIELDS = ['case_id','subject','activity','alpha','N','L','TP','FP','FN','TN','n_true','n_pred',
                 'precision','precision_null_reason','recall','recall_null_reason',
                 'FPR','FPR_null_reason','specificity','specificity_null_reason',
                 'n_true_events','n_pred_events','true_events_overlapped',
                 'pred_events_without_true_overlap','true_event_overlap_fraction']
EXPECTED_CONFIG = {
    'contract':'G24_CONSTANT_RUN_BASELINE_SPEC v0.1; LAB-027',
    'axis':'x', 'min_run_samples':3, 'epsilon':0, 'seed':None,
    'cases':['1600_A_alpha_0','1600_A_alpha_1','1600_E_raw'],
    'standing_start_line':14292, 'standing_end_line':17863,
    'standing_segment_sha256':'50edfd731735d54cd76fe4c0a38da914fca7b567ae4e3b3d389f2d687fadb61d',
    'raw_sha256':'40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f',
    'g23_reference_sha256':'8bf61ee71f68e0648ead7bc8eb8b6c44414e28411bd6de65e5f9dadf9c28eb38',
    'timestamp_unit':'UNKNOWN',
}


class Refusal(ValueError):
    def __init__(self, status: str, detail: str):
        super().__init__(detail)
        self.status = status


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha_file(path: Path) -> str:
    return ro.sha_file(path)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


def load_config(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError, UnicodeError) as exc:
        raise Refusal('REJECTED_CONFIG', f'config unavailable/invalid: {exc}') from exc
    if type(value) is not dict or set(value) != set(EXPECTED_CONFIG):
        raise Refusal('REJECTED_CONFIG', 'config fields differ from LAB-027')
    if any(type(value[key]) is not type(frozen) or value[key] != frozen
           for key, frozen in EXPECTED_CONFIG.items()):
        raise Refusal('REJECTED_CONFIG', 'frozen values differ; need new decision 00')
    return value


def _read_json(path: Path, status: str) -> dict:
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError, UnicodeError) as exc:
        raise Refusal(status, f'unavailable/invalid JSON {path.name}') from exc
    if type(obj) is not dict:
        raise Refusal(status, f'invalid JSON object {path.name}')
    return obj


def _check_bytes(path: Path, expected: str, label: str) -> bytes:
    try:
        blob = path.read_bytes()
    except OSError as exc:
        raise Refusal('BLOCKED_INPUT', f'{label}: missing file') from exc
    if sha256(blob) != expected:
        raise Refusal('BLOCKED_IDENTITY', f'{label}: SHA-256 mismatch: {sha256(blob)}')
    return blob


def read_observed_only(path: Path) -> np.ndarray:
    """Stage 1 reader: no reference values or assigned Z returned to detector."""
    try:
        with path.open('r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != G23_HEADER:
                raise Refusal('REJECTED_INPUT', 'G2.3 arrays header differs')
            xs = []
            for row in reader:
                try:
                    if None in row or any(v is None for v in row.values()):
                        raise ValueError('malformed CSV row')
                    xs.append(float(row['obs_x']))
                except ValueError as exc:
                    raise Refusal('REJECTED_INPUT', 'invalid observed_x token') from exc
    except (OSError, UnicodeError, csv.Error) as exc:
        raise Refusal('BLOCKED_INPUT', 'cannot read G2.3 arrays') from exc
    x = np.array(xs, dtype=np.float64)
    if x.size != EXPECTED_A_LINES[1] or not np.isfinite(x).all():
        raise Refusal('REJECTED_INPUT', 'G2.3 observed_x length/finite check failed')
    return x


def validate_g23_metadata(g23_dir: Path, config: dict) -> dict:
    prov = _read_json(g23_dir/'provenance.json', 'BLOCKED_INPUT')
    valid = _read_json(g23_dir/'validation.json', 'BLOCKED_INPUT')
    conf = _read_json(g23_dir/'config.json', 'BLOCKED_INPUT')
    sel = _read_json(g23_dir/'selection.json', 'BLOCKED_INPUT')
    if prov.get('status') != 'PASS_DEMO' or valid.get('status') != 'PASS_DEMO':
        raise Refusal('BLOCKED_IDENTITY', 'G2.3 input is not an accepted PASS_DEMO output')
    if prov.get('input_sha256') != config['raw_sha256'] or prov.get('reference_sha256') != config['g23_reference_sha256']:
        raise Refusal('BLOCKED_IDENTITY', 'G2.3 raw/reference identity mismatch')
    if conf != g23.CONFIG or sha_file(g23_dir/'config.json') != EXPECTED_CONFIG_SHA:
        raise Refusal('BLOCKED_IDENTITY', 'G2.3 contract config mismatch')
    if sha_file(g23_dir/'selection.json') != EXPECTED_SELECTION_SHA:
        raise Refusal('BLOCKED_IDENTITY', 'G2.3 selection differs')
    if (sel.get('subject'),sel.get('activity'),sel.get('start_line'),sel.get('end_line'),sel.get('n')) != (1600,'A',1,3574,3574):
        raise Refusal('BLOCKED_IDENTITY','G2.3 record selection differs')
    expected_files = {'reference.csv': config['g23_reference_sha256'],
                      'config.json': EXPECTED_CONFIG_SHA, 'selection.json': EXPECTED_SELECTION_SHA}
    expected_files.update({f'alpha_{a}/arrays.csv': d for a,d in EXPECTED_MODE_SHA.items()})
    for rel, digest in expected_files.items():
        _check_bytes(g23_dir/rel, digest, rel)
        if prov.get('files_sha256',{}).get(rel) != digest:
            raise Refusal('BLOCKED_IDENTITY', f'G2.3 provenance mismatch: {rel}')
    return {'g23_files_sha256':expected_files, 'g23_provenance_sha256':sha_file(g23_dir/'provenance.json')}


def read_raw_standing(raw_path: Path, config: dict) -> tuple[list, list, str]:
    blob = _check_bytes(raw_path, config['raw_sha256'], 'WISDM raw 1600')
    if len(blob) != EXPECTED_RAW_SIZE:
        raise Refusal('BLOCKED_IDENTITY','WISDM raw byte size differs')
    raw_lines = blob.splitlines(keepends=True)
    if len(raw_lines) != EXPECTED_RAW_LINES:
        raise Refusal('REPORT_MISMATCH', 'WISDM raw line count differs')
    segment = b''.join(raw_lines[EXPECTED_E_LINES[0]-1:EXPECTED_E_LINES[1]])
    digest = sha256(segment)
    if digest != config['standing_segment_sha256']:
        raise Refusal('REPORT_MISMATCH', 'Standing/E segment identity mismatch')
    # Reuse the audited G2.2 parser/record boundary logic without editing it.
    try:
        rows = ro.parse_file(blob)
        runs = ro.contiguous_runs(rows)
    except (ro.Refusal, ValueError) as exc:
        raise Refusal('REJECTED_INPUT', f'invalid raw rows: {exc}') from exc
    for label, start, end in [('A',*EXPECTED_A_LINES),('E',*EXPECTED_E_LINES)]:
        if runs.count((start,end,1600,label)) != 1:
            raise Refusal('REPORT_MISMATCH', f'{label} is not the exact contiguous raw run')
    if rows[EXPECTED_E_LINES[0]-2].activity!='D' or rows[EXPECTED_E_LINES[1]].activity!='F':
        raise Refusal('REPORT_MISMATCH', 'Standing neighbors differ')
    e = rows[EXPECTED_E_LINES[0]-1:EXPECTED_E_LINES[1]]
    q = [r.q for r in e]
    if len(e)!=3572 or (q[0], q[-1])!=(241892286783982,242072100924919) or any(v<=u for u,v in zip(q,q[1:])):
        raise Refusal('REPORT_MISMATCH', 'Standing q identity/order differs')
    return rows[:3574], e, digest


def validate_g23_arrays(path: Path, raw_rows: list, alpha: int, predicted: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    """Stage 2: read assigned Z only after the prediction exists."""
    if not isinstance(predicted, np.ndarray) or predicted.shape!=(3574,):
        raise Refusal('INVARIANT_FAILURE', 'prediction must already exist')
    with path.open('r',encoding='utf-8',newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != G23_HEADER:
            raise Refusal('REJECTED_INPUT', 'wrong arrays header')
        source_rows = list(reader)
    if len(source_rows)!=3574:
        raise Refusal('REPORT_MISMATCH', 'G2.3 arrays length mismatch')
    original = np.array([r.axes for r in raw_rows],dtype=np.float64).T
    reference = original.copy()
    expected_obs, expected_mask = g23.freeze(reference,alpha,g23.CONFIG['a'],g23.CONFIG['b'])
    true = np.zeros(3574,dtype=np.bool_)
    observed = np.zeros(3574,dtype=np.float64)
    for i,(row,r) in enumerate(zip(source_rows,raw_rows)):
        if row['i']!=str(i) or row['source_line']!=str(r.line) or row['q']!=str(r.q):
            raise Refusal('REPORT_MISMATCH', f'G2.3 index/source/q mismatch {i}')
        if any(row['ref_'+'xyz'[c]] != r.axes_tokens[c] for c in range(3)):
            raise Refusal('REPORT_MISMATCH', f'G2.3 reference tokens mismatch {i}')
        try:
            actual_obs=[float(row['obs_'+'xyz'[c]]) for c in range(3)]
        except (ValueError,TypeError) as exc:
            raise Refusal('REJECTED_INPUT','invalid observation token') from exc
        if any(not np.isfinite(v) or v!=expected_obs[c,i] for c,v in enumerate(actual_obs)):
            raise Refusal('REPORT_MISMATCH', f'G2.3 observed axes mismatch {i}')
        expected_bits=[int(expected_mask[c,i]) for c in range(3)]
        if [row['Z_'+c] for c in 'xyz'] != list(map(str,expected_bits)):
            raise Refusal('REPORT_MISMATCH', f'G2.3 assigned mask mismatch {i}')
        observed[i]=actual_obs[0]
        true[i]=bool(expected_bits[0])
    return observed,true


def _plot(path: Path, title: str, obs: np.ndarray, pred: np.ndarray, z: np.ndarray) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2,1,figsize=(12,5.8),sharex=True,gridspec_kw={'height_ratios':[2.5,1]})
    i=np.arange(obs.size)
    ax[0].plot(i,obs,lw=.75,color='#336b96',label='Observed x')
    ax[0].set_ylabel('x (WISDM original units)'); ax[0].grid(alpha=.2)
    ax[0].set_title(title+' · exact constant-run, L=3 · educational only')
    ax[1].step(i,pred.astype(int),where='mid',color='#dd6535',lw=1.5,label='Zhat, detection')
    ax[1].step(i,z.astype(int),where='mid',color='#1c8a68',lw=1.,linestyle='--',label='Z, assigned injection')
    ax[1].set_ylim(-.16,1.2);ax[1].set_yticks([0,1]);ax[1].grid(alpha=.2)
    ax[1].set_ylabel('Mask x only');ax[1].set_xlabel('Sample index i (not seconds; q units UNKNOWN)')
    ax[1].legend(loc='upper right',ncol=2,fontsize=8)
    fig.text(.02,.01,'Z=0 means no project injection, NOT verified healthy hardware. Offline detector; no sensor-fault ground truth.',fontsize=8)
    fig.tight_layout(rect=(0,.025,1,1));fig.savefig(path,dpi=140);plt.close(fig)


def _write_mask_csv(path: Path, rows: list, observed: np.ndarray, pred: np.ndarray, z: np.ndarray) -> None:
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,lineterminator='\n')
        w.writerow(['i','source_line','q','obs_x','Zhat_x','Z_x'])
        for i,r in enumerate(rows):
            w.writerow([i,r.line,str(r.q),repr(float(observed[i])),int(pred[i]),int(z[i])])


def _git_state() -> dict:
    try:
        head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True,timeout=2).stdout.strip()
        dirty=bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,text=True,capture_output=True,check=True,timeout=2).stdout)
        return {'git_sha':head,'git_dirty':dirty}
    except (OSError,subprocess.SubprocessError):
        return {'git_sha':None,'git_dirty':None}


def execute(g23_dir: Path, standing_input: Path, out: Path, config_path: Path,
            *, axis: str='x', L: int=3, invocation: list[str]|None=None) -> dict:
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise Refusal('OUTPUT_NOT_EMPTY','output directory must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    evidence = {'status':'PENDING','command_argv':invocation,'seed':None,
                'timestamp_unit':'UNKNOWN','session_id':None,'physical_continuity':'UNKNOWN',
                'full_remote_UCI_attestation':'UNVERIFIED','real_sensor_fault_labels':'UNKNOWN',
                'training_or_tuning':False,'detector_inputs':['observed_x','L'],
                'source_sha256':{p:sha_file(ROOT/p) for p in ['g24/demo.py','g24/detector.py','g24/evaluate.py',
                       'g24/configs/g24.json','g24/requirements.txt']},
                'versions':{'python':sys.version.split()[0], 'numpy':np.__version__},**_git_state()}
    try:
        config=load_config(config_path)
        if axis!='x' or type(L) is not int or L!=3:
            raise Refusal('REJECTED_CONFIG','frozen axis=x, min-run-samples=3, epsilon=0')
        g23_meta=validate_g23_metadata(g23_dir,config)
        walking,e_rows,segment_hash=read_raw_standing(standing_input,config)
        path0=g23_dir/'alpha_0/arrays.csv';path1=g23_dir/'alpha_1/arrays.csv'
        # Stage 1: observed-only; evaluator has not loaded Z from either CSV.
        observed={
            '1600_A_alpha_0':read_observed_only(path0),
            '1600_A_alpha_1':read_observed_only(path1),
            '1600_E_raw':np.asarray([r.axes[0] for r in e_rows],dtype=np.float64),
        }
        predicted={case: detect_constant_runs(signal, L) for case,signal in observed.items()}
        # Stage 2 (after all three Zhat masks exist): validate ground truth/metadata.
        obs0,z0=validate_g23_arrays(path0,walking,0,predicted['1600_A_alpha_0'])
        obs1,z1=validate_g23_arrays(path1,walking,1,predicted['1600_A_alpha_1'])
        if not np.array_equal(obs0,observed['1600_A_alpha_0']) or not np.array_equal(obs1,observed['1600_A_alpha_1']):
            raise Refusal('INVARIANT_FAILURE','stage-1/stage-2 observed mismatch')
        assigned={'1600_A_alpha_0':z0,'1600_A_alpha_1':z1,
                  '1600_E_raw':np.zeros(len(e_rows),dtype=np.bool_)}
        rows_for={'1600_A_alpha_0':walking,'1600_A_alpha_1':walking,'1600_E_raw':e_rows}
        reports=[]; details={}
        for case in config['cases']:
            metric=evaluate_mask(predicted[case],assigned[case])
            details[case]=metric
            alpha={'1600_A_alpha_0':'0','1600_A_alpha_1':'1','1600_E_raw':'none'}[case]
            reports.append({'case_id':case,'subject':1600,'activity':'E' if case.endswith('raw') else 'A',
                            'alpha':alpha,'L':L,**{k:metric[k] for k in ('N','TP','FP','FN','TN','n_true','n_pred',
                             'precision','precision_null_reason','recall','recall_null_reason',
                             'FPR','FPR_null_reason','specificity','specificity_null_reason')},
                             'n_true_events':len(metric['true_events']),
                             'n_pred_events':len(metric['pred_events']),
                             'true_events_overlapped':sum(metric['true_event_overlaps']),
                             'pred_events_without_true_overlap':metric['pred_events_without_true_overlap'],
                             'true_event_overlap_fraction':metric['true_event_overlap_fraction']})
        # All validation and predictions completed; now publish actual outputs.
        write_json(out/'config.json',config)
        for case in config['cases']:
            target=out/case;target.mkdir()
            _write_mask_csv(target/'masks.csv',rows_for[case],observed[case],predicted[case],assigned[case])
            _plot(target/'detection.png',case,observed[case],predicted[case],assigned[case])
        with (out/'results.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=RESULT_FIELDS,lineterminator='\n');w.writeheader()
            for row in reports: w.writerow({k:'null' if v is None else v for k,v in row.items()})
        write_json(out/'events.json',details)
        check={'status':'PASS_DEMO','stage':'G2.4_IMPLEMENTATION_ONLY',
               'scope':'three predetermined cases, no independence or real-fault claims',
               'checks':{'raw_sha':'PASS','standing_segment_sha':'PASS','g23_output_sha':'PASS',
                         'stage_separation':'PASS','three_cases':'PASS','no_parameter_tuning':'PASS'}}
        import matplotlib
        evidence['versions']['matplotlib']=matplotlib.__version__
        evidence['standing_segment_sha256']=segment_hash
        evidence['standing_raw_sha256']=sha_file(standing_input)
        evidence.update(g23_meta)
    except Refusal as exc:
        check={'status':exc.status,'detail':str(exc),'no_successful_results':True}
    except (OSError,ValueError,TypeError,csv.Error) as exc:
        check={'status':'REJECTED_INPUT','detail':str(exc),'no_successful_results':True}
    write_json(out/'validation.json',check)
    evidence['status']=check['status']
    evidence['files_sha256']={str(p.relative_to(out)):sha_file(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write_json(out/'provenance.json',evidence)
    return check


def main(argv: list[str]|None=None) -> int:
    p=argparse.ArgumentParser(description='Issue #20: fixed G2.4 exact constant-run baseline')
    p.add_argument('--g23-dir',type=Path,required=True)
    p.add_argument('--standing-input',type=Path,required=True,help='unmodified 1600 full raw TXT with Standing/E')
    p.add_argument('--axis',default='x')
    p.add_argument('--min-run-samples',type=int,default=3)
    p.add_argument('--config',type=Path,default=CONFIG_PATH)
    p.add_argument('--output-dir',type=Path,required=True)
    used=list(sys.argv[1:] if argv is None else argv)
    args=p.parse_args(used)
    try:
        result=execute(args.g23_dir,args.standing_input,args.output_dir,args.config,
                       axis=args.axis,L=args.min_run_samples,
                       invocation=[sys.executable,'-m','g24.demo',*used])
    except Refusal as exc:
        result={'status':exc.status,'detail':str(exc)}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0 if result['status']=='PASS_DEMO' else 2

if __name__=='__main__':
    raise SystemExit(main())
