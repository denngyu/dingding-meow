import unittest

from status_label import render_status_label


class StatusLabelTests(unittest.TestCase):
    def test_label_is_compact_and_uses_binary_alpha_for_color_key_window(self):
        image = render_status_label("久坐 32分钟")
        self.assertEqual(image.mode, "RGBA")
        self.assertLess(image.width, 150)
        self.assertLess(image.height, 36)
        self.assertLessEqual(set(image.getchannel("A").getdata()), {0, 255})


if __name__ == "__main__":
    unittest.main()
