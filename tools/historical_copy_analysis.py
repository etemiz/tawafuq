"""Descriptive historical-name pilot, with explicit coordinate uncertainty.

Historical annotations precede scoring. Replay uses the unchanged canonical
inventory and modern ledger; network and scans are unnecessary for --verify.
"""

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import same_word_alignment as sw
from semantic_validation import is_name

DATA = Path(__file__).resolve().parent / "data"
PLAN = DATA / "research_historical_copy_plan_v1.json"
LABELS = DATA / "research_historical_copy_annotations_v1.json"
OUTPUT = DATA / "research_historical_copy_analysis_v1.json"
MODERN = DATA / "research_same_word_alignment_v1.json"


def bounds(rows, tolerance, center_error=0, frame_edge_error=0, standalone=False):
    """Pairwise sufficient lower / necessary upper endpoint bounds.

    Each row has page, row, center, frame_width and word. Interval overlap
    permits a pair only; simultaneous attainability is not asserted.
    Fractions make the inclusive threshold and sensitivity reproducible.
    """
    selected = [r for r in rows if not standalone or r["word"] == "الله"]
    lower, point, upper = set(), set(), set()
    pairs = []
    tau = Fraction(str(tolerance))
    for i, a in enumerate(selected):
        for j, b in enumerate(selected[:i]):
            if a["page"] != b["page"] or a["row"] == b["row"]:
                continue
            assert a["frame_width"] == b["frame_width"]
            distance = abs(Fraction(str(a["center"])) - Fraction(str(b["center"])))
            width = Fraction(str(a["frame_width"]))
            certain = distance + 2*center_error <= tau*(width-2*frame_edge_error)
            central = distance <= tau*width
            possible = max(0, distance-2*center_error) <= tau*(width+2*frame_edge_error)
            for condition, endpoints in ((certain, lower), (central, point), (possible, upper)):
                if condition:
                    endpoints.update((a["t"], b["t"]))
            if possible:
                pairs.append(dict(tokens=[b["t"], a["t"]], distance=float(distance),
                                  guaranteed=certain, midpoint_match=central))
    return dict(occurrences=len(selected), guaranteed_aligned=len(lower),
                midpoint_aligned=len(point), possibly_aligned=len(upper),
                guaranteed_token_ids=sorted(lower), midpoint_token_ids=sorted(point),
                possible_token_ids=sorted(upper), possible_pairs=pairs)


def analyze():
    labels = json.loads(LABELS.read_text())
    canonical, _ = sw.canonical_inventory()
    names = defaultdict(list)
    verse_tokens = defaultdict(list)
    for row in canonical.values():
        verse_tokens[row["verse"]].append(row)
        if is_name(row["form"]):
            names[row["verse"]].append(row)
    modern = json.loads(MODERN.read_text())["views"]["conservative_v5"]["located_inventory"]
    modern_lookup = {r[0]: r for r in modern}
    extents = defaultdict(list)
    for t, page, row, x2, width in modern:
        extents[page].extend((Fraction(x2-width, 2), Fraction(x2+width, 2)))
    historical, matched_modern, pages = [], [], []
    seen = set()
    for page in labels["pages"]:
        expected = []
        active = False
        for verse, tokens in verse_tokens.items():
            if verse == page["first_verse"]:
                active = True
            if active:
                expected.extend(r["t"] for r in names[verse])
            if verse == page["last_verse"]:
                break
        found = []
        per_page = []
        for verse, ordinal, word, row, left, right in page["names"]:
            truth = names[verse][ordinal-1]
            assert truth["word"] == word, (verse, ordinal, truth["word"], word)
            t = truth["t"]
            assert t not in seen and left < right
            seen.add(t)
            found.append(t)
            historical.append(dict(t=t, page=page["folio"], row=row, word=word,
                                   center=(left+right)/2,
                                   frame_width=page["frame"][1]-page["frame"][0]))
            mapped = modern_lookup.get(t)
            detail = dict(t=t, verse=verse, ordinal=ordinal, word=word, historical_row=row)
            if mapped is not None:
                _, mp, mr, x2, width = mapped
                frame_width = max(extents[mp])-min(extents[mp])
                matched_modern.append(dict(t=t, page=mp, row=mr, word=word,
                                          center=x2/2, frame_width=float(frame_width)))
                detail.update(modern_page=mp, modern_seeded_row=mr,
                              modern_center=x2/2, modern_frame_width=float(frame_width))
            else:
                detail["modern_missing"] = True
            per_page.append(detail)
        assert sorted(expected) == sorted(found), (page["folio"], expected, found)
        content_pages = sorted({modern_lookup[r["t"]][1]
                                for verse, tokens in verse_tokens.items()
                                for r in tokens if r["t"] in modern_lookup
                                and tuple(map(int, page["first_verse"].split(":")))
                                <= tuple(map(int, verse.split(":")))
                                <= tuple(map(int, page["last_verse"].split(":")))})
        pages.append(dict(folio=page["folio"], file=page["file"], names=len(found),
                          canonical_name_inventory_complete=True,
                          modern_pages_for_full_verse_range=content_pages, tokens=per_page))
    scores = {}
    for tolerance in (0.02, 0.015):
        scores[str(tolerance)] = {}
        for group, standalone in (("allah_name_family", False), ("standalone_allah", True)):
            historical_score = bounds(historical, tolerance, labels["center_error"],
                                      labels["frame_edge_error"], standalone)
            modern_score = bounds(matched_modern, tolerance, standalone=standalone)
            scores[str(tolerance)][group] = dict(historical=historical_score,
                                                 matched_modern=modern_score)
    files = [PLAN, LABELS, MODERN, sw.mt.TOKENS_F, Path(__file__), Path(sw.__file__)]
    return dict(study=labels["study"], inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in files},
                methods=dict(modern_frame="All accepted mapped verse-token box extents on each modern page, independent of selected name alignment.",
                             modern_partner_population="Only the same canonical names selected on the six historical pages; no outside partners.",
                             uncertainty="Historical lower/upper are pairwise coordinate envelopes under the assumed allowances, not confidence intervals or joint sharp bounds.",
                             comparison="Descriptive unmatched page/row layouts; historical manual ink midpoints and modern detector-box midpoints differ in measurement method."),
                pages=pages, scores=scores, historical_occurrences=historical,
                matched_modern_occurrences=matched_modern,
                modern_unresolved=sorted(seen-set(r["t"] for r in matched_modern)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.verify:
        assert json.loads(OUTPUT.read_text()) == report
        print("Historical pilot deterministic replay passed")
    else:
        if OUTPUT.exists():
            raise FileExistsError("Frozen result exists; use --verify")
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for tolerance, groups in report["scores"].items():
        for group, score in groups.items():
            h, m = score["historical"], score["matched_modern"]
            print(tolerance, group, "historical lower/midpoint/upper/total",
                  h["guaranteed_aligned"], h["midpoint_aligned"], h["possibly_aligned"], h["occurrences"],
                  "modern", m["midpoint_aligned"], m["occurrences"])
    for page in report["pages"]:
        print(page["folio"], page["names"], page["modern_pages_for_full_verse_range"])


if __name__ == "__main__":
    main()
