"""Image/pin checks on the new pre-OCR six-page name annotation sample."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from alignment import ScoreSpec, reference_flags
from image_io import open_rgb
import map_tokens as mt
from semantic_validation import (ROOT, DATA, corpus_targets, independent_ink,
                                 load_pins, assess_pins)

MANUAL = DATA / "audit_manual_ocr_heldout.json"


def analyze(stored_pixels=None):
    manual = json.loads(MANUAL.read_text())
    verses = mt.load_tokens()
    pages, labels, positions = [], {}, {}
    for page in manual["pages"]:
        n = page["page"]
        targets = corpus_targets(verses, page["first_verse"], page["last_verse"])
        if [(x["verse"], x["occurrence"], x["form"]) for x in targets] != [
                (x["verse"], x["occurrence"], x["form"]) for x in page["names"]]:
            raise AssertionError("held-out exact name census differs")
        image = None
        if stored_pixels is None:
            path = ROOT / "hayrat-pics" / f"page_{n}.png"
            if hashlib.sha256(path.read_bytes()).hexdigest() != page["image_sha256"]:
                raise AssertionError("held-out image hash differs")
            image = open_rgb(path)
        rows, coords = [], []
        for target, label in zip(targets, page["names"]):
            pixels = (independent_ink(image, label["rect"]) if image is not None
                      else stored_pixels[str(target["t"])])
            labels[target["t"]] = dict(**label, page=n)
            rows.append(dict(**target, rect=label["rect"], pixels=pixels))
            coords.append((int(((label["rect"][1] + label["rect"][3]) / 2 - 60) / 110 + 0.5),
                           pixels["cx"]))
        positions[n] = np.array(coords, dtype=float).reshape(-1, 2)
        pages.append(dict(page=n, names=rows, target_names=len(rows)))
    flags = reference_flags(positions, ScoreSpec(pairing="none"))
    for page in pages:
        coords = positions[page["page"]]
        page["column_aligned_names"] = int(flags[page["page"]][0].sum())
        page["distance_aligned_names"] = sum(any(li != lj and abs(xi - xj) <= 15
                                                 for lj, xj in coords) for li, xi in coords)
    pin_path = DATA / "mark_identity_semantic_v4.json"
    pins = assess_pins(load_pins(pin_path, set(positions)), labels)
    source = json.loads(pin_path.read_text())["audit"]["component_source"]
    paths = [MANUAL, DATA / "quran-uthmani.json", pin_path,
             *(DATA / source / f"page_{n:03d}.json" for n in positions)]
    return dict(version="heldout-semantic-check-v1", pages=pages, total_names=len(labels),
                colored_names=sum(x["pixels"]["colored_pixels"] > 0 for p in pages for x in p["names"]),
                column_aligned_names=sum(p["column_aligned_names"] for p in pages),
                distance_aligned_names=sum(p["distance_aligned_names"] for p in pages),
                pins_v4=pins, inputs={str(p.relative_to(DATA)): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in paths},
                caveat="Fresh stratified sample, one AI reader. Windows localize name cores, not boundaries. "
                "Alignment rates are descriptive. V4 pin rules were not tuned on these pages. "
                "CPU replay uses saved pixel measurements; --scans independently rereads images.")


def verify(path, scans=False):
    saved = json.loads(path.read_text())
    pixels = {str(x["t"]): x["pixels"] for p in saved["pages"] for x in p["names"]}
    if analyze(None if scans else pixels) != saved:
        raise AssertionError("held-out semantic check does not reproduce")
    print("PASS held-out name census, ink measurements, v4 token/localization check and hashes"
          + ("; scans reread" if scans else "; stored pixels"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA / "audit_semantic_heldout.json")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify(args.output, args.scans)
    else:
        report = analyze()
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print({k: v for k, v in report.items() if k not in ("pages", "inputs", "pins_v4")})
        print("v4 pins", {k: v for k, v in report["pins_v4"].items() if k != "predictions_detail"})


if __name__ == "__main__":
    main()
