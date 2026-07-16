"""YOLO杯子候选解码与近脸区域复检几何。"""

import numpy as np


CUP_CLASSES = {39, 41}
CUP_MIN_CONFIDENCE = 0.28
CUP_MIN_OBJECTNESS = 0.35


def decode_cup_boxes(outputs, frame_width, frame_height, min_confidence=CUP_MIN_CONFIDENCE):
    boxes = []
    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = int(np.argmax(scores))
            confidence = float(scores[class_id])
            objectness = float(detection[4])
            if (
                class_id not in CUP_CLASSES
                or confidence < min_confidence
                or objectness < CUP_MIN_OBJECTNESS
            ):
                continue
            center_x = float(detection[0]) * frame_width
            center_y = float(detection[1]) * frame_height
            width = float(detection[2]) * frame_width
            height = float(detection[3]) * frame_height
            boxes.append((
                round(center_x - width / 2),
                round(center_y - height / 2),
                round(width),
                round(height),
            ))
    return boxes


def face_focus_region(frame_shape, face):
    frame_height, frame_width = frame_shape[:2]
    x, y, width, height = face
    left = max(0, round(x - 1.1 * width))
    top = max(0, round(y - 0.4 * height))
    right = min(frame_width, round(x + 2.1 * width))
    bottom = min(frame_height, round(y + 2.4 * height))
    return left, top, right, bottom


def remap_boxes(boxes, offset_x, offset_y):
    return [
        (x + offset_x, y + offset_y, width, height)
        for x, y, width, height in boxes
    ]


def largest_face(faces):
    if not faces:
        return None
    return max(faces, key=lambda box: box[2] * box[3])


def is_cup_near_face(face, cup):
    face_x, face_y, face_width, face_height = face
    cup_x, cup_y, cup_width, cup_height = cup
    if min(face_width, face_height, cup_width, cup_height) <= 0:
        return False

    # 眼镜误报通常位于脸上半部、横向很扁；真实杯子应延伸到嘴部下方。
    cup_center_y = cup_y + cup_height / 2
    cup_bottom = cup_y + cup_height
    if cup_height < face_height * 0.30:
        return False
    aspect_ratio = cup_width / cup_height
    if aspect_ratio < 0.20 or aspect_ratio > 1.65:
        return False
    if cup_width > face_width * 1.10 or cup_height > face_height * 1.65:
        return False
    if cup_center_y < face_y + face_height * 0.42:
        return False
    if cup_bottom < face_y + face_height * 0.65:
        return False
    if cup_center_y - (face_y + face_height) > face_height * 0.60:
        return False
    # 桌面垃圾桶通常落在扩展人脸框内，但顶部仍明显低于下巴；
    # 真正举到嘴边的杯子顶部应与下脸重叠，或至多相差很小距离。
    face_bottom = face_y + face_height
    if cup_y - face_bottom > face_height * 0.18:
        return False

    expanded_x = face_x - face_width * 0.5
    expanded_y = face_y - face_height * 0.18
    expanded_width = face_width * 2.0
    expanded_height = face_height * 1.78
    overlaps_x = min(expanded_x + expanded_width, cup_x + cup_width) - max(expanded_x, cup_x)
    overlaps_y = min(expanded_y + expanded_height, cup_y + cup_height) - max(expanded_y, cup_y)
    return overlaps_x > 0 and overlaps_y > 0
