"""Fresh scope check after developing the gold-mask wrapper on p304.

Selection excludes exposed annotation pages and the printed v1 scope-log
ranges (pages 1..100 and 580..604). Six fixed strata cover 101..579.
Unlabelled scans were read before masked-v2 predictions; two have headers.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path

import ocr_corpus_map as cm
from corpus_map_validation import EXCLUDE, selected_pages as earlier_pages, rule_hash
from ocr_ornament_bands import detect, SPEC as GOLD_SPEC
from semantic_validation import ROOT, DATA, localized

SEED = "t2-gold-ornament-scope-v2-2026-10-18"
STRATA = [(101, 180), (181, 260), (261, 340), (341, 420), (421, 500), (501, 579)]
EXCLUDED = EXCLUDE | set(earlier_pages())
MANUAL = DATA / "audit_manual_ornament_scope_v2.json"
MAPPING = DATA / "audit_ocr_corpus_map_masked_v2.json"
OUTPUT = DATA / "audit_ornament_scope_validation_v2.json"
LABELS = {
    160: ("7:82", "7:87", []),
    188: ("9:14", "9:20", []),
    272: ("16:55", "16:64", []),
    391: ("28:51", "28:59", []),
    427: ("34:1", "34:7", [dict(verse="34:0", word_in_verse=2, rect=[230, 245, 330, 340])]),
    517: ("50:1", "50:15", [dict(verse="50:0", word_in_verse=2, rect=[230, 245, 330, 340])]),
}


def selected_pages():
    return [min((n for n in range(lo, hi + 1) if n not in EXCLUDED),
                key=lambda n: hashlib.sha256(f"{SEED}:{n}".encode()).hexdigest()) for lo, hi in STRATA]


def build(scans=True, stored=None):
    if selected_pages() != list(LABELS):
        raise AssertionError("masked-v2 fresh sample selection differs")
    digest = hashlib.sha256((rule_hash() + json.dumps(GOLD_SPEC, sort_keys=True)
                             + inspect.getsource(detect) + inspect.getsource(cm.map_page_masked)).encode()).hexdigest()
    pages = []
    for n, stratum in zip(selected_pages(), STRATA):
        first, last, heads = LABELS[n]
        image_hash = (hashlib.sha256((ROOT / "hayrat-pics" / f"page_{n}.png").read_bytes()).hexdigest() if scans
                      else next(p["image_sha256"] for p in stored["pages"] if p["page"] == n))
        pages.append(dict(page=n, stratum=list(stratum), first_verse=first, last_verse=last,
                          head_basmala_names=heads, image_sha256=image_hash))
    return dict(version="fresh-ornament-scope-annotation-v2", seed=SEED, excluded_pages=sorted(EXCLUDED),
                excluded_log_ranges=[[1, 100], [580, 604]], rule_sha256=digest, pages=pages,
                protocol="One AI reader, unlabelled scans before masked-v2 predictions. First/last complete "
                "verse independently recorded. Two header/basmala pages included by fixed hash selection. "
                "Earlier v1 scope predictions were not inspected for these pages. No word-boundary or "
                "whole-corpus accuracy claim. p304 development failure is excluded.")


def analyze(mapping_path=MAPPING):
    manual = json.loads(MANUAL.read_text())
    if build(False, manual) != manual:
        raise AssertionError("masked-v2 frozen rule or annotations differ")
    mapping = json.loads(mapping_path.read_text())
    predictions = {p["page"]: p for p in mapping["pages"]}
    results = []
    for page in manual["pages"]:
        pred = predictions[page["page"]]
        if pred["image_sha256"] != page["image_sha256"]:
            raise AssertionError("fresh mask scope image hash differs")
        heads = []
        for label in page["head_basmala_names"]:
            word = next((w for w in pred["words"] if w["verse"] == label["verse"]
                         and w["word_in_verse"] == label["word_in_verse"]), None)
            box = word.get("bbox") if word else None
            correct = box is not None and localized(dict(cx=(box[0] + box[2]) / 2,
                                                         cy=(box[1] + box[3]) / 2), label)
            heads.append(dict(**label, bbox=box, correct=bool(correct)))
        results.append(dict(page=page["page"], expected_first=page["first_verse"], expected_last=page["last_verse"],
                            possible_first=pred.get("possible_first_verse"), possible_last=pred.get("possible_last_verse"),
                            first_correct=pred.get("possible_first_verse") == page["first_verse"],
                            last_correct=pred.get("possible_last_verse") == page["last_verse"],
                            ornament_bands=pred.get("ornament_bands"), head_names=heads))
    return dict(version="fresh-masked-corpus-scope-validation-v2", pages=results,
                correct_page_ranges=sum(r["first_correct"] and r["last_correct"] for r in results),
                correct_scope_endpoints=sum(r["first_correct"] + r["last_correct"] for r in results),
                manual_sha256=hashlib.sha256(MANUAL.read_bytes()).hexdigest(),
                mapping_sha256=hashlib.sha256(mapping_path.read_bytes()).hexdigest(),
                caveat="Six independent fresh page scopes, two with gold headers. Conditional mapper "
                "range checks, not whole-corpus scope certification or linguistic-null validation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    parser.add_argument("--mapping", type=Path, default=MAPPING)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.build:
        report = build()
        MANUAL.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("fresh masked-v2 scope pages", selected_pages())
    else:
        if args.scans:
            if build() != json.loads(MANUAL.read_text()):
                raise AssertionError("fresh scope scan hashes differ")
        report = analyze(args.mapping)
        if args.verify:
            if report != json.loads(args.output.read_text()):
                raise AssertionError("fresh masked-v2 scope checks do not reproduce")
            print("PASS fresh masked-v2 scope, basmala and frozen-rule checks")
        else:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
