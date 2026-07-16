"""把已去除色键的规则网格图集裁成盯盯喵运行帧。"""

import argparse
from pathlib import Path

from PIL import Image


FRAME_SIZE = 384


def keep_largest_alpha_component(frame, alpha_threshold=12):
    """移除图集相邻格串入的小碎片，只保留角色主体连通域。"""
    frame = frame.convert("RGBA")
    alpha = frame.getchannel("A")
    values = bytearray(alpha.tobytes())
    width, height = frame.size
    active = bytearray(value > alpha_threshold for value in values)
    largest = []

    for start in range(width * height):
        if not active[start]:
            continue
        active[start] = 0
        stack = [start]
        component = []
        while stack:
            index = stack.pop()
            component.append(index)
            x = index % width
            if x and active[index - 1]:
                active[index - 1] = 0
                stack.append(index - 1)
            if x + 1 < width and active[index + 1]:
                active[index + 1] = 0
                stack.append(index + 1)
            if index >= width and active[index - width]:
                active[index - width] = 0
                stack.append(index - width)
            if index + width < width * height and active[index + width]:
                active[index + width] = 0
                stack.append(index + width)
        if len(component) > len(largest):
            largest = component

    if not largest:
        return frame
    cleaned = bytearray(width * height)
    for index in largest:
        cleaned[index] = values[index]
    frame.putalpha(Image.frombytes("L", frame.size, bytes(cleaned)))
    return frame


def grid_boundaries(extent, parts):
    if extent < parts or parts < 1:
        raise ValueError("grid must have at least one source pixel per part")
    return [round(index * extent / parts) for index in range(parts + 1)]


def align_subject(frame, center_x=FRAME_SIZE // 2, ground_y=360):
    frame = frame.convert("RGBA")
    bbox = frame.getchannel("A").getbbox()
    if bbox is None:
        return frame
    subject_center = (bbox[0] + bbox[2]) / 2.0
    offset_x = int(round(center_x - subject_center))
    offset_y = int(round(ground_y - bbox[3]))
    aligned = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    aligned.alpha_composite(frame, (offset_x, offset_y))
    return aligned


def split_sheet(source_path, output_dir, columns, rows, frame_count, align=False):
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    with Image.open(source_path) as source:
        sheet = source.convert("RGBA")

    if frame_count > columns * rows:
        raise ValueError("frame count exceeds grid capacity")

    x_bounds = grid_boundaries(sheet.width, columns)
    y_bounds = grid_boundaries(sheet.height, rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index in range(frame_count):
        column = index % columns
        row = index // columns
        frame = sheet.crop(
            (
                x_bounds[column],
                y_bounds[row],
                x_bounds[column + 1],
                y_bounds[row + 1],
            )
        ).resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS)
        frame = keep_largest_alpha_component(frame)
        if align:
            frame = align_subject(frame)
        path = output_dir / ("frame_%02d.png" % index)
        frame.save(path, optimize=True)
        paths.append(path)
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output_dir")
    parser.add_argument("--columns", type=int, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--frames", type=int, required=True)
    parser.add_argument("--align-subject", action="store_true")
    args = parser.parse_args()
    paths = split_sheet(
        args.source,
        args.output_dir,
        args.columns,
        args.rows,
        args.frames,
        align=args.align_subject,
    )
    print("wrote %d frames to %s" % (len(paths), Path(args.output_dir).resolve()))


if __name__ == "__main__":
    main()
