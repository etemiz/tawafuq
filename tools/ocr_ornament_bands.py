"""Detect wide gold ornament bands from pixels, without Quran/map labels.

Verse rosettes are small; an ornament must span a substantial page width
and form a vertically extended band. Only OCR regions centered inside the
resulting bands are excluded by the versioned corpus-map wrapper.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from image_io import open_rgb
from semantic_validation import ROOT, DATA

OUTPUT = DATA / "audit_ocr_ornament_bands_v1.json"
SPEC = dict(minimum_row_fraction=.25, maximum_row_gap=16, minimum_band_height=60,
            red_minimum=60, green_minimum=55, blue_maximum=125,
            red_green_minimum=-20, red_green_maximum=80, green_blue_minimum=30)


def detect(image, spec=SPEC):
    array = np.asarray(image, dtype=np.int16)
    r, g, b = array[..., 0], array[..., 1], array[..., 2]
    gold = ((r > spec["red_minimum"]) & (g > spec["green_minimum"]) & (b < spec["blue_maximum"])
            & (r - g > spec["red_green_minimum"]) & (r - g < spec["red_green_maximum"])
            & (g - b > spec["green_blue_minimum"]))
    rows = np.flatnonzero(gold.mean(axis=1) >= spec["minimum_row_fraction"])
    groups = []
    for y in rows:
        if groups and y - groups[-1][-1] <= spec["maximum_row_gap"] + 1:
            groups[-1].append(int(y))
        else:
            groups.append([int(y)])
    return [[group[0], group[-1] + 1] for group in groups
            if group[-1] + 1 - group[0] >= spec["minimum_band_height"]]


def analyze():
    manifest_path = DATA / "google_corpus_manifest_v1.json"
    manifest = json.loads(manifest_path.read_text())
    pages = []
    for page in manifest["pages"]:
        path = ROOT / "hayrat-pics" / f'page_{page["page"]}.png'
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != page["image_sha256"]:
            raise AssertionError("ornament scan differs from OCR manifest")
        pages.append(dict(page=page["page"], image_sha256=digest, bands=detect(open_rgb(path))))
    return dict(version="pixel-gold-ornament-bands-v1", spec=SPEC, pages=pages,
                manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                pages_with_bands=sum(bool(p["bands"]) for p in pages),
                total_bands=sum(len(p["bands"]) for p in pages),
                caveat="Wide tall gold bands from pixels, no verse/rosette labels. "
                "This is an ornament-detection hypothesis, not independently certified segmentation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("gold ornament bands do not reproduce from scans")
        print("PASS image-derived ornament bands and all 604 scan hashes")
    else:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print("ornament pages", report["pages_with_bands"], "bands", report["total_bands"])


if __name__ == "__main__":
    main()
