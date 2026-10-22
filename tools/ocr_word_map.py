"""Exact-corpus identities attached to exclusive OCR image regions.

All minimum edit paths are retained. A region is accepted for a corpus word
only when the word cannot disappear and no other word can use any of its
candidate regions on an optimal path. Split-prefix regions can be united
on the same row. Multiword regions are never divided by text length.
Geometry comes solely from the OCR detector, not from ink-family assumptions.
The historical rule remains the default. Optional mandatory-v2 uses reverse
alignment to exclude wholly insertable regions and prevents intervening-word
unions; it supplies localization support, not certified complete boundaries.
"""
import argparse
import hashlib
import json
from pathlib import Path

import map_tokens as mt
from ocr_benchmark import reading_order, words
from ocr_line_map import align_words
from semantic_validation import DATA, MANUAL, corpus_targets, localized


def map_regions(reference_words, regions):
    mapped, optimum = align_words(reference_words, ["".join(words(r["text"])) for r in regions])
    users = [set() for _ in regions]
    for i, row in enumerate(mapped):
        for region in row["line_candidates"]:
            users[region].add(i)
    for i, row in enumerate(mapped):
        candidates = row["line_candidates"]
        boxes = [regions[r]["bbox"] for r in candidates]
        same_row = bool(boxes) and max(b[1] for b in boxes) < min(b[3] for b in boxes)
        accepted = (bool(candidates) and not row["whole_word_deletion_possible"] and same_row
                    and all(users[r] == {i} and regions[r].get("bbox_valid", True) for r in candidates))
        row["region_candidates"] = row.pop("line_candidates")
        row["stable_region"] = row.pop("stable_line")
        row["exclusive_regions"] = candidates if accepted else []
        if accepted:
            row["bbox"] = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                           max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return mapped, optimum


def map_mandatory_regions(reference_words, regions):
    """Use regions with non-optional ownership, not a union of possible owners.

    Reversing the edit alignment interchanges insertions/deletions. A region
    is mandatory for word i iff it cannot be wholly inserted in any optimal
    forward path and every possible aligned reference character belongs to i.
    This certifies support under the edit model, not the complete word extent.
    """
    normalized = ["".join(words(r["text"])) for r in regions]
    forward, optimum = align_words(reference_words, normalized)
    reverse, reverse_cost = align_words(normalized, reference_words)
    if reverse_cost != optimum:
        raise AssertionError("reversing unit edit alignment changed optimum")
    for i, row in enumerate(forward):
        candidates = row.pop("line_candidates")
        row["stable_region"] = row.pop("stable_line")
        row["region_candidates"] = candidates
        mandatory = [r for r in candidates if reverse[r]["stable_line"] == i]
        row["mandatory_regions"] = mandatory
        row["optional_region_candidates"] = [r for r in candidates if r not in mandatory]
        boxes = [regions[r]["bbox"] for r in mandatory]
        accepted = bool(boxes) and not row["whole_word_deletion_possible"]
        if accepted:
            box = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                   max(b[2] for b in boxes), max(b[3] for b in boxes)]
            top, bottom = max(b[1] for b in boxes), min(b[3] for b in boxes)
            same_row = top < bottom
            # Never unite pieces across another detected word's center.
            intervening = [r for r, region in enumerate(regions)
                           if r not in mandatory and normalized[r]
                           and box[0] < (region["bbox"][0] + region["bbox"][2]) / 2 < box[2]
                           and top < (region["bbox"][1] + region["bbox"][3]) / 2 < bottom]
            accepted = (same_row and not intervening
                        and all(regions[r].get("bbox_valid", True) for r in mandatory))
        row["exclusive_regions"] = mandatory if accepted else []
        if accepted:
            row["bbox"] = box
            row["surface_match"] = "".join(normalized[r] for r in mandatory) == reference_words[i]
            row["localization_scope"] = "mandatory_detector_support_not_certified_boundary"
    return forward, optimum


def analyze(source, manual_path=MANUAL, method="exclusive-v1"):
    mapper = {"exclusive-v1": map_regions, "mandatory-v2": map_mandatory_regions}[method]
    manual = json.loads(manual_path.read_text())
    verses = mt.load_tokens()
    flat = [(f"{s}:{a}", token) for s, a, ts in verses for token in ts]
    pages, inputs = [], {}
    for page in manual["pages"]:
        n = page["page"]
        path = source / f"page_{n}.json"
        obj = json.loads(path.read_text())
        if obj["image_sha256"] != page["image_sha256"]:
            raise AssertionError("OCR/manual image mismatch")
        regions = reading_order([word for line in obj["result"]["text_lines"]
                                 for word in (line.get("words") or [line])])
        i0 = next(i for i, (v, _) in enumerate(flat) if v == page["first_verse"])
        i1 = max(i for i, (v, _) in enumerate(flat) if v == page["last_verse"]) + 1
        tokens = flat[i0:i1]
        mapped, optimum = mapper(["".join(words(t)) for _, t in tokens], regions)
        for i, row in enumerate(mapped):
            row.update(t=i0 + i, verse=tokens[i][0], canonical_token=tokens[i][1])
        targets = corpus_targets(verses, page["first_verse"], page["last_verse"])
        if [(t["verse"], t["occurrence"], t["form"]) for t in targets] != [
                (x["verse"], x["occurrence"], x["form"]) for x in page["names"]]:
            raise AssertionError("manual name identities do not match exact corpus")
        names = []
        for target, label in zip(targets, page["names"]):
            row = mapped[target["t"] - i0]
            box = row.get("bbox")
            correct = box is not None and localized(
                dict(cx=(box[0] + box[2]) / 2, cy=(box[1] + box[3]) / 2), label)
            names.append(dict(**target, bbox=box, correct=bool(correct),
                              status="correct" if correct else "wrong_position" if box else "abstained"))
        pages.append(dict(page=n, edit_cost=optimum, total_words=len(mapped),
                          localized_words=sum("bbox" in x for x in mapped),
                          name_total=len(names), name_accepted=sum(x["bbox"] is not None for x in names),
                          name_correct=sum(x["correct"] for x in names), names=names, words=mapped))
        inputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = source / "metadata.json"
    inputs[metadata.name] = hashlib.sha256(metadata.read_bytes()).hexdigest()
    report = dict(version="exclusive-all-optimal-ocr-region-v1", pages=pages, inputs=inputs,
                manual_sha256=hashlib.sha256(manual_path.read_bytes()).hexdigest(),
                corpus_sha256=hashlib.sha256((DATA / "quran-uthmani.json").read_bytes()).hexdigest(),
                **{key: sum(p[key] for p in pages) for key in
                   ("total_words", "localized_words", "name_total", "name_accepted", "name_correct")},
                caveat="Exact text and edit-cost model supply identity hypotheses; image regions supply geometry. "
                "Exclusive all-optimal assignment is not a calibrated confidence. Only annotated name centers "
                "are evaluated, not full word boundaries or the other word identities.")
    if method == "mandatory-v2":
        report["version"] = "mandatory-bidirectional-ocr-region-v2"
        report["caveat"] = ("Bidirectional all-optimal edit paths supply mandatory region ownership. "
                            "Optional regions are excluded; unions cannot span another detected word center. "
                            "This is conditional localization support, not calibrated confidence or certified "
                            "complete word boundaries. Annotated name centers are evaluated independently.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DATA / "ocr_easy_sample_v1")
    parser.add_argument("--manual", type=Path, default=MANUAL)
    parser.add_argument("--output", type=Path, default=DATA / "audit_ocr_word_map.json")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--method", choices=("exclusive-v1", "mandatory-v2"), default="exclusive-v1")
    args = parser.parse_args()
    report = analyze(args.source, args.manual, args.method)
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("exclusive OCR region map does not reproduce")
        print("PASS exact-corpus exclusive OCR regions, identities, geometry and hashes")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print({k: v for k, v in report.items() if k not in ("pages", "inputs")})
        for p in report["pages"]:
            print(p["page"], "localized words", p["localized_words"], "/", p["total_words"],
                  "names correct/accepted/total", p["name_correct"], p["name_accepted"], p["name_total"])


if __name__ == "__main__":
    main()
