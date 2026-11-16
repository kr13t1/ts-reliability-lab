"""Raw-independent checks for the versioned Habr presentation artifact.

Does not perform sensor-fault detection, verify source WISDM, or certify UI UX.
"""
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_HTML_SHA256 = "9d45b2f740415f19d8857beafa0cffd6150748571eb94841744cb085c200a684"

class HabrPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob = (ROOT / "demo" / "index.html").read_bytes()
        cls.page = cls.blob.decode("utf-8")
        cls.article = (ROOT / "ARTICLE.md").read_text(encoding="utf-8")

    def test_exact_html_sha(self):
        self.assertEqual(hashlib.sha256(self.blob).hexdigest(), EXPECTED_HTML_SHA256)

    def test_embedded_data_and_no_script_downloads(self):
        self.assertIn("const DB=", self.page)
        self.assertNotIn("__DATA_PAYLOAD__", self.page)
        self.assertNotIn('src="http', self.page)
        self.assertNotIn("fetch(", self.page)
        self.assertNotIn("XMLHttpRequest", self.page)

    def test_controls_and_disclaimers(self):
        for token in ('data-case="clean"', 'data-case="freeze"',
                      'data-case="standing"', 'data-axis="y"',
                      'data-zoom="boundary"', 'data-visible="reference"'):
            with self.subTest(token=token):
                self.assertIn(token, self.page)
        self.assertIn("неаудированный интерактивный UI-прототип", self.page)
        self.assertIn("не проверяли шагомеры", self.page.lower())
        self.assertIn("10.24432/C5HK59", self.page)

    def test_article_requires_release_links(self):
        # Draft assertion: this version is not yet allowed to be published.
        self.assertIn("ССЫЛКА НА ПУБЛИЧНОЕ HTML-ДЕМО", self.article)
        self.assertIn("figures/overview.svg", self.article)
        self.assertIn("figures/boundary.svg", self.article)
        self.assertTrue((ROOT / "figures" / "overview.svg").is_file())
        self.assertTrue((ROOT / "figures" / "boundary.svg").is_file())

if __name__ == "__main__":
    unittest.main()
