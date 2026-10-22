"""Freeze broader physical-position v5 validation before reading predictions.

This writes a plan, not annotations or accuracy results. Selected full scans
must be read without OCR geometry; every scheduled position stays accounted.
"""
import argparse
import hashlib
import json
from pathlib import Path

import ocr_observation_map as om
import ocr_row_map as rm
from semantic_validation import DATA, ROOT
from word_union_review import PLAN as UNION_PLAN, RULES, digest
import word_boundary_sites as ws

OUTPUT = DATA / "audit_word_boundary_fresh_plan_v5.json"
SEED = "t2-v5-physical-rows-and-x-2026-10-19"
STRATA = [(2, 100), (101, 200), (201, 300), (301, 400), (401, 500), (501, 603)]
PRIOR = ["audit_manual_semantic_sample.json", "audit_manual_ocr_heldout.json",
         "audit_manual_word_validation_v2.json", "audit_manual_corpus_map_sample_v1.json",
         "audit_manual_ornament_scope_v2.json", "audit_manual_row_sample_v4.json"]


def plan():
    excluded = {1, 49, 154, 186, 206, 207, 422, 489, 567, 604} | rm.REPLAY
    for name in PRIOR:
        excluded.update(p["page"] for p in json.loads((DATA / name).read_text())["pages"])
    excluded.update(r["page"] for r in json.loads(UNION_PLAN.read_text())["samples"])
    ornaments = json.loads(om.ORNAMENTS.read_text())
    bands = {p["page"]: p["bands"] for p in ornaments["pages"]}
    pages = []
    for lo, hi in STRATA:
        candidates = [n for n in range(lo, hi+1) if n not in excluded and not bands[n]]
        n = min(candidates, key=lambda n: hashlib.sha256(f"{SEED}:{n}".encode()).hexdigest())
        pages.append(dict(page=n, stratum=[lo, hi], eligible_pages=len(candidates),
                          positions=[dict(physical_row=r, lexical_position_rtl=k)
                                     for r in (2, 7, 12) for k in (1, 4, 7)]))
    paths = [DATA / name for name in PRIOR] + [UNION_PLAN, om.ORNAMENTS, ws.OUTPUT]
    return dict(version="frozen-physical-position-validation-plan-v5", seed=SEED, pages=pages,
                excluded_pages=sorted(excluded), scheduled_positions=sum(len(p["positions"]) for p in pages),
                inputs={p.name: digest(p) for p in paths},
                rule_sources={name: digest(ROOT / "tools" / name) for name in RULES},
                selection_source_sha256=digest(Path(__file__)),
                protocol="Six new non-ornament pages, minimum SHA256(seed:page) in six page strata. "
                "Exclude all earlier annotated pages, fixed failure/replay pages and rejected-union review pages. "
                "Inference code, policy artifact and selection are frozen before this reader inspects selected "
                "pages or their predictions. On physical Quran text rows 2/7/12, independently transcribe "
                "lexical positions 1/4/7 from the right, ignoring rosettes. Retain all 54 scheduled slots: "
                "if a row/word is unavailable or identity uncertain, record that explicitly without replacement. "
                "First record canonical identity and a letter-core rectangle from scans without OCR boxes. "
                "Separately partition full word ink and assign overhanging diacritics using scan/context; "
                "ambiguous mark ownership means boundary-unscorable, never silent omission. A second reader "
                "must be identified if used; one reader cannot claim independent double annotation. Compare "
                "frozen broad and conservative v5 outputs only after labels are saved. Report correct centers, "
                "wrong accepted centers, abstentions and boundary-scorable denominators separately. "
                "Structured physical-position sample, not uniform corpus words or a full-corpus accuracy claim.",
                annotation_status="planned_only_no_scans_read_or_labels_created")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = plan()
    if args.verify:
        if report != json.loads(OUTPUT.read_text()):
            raise AssertionError("frozen v5 physical-position validation plan differs")
        print("PASS frozen v5 physical-position selection, inference rules and input hashes")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print("pages", [p["page"] for p in report["pages"]], "scheduled positions", report["scheduled_positions"])


if __name__ == "__main__":
    main()
