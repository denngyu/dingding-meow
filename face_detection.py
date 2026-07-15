"""多角度 Haar 人脸检测，包含正脸、左右侧脸。"""

import numpy as np


def load_face_cascades(cv2_module):
    root = cv2_module.data.haarcascades
    names = (
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt.xml",
        "haarcascade_profileface.xml",
    )
    cascades = tuple(cv2_module.CascadeClassifier(root + name) for name in names)
    if any(cascade.empty() for cascade in cascades):
        raise RuntimeError("OpenCV Haar face cascade failed to load")
    return cascades


def _detect(cascade, image, scale_factor, min_neighbors, min_size):
    boxes = cascade.detectMultiScale(
        image,
        scaleFactor=scale_factor,
        minNeighbors=min_neighbors,
        minSize=min_size,
    )
    return [tuple(int(value) for value in box) for box in boxes]


def detect_face_boxes(gray, frontal, alternate, profile):
    """按低成本顺序检测；正脸失败时同时检查左右侧脸。"""
    boxes = _detect(frontal, gray, 1.1, 5, (80, 80))
    if boxes:
        return boxes

    boxes = _detect(alternate, gray, 1.1, 5, (80, 80))
    if boxes:
        return boxes

    left_boxes = _detect(profile, gray, 1.08, 4, (60, 60))
    flipped = np.ascontiguousarray(gray[:, ::-1])
    flipped_boxes = _detect(profile, flipped, 1.08, 4, (60, 60))
    width = gray.shape[1]
    right_boxes = [(width - x - w, y, w, h) for x, y, w, h in flipped_boxes]
    return left_boxes + right_boxes
