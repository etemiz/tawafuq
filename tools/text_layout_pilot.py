"""Six-page, text/order-preserving interval-layout feasibility and pilot.

Detector intervals are not disjoint glyph bodies. Infeasible rows stay in the
report; no clipping, rescaling, reassignment or missing-word repair is applied.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import same_word_alignment as sw

PAGES = (36, 124, 298, 366, 500, 508)
FEASIBILITY = sw.DATA / "research_text_layout_feasibility_v1.json"


def feasibility():
    canonical, _ = sw.canonical_inventory()
    mapping = json.loads(sw.wm.OUTPUT.read_text())
    sites = json.loads(sw.ws.OUTPUT.read_text())
    located, unresolved = sw.locate(canonical, sites, mapping)
    by_page = {p["page"]: p for p in mapping["pages"]}
    located_by_t = {r["t"]: r for r in located}
    unresolved_by_t = {r["t"]: r for r in unresolved}
    virtual, _, _ = sw.cm.virtual_corpus()
    output = []
    for n in PAGES:
        page = by_page[n]
        groups = defaultdict(list)
        for word in located:
            if word["page"] == n:
                groups[word["row"]].append(word)
        rows = []
        for row_id, words in sorted(groups.items()):
            words = sorted(words, key=lambda w: w["t"])
            ts = [w["t"] for w in words]
            absent = [t for t in range(min(ts), max(ts)+1) if t not in ts]
            gaps = [a["bbox"][0]-b["bbox"][2] for a, b in zip(words, words[1:])]
            inversions = [[a["t"], b["t"]] for a, b in zip(words, words[1:]) if a["x2"] <= b["x2"]]
            reasons = []
            if absent:
                reasons.append("missing_or_other_row_internal_tokens")
            if inversions:
                reasons.append("canonical_order_center_inversion")
            if any(g < 0 for g in gaps):
                reasons.append("overlapping_detector_intervals")
            if len(words) < 2:
                reasons.append("fewer_than_two_words")
            rows.append(dict(row=row_id, center_y=page["row_groups"][row_id]["center_y"],
                token_ids=ts, missing_internal=[dict(t=t, canonical=canonical.get(t), located=located_by_t.get(t), unresolved=unresolved_by_t.get(t)) for t in absent],
                order_inversions=inversions, gaps_rtl=gaps,
                word_width_sum=sum(w["width"] for w in words),
                extent=[words[-1]["bbox"][0], words[0]["bbox"][2]],
                words=[dict(**w, verse=canonical[w["t"]]["verse"]) for w in words], exclusion_reasons=reasons))
        # Unknown tokens at row boundaries cannot be silently assigned. Exclude
        # both neighboring rows when the canonical sequence is discontinuous.
        transitions = []
        for a, b in zip(rows, rows[1:]):
            missing = list(range(a["token_ids"][-1]+1, b["token_ids"][0]))
            reversed_order = a["token_ids"][-1] >= b["token_ids"][0]
            if missing or reversed_order:
                transitions.append(dict(rows=[a["row"], b["row"]], missing_token_ids=missing, reversed_order=reversed_order))
                for row in (a, b):
                    row["exclusion_reasons"].append("uncertain_adjacent_row_boundary")
        starts = page["optimal_reference_startpoints"]
        ends = page["optimal_reference_endpoints"]
        envelopes = dict(starts=starts, ends_exclusive=ends,
            first_choices=[{k: virtual[v][k] for k in ("v_id", "kind", "t", "verse", "form")} for v in starts],
            last_choices=[{k: virtual[v-1][k] for k in ("v_id", "kind", "t", "verse", "form")} for v in ends])
        # Only a unique verse endpoint, matching the outer located token, is
        # accepted as a complete exterior boundary for this interval renderer.
        for row, candidates, key in ((rows[0], envelopes["first_choices"], 0), (rows[-1], envelopes["last_choices"], -1)):
            if len(candidates) != 1 or candidates[0]["kind"] != "verse" or candidates[0]["t"] != row["token_ids"][key]:
                row["exclusion_reasons"].append("uncertain_page_envelope_boundary")
        site_page = next(p for p in sites["pages"] if p["page"] == n)
        mandatory = Counter(i for w in site_page["words"] for i in w["mandatory_regions"])
        support_diagnostics = []
        for word in page["words"]:
            if word["kind"] != "verse":
                continue
            ids = word["mandatory_regions"]
            support_diagnostics.append(dict(t=word["t"], mandatory_regions=ids,
                possible_regions=word["possible_regions"], split=len(ids)>1,
                ambiguous_support=set(ids) != set(word["possible_regions"]),
                shared_mandatory=any(mandatory[i]>1 for i in ids),
                located=word["t"] in located_by_t and located_by_t[word["t"]]["page"] == n))
        for row in rows:
            row["exclusion_reasons"] = sorted(set(row["exclusion_reasons"]))
            row["eligible"] = not row["exclusion_reasons"]
        merged_or_ambiguous = [r for r in page["regions"] if len(r["candidate_v_ids"]) > 1]
        output.append(dict(page=n, image_sha256=page["image_sha256"], envelope=envelopes,
            rows=rows, discontinuous_row_transitions=transitions, supports=support_diagnostics,
            multiowner_candidate_regions=merged_or_ambiguous,
            seeded_rows_without_located_verse_words=[i for i, g in enumerate(page["row_groups"]) if g["seeds"] and i not in groups]))
    all_rows = [r for p in output for r in p["rows"]]
    return dict(version="text-order-interval-feasibility-v1", pages=output,
        summary=dict(pages=len(output), rows=len(all_rows), eligible_rows=sum(r["eligible"] for r in all_rows),
            located_words=sum(len(r["words"]) for r in all_rows),
            eligible_words=sum(len(r["words"]) for r in all_rows if r["eligible"]),
            exclusion_counts=dict(Counter(reason for r in all_rows for reason in r["exclusion_reasons"]))),
        inputs={p.name: sw.digest(p) for p in (sw.wm.OUTPUT, sw.ws.OUTPUT, sw.cm.SOURCE, sw.mt.TOKENS_F)},
        source_sha256=sw.digest(Path(__file__)),
        caveat="Exposed six-page development feasibility, no alignment scores. Original detector/support intervals are not certified glyph widths. Row membership and page scopes remain mapping hypotheses. Gaps may contain rosettes, stop signs or diacritics, so interval packing alone is not historical calligraphy.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feasibility", action="store_true", required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = feasibility()
    if args.verify:
        if json.loads(FEASIBILITY.read_text()) != report:
            raise AssertionError("layout feasibility differs")
    else:
        FEASIBILITY.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":"))+"\n")
    print(json.dumps(report["summary"], indent=2))
    for p in report["pages"]:
        print("page", p["page"], "eligible", sum(r["eligible"] for r in p["rows"]), "/", len(p["rows"]))
        for r in p["rows"]:
            if not r["eligible"]:
                print("excluded", r["row"], r["exclusion_reasons"], "negative gaps", [g for g in r["gaps_rtl"] if g<0])


if __name__ == "__main__":
    main()
