"""Windows portability regression tests. No raw WISDM needed for unit cases."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from visual_lab import build as viewer


class CanonicalPathTests(unittest.TestCase):
    def test_windows_and_posix_relative_paths(self):
        original = {
            r"1600_A_alpha_0\masks.csv": "a" * 64,
            "1600_A_alpha_1/masks.csv": "b" * 64,
        }
        self.assertEqual(viewer.canonical_provenance_map(original), {
            "1600_A_alpha_0/masks.csv": "a" * 64,
            "1600_A_alpha_1/masks.csv": "b" * 64,
        })

    def test_reject_duplicate_canonical_paths(self):
        for bad in (
            {"a/b.csv": "x", r"a\b.csv": "y"},
            {"a/b.csv": "x", "a/b.csv/../b.csv": "y"},
            {"a//b.csv": "x"},
            {"../a.csv": "x"},
            {r"..\a.csv": "x"},
            {"/absolute.csv": "x"},
            {r"C:\Windows\file.csv": "x"},
            {"a/./b.csv": "x"},
            {"a/b.csv": None},
        ):
            with self.subTest(bad=bad), self.assertRaises(viewer.InputError):
                viewer.canonical_provenance_map(bad)

    def test_mode_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(viewer.InputError, "Invalid PNG mode"):
                viewer.verified_inputs(Path(tmp), Path(tmp), png_mode="invalid")



G23 = Path(os.environ.get("VISUAL_LAB_TEST_G23", "g23/example"))
G24 = Path(os.environ.get("VISUAL_LAB_TEST_G24", "output_g24"))


@unittest.skipUnless((G23/"alpha_0/arrays.csv").is_file() and
                     (G24/"1600_E_raw/masks.csv").is_file(),
                     "integration inputs missing; no fake PASS")
class PortableIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.g23, self.g24 = root/"g23", root/"g24"
        shutil.copytree(G23, self.g23)
        shutil.copytree(G24, self.g24)
        self.root = root

    def as_windows_provenance(self):
        path = self.g24/"provenance.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["files_sha256"] = {k.replace("/", "\\"): v
                               for k, v in data["files_sha256"].items()}
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def portable(self, folder="portable"):
        out = self.root/folder
        response = viewer.build(self.g23, self.g24, out, png_mode="omit")
        return out, response

    def test_windows_keys_png_bytes_not_required(self):
        self.as_windows_provenance()
        for case in viewer.CASE_IDS:
            (self.g24/case/"detection.png").unlink(missing_ok=True)
        out, result = self.portable()
        self.assertEqual(result["status"], "PASS_PRESENTATION")
        page = (out/"index.html").read_text(encoding="utf-8")
        manifest = json.loads((out/"manifest.json").read_text(encoding="utf-8"))
        self.assertIn("G2.4 PNG omitted / unverified", page)
        self.assertIn("1190 · FP", page)
        self.assertIn("TP 1191", page)
        self.assertNotIn("G2.4/detection.png", page)
        self.assertEqual(manifest["g24_png_mode"], "omit")
        self.assertFalse(any(k.endswith("detection.png")
                             for k in manifest["input_sha256"]))
        self.assertTrue(any(k.endswith("masks.csv")
                            for k in manifest["input_sha256"]))

    def test_standing_modified_plus_mutable_sha_rejected(self):
        self.as_windows_provenance()
        p = self.g24/"1600_E_raw/masks.csv"
        with p.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            columns = reader.fieldnames
        self.assertIsNotNone(columns)
        original = rows[100]["obs_x"]
        rows[100]["obs_x"] = repr(float(original) + 0.125)
        with p.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        data = p.read_bytes()
        prov = self.g24/"provenance.json"
        info = json.loads(prov.read_text(encoding="utf-8"))
        info["files_sha256"][r"1600_E_raw\masks.csv"] = hashlib.sha256(data).hexdigest()
        prov.write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaises(viewer.InputError):
            self.portable()

    def test_result_modified_and_self_declared_sha_rejected(self):
        self.as_windows_provenance()
        p = self.g24/"results.csv"
        p.write_bytes(p.read_bytes() + b"\n")
        prov = self.g24/"provenance.json"
        info = json.loads(prov.read_text(encoding="utf-8"))
        info["files_sha256"]["results.csv"] = hashlib.sha256(p.read_bytes()).hexdigest()
        prov.write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaisesRegex(viewer.InputError, "fixed-source SHA mismatch"):
            self.portable()

    def test_ambiguous_platform_names_rejected(self):
        self.as_windows_provenance()
        prov = self.g24/"provenance.json"
        info = json.loads(prov.read_text(encoding="utf-8"))
        info["files_sha256"]["1600_E_raw/masks.csv"] = info["files_sha256"][r"1600_E_raw\masks.csv"]
        prov.write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaisesRegex(viewer.InputError, "Ambiguous/colliding"):
            self.portable()


if __name__ == "__main__":
    unittest.main()
