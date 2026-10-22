"""Exposed development comparison of v3 observations with preserved v1 sites.

No annotation or reviewed location is used to construct v3's observations or
text alignment. Every label here was exposed before this experiment.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_corpus_sites as cs
import ocr_observation_map as om
from corpus_map_validation import assess_name
from corpus_site_review import NAME_CORES, MISLOCALIZED_CORES, CONFLICT
from semantic_validation import DATA, corpus_targets, localized
from word_localization_validation import assess

OUTPUT = DATA / "audit_ocr_observation_validation_v3.json"


def analyze(mapping_path=om.OUTPUT):
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    new = json.loads(mapping_path.read_text())
    seeded_rows = new["version"] == "seeded-text-row-corpus-map-v4"
    old = json.loads(cs.OUTPUT.read_text())
    mapped, outcomes = [], Counter()
    for page in new["pages"]:
        words = []
        for word in page["words"]:
            row, status = cs.site(word, raw[page["page"]]["regions"])
            outcomes[status] += 1
            if row is not None:
                words.append(row)
        mapped.append(dict(page=page["page"], image_sha256=page["image_sha256"], words=words,
                           status=page["status"]))
    method_name = "seeded_rows_v4_sites" if seeded_rows else "filtered_observations_v3_sites"
    versions = {"preserved_sites_v1": {p["page"]: p for p in old["pages"]},
                method_name: {p["page"]: p for p in mapped}}
    screened = [dict(p, words=[w for w in p["words"] if w["surface_match"]
                              and w["overlaps_optimal_unique_anchor"]]) for p in mapped]
    versions["v4_exact_surface_anchor_screen" if seeded_rows else "v3_exact_surface_anchor_screen"] = {p["page"]: p for p in screened}
    verses = cm.mt.load_tokens()
    tokens, _, _ = cm.virtual_corpus()
    by_identity = {(w["verse"], w["word_in_verse"]): w for w in tokens if w["kind"] == "verse"}
    manuals = [DATA / name for name in (
        "audit_manual_semantic_sample.json", "audit_manual_ocr_heldout.json",
        "audit_manual_word_validation_v2.json", "audit_manual_corpus_map_sample_v1.json")]
    names = []
    for path in manuals:
        for page in json.loads(path.read_text())["pages"]:
            if page["image_sha256"] != raw[page["page"]]["image_sha256"]:
                raise AssertionError("annotation and OCR image hashes differ")
            targets = corpus_targets(verses, page["first_verse"], page["last_verse"])
            if len(targets) != len(page["names"]):
                raise AssertionError("name label inventory differs")
            for target, label in zip(targets, page["names"]):
                names.append(dict(page=page["page"], t=target["t"], verse=target["verse"],
                                  form=target["form"], rect=label["rect"]))
    reviews = [dict(t=t, page=n, rect=rect, issue="missing_name" if t in NAME_CORES else "wrong_name_location")
               for t, (n, rect, _, _) in {**NAME_CORES, **MISLOCALIZED_CORES}.items()]
    adjudicated_path = DATA / "audit_manual_word_validation_v2_adjudicated.json"
    scope_paths = [DATA / "audit_manual_corpus_map_sample_v1.json", DATA / "audit_manual_ornament_scope_v2.json"]
    results = {}
    for name, pages in versions.items():
        def evaluate(labels):
            details = [dict(**label, **{k: v for k, v in assess_name(label, label, pages[label["page"]]["words"]).items()
                                       if k not in label}) for label in labels]
            return dict(total=len(details), correct=sum(r["correct"] for r in details),
                        accepted=sum(r["bbox"] is not None for r in details), details=details)
        ordinary = []
        for page in json.loads(adjudicated_path.read_text())["pages"]:
            words = {w["t"]: w for w in pages[page["page"]]["words"] if w["kind"] == "verse"}
            for label in page["word_samples"]:
                truth = by_identity[(label["verse"], label["word_in_verse"])]
                if truth["form"] != label["form"]:
                    raise AssertionError("word annotation identity differs")
                ordinary.append(dict(page=page["page"], t=truth["t"], form=truth["form"],
                                     boundary_eligible=label["boundary_eligible"],
                                     **assess(words.get(truth["t"], {}), label)))
        scopes = []
        for path in scope_paths:
            for page in json.loads(path.read_text())["pages"]:
                rows = [w for w in pages[page["page"]]["words"] if w["kind"] == "verse"]
                first, last = (rows[0]["verse"], rows[-1]["verse"]) if rows else (None, None)
                heads = []
                for label in page.get("head_basmala_names", []):
                    word = next((w for w in pages[page["page"]]["words"] if w["verse"] == label["verse"]
                                 and w["word_in_verse"] == label["word_in_verse"]), {})
                    box = word.get("bbox")
                    heads.append(dict(**label, bbox=box, correct=bool(box and localized(
                        dict(cx=(box[0]+box[2])/2, cy=(box[1]+box[3])/2), label))))
                scopes.append(dict(page=page["page"], expected_first=page["first_verse"], expected_last=page["last_verse"],
                                   first_accepted_verse=first, last_accepted_verse=last,
                                   first_correct=first == page["first_verse"], last_correct=last == page["last_verse"],
                                   head_basmala_names=heads))
        conflicts = [dict(page=p["page"], **w) for p in pages.values() for w in p["words"]
                     if w["kind"] == "verse" and w["t"] == CONFLICT["t"]]
        known_ordinary = [dict(page=p["page"], **w) for p in pages.values() for w in p["words"]
                          if w["kind"] == "verse" and w["t"] in {25998, 70036}]
        results[name] = dict(exposed_names=evaluate(names), targeted_names=evaluate(reviews),
                            sampled_words=dict(total=len(ordinary), accepted=sum(r["accepted"] for r in ordinary),
                                               correct=sum(r["center_correct"] for r in ordinary),
                                               boundary_evaluable=sum(r["boundary_eligible"] for r in ordinary),
                                               boundary_pass=sum(r["horizontal_boundary_pass"] for r in ordinary), details=ordinary),
                            accepted_scope_checks=scopes,
                            scope_summary=dict(pages=len(scopes), exact_accepted_envelopes=sum(
                                r["first_correct"] and r["last_correct"] for r in scopes),
                                correct_endpoints=sum(r["first_correct"] + r["last_correct"] for r in scopes),
                                head_basmala_total=sum(len(r["head_basmala_names"]) for r in scopes),
                                head_basmala_correct=sum(h["correct"] for r in scopes for h in r["head_basmala_names"])),
                            duplicate_target=conflicts, known_ordinary_failures=known_ordinary)
    canonical = Counter(w["t"] for p in mapped for w in p["words"] if w["kind"] == "verse")
    expected_names = {w["t"] for w in tokens if w["kind"] == "verse" and not w["verse"].startswith("1:")
                      and cm.is_name(w["form"])}
    missing = [dict(t=w["t"], verse=w["verse"], form=w["form"]) for w in tokens
               if w["t"] in expected_names and w["t"] not in canonical]
    removed = Counter(r["reason"] for p in new["pages"] for r in p["observation_decisions"]["removed"])
    report = dict(version="exposed-geometry-observation-development-comparison-v3", results=results,
                filtered_site_summary=cm.summary(mapped), site_policy_outcomes=dict(outcomes),
                screened_site_summary=cm.summary(screened),
                removed_observations=dict(removed), missing_scanned_name_ids=missing,
                duplicate_canonical_ids={str(t): n for t, n in canonical.items() if n > 1},
                inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (*manuals, adjudicated_path, scope_paths[-1], mapping_path, cs.OUTPUT, cm.SOURCE,
                                  DATA / "audit_corpus_site_review_v1.json")},
                caveat="All labels/failures exposed before v3 development. Shared labels are not independent "
                "replications. Scope checks use accepted sites, not possible fringe envelopes. Manual targeted "
                "locations are used only for evaluation; they do not construct filtered observations or mapping. "
                "The optional screen requires exact normalized surface and overlap with an optimal unique "
                "anchor; anchor overlap need not cover the entire word and is not correctness certification. "
                "Boundary scores retain adjudication and uncertainty; no corpus-wide accuracy or probability claim.")
    if seeded_rows:
        report["version"] = "exposed-seeded-row-development-comparison-v4"
        report["caveat"] = report["caveat"].replace("before v3 development", "before v4 development")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=om.OUTPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze(args.mapping)
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("observation-map development comparison differs")
        print("PASS exposed observation-map comparison: all labels, outcomes and hashes")
    else:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for name, row in report["results"].items():
        print(name)
        for key in ("exposed_names", "targeted_names", "sampled_words"):
            print(key, {k: v for k, v in row[key].items() if k != "details"})
            if key != "sampled_words":
                print("unresolved", [r for r in row[key]["details"] if not r["correct"]])
        print("duplicate target pages", [r["page"] for r in row["duplicate_target"]])
        print("known ordinary", [(r["t"], r["bbox"]) for r in row["known_ordinary_failures"]])
        print("scopes", row["scope_summary"])
    for key in ("filtered_site_summary", "screened_site_summary", "removed_observations", "missing_scanned_name_ids", "duplicate_canonical_ids"):
        print(key, report[key])


if __name__ == "__main__":
    main()
