"""Post-hoc wordlike site view of the immutable gold-masked corpus map.

Correct a geometry-policy defect: an individual mandatory detector region
needs no union-contiguity test. Overlap with another OCR box does not create
a multi-region union. Actual unions retain the conservative v2 check.
Tiny (<35px tall) support boxes are excluded explicitly, not called words.
Both policies were developed after the scope checks; this is not held-out.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
from corpus_map_validation import MANUAL as NAME_MANUAL, assess_name
from semantic_validation import DATA, corpus_targets
import map_tokens as mt

MAPPING = DATA / "audit_ocr_corpus_map_masked_v2.json"
OUTPUT = DATA / "audit_ocr_corpus_sites_v1.json"
MINIMUM_HEIGHT = 35


def site(word, regions, minimum_height=MINIMUM_HEIGHT):
    row = dict(word)
    ids = word["mandatory_regions"]
    box = word.get("bbox")
    source = "mapped_support"
    if box is None and len(ids) == 1 and regions[ids[0]]["bbox_valid"]:
        box = regions[ids[0]]["bbox"]
        row["surface_match"] = cm.normalized(regions[ids[0]]["text"]) == word["normalized"]
        source = "single_mandatory_region_no_union"
    if box is None:
        return None, "no_usable_support"
    if box[3] - box[1] < minimum_height:
        return None, "small_support_box"
    row.update(bbox=box, geometry_policy=source)
    return row, source


def analyze(mapping_path=MAPPING, source=cm.SOURCE):
    mapping = json.loads(mapping_path.read_text())
    raw = {p["page"]: p for p in json.loads(source.read_text())["pages"]}
    if mapping["source_sha256"] != hashlib.sha256(source.read_bytes()).hexdigest():
        raise AssertionError("wordlike-site raw input differs from mapper")
    pages, outcomes, canonical = [], Counter(), defaultdict(list)
    for page in mapping["pages"]:
        words = []
        if page["status"] != "conditional_window_match":
            pages.append(dict(page=page["page"], image_sha256=page["image_sha256"], status=page["status"], words=[]))
            continue
        for word in page["words"]:
            row, status = site(word, raw[page["page"]]["regions"])
            outcomes[status] += 1
            if row is not None:
                words.append(row)
                if row["kind"] == "verse":
                    canonical[row["t"]].append(dict(page=page["page"], verse=row["verse"], form=row["form"], bbox=row["bbox"]))
        pages.append(dict(page=page["page"], image_sha256=page["image_sha256"], status=page["status"], words=words))
    predicted = {p["page"]: p for p in pages}
    verses = mt.load_tokens()
    validation, inputs = [], {}
    for filename in ("audit_manual_semantic_sample.json", "audit_manual_ocr_heldout.json",
                     "audit_manual_word_validation_v2.json", NAME_MANUAL.name):
        path = DATA / filename
        manual = json.loads(path.read_text())
        inputs[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        for page in manual["pages"]:
            for target, label in zip(corpus_targets(verses, page["first_verse"], page["last_verse"]), page["names"]):
                validation.append(dict(page=page["page"], **assess_name(target, label, predicted[page["page"]]["words"])))
    tokens, _, _ = cm.virtual_corpus()
    missing_names = [dict(t=w["t"], verse=w["verse"], form=w["form"], candidate_pages=[
        p["page"] for p in mapping["pages"] if p.get("virtual_token_window", [0, 0])[0] <= w["v_id"] <
        p.get("virtual_token_window", [0, 0])[1]]) for w in tokens
        if w["kind"] == "verse" and not w["verse"].startswith("1:") and w["t"] not in canonical
        and cm.is_name(w["form"])]
    return dict(version="posthoc-mandatory-wordlike-sites-v1", minimum_height=MINIMUM_HEIGHT, pages=pages,
                mapping_sha256=hashlib.sha256(mapping_path.read_bytes()).hexdigest(),
                ocr_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), annotation_inputs=inputs,
                policy_outcomes=dict(outcomes), summary=cm.summary(pages),
                duplicate_canonical_tokens={str(t): rows for t, rows in canonical.items() if len(rows) > 1},
                missing_scanned_verse_name_hypotheses=missing_names,
                exposed_name_check=dict(total=len(validation), correct=sum(r["correct"] for r in validation),
                                        details=validation),
                caveat="Post-hoc single-region geometry correction and minimum 35px height filter. "
                "All 111 name annotations were exposed during development; no new held-out score. "
                "Sites are hypotheses under the anchor/window/edit/geometry model, not certified full words. "
                "Missing token support does not imply absent or black ink; Fatiha is not in these scans.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=MAPPING)
    parser.add_argument("--source", type=Path, default=cm.SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze(args.mapping, args.source)
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("wordlike-site view does not reproduce")
        print("PASS post-hoc wordlike sites: policy, canonical IDs, geometry, exposed labels and missing support")
    else:
        args.output.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(json.dumps({k: report[k] for k in ("policy_outcomes", "summary", "duplicate_canonical_tokens",
                                                "missing_scanned_verse_name_hypotheses")}, ensure_ascii=False, indent=2))
        print("exposed names", report["exposed_name_check"]["correct"], "/", report["exposed_name_check"]["total"])


if __name__ == "__main__":
    main()
