import unittest
from pathlib import Path


class PromoEntrypointTests(unittest.TestCase):
    def test_github_pages_entrypoint_matches_promo_page(self):
        root = Path(__file__).resolve().parents[1]

        self.assertEqual(
            (root / "index.html").read_bytes(),
            (root / "promo.html").read_bytes(),
            "GitHub Pages serves index.html, so it must stay in sync with promo.html",
        )


if __name__ == "__main__":
    unittest.main()
