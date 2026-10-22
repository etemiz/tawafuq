"""Inventory structural consistency, keeping it separate from ground truth.

python tools/audit_integrity.py [--scans]
All checks read project-local files. Optional scan hashes describe inputs,
not permission to redistribute the page images.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

import map_tokens as mt
from alignment import ScoreSpec, encode
from real_stats import load_all

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data"


def report(include_scans=False):
    corpus = json.loads((DATA / "quran-uthmani.json").read_text())["verses"]
    stream = mt.load_tokens()
    flat = [(s, a, t) for s, a, ts in stream for t in ts]
    raw_count = sum(len(v["text_uthmani"].split()) for v in corpus)
    token_map = json.loads((DATA / "token_map2.json").read_text())
    records = token_map["map"]
    indices = [r["t"] for r in records]
    invalid = [t for t in indices if not 0 <= t < len(flat)]
    reversed_x = [r["t"] for r in records if r.get("x") and r["x"][0] > r["x"][1]]
    spans = {int(k): v for k, v in token_map["spans"].items()}
    gaps = [p for p in sorted(spans) if p + 1 in spans and spans[p][1] + 1 != spans[p + 1][0]]
    with np.load(DATA / "rosette_seq.npz", allow_pickle=False) as archive:
        meta = archive["meta"]
    assigned = (meta[:, 3] > 0) & (meta[:, 4] > 0)
    raw_read = meta[:, 5] >= 0
    agree = assigned & raw_read & (meta[:, 4] == meta[:, 5])
    pins_report = {}
    for filename in ("mark_identity_semantic.json", "mark_identity.json", "mark_identity_quran.json",
                     "mark_identity_semantic_v3.json"):
        if not (DATA / filename).exists():
            continue
        obj = json.loads((DATA / filename).read_text())
        pins = [p for s in obj["segments"] for p in s.get("pins", [])]
        mismatch = [p["t"] for p in pins if not 0 <= p["t"] < len(flat)
                    or flat[p["t"]][2] != p["tok"]]
        counter = Counter(p["t"] for p in pins)
        pins_report[filename] = dict(pins=len(pins), unique_tokens=len(counter),
                                     repeated_token_ids=sum(n > 1 for n in counter.values()),
                                     reversed_x_intervals=sum(p["x0"] > p["x1"] for p in pins),
                                     token_mismatches=mismatch,
                                     carried_runs=sum(r.get("page", s["page"]) != s["page"]
                                                      for s in obj["segments"] for r in s.get("runs", [])))
    out = dict(corpus=dict(verses=len(corpus), unique_verse_keys=len({v["verse_key"] for v in corpus}),
                           whitespace_tokens=raw_count, normalized_nonempty_tokens=len(flat)),
               historical_token_map=dict(records=len(records), unique_indices=len(set(indices)),
                                         invalid_indices=invalid, reversed_x_intervals=len(reversed_x),
                                         reversed_x_examples=reversed_x[:20], span_tile_gaps=gaps),
               historical_rosettes=dict(rows=len(meta), assigned=int(assigned.sum()),
                                        raw_digit_reads=int(raw_read.sum()),
                                        read_equals_assigned_verse=int(agree.sum()),
                                        note="Agreement with inferred assignments is NOT held-out digit accuracy."),
               pins=pins_report,
               caveat="Structural agreement does not validate verse labels, token geometry or semantic pin identities.")
    out["checkpoint_source_hashes"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in sorted((ROOT / "tools").glob("*.py"))}
    names = ("quran-uthmani.json", "token_map2.json", "letter_model.json", "red_types.npz",
             "rosette_seq.npz", "rosette_digits.npz", "page_verse_map.json",
             "mark_identity.json", "mark_identity_semantic.json", "mark_identity_quran.json")
    out["historical_input_hashes"] = {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                                      for name in names}
    if (DATA / "real_boxes_v3").exists():
        pages = load_all(include_empty=True, data=DATA / "real_boxes_v3")
        n_reds = box_matches = center_matches = cell_matches = gold_slots = n_slots = 0
        red_widths, slot_widths = [], []
        for pg, page in pages.items():
            raw = json.loads((DATA / "real_boxes_v3" / f"page_{pg:03d}.json").read_text())
            slots = [s for s in raw["slots"] if s["line"] is not None]
            reds = [raw["reds"][i] for i in page["red_indices"]]
            boxes = {tuple(s[k] for k in ("x0", "x1", "y0", "y1")) for s in slots}
            centers = {(s["line"], s["cx"]) for s in slots}
            slines, scols, _ = encode(pg, page["slots"], ScoreSpec())
            rlines, rcols, _ = encode(pg, page["reds"], ScoreSpec())
            cells = set(zip(slines, scols))
            n_reds += len(reds)
            n_slots += len(slots)
            gold_slots += sum(s["color"] == "gold" for s in slots)
            box_matches += sum(tuple(r[k] for k in ("x0", "x1", "y0", "y1")) in boxes for r in reds)
            center_matches += sum((r["line"], r["cx"]) in centers for r in reds)
            cell_matches += sum((li, col) in cells for li, col in zip(rlines, rcols))
            red_widths.extend(r["x1"] - r["x0"] + 1 for r in reds)
            slot_widths.extend(s["x1"] - s["x0"] + 1 for s in slots)
        out["observed_reference_unit_comparability"] = dict(
            observed_groups=n_reds, raw_reference_components=n_slots,
            observed_bbox_in_raw_pool=box_matches,
            observed_center_line_in_raw_pool=center_matches,
            observed_column_line_cell_in_raw_pool=int(cell_matches),
            gold_class_reference_components=gold_slots,
            observed_width_quantiles=np.percentile(red_widths, [10, 50, 90]).tolist(),
            reference_width_quantiles=np.percentile(slot_widths, [10, 50, 90]).tolist(),
            interpretation="Observed red groups are merged; reference components are pre-merge and "
            "include fragments and gold glyphs. The mathematical reference model is explicit, "
            "but an exchangeable neutral WORD-placement null is not established.")
    if include_scans:
        scans = {}
        for f in sorted((ROOT / "hayrat-pics").glob("page_*.png")):
            with Image.open(f) as im:
                scans[f.name] = dict(size=list(im.size), mode=im.mode,
                                     transparency=("A" in im.getbands() or "transparency" in im.info),
                                     sha256=hashlib.sha256(f.read_bytes()).hexdigest())
        out["scans"] = scans
        out["scan_sizes"] = {f"{w}x{h}": n for (w, h), n in
                             Counter(tuple(s["size"]) for s in scans.values()).items()}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    out = report(args.scans)
    (DATA / "audit_integrity.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "scans"}, indent=2))


if __name__ == "__main__":
    main()
