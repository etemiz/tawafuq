"""Experimental v4: seeded text rows over v3's geometry-filtered observations.

Reuse the exact anchor/subsequence-edit mathematics with a separate, recorded
reading order. Historical map functions and annotation rule hashes are kept.
"""
import argparse
from bisect import bisect_left, bisect_right
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_observation_map as om
from ocr_reading_order import RowSpec, row_groups
from semantic_validation import DATA

OUTPUT = DATA / "audit_ocr_row_map_v4.json"
REPLAY = {67, 83, 171, 204, 209, 231, 315, 316, 378, 457, 510, 542, 574}


def ordered_map(page, regions, tokens, starts, reference, index, spec):
    """Same conditional substring-support definition as v1, supplied order.

    Kept separate because historical annotation provenance hashes the original
    map_page source. The scalar/exhaustive edit-path tests cover the shared
    recurrence and ownership function; no historical function is patched.
    """
    normalized = [cm.normalized(r["text"]) for r in regions]
    observed = "".join(normalized)
    retrieval = cm.retrieve(observed, reference, index, spec)
    report = dict(page=page["page"], image_sha256=page["image_sha256"], retrieval=retrieval,
                  normalized_ocr_chars=len(observed), regions=[], words=[], status=retrieval["status"])
    if retrieval["status"] != "retrieved":
        return report
    lo, hi = retrieval["reference_char_window"]
    v0 = max(0, bisect_right(starts, lo) - 1)
    v1 = min(len(tokens), bisect_left(starts, hi) + 1)
    selected = tokens[v0:v1]
    local = cm.semiglobal_support([t["normalized"] for t in selected], normalized,
                                 [(a["reference"] - starts[v0], a["observed"], spec.anchor_length)
                                  for a in retrieval["anchors"]])
    anchor_mask = 0
    for _, j, k in local["optimal_exact_anchors"]:
        anchor_mask |= ((1 << k) - 1) << j
    report.update(edit_cost=local["edit_cost"], edit_rate=local["edit_cost"] / max(1, len(observed)),
                  virtual_token_window=[v0, v1],
                  optimal_reference_startpoints=[starts[v0] + i for i in local["optimal_reference_startpoints"]],
                  optimal_reference_endpoints=[starts[v0] + i for i in local["optimal_reference_endpoints"]],
                  optimal_anchor_covered_chars=anchor_mask.bit_count())
    report["status"] = ("anchors_not_supported_by_optimum" if anchor_mask.bit_count() < spec.minimum_anchor_coverage
                        else "high_conditional_edit_rate" if report["edit_rate"] > spec.maximum_edit_rate
                        else "conditional_window_match")
    mandatory, possible = {}, {}
    for r, row in enumerate(local["regions"]):
        owners = [selected[i]["v_id"] for i in row["candidate_words"]]
        owner = selected[row["mandatory_word"]]["v_id"] if row["mandatory_word"] is not None else None
        report["regions"].append(dict(source_region=regions[r]["source_region"], candidate_v_ids=owners,
                                      whole_region_insertion_possible=row["whole_region_insertion_possible"],
                                      mandatory_v_id=owner))
        for vid in owners:
            possible.setdefault(vid, []).append(r)
        if owner is not None:
            mandatory.setdefault(owner, []).append(r)
    for vid in sorted(possible):
        token, ids = tokens[vid], mandatory.get(vid, [])
        box = cm.support_box(regions, ids) if report["status"] == "conditional_window_match" else None
        start, end = starts[vid] - starts[v0], starts[vid + 1] - starts[v0]
        row = dict(**token, mandatory_regions=[regions[r]["source_region"] for r in ids],
                   possible_regions=[regions[r]["source_region"] for r in possible[vid]],
                   is_allah_form=token["kind"] == "verse" and cm.is_name(token["form"]),
                   overlaps_optimal_unique_anchor=any(start < i + k and end > i
                                                      for i, _, k in local["optimal_exact_anchors"]))
        if box is not None:
            row.update(bbox=box, surface_match="".join(normalized[r] for r in ids) == token["normalized"])
        report["words"].append(row)
    verse_words = [w for w in report["words"] if w["kind"] == "verse"]
    report["possible_first_verse"] = verse_words[0]["verse"] if verse_words else None
    report["possible_last_verse"] = verse_words[-1]["verse"] if verse_words else None
    return report


def page_observations(page, ornament, observation_spec, row_spec):
    if page["image_sha256"] != ornament["image_sha256"]:
        raise AssertionError("OCR and ornament image hashes differ")
    decision = om.observations(page["regions"], ornament["bands"], observation_spec)
    active = [dict(page["regions"][i], source_region=i) for i in decision["retained"]]
    groups = row_groups(active, row_spec)
    ordered = [active[i] for g in groups for i in g["ordered_indices"]]
    recorded = [dict(center_y=g["center_y"], **{key: [active[i]["source_region"] for i in g[key]]
                                               for key in ("seeds", "satellites", "ordered_indices")}) for g in groups]
    return ordered, decision, recorded


def map_page(page, ornament, tokens, starts, reference, index, spec, observation_spec, row_spec):
    ordered, decision, groups = page_observations(page, ornament, observation_spec, row_spec)
    report = ordered_map(page, ordered, tokens, starts, reference, index, spec)
    report.update(observation_decisions=decision, row_groups=groups)
    return report


def analyze(selected=None, spec=cm.Spec(), observation_spec=om.ObservationSpec(), row_spec=RowSpec()):
    raw = json.loads(cm.SOURCE.read_text())
    ornaments = {p["page"]: p for p in json.loads(om.ORNAMENTS.read_text())["pages"]}
    tokens, starts, reference = cm.virtual_corpus()
    index = cm.unique_index(reference, spec.anchor_length)
    pages = []
    for page in raw["pages"]:
        if selected is not None and page["page"] not in selected:
            continue
        row = map_page(page, ornaments[page["page"]], tokens, starts, reference, index, spec, observation_spec, row_spec)
        pages.append(row)
        print("page", row["page"], row["status"], "names", sum(w["is_allah_form"] and "bbox" in w for w in row["words"]), flush=True)
    return dict(version="seeded-text-row-corpus-map-v4", spec=asdict(spec), observation_spec=asdict(observation_spec),
                row_spec=asdict(row_spec), pages=pages, summary=cm.summary(pages),
                inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (cm.SOURCE, om.ORNAMENTS, cm.mt.TOKENS_F)},
                caveat="Experimental v3 observation selection with median-height-seeded rows. "
                "Short satellites cannot move row centers. Conditional character-edit support is still not "
                "certified word identity or geometry. Earlier labels and failure reviews are exposed development.")


def verify(path=OUTPUT, full=False):
    saved = json.loads(path.read_text())
    for p in (cm.SOURCE, om.ORNAMENTS, cm.mt.TOKENS_F):
        if saved["inputs"][p.name] != hashlib.sha256(p.read_bytes()).hexdigest():
            raise AssertionError("row-map input hashes differ")
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    ornaments = {p["page"]: p for p in json.loads(om.ORNAMENTS.read_text())["pages"]}
    tokens, starts, reference = cm.virtual_corpus()
    spec, obs_spec, row_spec = cm.Spec(**saved["spec"]), om.ObservationSpec(**saved["observation_spec"]), RowSpec(**saved["row_spec"])
    index = cm.unique_index(reference, spec.anchor_length)
    if saved["summary"] != cm.summary(saved["pages"]):
        raise AssertionError("row-map summary differs")
    for page in saved["pages"]:
        n = page["page"]
        ordered, decision, groups = page_observations(raw[n], ornaments[n], obs_spec, row_spec)
        if (decision, groups, page["image_sha256"]) != (page["observation_decisions"], page["row_groups"], raw[n]["image_sha256"]):
            raise AssertionError("row-map image or observation/row decisions differ")
        local = {r["source_region"]: i for i, r in enumerate(ordered)}
        if page["regions"] and {r["source_region"] for r in page["regions"]} != set(local):
            raise AssertionError("row-map source-region inventory differs")
        for word in page["words"]:
            if any(word[k] != tokens[word["v_id"]][k] for k in tokens[word["v_id"]]):
                raise AssertionError("row-map canonical identity differs")
            owners = {r["source_region"] for r in page["regions"] if r["mandatory_v_id"] == word["v_id"]}
            if set(word["mandatory_regions"]) != owners:
                raise AssertionError("row-map mandatory support accounting differs")
            ids = [local[i] for i in word["mandatory_regions"]]
            box = cm.support_box(ordered, ids) if page["status"] == "conditional_window_match" else None
            if word.get("bbox") != box:
                raise AssertionError("row-map support geometry differs")
            if box is not None and word["surface_match"] != ("".join(cm.normalized(ordered[i]["text"]) for i in ids) == word["normalized"]):
                raise AssertionError("row-map surface flag differs")
        if full or n in REPLAY:
            if map_page(raw[n], ornaments[n], tokens, starts, reference, index, spec, obs_spec, row_spec) != page:
                raise AssertionError(f"p{n}: row-map exact DP replay differs")
    print("PASS v4 row-map: all-page identities, supports, row decisions, hashes and "
          + ("full" if full else "fixed review-page") + " DP replays")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify(args.output, args.full)
    else:
        report = analyze(set(map(int, args.pages.split(","))) if args.pages else None)
        args.output.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
