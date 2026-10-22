"""Replayable, targeted diagnostics of corpus-site omissions and duplicates.

This is an exposed error review, not a held-out accuracy sample. Original maps
remain inputs; reviewed approximate name cores are explicitly distinguished
from automatic support hypotheses and complete word boundaries.
"""
import argparse
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_corpus_sites as cs
from semantic_validation import DATA, ROOT

OUTPUT = DATA / "audit_corpus_site_review_v1.json"

# Read directly on the full scans after the known-failure diagnostics. These
# are approximate name-core windows, not exhaustive ink or word boundaries.
NAME_CORES = {
    8595: (67, [320, 1572, 397, 1652], "reading_order_or_recognition",
           "Bottom line reads والله يحب المحسنين; the mandatory support is a tiny mark elsewhere."),
    10560: (83, [24, 1464, 103, 1546], "nonmandatory_exact_detection",
            "Left end of the penultimate line, after ما اتيهم."),
    21893: (171, [262, 32, 343, 112], "nonmandatory_exact_detection",
            "Top line, between قوما and مهلكهم."),
    26005: (204, [24, 1136, 103, 1221], "exact_detection_without_target_ownership",
            "Left end of line 11, after من دون; raw region 101 reads الله, but target support points elsewhere."),
    26611: (209, [918, 1027, 1001, 1110], "no_matching_word_detection",
            "Right start of line 10 before قل; mandatory support is a tiny annotation elsewhere."),
    29620: (231, [21, 577, 102, 664], "exact_detection_without_target_ownership",
            "Left end of line 6, after عليكم من; raw region 63 reads الله, but target support points elsewhere."),
    48752: (378, [28, 473, 111, 551], "nonmandatory_exact_detection",
            "Left end of line 5 after verse marker 25; starts verse 26 before next-line لا اله الا هو."),
    59014: (457, [288, 802, 350, 883], "overlapping_duplicate_detections",
            "Within الا لله الدين الخالص; Google supplies overlapping لله and combined الا لله readings."),
    65985: (510, [917, 1570, 1004, 1659], "exact_detection_without_target_ownership",
            "Right start of final line, after previous-line لتؤمنوا and before ورسوله; raw region 119 reads بالله."),
    70044: (542, [217, 691, 301, 782], "exact_detection_without_target_ownership",
            "Line 7 after لولا يعذبنا; raw region 86 reads الله. The earlier same-line الله is another token."),
    74219: (574, [680, 139, 753, 218], "overlapping_duplicate_detections",
            "Second line after معك; split و / الله and combined والله overlap."),
}
CONFLICT = dict(t=40736, verse="20:77", form="ولقد", accepted_page=316, rejected_page=315,
                accepted_rect=[900, 25, 1001, 110],
                reason="p315 ends at 20:76 من تزكى; its extra OCR مال region lies inside تزكى. "
                "p316 begins ولقد اوحينا الى موسى, the actual start of 20:77.")
MISLOCALIZED_CORES = {
    70038: (542, [790, 695, 878, 785], "wrong_accepted_name_location",
            "Line 7 in بما لم يحيك به الله; the original accepted box instead covers the later name after يعذبنا."),
}


def center_inside(box, rect):
    return (rect[0] <= (box[0] + box[2]) / 2 <= rect[2]
            and rect[1] <= (box[1] + box[3]) / 2 <= rect[3])


def analyze():
    sites = json.loads(cs.OUTPUT.read_text())
    mapped = {p["page"]: p for p in json.loads(cs.MAPPING.read_text())["pages"]}
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    tokens, _, _ = cm.virtual_corpus()
    by_t = {w["t"]: w for w in tokens if w["kind"] == "verse"}
    targets = [(row, "missing_name") for row in sites["missing_scanned_verse_name_hypotheses"]]
    for t, (n, _, _, _) in MISLOCALIZED_CORES.items():
        word = by_t[t]
        targets.append((dict(t=t, verse=word["verse"], form=word["form"], candidate_pages=[n]),
                        "wrong_name_location"))
    for t, candidates in sites["duplicate_canonical_tokens"].items():
        word = by_t[int(t)]
        targets.append((dict(t=int(t), verse=word["verse"], form=word["form"],
                             candidate_pages=[r["page"] for r in candidates]), "duplicate"))
    reviews = []
    for target, issue in targets:
        pages = []
        for n in target["candidate_pages"]:
            if mapped[n]["image_sha256"] != raw[n]["image_sha256"]:
                raise AssertionError("mapped and raw image hashes differ")
            words = mapped[n]["words"]
            matches = [w for w in words if w["kind"] == "verse" and w["t"] == target["t"]]
            nearby = [w for w in words if w["kind"] == "verse" and abs(w["t"] - target["t"]) <= 2]
            ids = sorted({r for w in nearby for r in w["possible_regions"]})
            regions = [dict(source_region=i, **raw[n]["regions"][i]) for i in ids]
            pages.append(dict(page=n, image_sha256=raw[n]["image_sha256"],
                              possible_first_verse=mapped[n].get("possible_first_verse"),
                              possible_last_verse=mapped[n].get("possible_last_verse"),
                              target_support=matches, nearby_words=nearby, nearby_regions=regions))
        review = dict(issue=issue, t=target["t"], verse=target["verse"], form=target["form"], pages=pages)
        if issue != "duplicate":
            cores = NAME_CORES if issue == "missing_name" else MISLOCALIZED_CORES
            n, rect, cause, note = cores[target["t"]]
            if n not in target["candidate_pages"]:
                raise AssertionError("reviewed name is outside recorded candidate pages")
            word = by_t[target["t"]]
            if (word["verse"], word["form"]) != (target["verse"], target["form"]):
                raise AssertionError("reviewed name identity differs from canonical corpus")
            ownership = {r["source_region"]: r for r in mapped[n]["regions"]}
            overlapping = [dict(source_region=i, **r, alignment=ownership.get(i)) for i, r in enumerate(raw[n]["regions"])
                           if max(rect[0], r["bbox"][0]) < min(rect[2], r["bbox"][2])
                           and max(rect[1], r["bbox"][1]) < min(rect[3], r["bbox"][3])]
            review["visual_review"] = dict(page=n, rect=rect, visually_colored=True,
                                            geometry="approximate_name_core", cause=cause, note=note,
                                            image_sha256=raw[n]["image_sha256"], overlapping_ocr_regions=overlapping)
            review["other_accepted_sites_inside_core"] = [dict(page=n, t=w["t"], verse=w["verse"],
                                                                form=w["form"], bbox=w["bbox"])
                for p in sites["pages"] if p["page"] == n for w in p["words"]
                if w["kind"] == "verse" and w["t"] != target["t"]
                and center_inside(w["bbox"], rect)]
        else:
            if target["t"] != CONFLICT["t"]:
                raise AssertionError("unreviewed duplicate")
            review["visual_review"] = CONFLICT
        reviews.append(review)
    if set(NAME_CORES) != {r["t"] for r in reviews if r["issue"] == "missing_name"}:
        raise AssertionError("review annotation inventory differs from omissions")
    automatic_names = [dict(page=p["page"], t=w["t"], verse=w["verse"], form=w["form"],
                           bbox=w["bbox"], geometry="automatic_support_hypothesis",
                           image_sha256=p["image_sha256"])
                      for p in sites["pages"] for w in p["words"] if w["is_allah_form"]]
    superseded = [r for r in automatic_names if r["t"] in MISLOCALIZED_CORES]
    if {r["t"] for r in superseded} != set(MISLOCALIZED_CORES):
        raise AssertionError("mislocalized automatic annotation is no longer present")
    name_locations = [r for r in automatic_names if r["t"] not in MISLOCALIZED_CORES]
    name_locations.extend(dict(page=r["visual_review"]["page"], t=r["t"], verse=r["verse"], form=r["form"],
                               bbox=r["visual_review"]["rect"], geometry="reviewed_name_core",
                               image_sha256=r["visual_review"]["image_sha256"])
                          for r in reviews if r["issue"] != "duplicate")
    name_locations.sort(key=lambda r: r["t"])
    collisions = []
    for t, (n, rect, _, _) in {**NAME_CORES, **MISLOCALIZED_CORES}.items():
        for row in name_locations:
            box = row["bbox"]
            if row["page"] == n and row["t"] != t and center_inside(box, rect):
                collisions.append(dict(reviewed_t=t, conflicting_location=row))
    if collisions:
        raise AssertionError("reconciled names still collide with reviewed cores")
    expected = {w["t"] for w in tokens if w["kind"] == "verse"
                and not w["verse"].startswith("1:") and cm.is_name(w["form"])}
    if len(name_locations) != len(expected) or {r["t"] for r in name_locations} != expected:
        raise AssertionError("reconciled scanned-name token inventory is not one-to-one")
    duplicate = sites["duplicate_canonical_tokens"][str(CONFLICT["t"])]
    if {r["page"] for r in duplicate} != {CONFLICT["accepted_page"], CONFLICT["rejected_page"]}:
        raise AssertionError("duplicate candidate inventory differs")
    accepted = next(r for r in duplicate if r["page"] == CONFLICT["accepted_page"])
    box, rect = accepted["bbox"], CONFLICT["accepted_rect"]
    if not center_inside(box, rect):
        raise AssertionError("accepted conflict support misses the independently read core")
    return dict(version="targeted-corpus-site-review-v1",
                inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (cs.OUTPUT, cs.MAPPING, cm.SOURCE, cm.mt.TOKENS_F)},
                reviews=reviews, reconciled_verse_name_locations=name_locations,
                superseded_automatic_name_locations=superseded,
                reconciled_locations_inside_other_reviewed_name_cores=collisions,
                summary=dict(reviewed_missing_names=len(NAME_CORES), visually_colored_missing_names=len(NAME_CORES),
                             corrected_wrong_name_locations=len(superseded), resolved_duplicate_tokens=1,
                             automatic_name_location_hypotheses=len(name_locations)-len(NAME_CORES)-len(MISLOCALIZED_CORES),
                             reviewed_name_cores=len(NAME_CORES)+len(MISLOCALIZED_CORES),
                             scanned_verse_name_token_coverage=len(expected)),
                caveat="Targets selected from known failures; no independent accuracy estimate. "
                "One AI reader inspected the scans after diagnostics. Possible and mandatory supports remain "
                "separate. Reconciled names combine automatic support hypotheses with explicitly marked manual "
                "core windows, not certified full boundaries. Full token-ID coverage does not certify all "
                "automatic locations or ink colors. Fatiha is unscanned; head basmalas are separate.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.scans:
        for review in report["reviews"]:
            for page in review["pages"]:
                path = ROOT / "hayrat-pics" / f'page_{page["page"]}.png'
                if hashlib.sha256(path.read_bytes()).hexdigest() != page["image_sha256"]:
                    raise AssertionError(f"scan differs: {path.name}")
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("targeted corpus-site review differs")
        print("PASS targeted corpus-site review, complete name-ID inventory, input hashes" + (" and scans" if args.scans else ""))
    else:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for row in report["reviews"]:
        print(row["issue"], row["t"], row["verse"], row["form"])
        review = row["visual_review"]
        print(" review", review.get("cause", "cross_page_conflict"), review.get("page", review.get("accepted_page")))
        if row.get("other_accepted_sites_inside_core"):
            print(" other automatic sites inside core", row["other_accepted_sites_inside_core"])
    print("summary", report["summary"])
    print("collisions", report["reconciled_locations_inside_other_reviewed_name_cores"])


if __name__ == "__main__":
    main()
