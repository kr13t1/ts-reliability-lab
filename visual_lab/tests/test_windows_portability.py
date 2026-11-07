"""Windows portability regression tests. No raw WISDM needed for unit cases."""
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

    def test_portable_html_never_claims_g24_png_verified(self):
        # This synthetic test exercises only rendering. It is NOT a G2.4 experiment.
        fake = {"metrics": {"TP": "0", "FP": "0", "FN": "0", "TN": "1",
                            "N": "1", "precision": "null", "recall": "null"}}
        cases = {key: {**fake, "image": None, "observed": [0.0], "z": [0], "pred": [0]}
                 for key in viewer.CASE_IDS}
        g23_rows = [{"ref_x": "0"}]
        model = {"cases": cases, "g23_rows": {1: g23_rows},
                 "images": {"g23_alpha_0": "eA==", "g23_alpha_1": "eA=="}}
        # render() uses frozen boundary indices; SVG is valid even for a tiny
        # synthetic array because it only reads an empty zoom selection via slicing.
        # Instead of claiming coverage from a fabricated model, test the actual
        # portable input gate in the integration tests below.
        self.assertIsNone(cases[viewer.CASE_IDS[0]]["image"])


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
        data = p.read_bytes().replace(b",0,0\n", b",1,0\n", 1)
        self.assertNotEqual(data, p.read_bytes(), "Fixture failed to modify Standing")
        p.write_bytes(data)
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
