"""Independent raw-free consistency checks for the frozen publication payload.

These tests do not authenticate the WISDM source or reproduce the missing
raw-dependent HTML builder. They independently recompute the displayed
constant-run masks from the signal arrays already embedded in HTML.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "demo" / "index.html"


def load_payload():
    page = HTML.read_text(encoding="utf-8")
    start_token = "const DB="
    end_token = ";\nconst ST="
    if page.count(start_token) != 1 or page.count(end_token) != 1:
        raise AssertionError("Unexpected embedded payload format")
    return json.loads(page.split(start_token, 1)[1].split(end_token, 1)[0])


def constant_run_mask(values, minimum=3):
    result = [False] * len(values)
    start = 0
    for end in range(1, len(values) + 1):
        if end == len(values) or values[end] != values[start]:
            if end - start >= minimum:
                for index in range(start, end):
                    result[index] = True
            start = end
    return result


def confusion(expected, predicted):
    return {
        "tp": sum(a and b for a, b in zip(expected, predicted)),
        "fp": sum(not a and b for a, b in zip(expected, predicted)),
        "fn": sum(a and not b for a, b in zip(expected, predicted)),
        "tn": sum(not a and not b for a, b in zip(expected, predicted)),
    }


class EmbeddedPayloadConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = load_payload()

    def test_shapes_and_source_metadata(self):
        db = self.db
        self.assertEqual(len(db["walking"]), 3574)
        self.assertEqual(len(db["standing"]), 3572)
        for record in (db["walking"], db["standing"]):
            self.assertTrue(all(len(row) == 3 for row in record))
            self.assertTrue(all(isinstance(value, (int, float)) for row in record for value in row))
        self.assertEqual(db["facts"]["subject"], 1600)
        self.assertEqual(db["facts"]["freeze"], [1191, 2382])
        self.assertEqual(db["facts"]["pred"], [1190, 2382])
        self.assertEqual(db["provenance"]["browser_detector_executed"], False)

    def test_independent_masks_and_metrics(self):
        db = self.db
        start, end = db["facts"]["freeze"]
        for name, record in (("clean", db["walking"]),
                             ("freeze", db["walking"]),
                             ("standing", db["standing"])):
            x = [row[0] for row in record]
            expected = [False] * len(x)
            if name == "freeze":
                x[start:end] = [x[start - 1]] * (end - start)
                expected[start:end] = [True] * (end - start)
            predicted = constant_run_mask(x)
            self.assertEqual(
                confusion(expected, predicted),
                db["facts"]["metrics"][name],
                msg=name,
            )
            if name == "freeze":
                self.assertEqual(
                    [i for i, flagged in enumerate(predicted) if flagged],
                    list(range(*db["facts"]["pred"])),
                )

    def test_article_discloses_single_episode_and_boundary(self):
        article = (ROOT / "ARTICLE.md").read_text(encoding="utf-8")
        self.assertIn("1191 TP", article)
        self.assertIn("1190", article)
        self.assertIn("не 1191 независим", article)
        self.assertIn("искусствен", article.lower())


if __name__ == "__main__":
    unittest.main()
