"""Exposed comparison of boundary-aware v5 with seeded-row v4 hypotheses.

Includes every earlier name/word label, the targeted error review and the
formerly fresh v4 sample. All are exposed development for the v5 model.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_corpus_sites as cs
import ocr_row_map as rm
import ocr_word_boundary_map as wm
from word_boundary_sites import exact_union
from corpus_site_review import NAME_CORES, MISLOCALIZED_CORES
from semantic_validation import DATA, corpus_targets, localized
from word_localization_validation import assess

OUTPUT = DATA / "audit_word_boundary_development_v5.json"


def site_pages(mapping, raw):
    result = {}
    for page in mapping["pages"]:
        rows = []
        if page["status"] in {"conditional_window_match", "conditional_word_window_match"}:
            for word in page["words"]:
                row, _ = cs.site(word, raw[page["page"]]["regions"])
                if row is not None:
                    rows.append(row)
        result[page["page"]] = dict(page=page["page"], image_sha256=page["image_sha256"], status=page["status"], words=rows)
    return result


def prediction(label, rows):
    matches = [w for w in rows if w["kind"] == label.get("kind", "verse")
               and (w["t"] == label["t"] if label.get("kind", "verse") == "verse" else
                    (w["verse"], w["word_in_verse"]) == (label["verse"], label["word_in_verse"]))]
    if len(matches) > 1:
        raise AssertionError("duplicate token identity within page")
    return matches[0] if matches else {}


def analyze():
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    sources = {"seeded_rows_v4": rm.OUTPUT, "word_boundaries_v5": wm.OUTPUT,
               "v5_exact_multiregion_unions": wm.OUTPUT}
    tokens, _, _ = cm.virtual_corpus()
    verses = cm.mt.load_tokens()
    by_t = {t["t"]: t for t in tokens if t["kind"] == "verse"}
    by_identity = {(t["verse"], t["word_in_verse"]): t for t in tokens}
    paths = [DATA / name for name in ("audit_manual_semantic_sample.json", "audit_manual_ocr_heldout.json",
        "audit_manual_word_validation_v2.json", "audit_manual_corpus_map_sample_v1.json")]
    groups = {"earlier_names": [], "targeted_names": [], "adjudicated_words": [],
              "previous_fresh_v4_words": [], "earlier_head_basmala_names": []}
    for path in paths:
        for page in json.loads(path.read_text())["pages"]:
            if page["image_sha256"] != raw[page["page"]]["image_sha256"]:
                raise AssertionError("manual name/scan hashes differ")
            targets = corpus_targets(verses, page["first_verse"], page["last_verse"])
            if len(targets) != len(page["names"]):
                raise AssertionError("manual name inventory differs from corpus")
            for target, label in zip(targets, page["names"]):
                groups["earlier_names"].append(dict(page=page["page"], **target, rect=label["rect"]))
    for t, (n, rect, _, _) in {**NAME_CORES, **MISLOCALIZED_CORES}.items():
        groups["targeted_names"].append(dict(page=n, t=t, verse=by_t[t]["verse"], form=by_t[t]["form"], rect=rect))
    adjudicated = DATA / "audit_manual_word_validation_v2_adjudicated.json"
    fresh_v4 = DATA / "audit_manual_row_sample_v4.json"
    for path, key in ((adjudicated, "adjudicated_words"), (fresh_v4, "previous_fresh_v4_words")):
        for page in json.loads(path.read_text())["pages"]:
            if page["image_sha256"] != raw[page["page"]]["image_sha256"]:
                raise AssertionError("manual word/scan hashes differ")
            for label in page["word_samples"]:
                truth = by_identity[label["verse"], label["word_in_verse"]]
                if truth["form"] != label["form"]:
                    raise AssertionError("word label/corpus identity differs")
                groups[key].append(dict(label, page=page["page"], t=truth["t"], kind=truth["kind"]))
    scopes = [DATA / "audit_manual_corpus_map_sample_v1.json", DATA / "audit_manual_ornament_scope_v2.json"]
    for path in scopes:
        for page in json.loads(path.read_text())["pages"]:
            for label in page["head_basmala_names"]:
                truth = by_identity[label["verse"], label["word_in_verse"]]
                groups["earlier_head_basmala_names"].append(dict(page=page["page"], **label, kind=truth["kind"], t=None))
    results = {}
    for method, source in sources.items():
        mapping = json.loads(source.read_text())
        pages = site_pages(mapping, raw)
        excluded_unions = []
        if method == "v5_exact_multiregion_unions":
            for page in pages.values():
                excluded_unions.extend(dict(page=page["page"], **w) for w in page["words"]
                                       if not exact_union(w))
                page["words"] = [w for w in page["words"] if exact_union(w)]
        checks = {}
        for key, labels in groups.items():
            details = []
            for label in labels:
                row = prediction(label, pages[label["page"]]["words"])
                if "x_edges" in label:
                    outcome = assess(row, label)
                    correct = outcome["center_correct"]
                else:
                    box = row.get("bbox")
                    correct = bool(box and localized(dict(cx=(box[0]+box[2])/2, cy=(box[1]+box[3])/2), label))
                    outcome = dict(accepted=bool(box), bbox=box, status="correct" if correct else "wrong_position" if box else "abstained")
                details.append(dict(**label, **outcome, correct=correct))
            summary = dict(total=len(details), correct=sum(r["correct"] for r in details),
                           accepted=sum(r["accepted"] for r in details),
                           wrong_accepted=sum(r["accepted"] and not r["correct"] for r in details))
            if details and "x_edges" in details[0]:
                summary.update(boundary_evaluable=sum(r["boundary_eligible"] for r in details),
                               boundary_pass=sum(r["horizontal_boundary_pass"] for r in details))
            checks[key] = dict(**summary, details=details)
        canonical = Counter(w["t"] for p in pages.values() for w in p["words"] if w["kind"] == "verse")
        expected = [w for w in tokens if w["kind"] == "verse" and not w["verse"].startswith("1:") and cm.is_name(w["form"])]
        scope_rows = []
        for path in scopes:
            for page in json.loads(path.read_text())["pages"]:
                rows = [w for w in pages[page["page"]]["words"] if w["kind"] == "verse"]
                endpoints = (rows[0]["verse"], rows[-1]["verse"]) if rows else (None, None)
                scope_rows.append(dict(page=page["page"], expected=[page["first_verse"], page["last_verse"]],
                                       accepted=list(endpoints), correct=endpoints == (page["first_verse"], page["last_verse"])))
        results[method] = dict(groups=checks, summary=cm.summary(list(pages.values())), excluded_nonexact_unions=excluded_unions,
            missing_scanned_name_ids=[dict(t=w["t"], verse=w["verse"], form=w["form"]) for w in expected if w["t"] not in canonical],
            duplicate_canonical_ids={str(t): n for t, n in canonical.items() if n > 1},
            accepted_scope_checks=scope_rows,
            diagnostic_tokens=[dict(page=p["page"], **w) for p in pages.values() for w in p["words"]
                               if w["kind"] == "verse" and w["t"] in {8595, 25998, 40736, 70036}])
    inputs = [cm.SOURCE, cm.mt.TOKENS_F, *sources.values(), *paths, adjudicated, fresh_v4, scopes[-1],
              DATA / "audit_corpus_site_review_v1.json"]
    return dict(version="exposed-boundary-aware-development-v5", results=results,
                inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                caveat="All annotations exposed before v5 development; the formerly fresh v4 labels are "
                "development here. Boundary-aware costs and group limits are modeling choices, not calibrated "
                "probabilities. The stricter view requires exact normalized text only for actual multi-region "
                "unions; single regions keep the original policy. Region identities/centers and horizontal edge checks do not certify full "
                "linguistic word geometry. Shared samples are dependent; no new accuracy or inference claim.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("word-boundary development comparison differs")
        print("PASS v5 development comparison: all annotations, outcomes and hashes")
    else:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for method, row in report["results"].items():
        print(method, row["summary"])
        for key, group in row["groups"].items():
            print(key, {k: v for k, v in group.items() if k != "details"})
            print("wrong/abstained", [(r["page"], r["verse"], r.get("form"), r["status"], r.get("bbox"))
                                      for r in group["details"] if not r["correct"]])
        print("missing names", row["missing_scanned_name_ids"], "duplicates", row["duplicate_canonical_ids"])
        print("excluded nonexact unions", len(row["excluded_nonexact_unions"]))
        print("scope errors", [r for r in row["accepted_scope_checks"] if not r["correct"]])
        print("diagnostic tokens", [(r["page"], r["t"], r["form"], r.get("bbox")) for r in row["diagnostic_tokens"]])


if __name__ == "__main__":
    main()
