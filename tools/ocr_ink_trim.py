"""Experimental horizontal-only ink hull inside an existing OCR box.

Inference uses the image and box only. It neither expands a box nor changes
its vertical extent, identity, text support or acceptance. This is not word
segmentation: all thresholded ink, including neighboring marks, is retained.
"""
from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class TrimSpec:
    black_max_exclusive: int = 120
    colored_red_min_exclusive: int = 120
    colored_red_green_min_exclusive: int = 45


def validate_box(box, size=None):
    if (len(box) != 4 or any(not isinstance(x, int) or isinstance(x, bool) for x in box)
            or not (0 <= box[0] < box[2] and 0 <= box[1] < box[3])):
        raise AssertionError("need a positive, integer, half-open image box")
    if size and (box[2] > size[0] or box[3] > size[1]):
        raise AssertionError("OCR box outside image bounds")


def measure(image, box, spec=TrimSpec()):
    validate_box(box, image.size)
    array = np.asarray(image.crop(box), dtype=np.int16)
    r, g, b = array[..., 0], array[..., 1], array[..., 2]
    mask = ((r < spec.black_max_exclusive) & (g < spec.black_max_exclusive)
            & (b < spec.black_max_exclusive)) | (
                (r > spec.colored_red_min_exclusive) & (r-g > spec.colored_red_green_min_exclusive))
    return dict(column_ink_counts=mask.sum(axis=0).tolist(), row_ink_counts=mask.sum(axis=1).tolist())


def trim(box, pixels):
    """Replay a measured crop; an ink-empty box is preserved, not certified."""
    validate_box(box)
    x0, y0, x1, y1 = box
    columns, rows = pixels["column_ink_counts"], pixels["row_ink_counts"]
    if (len(columns) != x1-x0 or len(rows) != y1-y0
            or any(not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= y1-y0 for n in columns)
            or any(not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= x1-x0 for n in rows)
            or sum(columns) != sum(rows)):
        raise AssertionError("invalid ink projection counts")
    xs, ys = [i for i, n in enumerate(columns) if n], [i for i, n in enumerate(rows) if n]
    if not xs:
        return dict(bbox=list(box), status="no_threshold_ink", ink_pixels=0,
                    removed_horizontal_margins=[0, 0], vertical_ink_contact=False)
    candidate = [x0+xs[0], y0, x0+xs[-1]+1, y1]
    return dict(bbox=candidate, status="trimmed" if candidate != list(box) else "unchanged",
                ink_pixels=sum(columns), ink_bbox=[candidate[0], y0+ys[0], candidate[2], y0+ys[-1]+1],
                removed_horizontal_margins=[xs[0], x1-candidate[2]],
                vertical_ink_contact=bool(rows[0] or rows[-1]))


def specification():
    return dict(spec=asdict(TrimSpec()), geometry="horizontal_minimal_hull_inside_original_box",
                empty_crop="preserve_original_box", acceptance="preserve_original_acceptance",
                vertical_extent="unchanged", expansion="never")
