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

    def test_promo_and_onepage_describe_the_shipped_features(self):
        root = Path(__file__).resolve().parents[1]
        promo = (root / "promo.html").read_text(encoding="utf-8")
        onepage = (root / "onepage.html").read_text(encoding="utf-8")

        for page in (promo, onepage):
            for phrase in (
                "v1.5",
                # v1.4 起的招牌能力
                "滚到中央",
                "叩屏三次",
                "锁屏立即",
                "30 秒",
                # v1.5 新增的两个用户可见功能
                "延时摄影",
                "皮肤",
                "DingDingMeow-windows.zip",
            ):
                self.assertIn(phrase, page)
            # 发布页不能再挂旧版本号的下载按钮
            for stale in ("下载 v1.0", "下载 v1.4"):
                self.assertNotIn(stale, page)


if __name__ == "__main__":
    unittest.main()
