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

    def test_promo_and_onepage_describe_the_v14_stable_features(self):
        root = Path(__file__).resolve().parents[1]
        promo = (root / "promo.html").read_text(encoding="utf-8")
        onepage = (root / "onepage.html").read_text(encoding="utf-8")

        for page in (promo, onepage):
            for phrase in (
                "v1.4",
                "滚到中央",
                "叩屏三次",
                "锁屏立即",
                "30 秒",
                "DingDingMeow-windows.zip",
            ):
                self.assertIn(phrase, page)
            self.assertNotIn("下载 v1.0", page)


if __name__ == "__main__":
    unittest.main()
