"""Re-run the unchanged local experiment using the existing committed reference CSV."""
import argparse, csv, hashlib, json, shutil
from pathlib import Path
import numpy as np
import run

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT.parents[1] / 'g23/example/reference.csv'
REF_BLOB = '3af84ad7262d64508e6c6e02ca144b9aeac10e19'

def read_reference(path, c):
    b = path.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    assert blob == REF_BLOB, blob
    rows = list(csv.DictReader(b.decode().splitlines()))
    assert len(rows) == 3574
    assert [int(r['i']) for r in rows] == list(range(3574))
    assert [int(r['source_line']) for r in rows] == list(range(1, 3575))
    assert all(r['subject'] == str(c['subject']) and r['activity'] == c['activity'] for r in rows)
    q = [int(r['q']) for r in rows]
    assert all(v > u for u, v in zip(q, q[1:]))
    x = np.asarray([float(r['xyz'[c['axis']]]) for r in rows])
    assert np.isfinite(x).all()
    return x

def compare(path, actual, keyfields, metrics, count):
    a = list(csv.DictReader(path.open()))
    b = list(csv.DictReader(actual.open()))
    assert len(a) == len(b) == count
    assert len({tuple(r[k] for k in keyfields) for r in a}) == count
    for x, y in zip(a, b):
        assert all(x[k] == y[k] for k in keyfields)
        for k in metrics:
            np.testing.assert_allclose(float(x[k]), float(y[k]), rtol=1e-9, atol=1e-10, err_msg=str((x, k)))

def main(out):
    out = out.resolve()
    assert out != ROOT and not out.exists(), 'Choose a new output directory'
    out.mkdir(parents=True)
    for name in ['config.json', 'SPEC.md', 'run.py']:
        shutil.copy2(ROOT / name, out / name)
    config = json.loads((ROOT / 'config.json').read_text())
    read_reference(REFERENCE, config)
    run.ROOT = out
    run.load = read_reference
    run.main(REFERENCE)
    p = json.loads((out / 'provenance.json').read_text())
    p.pop('archive_sha256')
    p.pop('raw_sha256')
    p.update(input_kind='previously_committed_reference_csv_not_raw_archive', reference_path='g23/example/reference.csv', reference_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), reference_git_blob=REF_BLOB, adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out / 'provenance.json').write_text(json.dumps(p, indent=2))
    compare(ROOT/'results.csv', out/'results.csv', ['start','length','method'], ['mae','rmse','outside_max'],96)
    compare(ROOT/'summary.csv', out/'summary.csv', ['length','method','wins_vs_hold','windows'], ['mean_rmse','mean_mae'],12)
    print('PASS: all 96 result rows and 12 summary rows reproduced within tolerance on pinned reference CSV; raw not independently rerun.')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    main(ap.parse_args().out)
