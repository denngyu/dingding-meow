import unittest

import numpy as np

from cup_detection import (
    CUP_CLASSES,
    CUP_MIN_CONFIDENCE,
    CUP_MIN_OBJECTNESS,
    decode_cup_boxes,
    face_focus_region,
    is_cup_near_face,
    largest_face,
    remap_boxes,
)


class CupDetectionTests(unittest.TestCase):
    def test_wine_glass_class_is_excluded_to_avoid_eyeglass_false_positives(self):
        self.assertEqual(CUP_CLASSES, {39, 41})

    def test_lower_confidence_keeps_tilted_cup_candidates(self):
        self.assertEqual(CUP_MIN_CONFIDENCE, 0.28)
        detection = np.zeros(85, dtype=float)
        detection[:4] = (0.5, 0.5, 0.2, 0.4)
        detection[4] = 0.80
        detection[5 + 41] = 0.31

        boxes = decode_cup_boxes([np.array([detection])], 640, 480)

        self.assertEqual(boxes, [(256, 144, 128, 192)])

    def test_noise_below_threshold_is_rejected(self):
        detection = np.zeros(85, dtype=float)
        detection[:4] = (0.5, 0.5, 0.2, 0.4)
        detection[4] = 0.80
        detection[5 + 41] = 0.27
        self.assertEqual(decode_cup_boxes([np.array([detection])], 640, 480), [])

    def test_low_objectness_shape_is_rejected_even_with_a_cup_class_score(self):
        self.assertEqual(CUP_MIN_OBJECTNESS, 0.35)
        detection = np.zeros(85, dtype=float)
        detection[:4] = (0.5, 0.5, 0.2, 0.4)
        detection[4] = 0.20
        detection[5 + 41] = 0.90
        self.assertEqual(decode_cup_boxes([np.array([detection])], 640, 480), [])

    def test_face_focus_region_enlarges_and_clips_the_search_area(self):
        self.assertEqual(
            face_focus_region((480, 640), (250, 100, 100, 100)),
            (140, 60, 460, 340),
        )
        self.assertEqual(
            face_focus_region((120, 160), (5, 5, 60, 60)),
            (0, 0, 131, 120),
        )

    def test_crop_boxes_are_mapped_back_to_the_full_frame(self):
        self.assertEqual(
            remap_boxes([(10, 20, 30, 40)], offset_x=140, offset_y=60),
            [(150, 80, 30, 40)],
        )

    def test_largest_face_is_used_as_the_primary_drinking_region(self):
        self.assertEqual(
            largest_face([(10, 10, 40, 40), (100, 50, 90, 80)]),
            (100, 50, 90, 80),
        )
        self.assertIsNone(largest_face([]))

    def test_eyeglass_shaped_box_in_the_eye_region_is_rejected(self):
        face = (100, 100, 100, 100)
        eyeglasses = (105, 120, 90, 28)
        self.assertFalse(is_cup_near_face(face, eyeglasses))

    def test_real_and_slightly_tilted_cups_near_the_mouth_are_kept(self):
        face = (100, 100, 100, 100)
        self.assertTrue(is_cup_near_face(face, (140, 155, 50, 80)))
        self.assertTrue(is_cup_near_face(face, (125, 150, 80, 55)))

    def test_candidate_far_below_the_face_is_rejected(self):
        self.assertFalse(is_cup_near_face((100, 100, 100, 100), (130, 270, 50, 60)))

    def test_desktop_trash_can_below_the_chin_is_rejected(self):
        face = (100, 100, 100, 100)
        trash_can = (85, 225, 105, 145)
        self.assertFalse(is_cup_near_face(face, trash_can))


if __name__ == "__main__":
    unittest.main()
