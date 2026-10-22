"""Reproducible page sample and independent image-to-text validation.

Sampling is fixed before reading the selected images or inspecting pin labels.
Review scans first, then record verse/token identities and localized rectangles.
The exact corpus supplies spelling/order, not image coordinates or ink labels.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from alignment import ScoreSpec, reference_flags
from divine_census import TRUE_FORMS
from image_io import open_rgb
import map_tokens as mt
from rebuild_runs import page_bands

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data"
SEED = "t2-independent-semantic-validation-v1-2026-10-18"
EXCLUDED = {1, 49, 186, 206, 207, 422, 567}
STRATA = [(1, 100), (101, 200), (201, 300), (301, 400), (401, 500), (501, 604)]
MANUAL = DATA / "audit_manual_semantic_sample.json"


def is_name(word):
    return word == "الله" or word in TRUE_FORMS


def corpus_targets(verses, first, last):
    active, targets, ordinal, t = False, [], Counter(), 0
    for s, a, tokens in verses:
        key = f"{s}:{a}"
        if key == first:
            active = True
        for token in tokens:
            if active and is_name(token):
                ordinal[key] += 1
                targets.append(dict(verse=key, occurrence=ordinal[key], form=token, t=t))
            t += 1
        if key == last:
            if not active:
                raise ValueError("page verse range is reversed or first verse is missing")
            return targets
    raise ValueError("page verse range not found")


def localized(pin, label):
    x0, y0, x1, y1 = label["rect"]
    return x0 <= pin["cx"] <= x1 and y0 <= pin["cy"] <= y1


def independent_ink(image, rect):
    x0, y0, x1, y1 = rect
    im = np.asarray(image.crop((x0, y0, x1 + 1, y1 + 1)), dtype=np.int16)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    colored = (r > 120) & (r - g > 45)
    yy, xx = np.where(colored)
    if not len(xx):
        return dict(colored_pixels=0, crimson_pixels=0, magenta_pixels=0)
    return dict(colored_pixels=int(colored.sum()),
                crimson_pixels=int((colored & (b < 108)).sum()),
                magenta_pixels=int((colored & (b >= 108)).sum()),
                ink_bbox=[x0 + int(xx.min()), y0 + int(yy.min()),
                          x0 + int(xx.max()), y0 + int(yy.max())],
                cx=x0 + (int(xx.min()) + int(xx.max())) / 2,
                cy=y0 + (int(yy.min()) + int(yy.max())) / 2)


def load_pins(path, selected, names_only=True):
    obj = json.loads(path.read_text())
    boxes = DATA / obj.get("audit", {}).get("component_source", "real_boxes")
    bands, pins, seen = {}, [], set()
    for segment in obj["segments"]:
        for pin in segment.get("pins", []):
            pg = pin.get("page", segment["page"])
            if pg not in selected or (names_only and not is_name(pin["tok"])):
                continue
            identity = (pin["t"], pg, pin["kind"], pin["band"], pin["x0"], pin["x1"])
            if identity in seen:
                continue
            seen.add(identity)
            if pg not in bands:
                bands[pg] = page_bands(pg, boxes=boxes)
            y0, y1, _ = bands[pg][pin["band"]]
            pins.append(dict(t=pin["t"], page=pg, form=pin["tok"], kind=pin["kind"],
                             cx=(pin["x0"] + pin["x1"]) / 2, cy=(y0 + y1) / 2,
                             x0=pin["x0"], x1=pin["x1"]))
    return pins


def assess_pins(pins, labels):
    """Separate token recall from location precision; do not count-match labels."""
    rows = []
    for pin in pins:
        truth = labels.get(pin["t"])
        status = ("wrong_page_or_token" if truth is None or pin["page"] != truth["page"]
                  else "correct" if localized(pin, truth) else "wrong_position")
        rows.append(dict(**pin, status=status))
    correct = {p["t"] for p in rows if p["status"] == "correct"}
    claimed = {p["t"] for p in rows}
    return dict(predictions=len(rows), correct_localized_tokens=len(correct),
                target_tokens=len(labels),
                localized_token_recall=len(correct) / len(labels) if labels else None,
                localized_prediction_precision=(sum(p["status"] == "correct" for p in rows) / len(rows)
                                                 if rows else None),
                status_counts=dict(Counter(p["status"] for p in rows)),
                missing_token_ids=sorted(set(labels) - claimed),
                unlocalized_token_ids=sorted(set(labels) - correct), predictions_detail=rows)


def analyze(scans=False, stored_pixels=None):
    manual = json.loads(MANUAL.read_text())
    if [p["page"] for p in manual["pages"]] != selected_pages():
        raise AssertionError("manual pages differ from fixed selection")
    verses = mt.load_tokens()
    labels, page_rows, placements = {}, [], {}
    for page in manual["pages"]:
        n = page["page"]
        targets = corpus_targets(verses, page["first_verse"], page["last_verse"])
        if [{k: x[k] for k in ("verse", "occurrence", "form")} for x in targets] != [
                {k: x[k] for k in ("verse", "occurrence", "form")} for x in page["names"]]:
            raise AssertionError(f"p{n}: manual name census differs from exact verse text")
        im = None
        if scans:
            image = ROOT / "hayrat-pics" / f"page_{n}.png"
            if hashlib.sha256(image.read_bytes()).hexdigest() != page["image_sha256"]:
                raise AssertionError("sample scan hash differs")
            im = open_rgb(image)
        rows, positions = [], []
        # Manual windows define words; pixels only refine their ink centers.
        for target, label in zip(targets, page["names"]):
            t = target["t"]
            labels[t] = dict(**label, page=n)
            pixels = independent_ink(im, label["rect"]) if scans else stored_pixels[str(t)]
            rows.append(dict(**target, rect=label["rect"], pixels=pixels))
            # Coarse manually observed row grouping, independent of pipeline grids.
            positions.append((int(((label["rect"][1] + label["rect"][3]) / 2 - 60) / 110 + 0.5),
                              pixels.get("cx", (label["rect"][0] + label["rect"][2]) / 2)))
        placements[n] = np.array(positions, dtype=float).reshape(-1, 2)
        page_rows.append(dict(page=n, target_names=len(targets), names=rows))
    flags = reference_flags(placements, ScoreSpec(pairing="none"))
    shifted = reference_flags(placements, ScoreSpec(pairing="none", column_origin=41))
    for row in page_rows:
        n = row["page"]
        row["column_aligned_names"] = int(flags[n][0].sum())
        row["shifted_column_aligned_names"] = int(shifted[n][0].sum())
        positions = placements[n]
        row["distance_aligned_names"] = {
            str(tolerance): sum(any(li != lj and abs(xi - xj) <= tolerance
                                   for lj, xj in positions) for li, xi in positions)
            for tolerance in (15, 30)}
    paths = [DATA / "mark_identity_semantic.json", DATA / "mark_identity_semantic_v3.json"]
    if (DATA / "mark_identity_semantic_v4.json").exists():
        paths.append(DATA / "mark_identity_semantic_v4.json")
    comparisons = {}
    for path in paths:
        comparisons[path.name] = assess_pins(load_pins(path, set(placements)), labels)
        all_pins = load_pins(path, set(placements), names_only=False)
        wrong_at_names = []
        for pin in all_pins:
            for t, label in labels.items():
                if pin["page"] == label["page"] and localized(pin, label) and pin["t"] != t:
                    wrong_at_names.append(dict(**pin, correct_t=t, correct_verse=label["verse"],
                                               correct_form=label["form"]))
        obj = json.loads(path.read_text())
        black = {t for segment in obj["segments"] for t in segment.get("black", [])}
        unlocated = {t for segment in obj["segments"] for t in segment.get("unlocated", [])}
        comparisons[path.name]["other_tokens_incorrectly_pinned_at_name_sites"] = wrong_at_names
        comparisons[path.name]["colored_names_reported_in_black_list"] = sorted(set(labels) & black)
        comparisons[path.name]["colored_names_without_detected_runs"] = sorted(set(labels) & unlocated)
    rosette_results = {}
    for directory in (DATA, DATA / "rosette_map_v3"):
        path = directory / "rosette_seq.npz"
        meta = np.load(path, allow_pickle=False)["meta"]
        details = []
        for page in manual["pages"]:
            found = meta[(meta[:, 0] == page["page"]) & (meta[:, 1] >= 0)]
            used = set()
            for marker in page["rosettes"]:
                distances = np.hypot(found[:, 1] - marker["cx"], found[:, 2] - marker["cy"])
                j = int(distances.argmin())
                nearby = distances[j] <= 25
                if nearby and j in used:
                    raise AssertionError("manual markers matched one detection twice")
                if nearby:
                    used.add(j)
                assigned = f"{int(found[j, 3])}:{int(found[j, 4])}" if nearby else None
                details.append(dict(page=page["page"], expected=marker["verse"], assigned=assigned,
                                    correct=assigned == marker["verse"],
                                    distance=float(distances[j]), found=bool(nearby)))
        rosette_results[str(path.relative_to(DATA))] = dict(
            markers=len(details), correct=sum(r["correct"] for r in details), details=details)
    input_paths = [MANUAL, DATA / "quran-uthmani.json", *paths,
                   DATA / "rosette_seq.npz", DATA / "rosette_map_v3" / "rosette_seq.npz"]
    # Pin vertical locations depend on component versions as well as pin JSON.
    input_paths.extend(DATA / directory / f"page_{n:03d}.json"
                       for directory in ("real_boxes", "real_boxes_v3") for n in placements)
    return dict(version="independent-semantic-validation-v1", pages=page_rows,
                total_names=len(labels), visually_colored_names=sum(x["visually_colored"] for x in labels.values()),
                names_with_detected_colored_ink=sum(x["pixels"]["colored_pixels"] > 0 for p in page_rows for x in p["names"]),
                column_aligned_names=sum(p["column_aligned_names"] for p in page_rows),
                shifted_column_aligned_names=sum(p["shifted_column_aligned_names"] for p in page_rows),
                distance_aligned_names={str(t): sum(p["distance_aligned_names"][str(t)] for p in page_rows)
                                        for t in (15, 30)},
                pins=comparisons, rosettes=rosette_results,
                inputs={str(p.relative_to(DATA)): hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths},
                caveat="Six stratified pages, one AI reader; not a corpus-wide accuracy estimate. "
                "Allah-name marking is checked exhaustively within these complete-verse pages; "
                "other word families are outside this annotation set. Column rate is descriptive, "
                "with manual name windows and pixel-refined centers, not a p-value.")


def verify_report(path, scans=False):
    saved = json.loads(path.read_text())
    pixels = {str(x["t"]): x["pixels"] for p in saved["pages"] for x in p["names"]}
    current = analyze(scans=scans, stored_pixels=pixels)
    if current != saved:
        raise AssertionError("independent semantic validation report does not reproduce")
    print("PASS semantic sample: corpus census, pin identity/localization, rosette labels, hashes"
          + (", scan hashes and localized pixels" if scans else "; pixel measurements read from stored report"))


def brief(report):
    print("sample pages:", selected_pages())
    for key in ("total_names", "visually_colored_names", "names_with_detected_colored_ink", "column_aligned_names",
                "shifted_column_aligned_names", "distance_aligned_names"):
        print(key, report[key])
    targets = {x["t"]: (p["page"], x["verse"], x["occurrence"], x["form"])
               for p in report["pages"] for x in p["names"]}
    for name, row in report["pins"].items():
        print(name, {k: v for k, v in row.items() if k not in
                     ("predictions_detail", "missing_token_ids", "unlocalized_token_ids")})
        print("  missing/unlocalized:", [targets[t] for t in row["unlocalized_token_ids"]])
        print("  wrong predictions:", [p for p in row["predictions_detail"] if p["status"] != "correct"])
        print("  non-name labels at name sites:", row["other_tokens_incorrectly_pinned_at_name_sites"])
        print("  colored names in black list:", [targets[t] for t in row["colored_names_reported_in_black_list"]])
    for name, row in report["rosettes"].items():
        print(name, row["correct"], "/", row["markers"])


def diagnose(path):
    manual = json.loads(MANUAL.read_text())
    verses = mt.load_tokens()
    obj = json.loads(path.read_text())
    for page in manual["pages"]:
        for target in corpus_targets(verses, page["first_verse"], page["last_verse"]):
            containing = [s for s in obj["segments"] if target["t"] in s.get("toks", [])]
            for segment in containing:
                matching = [p for p in segment.get("pins", []) if p["t"] == target["t"]]
                if matching:
                    continue
                print("missing", page["page"], target, "segment", {k: segment.get(k) for k in
                      ("verses", "valid", "cls_state", "n_cri_t", "n_cri_r", "n_mag_t", "n_mag_r")})
                print("  runs", segment.get("runs", []))


def selected_pages():
    return [min((n for n in range(lo, hi + 1) if n not in EXCLUDED),
                key=lambda n: hashlib.sha256(f"{SEED}:{n}".encode()).hexdigest())
            for lo, hi in STRATA]


def build_review(output):
    output.mkdir(parents=True, exist_ok=True)
    pages = []
    for n, (lo, hi) in zip(selected_pages(), STRATA):
        image = ROOT / "hayrat-pics" / f"page_{n}.png"
        im = open_rgb(image)
        # Fixed overlapping slices; no predicted word/rosette labels shown.
        for part, top in enumerate(range(0, im.height, 560)):
            im.crop((0, top, im.width, min(im.height, top + 640))).resize(
                (im.width * 2, min(640, im.height - top) * 2)).save(output / f"page_{n}_{part}.png")
        pages.append(dict(page=n, stratum=[lo, hi],
                          image_sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
    report = dict(version="independent-page-sample-v1", seed=SEED,
                  selection="minimum SHA256(seed:page) within each fixed page-number stratum",
                  excluded_pages=sorted(EXCLUDED),
                  exclusion_reason="six rosette training anchors and prior manually annotated p567",
                  pages=pages,
                  protocol="Read unlabelled scans before inspecting predicted semantic pins. "
                  "Record all Allah-form occurrences, ink classes, coordinates and uncertainty; "
                  "record all localized verse-end labels. Corpus confirms text/order. "
                  "Report missed and false pins separately from coverage. "
                  "This is one AI reader, not independent human double annotation.")
    (output / "sample.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def corpus(first, last):
    verses = json.loads((DATA / "quran-uthmani.json").read_text())["verses"]
    active = False
    for v in verses:
        if v["verse_key"] == first:
            active = True
        if active:
            print(v["verse_key"], v["text_uthmani"])
        if v["verse_key"] == last:
            break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--corpus", nargs=2, metavar=("FIRST", "LAST"))
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--diagnose", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--scans", action="store_true", help="recheck source images during verification")
    parser.add_argument("--output", type=Path, default=DATA / "audit_semantic_validation.json")
    args = parser.parse_args()
    if args.review:
        build_review(args.review)
    elif args.corpus:
        corpus(*args.corpus)
    elif args.analyze:
        report = analyze(scans=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        brief(report)
    elif args.diagnose:
        diagnose(args.diagnose)
    elif args.verify:
        verify_report(args.verify, args.scans)
    else:
        print(selected_pages())


if __name__ == "__main__":
    main()
