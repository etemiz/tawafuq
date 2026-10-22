"""Freeze untouched scan-first validation of the horizontal ink-trim candidate.

Plan only: no selected scans, annotations or page-specific predictions are read.
"""
import argparse
import hashlib
import json
from pathlib import Path

import ocr_observation_map as om
import ocr_corpus_map as cm
import ocr_word_boundary_map as wm
import word_boundary_sites as ws
from ocr_ink_trim import specification
from semantic_validation import DATA, ROOT
from word_boundary_fresh_plan import OUTPUT as PREVIOUS, STRATA
from word_boundary_ink_audit import OUTPUT as DEVELOPMENT
from word_union_review import RULES, digest

OUTPUT = DATA / "audit_word_ink_trim_fresh_plan_v6.json"
SEED = "t2-v6-horizontal-ink-trim-physical-validation-2026-10-19"
EXTRA_RULES = ["ocr_ink_trim.py", "word_localization_validation.py", "word_boundary_ownership_policy.py"]


def select_pages(excluded, bands):
    pages = []
    for lo, hi in STRATA:
        candidates = [n for n in range(lo, hi+1) if n not in excluded and not bands[n]]
        n = min(candidates, key=lambda n: hashlib.sha256(f"{SEED}:{n}".encode()).hexdigest())
        pages.append(dict(page=n, stratum=[lo, hi], eligible_pages=len(candidates),
                          positions=[dict(physical_row=r, lexical_position_rtl=k)
                                     for r in (2, 7, 12) for k in (1, 4, 7)]))
    return pages


def plan():
    previous = json.loads(PREVIOUS.read_text())
    diagnostic = json.loads(DEVELOPMENT.read_text())
    excluded = set(previous["excluded_pages"]) | {p["page"] for p in previous["pages"]}
    excluded.update(map(int, diagnostic["scan_sha256"]))
    bands = {p["page"]: p["bands"] for p in json.loads(om.ORNAMENTS.read_text())["pages"]}
    pages = select_pages(excluded, bands)
    return dict(version="frozen-in-box-horizontal-ink-validation-plan-v6", seed=SEED, pages=pages,
                excluded_pages=sorted(excluded), scheduled_positions=sum(len(p["positions"]) for p in pages),
                candidate=specification(),
                inputs={p.name: digest(p) for p in (PREVIOUS, DEVELOPMENT, om.ORNAMENTS, cm.SOURCE,
                                                   wm.OUTPUT, ws.OUTPUT, cm.mt.TOKENS_F)},
                rule_sources={name: digest(ROOT / "tools" / name) for name in RULES+EXTRA_RULES},
                selection_source_sha256=digest(Path(__file__)),
                annotation_status="planned_only_no_selected_scans_inspected_or_labels_created",
                protocol="Six SHA256-ranked new non-ornament pages across the original six strata. Exclude every earlier scan-first page, prior exclusions and all scans measured in the ink diagnostic. No selected scan or page-specific prediction is inspected during selection. Transcribe canonical lexical positions 1/4/7 on physical rows 2/7/12 from scans without OCR boxes; keep every scheduled slot with explicit unavailability and no replacement. Save independent letter-core rectangles and full-ink whitespace partitions, recording mandatory/possible auxiliary-mark ownership before comparing any prediction. Keep unresolved ownership explicit; a boundary verdict is permitted only with fixed edges or an exact all-ownership certificate. Keep the 12px tolerance. After labels and evaluator are locked, compare original and horizontally trimmed broad/conservative v5 hypotheses as four paired dependent methods, recomputing centers and retaining every regression, wrong accepted site, abstention and unavailable slot. No inference retuning on this sample; the two partial-word unions, marker-contaminated union and p67 wrong-location case remain exposed development counterexamples. One-reader structured sample, not independent double annotation or a uniform-word corpus accuracy estimate.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = plan()
    if args.verify:
        if report != json.loads(OUTPUT.read_text()):
            raise AssertionError("frozen horizontal ink-trim validation plan differs")
        print("PASS frozen ink-trim inference, untouched-page selection and complete slot schedule")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print("pages", [p["page"] for p in report["pages"]], "slots", report["scheduled_positions"])


if __name__ == "__main__":
    main()
