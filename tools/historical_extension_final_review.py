"""Apply exposed scan-context corrections and replay current historical results.

Original annotations and v1/v2 results are preserved. This v3 reconstruction
is scan-free; local review sheets can be rebuilt separately.
"""

from copy import deepcopy
import argparse
import json
from pathlib import Path

import historical_extension as ext
import historical_copy_analysis as old
import same_word_alignment as sw
from semantic_validation import is_name

CORRECTIONS=ext.DATA/"research_historical_extension_coordinate_review_v1.json"
OUTPUT=ext.DATA/"research_historical_extension_review_v3.json"


def corrected_labels(labels,corrections):
    labels=deepcopy(labels)
    lookup={(p["folio"],r[0],r[1]):(p,r) for p in labels["pages"] for r in p["names"]}
    seen=set()
    for folio,verse,ordinal,left,right,new_left,new_right in corrections["updates"]:
        key=folio,verse,ordinal
        if key in seen or key not in lookup:
            raise ValueError("Duplicate/unknown correction")
        page,row=lookup[key]
        if row[4:]!=[left,right]:
            raise ValueError("Correction's original interval differs")
        if not page["frame"][0]<=new_left<new_right<=page["frame"][1]:
            raise ValueError("Corrected body outside frame")
        row[4:]=[new_left,new_right]
        seen.add(key)
    return labels


def analyze():
    base=json.loads(ext.OUTPUT.read_text())
    corrections=json.loads(CORRECTIONS.read_text())
    labels=corrected_labels(json.loads(ext.LABELS.read_text()),corrections)
    canonical,_=sw.canonical_inventory()
    names={}
    for row in canonical.values():
        if is_name(row["form"]):
            names.setdefault(row["verse"],[]).append(row)
    before={r["t"]:r for r in base["historical_occurrences"]}
    rows=[]
    for page in labels["pages"]:
        expected={t for t,r in ext.page_inventory(canonical,page).items() if is_name(r["form"])}
        actual=set()
        for verse,ordinal,word,physical_row,left,right in page["names"]:
            truth=names[verse][ordinal-1]
            t=truth["t"]
            previous=before[t]
            if word!=truth["word"] or previous["page"]!=page["folio"] or previous["row"]!=physical_row or t in actual:
                raise ValueError("Inventory/identity changed during coordinate correction")
            actual.add(t)
            rows.append(dict(previous,center=(left+right)/2))
        if actual!=expected:
            raise ValueError("Canonical page inventory differs")
    if {r["t"] for r in rows}!=set(before):
        raise ValueError("Incomplete paired inventory")
    scores={}
    modern=base["modern_ledger_context_only"]
    for tolerance in (.02,.015):
        scores[str(tolerance)]={group:dict(historical=old.bounds(rows,tolerance,5,3,standalone),
                                         modern_ledger_context_only=old.bounds(modern,tolerance,standalone=standalone))
                               for group,standalone in (("allah_name_family",False),("standalone_allah",True))}
    page_scores={p["folio"]:old.bounds([r for r in rows if r["page"]==p["folio"]],.02,5,3) for p in labels["pages"]}
    files=[ext.OUTPUT,ext.LABELS,CORRECTIONS,Path(__file__),Path(old.__file__),sw.mt.TOKENS_F]
    return dict(study=base["study"],status="Current v3, after all-name enlarged scan-context review; original v1/v2 coordinate results superseded.",
                inputs={p.name:ext.sha(p) for p in files},pages=base["pages"],
                historical_occurrences=rows,scores=scores,page_scores=page_scores,
                modern_ledger_context_only=modern,modern_unresolved=base["modern_unresolved"],
                phrases=base["phrases"],ocr=base["ocr"],colophon=base["colophon"],
                corrected_intervals=len(corrections["updates"]),
                inference=base["inference"],compatibility=base["compatibility"])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    report=analyze()
    if args.verify:
        if json.loads(OUTPUT.read_text())!=report:
            raise ValueError("Corrected historical review differs")
        print("Current v3 scan-free reconstruction passed")
    else:
        ext.save_new(OUTPUT,report)
    for tau,groups in report["scores"].items():
        print(tau,{g:[s["historical"][k] for k in ("guaranteed_aligned","midpoint_aligned","possibly_aligned","occurrences")]
                   for g,s in groups.items()})
    for page,score in report["page_scores"].items():
        print(page,score["guaranteed_aligned"],score["midpoint_aligned"],score["possibly_aligned"],score["occurrences"])


if __name__=="__main__":
    main()
