"""Independent name and ordinary-word checks for the frozen v2 evaluation set.

The two mapper versions share raw OCR and manual annotations. Horizontal
boundary checks use the annotation's prespecified coarse +/-12px tolerance,
not pixel-exact ground truth. All accepted failures and abstentions remain.
"""
import argparse
import hashlib
import json
from pathlib import Path

import map_tokens as mt
from ocr_word_map import analyze as analyze_map
from semantic_validation import DATA, is_name, localized
from word_validation_sample import MANUAL


def assess(row, label):
    box = row.get("bbox")
    if box is None:
        return dict(accepted=False, center_correct=False, correct_line=False,
                    horizontal_boundary_pass=False, status="abstained")
    center = dict(cx=(box[0] + box[2]) / 2, cy=(box[1] + box[3]) / 2)
    correct_line = label["rect"][1] <= center["cy"] <= label["rect"][3]
    errors = [box[0] - label["x_edges"][0], box[2] - label["x_edges"][1]]
    boundary = (label.get("boundary_eligible", True) and correct_line
                and max(map(abs, errors)) <= label["x_edge_tolerance"])
    correct = localized(center, label)
    return dict(accepted=True, bbox=box, center_correct=correct, correct_line=correct_line,
                horizontal_boundary_pass=boundary, signed_x_edge_errors=errors,
                status="correct_center" if correct else "wrong_center")


def analyze(source, manual_path=MANUAL):
    manual = json.loads(manual_path.read_text())
    verses = mt.load_tokens()
    t, identities = 0, {}
    for s, a, ts in verses:
        for i, token in enumerate(ts, 1):
            identities[(f"{s}:{a}", i)] = (t, token)
            t += 1
    methods = {}
    for method in ("exclusive-v1", "mandatory-v2"):
        mapping = analyze_map(source, manual_path, method)
        rows = []
        for page, mapped_page in zip(manual["pages"], mapping["pages"]):
            if page["page"] != mapped_page["page"]:
                raise AssertionError("page ordering differs")
            predicted = {r["t"]: r for r in mapped_page["words"]}
            for label in page["word_samples"]:
                t, token = identities[(label["verse"], label["word_in_verse"])]
                if token != label["form"] or predicted[t]["canonical_token"] != token:
                    raise AssertionError("ordinary-word label differs from canonical token")
                rows.append(dict(page=page["page"], t=t, **label, is_allah_form=is_name(token),
                                 **assess(predicted[t], label)))
        groups = {}
        for name, subset in (("all_sampled_words", rows),
                             ("non_allah_sampled_words", [r for r in rows if not r["is_allah_form"]]),
                             ("fixed_position_non_allah", [r for r in rows if not r["is_allah_form"]
                                                           and r["selection"] == "fixed_row_positions"]),
                             ("supplemental_vocative", [r for r in rows
                                                        if r["selection"] == "supplemental_vocative"])):
            groups[name] = dict(total=len(subset), **{key: sum(r[key] for r in subset) for key in
                               ("accepted", "center_correct", "correct_line", "horizontal_boundary_pass")})
            if "adjudication" in manual:
                groups[name]["boundary_evaluable"] = sum(r["boundary_eligible"] for r in subset)
        methods[method] = dict(mapping=mapping, sampled_words=rows, groups=groups)
    result = dict(version="fresh-word-localization-validation-v2", methods=methods,
                manual_sha256=hashlib.sha256(manual_path.read_bytes()).hexdigest(),
                caveat="One AI reader's pre-OCR annotations. Coarse horizontal word extents have +/-12px "
                "tolerance; boundary pass is not full pixel-accurate segmentation. Name evaluation covers "
                "all scoped corpus occurrences; ordinary words use fixed physical row/word positions. "
                "Supplemental اللهم is separate from the operational Allah-form census. "
                "V2 inference was frozen before these OCR predictions.")
    if "adjudication" in manual:
        result["version"] = "ruler-adjudicated-word-localization-v2"
        result["caveat"] = ("Mapper inference frozen before OCR, but ordinary-word labels were adjudicated "
                            "after predictions by the same reader. Original pre-OCR evaluation is retained "
                            "separately. Pixel-refined horizontal extents inside manual word partitions, "
                            "+/-12px tolerance; not a new blind boundary-accuracy estimate. Name-core "
                            "annotations are unchanged. Supplemental اللهم remains outside the Allah census.")
    return result


def verify(path, source, manual_path=MANUAL):
    if analyze(source, manual_path) != json.loads(path.read_text()):
        raise AssertionError("fresh word-localization validation does not reproduce")
    print("PASS fresh word localization: both mapper versions, all outcomes, coarse boundaries and hashes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DATA / "ocr_word_validation_google_v2")
    parser.add_argument("--manual", type=Path, default=MANUAL)
    parser.add_argument("--output", type=Path, default=DATA / "audit_word_localization_v2.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify(args.output, args.source, args.manual)
    else:
        report = analyze(args.source, args.manual)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        for method, result in report["methods"].items():
            mapped = result["mapping"]
            print(method, "names correct/accepted/total", mapped["name_correct"], mapped["name_accepted"],
                  mapped["name_total"], "word hypotheses", mapped["localized_words"], "/", mapped["total_words"])
            print(json.dumps(result["groups"], indent=2))
            print("sampled-word failures:", [r for r in result["sampled_words"]
                                              if not r["horizontal_boundary_pass"]])


if __name__ == "__main__":
    main()
