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


def _overlap_ratio(first, second):
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    left = max(ax, bx)
    top = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)
    if right <= left or bottom <= top:
        return 0.0
    intersection = (right - left) * (bottom - top)
    return intersection / float(min(aw * ah, bw * bh))


def _confirmed_boxes(primary, secondary, minimum_overlap=0.5):
    return [
        box
        for box in primary
        if any(_overlap_ratio(box, other) >= minimum_overlap for other in secondary)
    ]


def _remove_opposite_profile_duplicates(left_boxes, right_boxes):
    """同一静态纹理若正反都像侧脸，宁可拒绝，避免柜体/花纹长期冒充人。"""
    ambiguous_left = {
        index
        for index, box in enumerate(left_boxes)
        if any(_overlap_ratio(box, other) >= 0.65 for other in right_boxes)
    }
    ambiguous_right = {
        index
        for index, box in enumerate(right_boxes)
        if any(_overlap_ratio(box, other) >= 0.65 for other in left_boxes)
    }
    return (
        [box for index, box in enumerate(left_boxes) if index not in ambiguous_left]
        + [box for index, box in enumerate(right_boxes) if index not in ambiguous_right]
    )


def detect_face_boxes(gray, frontal, alternate, profile):
    """正脸需双分类器交叉确认；失败时再检查左右侧脸。"""
    frontal_boxes = _detect(frontal, gray, 1.1, 5, (80, 80))
    alternate_boxes = _detect(alternate, gray, 1.1, 5, (80, 80))
    confirmed = _confirmed_boxes(frontal_boxes, alternate_boxes)
    if confirmed:
        return confirmed

    left_boxes = _detect(profile, gray, 1.08, 5, (60, 60))
    flipped = np.ascontiguousarray(gray[:, ::-1])
    flipped_boxes = _detect(profile, flipped, 1.08, 5, (60, 60))
    width = gray.shape[1]
    right_boxes = [(width - x - w, y, w, h) for x, y, w, h in flipped_boxes]
    return _remove_opposite_profile_duplicates(left_boxes, right_boxes)
