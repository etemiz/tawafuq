"""Independent full-page scope/name checks for anchor/substr matching.

The newest six unlabelled scans were read before their corpus-map predictions.
Earlier 18 pages remain exposed development checks. Basmala names are separate
from canonical verse-name token IDs. No predicted scope supplies ground truth.
"""
import argparse
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path

import map_tokens as mt
import ocr_corpus_map as cm
from semantic_validation import ROOT, DATA, STRATA, corpus_targets, localized
from word_validation_sample import EXCLUDED, selected_pages as word_pages

SEED = "t2-exact-corpus-page-anchoring-v1-2026-10-18"
EXCLUDE = EXCLUDED | set(word_pages()) | {154, 489, 604}
MANUAL = DATA / "audit_manual_corpus_map_sample_v1.json"
LABELS = {
    11: ("2:77", "2:83", [
        ("2:77", 1, "الله", [661, 31, 743, 108]),
        ("2:79", 1, "الله", [662, 361, 744, 440]),
        ("2:80", 1, "الله", [662, 693, 745, 768]),
        ("2:80", 2, "الله", [191, 693, 274, 770]),
        ("2:80", 3, "الله", [664, 805, 744, 879]),
        ("2:83", 1, "الله", [207, 1247, 288, 1323]),
    ], []),
    199: ("9:80", "9:86", [
        ("9:80", 1, "الله", [817, 140, 900, 218]),
        ("9:80", 2, "بالله", [313, 141, 409, 223]),
        ("9:80", 3, "والله", [23, 142, 104, 217]),
        ("9:81", 1, "الله", [818, 362, 899, 439]),
        ("9:81", 2, "الله", [818, 472, 900, 550]),
        ("9:83", 1, "الله", [24, 694, 107, 768]),
        ("9:84", 1, "بالله", [315, 1135, 411, 1213]),
        ("9:85", 1, "الله", [24, 1247, 106, 1321]),
        ("9:86", 1, "بالله", [348, 1467, 446, 1543]),
    ], []),
    239: ("12:38", "12:43", [
        ("12:38", 1, "بالله", [575, 140, 674, 222]),
        ("12:38", 2, "الله", [24, 142, 105, 218]),
        ("12:39", 1, "الله", [24, 363, 105, 438]),
        ("12:40", 1, "الله", [585, 583, 665, 661]),
        ("12:40", 2, "لله", [23, 582, 105, 661]),
    ], []),
    304: ("19:1", "19:11", [], [dict(verse="19:0", word_in_verse=2, form="الله",
                                    rect=[289, 252, 369, 331])]),
    402: ("29:53", "29:63", [
        ("29:60", 1, "الله", [921, 1027, 998, 1100]),
        ("29:61", 1, "الله", [921, 1248, 998, 1323]),
        ("29:62", 1, "الله", [564, 1248, 644, 1323]),
        ("29:62", 2, "الله", [565, 1358, 644, 1435]),
        ("29:63", 1, "الله", [920, 1578, 998, 1652]),
        ("29:63", 2, "لله", [563, 1578, 643, 1652]),
    ], []),
    570: ("71:11", "71:28", [
        ("71:13", 1, "لله", [921, 249, 999, 329]),
        ("71:15", 1, "الله", [24, 252, 107, 328]),
        ("71:17", 1, "والله", [917, 470, 999, 548]),
        ("71:19", 1, "والله", [917, 581, 999, 659]),
        ("71:25", 1, "الله", [23, 1136, 106, 1213]),
    ], []),
}


def selected_pages():
    return [min((n for n in range(lo, hi + 1) if n not in EXCLUDE),
                key=lambda n: hashlib.sha256(f"{SEED}:{n}".encode()).hexdigest())
            for lo, hi in STRATA]


def rule_hash():
    functions = (cm.normalized, cm.virtual_corpus, cm.unique_index, cm.retrieve,
                 cm.edit_table, cm.semiglobal_support, cm.support_box, cm.map_page)
    return hashlib.sha256((json.dumps(asdict(cm.Spec()), sort_keys=True)
                           + "".join(inspect.getsource(f) for f in functions)).encode()).hexdigest()


def build(scans=True, stored=None):
    if selected_pages() != list(LABELS):
        raise AssertionError("fresh page selection differs")
    verses = mt.load_tokens()
    pages = []
    for n, stratum in zip(selected_pages(), STRATA):
        first, last, names, heads = LABELS[n]
        names = [dict(verse=v, occurrence=i, form=f, rect=r, visually_colored=True) for v, i, f, r in names]
        expected = corpus_targets(verses, first, last)
        if [(x["verse"], x["occurrence"], x["form"]) for x in expected] != [
                (x["verse"], x["occurrence"], x["form"]) for x in names]:
            raise AssertionError(f"p{n}: independent name transcription differs from exact corpus")
        digest = (hashlib.sha256((ROOT / "hayrat-pics" / f"page_{n}.png").read_bytes()).hexdigest()
                  if scans else next(p["image_sha256"] for p in stored["pages"] if p["page"] == n))
        pages.append(dict(page=n, stratum=list(stratum), first_verse=first, last_verse=last,
                          image_sha256=digest, names=names, head_basmala_names=heads))
    return dict(version="independent-corpus-page-anchor-sample-v1", seed=SEED,
                excluded_pages=sorted(EXCLUDE), spec=asdict(cm.Spec()), rule_sha256=rule_hash(), pages=pages,
                protocol="One AI reader read complete unlabelled scans before seeing corpus-map predictions "
                "for these pages. Names and first/last verse labels are recorded independently; exact corpus "
                "confirms spelling/counts. Basmala on p304 is separate from verse-name occurrences. "
                "Approximate name-core windows, not complete word boundaries. Earlier 18 pages are development.")


def assess_name(target, label, predicted):
    row = next((w for w in predicted if w["t"] == target["t"] and w["kind"] == "verse"), None)
    box = row.get("bbox") if row else None
    correct = bool(box is not None and localized(dict(cx=(box[0] + box[2]) / 2,
                                                      cy=(box[1] + box[3]) / 2), label))
    return dict(**target, bbox=box, correct=correct,
                status="correct" if correct else "wrong_position" if box else "abstained")


def analyze(mapping_path):
    mapping = json.loads(mapping_path.read_text())
    mapped = {p["page"]: p for p in mapping["pages"]}
    verses = mt.load_tokens()
    flat = [f"{s}:{a}" for s, a, ts in verses for _ in ts]
    manuals = [("development", DATA / name) for name in (
        "audit_manual_semantic_sample.json", "audit_manual_ocr_heldout.json", "audit_manual_word_validation_v2.json")]
    manuals.append(("fresh", MANUAL))
    groups, scope_checks, inputs = {}, [], {}
    for group, path in manuals:
        manual = json.loads(path.read_text())
        inputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if group == "fresh" and build(False, manual) != manual:
            raise AssertionError("fresh labels/rule/selection provenance differs")
        results = groups.setdefault(group, [])
        for page in manual["pages"]:
            prediction = mapped[page["page"]]
            if prediction["image_sha256"] != page["image_sha256"]:
                raise AssertionError("map/manual image hash differs")
            targets = corpus_targets(verses, page["first_verse"], page["last_verse"])
            for target, label in zip(targets, page["names"]):
                results.append(dict(page=page["page"], **assess_name(target, label, prediction["words"])))
            if group != "fresh":
                continue
            lo = next(i for i, v in enumerate(flat) if v == page["first_verse"])
            hi = max(i for i, v in enumerate(flat) if v == page["last_verse"]) + 1
            outside = [w for w in prediction["words"] if w["kind"] == "verse" and "bbox" in w
                       and not lo <= w["t"] < hi]
            heads = []
            for label in page["head_basmala_names"]:
                row = next((w for w in prediction["words"] if w["verse"] == label["verse"]
                            and w["word_in_verse"] == label["word_in_verse"]), None)
                box = row.get("bbox") if row else None
                correct = box is not None and localized(dict(cx=(box[0] + box[2]) / 2,
                                                             cy=(box[1] + box[3]) / 2), label)
                heads.append(dict(**label, bbox=box, correct=bool(correct)))
            scope_checks.append(dict(page=page["page"], expected_first=page["first_verse"],
                                     expected_last=page["last_verse"],
                                     possible_first=prediction.get("possible_first_verse"),
                                     possible_last=prediction.get("possible_last_verse"),
                                     first_correct=prediction.get("possible_first_verse") == page["first_verse"],
                                     last_correct=prediction.get("possible_last_verse") == page["last_verse"],
                                     accepted_outside_scope=outside, head_basmala_names=heads))
    result = dict(version="independent-anchor-corpus-map-validation-v1", inputs=inputs,
                mapping_sha256=hashlib.sha256(mapping_path.read_bytes()).hexdigest(),
                groups={g: dict(total=len(rs), correct=sum(r["correct"] for r in rs),
                                accepted=sum(r["bbox"] is not None for r in rs), details=rs)
                        for g, rs in groups.items()}, scope_checks=scope_checks,
                caveat="Fresh six-page scope/name labels vs independent OCR/corpus matching; earlier 18 pages "
                "are exposed development. Support outside labelled bounds and scope errors are reported. "
                "No automatic scope ground truth, full-boundary certification or calibrated probability.")
    if mapping["version"] == "gold-masked-anchor-conditional-substring-map-v2":
        result["version"] = "exposed-v1-sample-masked-v2-development-validation"
        result["groups"]["fresh"]["role"] = "Fresh for v1, exposed while developing gold-mask v2; not v2 held-out"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--verify-manual", action="store_true")
    parser.add_argument("--scans", action="store_true")
    parser.add_argument("--mapping", type=Path, default=cm.OUTPUT)
    parser.add_argument("--output", type=Path, default=DATA / "audit_corpus_map_validation_v1.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.build:
        report = build()
        MANUAL.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("fresh pages", selected_pages(), "verse names", sum(len(p["names"]) for p in report["pages"]))
    elif args.verify_manual:
        saved = json.loads(MANUAL.read_text())
        if build(args.scans, saved) != saved:
            raise AssertionError("independent corpus-map annotation differs")
        print("PASS independent corpus-map sample, exact names, rule hash" + (" and scans" if args.scans else ""))
    else:
        report = analyze(args.mapping)
        if args.verify:
            if report != json.loads(args.output.read_text()):
                raise AssertionError("corpus-map validation does not reproduce")
            print("PASS independent fresh scope/name and exposed-development corpus-map checks")
        else:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            for g, row in report["groups"].items():
                print(g, "correct/accepted/total", row["correct"], row["accepted"], row["total"])
                print("unresolved/wrong", [r for r in row["details"] if not r["correct"]])
            print("scope checks", report["scope_checks"])


if __name__ == "__main__":
    main()
