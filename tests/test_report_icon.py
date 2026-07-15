import base64
import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from report_icon import (
    build_cat_head_image,
    build_report_favicon_data_uri,
    build_report_favicon_image,
    report_favicon_link,
    save_ico,
)


class ReportIconTests(unittest.TestCase):
    def test_favicon_is_a_visible_square_cat_crop(self):
        image = build_report_favicon_image()
        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.size, (64, 64))
        bbox = image.getchannel("A").getbbox()
        self.assertIsNotNone(bbox)
        self.assertGreater(bbox[2] - bbox[0], 40)
        self.assertGreater(bbox[3] - bbox[1], 40)

    def test_favicon_is_embedded_as_a_self_contained_png(self):
        data_uri = build_report_favicon_data_uri()
        self.assertTrue(data_uri.startswith("data:image/png;base64,"))
        payload = base64.b64decode(data_uri.split(",", 1)[1])
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        link = report_favicon_link()
        self.assertIn('rel="icon"', link)
        self.assertIn(data_uri, link)


class CatHeadImageTests(unittest.TestCase):
    def test_supports_arbitrary_sizes(self):
        for size in (16, 32, 128, 256):
            image = build_cat_head_image(size)
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.size, (size, size))

    def test_head_is_centered_with_padding(self):
        image = build_cat_head_image(64)
        bbox = image.getchannel("A").getbbox()
        self.assertIsNotNone(bbox)
        # 有留白：头不会顶到画布边框
        self.assertGreaterEqual(bbox[0], 1)
        self.assertGreaterEqual(bbox[1], 1)
        self.assertLessEqual(bbox[2], 63)
        self.assertLessEqual(bbox[3], 63)

    def test_favicon_delegates_to_cat_head(self):
        favicon = build_report_favicon_image()
        head = build_cat_head_image(64)
        # 两条路径应产出像素完全相同的图
        self.assertEqual(list(favicon.getdata()), list(head.getdata()))


class SaveIcoTests(unittest.TestCase):
    def test_writes_valid_multi_size_ico(self):
        with tempfile.TemporaryDirectory() as tmp:
            ico_path = Path(tmp) / "test.ico"
            save_ico(str(ico_path))
            self.assertTrue(ico_path.exists())
            self.assertGreater(ico_path.stat().st_size, 200)
            with Image.open(ico_path) as im:
                self.assertEqual(im.format, "ICO")
                # PIL 打开 ICO 会拿到最大尺寸的那一张
                self.assertGreaterEqual(im.size[0], 64)


if __name__ == "__main__":
    unittest.main()
