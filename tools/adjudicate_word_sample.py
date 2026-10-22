"""Post-OCR full-label ruler review and OCR-independent ink-edge measurement.

Original pre-OCR annotations are preserved. All 33 sampled-word labels were
reread on unlabelled ruled row crops, not just failures. Manual whitespace
partitions establish token ownership; pixel masks measure ink within them.
This is post-hoc adjudication by the same reader, not a new blind test.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from image_io import open_rgb
from semantic_validation import ROOT, DATA
from word_validation_sample import MANUAL

# Whitespace-delimited partitions read from ruled scans. No OCR coordinates
# are inputs to the edge measurement; indices follow the frozen sample list.
PARTITIONS = {
    26: [(700, 852), (456, 535), (797, 846), (511, 618), (855, 918), (539, 686)],
    130: [(818, 892), (608, 680), (748, 865), (405, 539), (784, 889), (413, 589)],
    286: [(745, 892), (438, 502), (769, 847), (385, 496), (653, 844), (325, 440)],
    393: [(810, 943), (578, 669), (745, 812), (414, 554), (795, 860), (477, 590)],
    462: [(746, 849), (412, 502), (687, 892), (278, 382), (714, 791), (413, 517), (745, 875)],
    588: [(685, 790), (353, 490)],
}


def measure(image, partition, ink_class):
    x0, y0, x1, y1 = partition
    array = np.asarray(image.crop(partition), dtype=np.int16)
    r, g, b = array[..., 0], array[..., 1], array[..., 2]
    mask = ((r < 120) & (g < 120) & (b < 120) if ink_class == "black"
            else (r > 120) & (r - g > 45))
    yy, xx = np.where(mask)
    if not len(xx):
        raise AssertionError("manual word partition contains no target ink")
    contact = bool(xx.min() == 0 or xx.max() == x1 - x0 - 1)
    return dict(ink_pixels=int(mask.sum()), horizontal_partition_contact=contact,
                ink_bbox=[x0 + int(xx.min()), y0 + int(yy.min()),
                                                   x0 + int(xx.max()) + 1, y0 + int(yy.max()) + 1])


def build(stored=None):
    report = json.loads(MANUAL.read_text())
    measurements = {(p["page"], i): w["adjudication_pixels"] for p in stored["pages"]
                    for i, w in enumerate(p["word_samples"])} if stored else None
    for page in report["pages"]:
        n = page["page"]
        image = None
        if measurements is None:
            path = ROOT / "hayrat-pics" / f"page_{n}.png"
            if hashlib.sha256(path.read_bytes()).hexdigest() != page["image_sha256"]:
                raise AssertionError("adjudication scan hash differs")
            image = open_rgb(path)
        if len(PARTITIONS[n]) != len(page["word_samples"]):
            raise AssertionError("ruler partition count differs")
        for i, (word, (left, right)) in enumerate(zip(page["word_samples"], PARTITIONS[n])):
            row = 11 if word["selection"] == "supplemental_vocative" else (3, 8, 13)[i // 2]
            top = (row - 1) * 110 + 10
            partition = [left, top, right, top + 130]
            pixels = (measure(image, partition, word["ink_class"]) if image is not None
                      else measurements[(n, i)])
            box = pixels["ink_bbox"]
            word.update(original_rect=word["rect"], ruler_partition=partition, adjudication_pixels=pixels,
                        rect=[box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2],
                        x_edges=[box[0], box[2]],
                        boundary_eligible=not pixels["horizontal_partition_contact"])
    report["version"] = "ruler-adjudicated-word-sample-v2"
    report["adjudication"] = dict(
        source_sha256=hashlib.sha256(MANUAL.read_bytes()).hexdigest(),
        stage="post-OCR full-label ruler review by the same reader; not blind",
        correction="Original coarse windows were not precise ink extents; 17:57 word 15's window was on ان, "
                   "not عذاب. Every sampled label was reviewed, not only failures. Original labels retained.",
        measurement="Manual whitespace partitions from unlabelled ruled scans; black RGB<120 per channel, "
                    "colored R>120 and R-G>45. No OCR geometry used. Horizontal edges are measured ink extents "
                    "within these partitions, not certified inclusion of every diacritic. Ink contacting a "
                    "horizontal partition edge makes the boundary unscorable (overlap/clipping ambiguity). "
                    "Original +/-12px tolerance.")
    report["protocol"] += " Ordinary-word rectangles/edges in this version are post-OCR adjudicated; see adjudication."
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA / "audit_manual_word_validation_v2_adjudicated.json")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    if args.verify:
        saved = json.loads(args.output.read_text())
        if build(None if args.scans else saved) != saved:
            raise AssertionError("word-label adjudication does not reproduce")
        print("PASS full-label ruler adjudication, original-label provenance and "
              + ("scan pixel measurements" if args.scans else "stored pixel measurements"))
    else:
        report = build()
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        for p in report["pages"]:
            print(p["page"], [(w["form"], w["x_edges"]) for w in p["word_samples"]])


if __name__ == "__main__":
    main()
