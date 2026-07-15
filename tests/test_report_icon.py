import base64
import unittest

from PIL import Image

from report_icon import build_report_favicon_data_uri, build_report_favicon_image, report_favicon_link


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


if __name__ == "__main__":
    unittest.main()
