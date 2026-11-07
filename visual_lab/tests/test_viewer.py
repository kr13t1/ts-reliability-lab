import csv
import io
from contextlib import redirect_stdout
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from visual_lab import build as viewer


class StatelessHelpers(unittest.TestCase):
    def test_event_intervals_are_half_open(self):
        self.assertEqual(viewer.segments([0, 1, 1, 0, 1, 1, 1]), [[1, 3], [4, 7]])
        self.assertEqual(viewer.segments([0, 0]), [])

    def test_svg_marks_anchor_but_not_injected_start(self):
        reference = list(range(1220))
        observed = list(range(1220))
        assigned = [0] * 1220
        predicted = [0] * 1220
        assigned[1191:1210] = [1] * 19
        predicted[1190:1210] = [1] * 20
        svg = viewer.signal_svg(reference, observed, assigned, predicted, 1183, 1211, True)
        self.assertIn('i=1190 · FP', svg)
        self.assertIn('Назначено Z', svg)
        self.assertIn('Найдено Zhat', svg)
        self.assertNotIn('<script', svg)

    def test_numbers_never_treat_null_as_zero(self):
        self.assertEqual(viewer._rate('null'), 'не определено')
        self.assertEqual(viewer._rate('1.0'), '100.00%')

    def test_missing_input_is_controlled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = viewer.main(['--g23-dir', str(root/'unknown'),
                                  '--g24-dir', str(root/'missing'),
                                  '--output-dir', str(root/'output')])
            self.assertEqual(result, 2)
            self.assertFalse((root/'output').exists())

    def test_nonempty_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'old.txt').write_text('unchanged')
            with self.assertRaises(viewer.InputError):
                viewer.build(root, root, root)
            self.assertEqual((root/'old.txt').read_text(), 'unchanged')

    def test_invalid_csv_scheme(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'test.csv'
            p.write_text('wrong,column\n1,2\n',encoding='utf-8')
            with self.assertRaisesRegex(viewer.InputError, 'header/scheme'):
                viewer.read_csv(p, ('i', 'source_line'))

    def test_reject_malformed_binary_or_numeric_values(self):
        with self.assertRaises(viewer.InputError):
            viewer.number('nan', 'x')
        with self.assertRaises(viewer.InputError):
            viewer.integer('1.0', 'i')

    def test_windows_and_posix_provenance_are_same_canonical_key(self):
        pin = "1" * 64
        normalized = viewer.canonical_g24_files_sha({
            "results.csv": pin, r"1600_A_alpha_0\masks.csv": pin,
            "1600_A_alpha_1/masks.csv": pin,
        })
        self.assertEqual(normalized["1600_A_alpha_0/masks.csv"], pin)
        self.assertEqual(len(normalized), 3)

    def test_reject_windows_path_collisions(self):
        pin = "1" * 64
        with self.assertRaisesRegex(viewer.InputError, "colliding"):
            viewer.canonical_g24_files_sha({
                "1600_E_raw/masks.csv": pin,
                r"1600_E_raw\masks.csv": pin,
            })

    def test_reject_unsafe_windows_provenance_path(self):
        for bad in ("../results.csv", "/results.csv", r"C:\temp\results.csv",
                    r"..\results.csv", r"foo\\bar.csv", "./results.csv"):
            with self.subTest(path=bad), self.assertRaises(viewer.InputError):
                viewer.canonical_g24_files_sha({bad: "1" * 64})
        with self.assertRaises(viewer.InputError):
            viewer.canonical_g24_files_sha({"results.csv": "not-a-sha256"})


G23 = Path(os.environ.get('VISUAL_LAB_TEST_G23', 'g23/example'))
G24 = Path(os.environ.get('VISUAL_LAB_TEST_G24', 'output_g24'))


@unittest.skipUnless((G23/'alpha_0/arrays.csv').is_file() and (G24/'1600_E_raw/masks.csv').is_file(),
                     'integration: accepted G2.3 and generated G2.4 outputs are not available')
class IntegrationCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.g23 = root/'g23'
        self.g24 = root/'g24'
        shutil.copytree(G23, self.g23)
        shutil.copytree(G24, self.g24)

    def run_viewer(self, name='page', mode='strict'):
        out = Path(self.tmp.name)/name
        result = viewer.build(self.g23, self.g24, out, g24_png_mode=mode)
        return out, result

    def rewrite_prov(self):
        p = self.g24/'provenance.json'
        d = json.loads(p.read_text(encoding='utf-8'))
        d['files_sha256'] = {
            relative: hashlib.sha256((self.g24/relative).read_bytes()).hexdigest()
            for relative in d['files_sha256']
        }
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

    def make_windows_provenance(self):
        p = self.g24 / 'provenance.json'
        d = json.loads(p.read_text(encoding='utf-8'))
        d['files_sha256'] = {k.replace('/', '\\'): v for k, v in d['files_sha256'].items()}
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True)+'\n',
                     encoding='utf-8')

    def test_portable_windows_provenance_omits_unverified_g24_png(self):
        self.make_windows_provenance()
        # Original Windows uses different PNG bytes. They may be absent entirely
        # in the portable mode: do not read, validate, or display them.
        for case in viewer.CASE_IDS:
            (self.g24 / case / 'detection.png').unlink()
        out, result = self.run_viewer('portable', mode='omit')
        self.assertEqual(result['status'], 'PASS_PRESENTATION')
        page = (out / 'index.html').read_text(encoding='utf-8')
        manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
        self.assertIn('G2.4 PNG omitted', page)
        self.assertIn('1190 · FP', page)
        self.assertIn('TP 1191', page)
        self.assertEqual(page.count('data:image/png;base64,'), 2)  # Only accepted G2.3
        self.assertEqual(manifest['g24_png_mode'], 'omit')
        self.assertFalse(manifest['g24_png_verified'])
        self.assertFalse(manifest['g24_png_embedded'])
        self.assertNotIn('g24/1600_E_raw/detection.png', manifest['input_sha256'])
        self.assertEqual(manifest['input_sha256']['g24/1600_E_raw/masks.csv'],
                         viewer.G24_FIXED_PINS['1600_E_raw/masks.csv'])

    def test_portable_windows_provenance_rejects_mutated_standing_csv(self):
        self.make_windows_provenance()
        p = self.g24 / '1600_E_raw/masks.csv'
        with p.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            columns = reader.fieldnames
        self.assertIsNotNone(columns)
        rows[100]['obs_x'] = repr(float(rows[100]['obs_x']) + .125)
        with p.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        prov_path = self.g24 / 'provenance.json'
        prov = json.loads(prov_path.read_text(encoding='utf-8'))
        prov['files_sha256'][r'1600_E_raw\masks.csv'] = hashlib.sha256(p.read_bytes()).hexdigest()
        prov_path.write_text(json.dumps(prov, ensure_ascii=False), encoding='utf-8')
        with self.assertRaisesRegex(viewer.InputError, 'fixed-source SHA mismatch'):
            self.run_viewer('tampered_portable', mode='omit')

    def test_strict_windows_provenance_still_rejects_png_swap(self):
        self.make_windows_provenance()
        standing = self.g24 / '1600_E_raw/detection.png'
        walking = self.g24 / '1600_A_alpha_1/detection.png'
        standing.write_bytes(walking.read_bytes())
        prov_path = self.g24 / 'provenance.json'
        prov = json.loads(prov_path.read_text(encoding='utf-8'))
        prov['files_sha256'][r'1600_E_raw\detection.png'] = hashlib.sha256(standing.read_bytes()).hexdigest()
        prov_path.write_text(json.dumps(prov, ensure_ascii=False), encoding='utf-8')
        with self.assertRaisesRegex(viewer.InputError, 'fixed-source SHA mismatch'):
            self.run_viewer('tampered_strict', mode='strict')

    def test_snapshot_html_is_real_and_repeatable(self):
        out1, result1 = self.run_viewer('one')
        out2, result2 = self.run_viewer('two')
        self.assertEqual(result1['status'], 'PASS_PRESENTATION')
        self.assertEqual(result1['html_sha256'], result2['html_sha256'])
        self.assertEqual((out1/'index.html').read_bytes(), (out2/'index.html').read_bytes())
        page = (out1/'index.html').read_text()
        for key in ('1190 · FP', '1191', '1192', 'Walking', 'Standing', 'не определено',
                    'TP 1191', 'FP 1', 'data:image/png;base64,'):
            self.assertIn(key, page)
        manifest = json.loads((out1/'manifest.json').read_text())
        self.assertEqual(manifest['scope'], 'G2.3/G2.4 precomputed outputs; no detector run')
        self.assertFalse(manifest['read_raw'])
        self.assertFalse(manifest['recomputed_detector'])
        self.assertTrue(manifest['input_sha256']['g24/1600_E_raw/masks.csv'])
        self.assertEqual(manifest['viewer_executed_source_sha256'],
                         hashlib.sha256(Path(viewer.__file__).read_bytes()).hexdigest())
        if not (Path(viewer.__file__).resolve().parents[1]/'.git').exists():
            self.assertIsNone(manifest['viewer_git_sha'])

    def test_missing_png_rejected(self):
        (self.g24/'1600_E_raw/detection.png').unlink()
        with self.assertRaises(viewer.InputError):
            self.run_viewer()

    def test_sha_tamper_rejected(self):
        p = self.g24/'1600_A_alpha_1/masks.csv'
        p.write_bytes(p.read_bytes() + b'bad')
        with self.assertRaisesRegex(viewer.InputError, 'provenance/hash mismatch'):
            self.run_viewer()

    def test_mask_length_rejected_even_if_provenance_rehashed(self):
        p = self.g24/'1600_E_raw/masks.csv'
        lines = p.read_text(encoding='utf-8').splitlines(keepends=True)
        p.write_text(''.join(lines[:-1]), encoding='utf-8')
        self.rewrite_prov()
        with self.assertRaisesRegex(viewer.InputError, 'Incorrect mask length'):
            self.run_viewer()

    def test_wrong_assigned_mask_rejected_even_if_rehashed(self):
        p = self.g24/'1600_A_alpha_1/masks.csv'
        with p.open(encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        rows[1191]['Z_x'] = '0'
        with p.open('w',encoding='utf-8',newline='') as f:
            w = csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
            w.writeheader();w.writerows(rows)
        self.rewrite_prov()
        with self.assertRaisesRegex(viewer.InputError, 'Mask differs from frozen G2.3'):
            self.run_viewer()

    def test_wrong_source_line_rejected_even_if_rehashed(self):
        p = self.g24/'1600_E_raw/masks.csv'
        with p.open(encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        rows[0]['source_line'] = '999'
        with p.open('w',encoding='utf-8',newline='') as f:
            w = csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
            w.writeheader();w.writerows(rows)
        self.rewrite_prov()
        with self.assertRaisesRegex(viewer.InputError, 'Mask/source row identity'):
            self.run_viewer()

    def test_swapped_standing_png_with_self_declared_hash_is_rejected(self):
        standing_png = self.g24/'1600_E_raw/detection.png'
        walking_png = self.g24/'1600_A_alpha_1/detection.png'
        assert standing_png.read_bytes() != walking_png.read_bytes()
        standing_png.write_bytes(walking_png.read_bytes())  # valid, different PNG
        self.rewrite_prov()  # attacker also repairs the mutable hash map
        result = io.StringIO()
        out = Path(self.tmp.name)/'page'
        with redirect_stdout(result):
            status = viewer.main(['--g23-dir', str(self.g23), '--g24-dir', str(self.g24),
                                  '--output-dir', str(out)])
        self.assertEqual(status, 2)
        outcome = json.loads(result.getvalue())
        self.assertEqual(outcome['status'], 'REJECTED_INPUT')
        self.assertIn('fixed-source SHA mismatch: 1600_E_raw/detection.png', outcome['detail'])
        self.assertFalse((out/'index.html').exists())
        self.assertFalse((out/'manifest.json').exists())

    def test_standing_observation_rewrite_with_rehashed_provenance_is_rejected(self):
        p = self.g24/'1600_E_raw/masks.csv'
        with p.open(newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f); rows = list(reader)
            columns = reader.fieldnames
        assert columns is not None
        original = rows[100]['obs_x']
        rows[100]['obs_x'] = repr(float(original) + .125)
        with p.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
        self.rewrite_prov()  # attacker also repairs the mutable hash map
        result = io.StringIO()
        out = Path(self.tmp.name)/'page'
        with redirect_stdout(result):
            status = viewer.main(['--g23-dir', str(self.g23), '--g24-dir', str(self.g24),
                                  '--output-dir', str(out)])
        self.assertEqual(status, 2)
        outcome = json.loads(result.getvalue())
        self.assertEqual(outcome['status'], 'REJECTED_INPUT')
        self.assertIn('fixed-source SHA mismatch: 1600_E_raw/masks.csv', outcome['detail'])
        self.assertFalse((out/'index.html').exists())
        self.assertFalse((out/'manifest.json').exists())

    def test_wrong_provenance_type_is_refused(self):
        p = self.g24/'provenance.json'
        d = json.loads(p.read_text());d['files_sha256'] = None
        p.write_text(json.dumps(d),encoding='utf-8')
        with self.assertRaisesRegex(viewer.InputError, 'files_sha256 must be'):
            self.run_viewer()

    def test_invalid_g23_accepted_png_hash_fails(self):
        png = self.g23/'alpha_1/comparison.png'
        png.write_bytes(png.read_bytes() + b'corrupt')
        with self.assertRaisesRegex(viewer.InputError, 'G2.3 SHA mismatch'):
            self.run_viewer()


if __name__ == '__main__':
    unittest.main()
