"""Scan-component granularity diagnostics, with no inferred word ownership.

Manual partitions are evaluation only. The oracle error is the minimum number
of in-box pixel mistakes if each connected component is kept or removed whole.
It is a lower bound for that restricted model, not an implementable predictor.
"""
import itertools

import numpy as np
from scipy.ndimage import label, find_objects

from ocr_ownership_evidence import ink_mask, overlaps


def index_components(mask, connectivity):
    if connectivity not in (4, 8):
        raise AssertionError("connectivity must be 4 or 8")
    structure = np.ones((3, 3), dtype=bool) if connectivity == 8 else np.array(
        [[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    indexed, count = label(mask, structure)
    counts = np.bincount(indexed.ravel(), minlength=count+1)
    boxes = find_objects(indexed)
    return indexed, counts, boxes


def component_records(index, box, truth=None, origin=(0, 0)):
    """Describe full indexed components touching B; score only pixels inside B."""
    indexed, counts, boxes = index
    x0, y0, x1, y1 = box
    ox, oy = origin
    local = indexed[y0-oy:y1-oy, x0-ox:x1-ox]
    ids, local_counts = np.unique(local, return_counts=True)
    target_counts = np.bincount(local[truth], minlength=len(counts)) if truth is not None else None
    records = []
    for component, inside in zip(ids.tolist(), local_counts.tolist()):
        if component == 0:
            continue
        ys, xs = boxes[component-1]
        row = dict(component_id=component, bbox=[xs.start+ox, ys.start+oy, xs.stop+ox, ys.stop+oy],
                   in_box_ink_pixels=inside, frame_ink_pixels=int(counts[component]),
                   outside_box_ink_pixels=int(counts[component])-inside)
        if target_counts is not None:
            target = int(target_counts[component])
            row.update(target_ink_pixels=target, non_target_ink_pixels=inside-target)
        records.append(row)
    return records


def summarize(records, has_reference):
    result = dict(components=len(records), in_box_ink_pixels=sum(r["in_box_ink_pixels"] for r in records),
                  components_extending_outside_box=sum(r["outside_box_ink_pixels"] > 0 for r in records))
    if not has_reference:
        return result
    mixed = [r for r in records if r["target_ink_pixels"] and r["non_target_ink_pixels"]]
    result.update(target_ink_pixels=sum(r["target_ink_pixels"] for r in records),
                  non_target_ink_pixels=sum(r["non_target_ink_pixels"] for r in records),
                  target_components=sum(r["target_ink_pixels"] > 0 for r in records),
                  pure_target_components=sum(r["target_ink_pixels"] > 0 and not r["non_target_ink_pixels"] for r in records),
                  pure_foreign_components=sum(r["non_target_ink_pixels"] > 0 and not r["target_ink_pixels"] for r in records),
                  mixed_components=len(mixed), target_ink_in_mixed_components=sum(r["target_ink_pixels"] for r in mixed),
                  non_target_ink_in_mixed_components=sum(r["non_target_ink_pixels"] for r in mixed),
                  oracle_minimum_pixel_errors=sum(min(r["target_ink_pixels"], r["non_target_ink_pixels"]) for r in records),
                  exact_in_box_partition_representable=not mixed)
    return result


def reference_mask(image, box, reference):
    if reference is None:
        return None
    truth = ink_mask(image, box, reference["ink_class"])
    selected = np.zeros_like(truth)
    partition = reference["partition"]
    if overlaps(box, partition):
        left, top = max(box[0], partition[0]), max(box[1], partition[1])
        right, bottom = min(box[2], partition[2]), min(box[3], partition[3])
        selected[top-box[1]:bottom-box[1], left-box[0]:right-box[0]] = True
    return truth & selected


def measure(image, box, reference=None, page_indices=None):
    possible = ink_mask(image, box)
    truth = reference_mask(image, box, reference)
    if truth is not None and int(truth.sum()) != reference["in_box_projection"]["ink_pixels"]:
        raise AssertionError("component manual reference differs from frozen ownership evidence")
    if page_indices is None:
        full = ink_mask(image, [0, 0, image.width, image.height])
        page_indices = {c: index_components(full, c) for c in (4, 8)}
    result = {}
    for connectivity, frame in itertools.product((4, 8), ("crop", "page")):
        index = index_components(possible, connectivity) if frame == "crop" else page_indices[connectivity]
        records = component_records(index, box, truth, origin=tuple(box[:2]) if frame == "crop" else (0, 0))
        result[f"{frame}_{connectivity}"] = dict(components=records, summary=summarize(records, truth is not None))
    return result


def verify_measurement(box, pixels, measured):
    """Scan-free accounting checks; only scan replay verifies connectivity."""
    expected = pixels["possible"]["ink_pixels"]
    reference = pixels["clear_manual_reference"]
    for mode in ("crop_4", "crop_8", "page_4", "page_8"):
        entry = measured[mode]
        ids = set()
        for row in entry["components"]:
            component = row["component_id"]
            if component <= 0 or component in ids:
                raise AssertionError("invalid component identifier")
            ids.add(component)
            n, full = row["in_box_ink_pixels"], row["frame_ink_pixels"]
            if not 0 < n <= full or row["outside_box_ink_pixels"] != full-n:
                raise AssertionError("invalid component ink accounting")
            if not overlaps(box, row["bbox"]):
                raise AssertionError("component does not touch the crop")
            if mode.startswith("crop") and (full != n or any(
                    not lo <= value <= hi for value, lo, hi in zip(row["bbox"], box[:2]*2, box[2:]*2))):
                raise AssertionError("crop component exceeds its frame")
            if reference is not None and (not 0 <= row["target_ink_pixels"] <= n or
                    row["target_ink_pixels"]+row["non_target_ink_pixels"] != n):
                raise AssertionError("invalid component reference partition")
        summary = summarize(entry["components"], reference is not None)
        if summary != entry["summary"] or summary["in_box_ink_pixels"] != expected:
            raise AssertionError("component summary differs")
        if reference is not None and summary["target_ink_pixels"] != reference["in_box_projection"]["ink_pixels"]:
            raise AssertionError("component target total differs")
    if reference is not None:
        error = {mode: entry["summary"]["oracle_minimum_pixel_errors"] for mode, entry in measured.items()}
        # Coarsening a partition restricts feasible whole-component assignments.
        if not (error["crop_4"] <= error["crop_8"] <= error["page_8"] and
                error["crop_4"] <= error["page_4"] <= error["page_8"]):
            raise AssertionError("coarser components improved the exact oracle lower bound")
