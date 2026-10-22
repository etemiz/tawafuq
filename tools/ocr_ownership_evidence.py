"""Conditional in-box ownership evidence from other word/rosette rectangles.

These masks are geometric hypotheses, not linguistic ownership certificates.
The column-shadow policy is an explicit aggressive stress test. No text,
manual annotations or tolerance is used to construct the proposed boxes.
"""
import hashlib
import math

import numpy as np

from ocr_ink_trim import TrimSpec, validate_box

POLICIES = ("other_words", "rosette_rectangles", "other_words_and_rosettes", "rosette_columns_stress")


def overlaps(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def rosette_box(row):
    # Cached widths/heights can come from gold rings or pale disks. Treat the
    # resulting rectangle as evidence only, not a certified full marker mask.
    return [math.floor(row["cx"]-row["w"]/2), math.floor(row["cy"]-row["h"]/2),
            math.ceil(row["cx"]+row["w"]/2), math.ceil(row["cy"]+row["h"]/2)]


def rectangle_mask(box, rectangles, columns=False):
    validate_box(box)
    x0, y0, x1, y1 = box
    result = np.zeros((y1-y0, x1-x0), dtype=bool)
    for rect in rectangles:
        if not overlaps(box, rect):
            continue
        left, right = max(x0, rect[0]), min(x1, rect[2])
        top, bottom = (y0, y1) if columns else (max(y0, rect[1]), min(y1, rect[3]))
        result[top-y0:bottom-y0, left-x0:right-x0] = True
    return result


def ink_mask(image, box, ink_class="mixed"):
    validate_box(box, image.size)
    array = np.asarray(image.crop(box), dtype=np.int16)
    r, g, b = array[..., 0], array[..., 1], array[..., 2]
    spec = TrimSpec()
    black = (r < spec.black_max_exclusive) & (g < spec.black_max_exclusive) & (b < spec.black_max_exclusive)
    colored = (r > spec.colored_red_min_exclusive) & (r-g > spec.colored_red_green_min_exclusive)
    if ink_class not in {"black", "colored", "mixed"}:
        raise AssertionError("unknown ink class")
    return black if ink_class == "black" else colored if ink_class == "colored" else black | colored


def project(mask):
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 2:
        raise AssertionError("need a two-dimensional mask")
    return dict(column_ink_counts=mask.sum(axis=0).tolist(), ink_pixels=int(mask.sum()),
                mask_sha256=hashlib.sha256(np.packbits(mask.reshape(-1)).tobytes()).hexdigest())


def check_projection(box, profile):
    validate_box(box)
    counts = profile["column_ink_counts"]
    if (len(counts) != box[2]-box[0] or any(not isinstance(n, int) or isinstance(n, bool)
            or not 0 <= n <= box[3]-box[1] for n in counts) or sum(counts) != profile["ink_pixels"]):
        raise AssertionError("invalid ownership projection")
    return counts


def proposal(box, possible, mandatory):
    """Exact in-box horizontal support, conditional on the measured M⊆S⊆P.

    Profiles replay horizontal extrema; scan replay verifies the actual pixel
    subset construction and mask digests. Empty M cannot certify any edge.
    """
    p, m = check_projection(box, possible), check_projection(box, mandatory)
    if any(a > b for a, b in zip(m, p)):
        raise AssertionError("mandatory projection exceeds possible ink")
    px, mx = [i for i, n in enumerate(p) if n], [i for i, n in enumerate(m) if n]
    optional = possible["ink_pixels"]-mandatory["ink_pixels"]
    if not mx:
        return dict(bbox=list(box), status="empty_mandatory_fallback" if px else "no_threshold_ink",
                    optional_ink_pixels=optional, conditional_edge_support=None, horizontal_invariant=None)
    support = [[box[0]+x for x in px if x <= mx[0]], [box[0]+x+1 for x in px if x >= mx[-1]]]
    candidate = [box[0]+mx[0], box[1], box[0]+mx[-1]+1, box[3]]
    return dict(bbox=candidate, status="mandatory_ink_hull", optional_ink_pixels=optional,
                conditional_edge_support=support, horizontal_invariant=all(len(s) == 1 for s in support))


def measure(image, box, other_boxes, rosettes, truth_label=None):
    possible = ink_mask(image, box)
    words = rectangle_mask(box, other_boxes)
    markers = rectangle_mask(box, rosettes)
    shadows = rectangle_mask(box, rosettes, columns=True)
    masks = dict(other_words=words, rosette_rectangles=markers,
                 other_words_and_rosettes=words | markers, rosette_columns_stress=shadows)
    truth = None
    reference = None
    if truth_label is not None:
        partition = truth_label["partition"]
        full = ink_mask(image, partition, truth_label["ink_class"])
        truth = np.zeros_like(possible)
        if overlaps(box, partition):
            left, top = max(box[0], partition[0]), max(box[1], partition[1])
            right, bottom = min(box[2], partition[2]), min(box[3], partition[3])
            truth[top-box[1]:bottom-box[1], left-box[0]:right-box[0]] = full[
                top-partition[1]:bottom-partition[1], left-partition[0]:right-partition[0]]
        if np.any(truth & ~possible):
            raise AssertionError("manual target ink not contained in the in-box threshold union")
        reference = dict(partition=partition, ink_class=truth_label["ink_class"], full_manual_ink_pixels=int(full.sum()),
                         in_box_projection=project(truth))
        if reference["full_manual_ink_pixels"] != truth_label["pixels"]["ink_pixels"]:
            raise AssertionError("clear manual target scan pixels differ")
    result = dict(possible=project(possible), clear_manual_reference=reference, policies={})
    for name, mask in masks.items():
        mandatory = possible & ~mask
        if np.any(mandatory & ~possible):
            raise AssertionError("ownership construction violates pixel containment")
        profile = project(mandatory)
        if truth is not None:
            profile["mandatory_target_column_counts"] = (mandatory & truth).sum(axis=0).tolist()
        result["policies"][name] = profile
    return result


def reference_checks(box, candidate, possible, mandatory, reference):
    if reference is None:
        return None
    p, m = check_projection(box, possible), check_projection(box, mandatory)
    truth = check_projection(box, reference["in_box_projection"])
    target = mandatory["mandatory_target_column_counts"]
    if (len(target) != len(truth) or any(not isinstance(n, int) or isinstance(n, bool) or
            not 0 <= n <= min(t, a) for n, t, a in zip(target, truth, m))
            or any(t > a for t, a in zip(truth, p))):
        raise AssertionError("invalid target/mandatory intersection projection")
    outside = reference["full_manual_ink_pixels"]-sum(truth)
    if outside < 0:
        raise AssertionError("in-box target exceeds full manual target ink")
    left, right = candidate[0]-box[0], candidate[2]-box[0]
    newly_clipped = sum(truth[:left])+sum(truth[right:])
    return dict(mandatory_non_target_pixels=sum(m)-sum(target),
                target_pixels_made_optional=sum(truth)-sum(target),
                target_pixels_outside_original_box=outside,
                extra_target_pixels_clipped=newly_clipped,
                target_pixels_outside_candidate_box=outside+newly_clipped)
