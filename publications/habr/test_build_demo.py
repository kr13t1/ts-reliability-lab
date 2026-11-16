"""Tests for snapshot-based Habr publication artifact reconstruction."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_demo


class ReconstructedPublicationTests(unittest.TestCase):
    def test_exact_reconstruction(self):
        rebuilt = build_demo.build()
        committed = (HERE / "demo" / "index.html").read_bytes()
        self.assertEqual(rebuilt, committed)
        self.assertEqual(hashlib.sha256(rebuilt).hexdigest(),
                         build_demo.EXPECTED_SHA256)

    def test_explicit_snapshot_boundary(self):
        source = (HERE / "source" / "template.html").read_text(encoding="utf-8")
        self.assertEqual(source.count(build_demo.PLACEHOLDER), 1)
        payload = build_demo.PAYLOAD.read_text(encoding="utf-8")
        self.assertIn('"walking"', payload)
        self.assertIn('"standing"', payload)

    def test_nondefault_output_does_not_change_committed_html(self):
        before = (HERE / "demo" / "index.html").read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "nested" / "index.html"
            output.parent.mkdir(parents=True)
            output.write_bytes(build_demo.build())
            self.assertEqual(output.read_bytes(), before)
        self.assertEqual(before, (HERE / "demo" / "index.html").read_bytes())

    def test_tampering_fails_validation(self):
        import json
        data = json.loads(build_demo.PAYLOAD.read_text(encoding="utf-8"))
        data["facts"]["metrics"]["freeze"]["fp"] = 0
        with self.assertRaises(ValueError):
            build_demo.validate(data)

    def test_freeze_boundary_includes_anchor_as_predicted(self):
        import json
        data = json.loads(build_demo.PAYLOAD.read_text(encoding="utf-8"))
        x = [r[0] for r in data["walking"]]
        x[1191:2382] = [x[1190]] * 1191
        mask = build_demo.run_mask(x)
        self.assertFalse(mask[1189])
        self.assertTrue(mask[1190])
        self.assertTrue(mask[2381])
        self.assertFalse(mask[2382])


if __name__ == "__main__":
    unittest.main()
