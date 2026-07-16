import unittest

import numpy as np

from face_detection import detect_face_boxes


class FakeCascade:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def detectMultiScale(self, image, **kwargs):
        self.calls.append((image.copy(), kwargs))
        if not self.results:
            return []
        return self.results.pop(0)


class FaceDetectionTests(unittest.TestCase):
    def setUp(self):
        self.gray = np.arange(80, dtype=np.uint8).reshape(8, 10)

    def test_frontal_detection_requires_overlap_from_both_cascades(self):
        frontal = FakeCascade([[(1, 2, 3, 4)]])
        alternate = FakeCascade([[(1, 2, 3, 4)]])
        profile = FakeCascade([[], []])

        boxes = detect_face_boxes(self.gray, frontal, alternate, profile)

        self.assertEqual(boxes, [(1, 2, 3, 4)])
        self.assertEqual(len(alternate.calls), 1)
        self.assertEqual(len(profile.calls), 0)

    def test_single_frontal_cascade_hit_is_rejected_as_false_positive(self):
        boxes = detect_face_boxes(
            self.gray,
            FakeCascade([[(1, 2, 3, 4)]]),
            FakeCascade([[]]),
            FakeCascade([[], []]),
        )

        self.assertEqual(boxes, [])

    def test_left_profile_is_used_when_frontal_detectors_miss(self):
        profile = FakeCascade([[(2, 1, 3, 4)], []])

        boxes = detect_face_boxes(
            self.gray, FakeCascade([[]]), FakeCascade([[]]), profile
        )

        self.assertEqual(boxes, [(2, 1, 3, 4)])
        self.assertEqual(len(profile.calls), 2)

    def test_right_profile_is_detected_on_flipped_frame_and_remapped(self):
        profile = FakeCascade([[], [(1, 1, 3, 4)]])

        boxes = detect_face_boxes(
            self.gray, FakeCascade([[]]), FakeCascade([[]]), profile
        )

        self.assertEqual(boxes, [(6, 1, 3, 4)])
        np.testing.assert_array_equal(profile.calls[1][0], self.gray[:, ::-1])

    def test_profile_detection_uses_more_tolerant_parameters(self):
        profile = FakeCascade([[], []])

        detect_face_boxes(self.gray, FakeCascade([[]]), FakeCascade([[]]), profile)

        kwargs = profile.calls[0][1]
        self.assertEqual(kwargs["scaleFactor"], 1.08)
        self.assertEqual(kwargs["minNeighbors"], 5)
        self.assertEqual(kwargs["minSize"], (60, 60))

    def test_same_static_shape_detected_as_both_profiles_is_rejected(self):
        profile = FakeCascade([[(2, 1, 3, 4)], [(5, 1, 3, 4)]])

        boxes = detect_face_boxes(
            self.gray,
            FakeCascade([[]]),
            FakeCascade([[]]),
            profile,
        )

        self.assertEqual(boxes, [])


if __name__ == "__main__":
    unittest.main()
