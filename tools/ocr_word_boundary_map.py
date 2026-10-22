"""Experimental v5: all-optimal boundary-aware word/region alignment.

Character edits cost four; every extra word or detector region within a
split/merge edge costs one. Edges permit 1:1, 1:2, 1:3, 2:1 and 3:1 groups.
Whole canonical words delimit free reference ends. These are explicit model
choices, not estimated OCR probabilities or certified word boundaries.
"""
import argparse
from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
from rapidfuzz.distance import Levenshtein
from rapidfuzz.process import cdist

import ocr_corpus_map as cm
import ocr_observation_map as om
import ocr_row_map as rm
from ocr_reading_order import RowSpec
from semantic_validation import DATA

OUTPUT = DATA / "audit_ocr_word_boundary_map_v5.json"


@dataclass(frozen=True)
class WordSpec:
    character_cost: int = 4
    boundary_cost: int = 1
    maximum_group: int = 3


def group_costs(reference, observed, spec):
    costs = {}
    for p, q in [(1, 1)] + [(1, k) for k in range(2, spec.maximum_group+1)] + [(k, 1) for k in range(2, spec.maximum_group+1)]:
        if p <= len(reference) and q <= len(observed):
            refs = ["".join(reference[i:i+p]) for i in range(len(reference)-p+1)]
            obs = ["".join(observed[j:j+q]) for j in range(len(observed)-q+1)]
            costs[p, q] = (spec.character_cost * cdist(refs, obs, scorer=Levenshtein.distance, dtype=np.int32, workers=1)
                           + spec.boundary_cost * (p+q-2))
    return costs


def table(ref_lengths, obs_lengths, costs, scale):
    """Variable insertion-cost left closure, with bounded group-edge bases."""
    n, m = len(ref_lengths), len(obs_lengths)
    prefix = np.r_[0, np.cumsum(obs_lengths, dtype=np.int32)] * scale
    result = np.empty((n+1, m+1), dtype=np.int32)
    result[0] = prefix
    for i in range(1, n+1):
        result[i, 0] = 0
        base = result[i-1, 1:] + scale * ref_lengths[i-1]
        for (p, q), edge_cost in costs.items():
            if p <= i:
                base[q-1:] = np.minimum(base[q-1:], result[i-p, :m-q+1] + edge_cost[i-p])
        result[i, 1:] = prefix[1:] + np.minimum.accumulate(np.minimum(base-prefix[1:], 0))
    return result


def word_support(reference, observed, spec=WordSpec()):
    costs = group_costs(reference, observed, spec)
    r_lengths, o_lengths = list(map(len, reference)), list(map(len, observed))
    forward = table(r_lengths, o_lengths, costs, spec.character_cost)
    # Reverse edge matrices, not concatenated word strings: reversing word
    # order alone would change split/merge character distances incorrectly.
    backward = table(r_lengths[::-1], o_lengths[::-1],
                     {key: value[::-1, ::-1] for key, value in costs.items()}, spec.character_cost)[::-1, ::-1]
    optimum = int(forward[:, -1].min())
    if optimum != int(backward[:, 0].min()):
        raise AssertionError("word forward/backward optima differ")
    owners = [set() for _ in observed]
    supported = set()
    for (p, q), edge_cost in costs.items():
        valid = forward[:len(reference)-p+1, :len(observed)-q+1] + edge_cost + backward[p:, q:] == optimum
        for i, j in np.argwhere(valid):
            ids = set(range(int(i), int(i)+p))
            supported.update(ids)
            for r in range(int(j), int(j)+q):
                owners[r].update(ids)
    rows = []
    for j, text in enumerate(observed):
        inserted = bool(np.any(forward[:, j] + len(text)*spec.character_cost + backward[:, j+1] == optimum))
        choices = sorted(owners[j])
        rows.append(dict(candidate_words=choices, whole_region_insertion_possible=inserted,
                         mandatory_word=choices[0] if len(choices) == 1 and not inserted else None))
    return dict(edit_cost=optimum, regions=rows, possible_words=sorted(supported),
                optimal_reference_startpoints=np.flatnonzero(backward[:, 0] == optimum).tolist(),
                optimal_reference_endpoints=np.flatnonzero(forward[:, -1] == optimum).tolist())


def map_page(page, ornament, tokens, starts, reference, index, spec, observation_spec, row_spec, word_spec):
    ordered, decision, groups = rm.page_observations(page, ornament, observation_spec, row_spec)
    recognized = [cm.normalized(r["text"]) for r in ordered]
    observed = "".join(recognized)
    retrieval = cm.retrieve(observed, reference, index, spec)
    report = dict(page=page["page"], image_sha256=page["image_sha256"], retrieval=retrieval,
                  normalized_ocr_chars=len(observed), regions=[], words=[], status=retrieval["status"],
                  observation_decisions=decision, row_groups=groups)
    if retrieval["status"] != "retrieved":
        return report
    lo, hi = retrieval["reference_char_window"]
    v0, v1 = max(0, bisect_right(starts, lo)-1), min(len(tokens), bisect_left(starts, hi)+1)
    selected = tokens[v0:v1]
    local = word_support([t["normalized"] for t in selected], recognized, word_spec)
    report.update(edit_cost=local["edit_cost"],
                  edit_rate=local["edit_cost"] / max(1, word_spec.character_cost * len(observed)),
                  virtual_token_window=[v0, v1],
                  optimal_reference_startpoints=[v0+i for i in local["optimal_reference_startpoints"]],
                  optimal_reference_endpoints=[v0+i for i in local["optimal_reference_endpoints"]])
    report["status"] = ("high_boundary_edit_rate" if report["edit_rate"] > spec.maximum_edit_rate
                        else "conditional_word_window_match")
    mandatory, possible = defaultdict(list), defaultdict(list)
    for r, row in enumerate(local["regions"]):
        choices = [selected[i]["v_id"] for i in row["candidate_words"]]
        owner = selected[row["mandatory_word"]]["v_id"] if row["mandatory_word"] is not None else None
        report["regions"].append(dict(source_region=ordered[r]["source_region"], candidate_v_ids=choices,
                                      whole_region_insertion_possible=row["whole_region_insertion_possible"], mandatory_v_id=owner))
        for vid in choices:
            possible[vid].append(r)
        if owner is not None:
            mandatory[owner].append(r)
    for vid in sorted(possible):
        token, ids = tokens[vid], mandatory[vid]
        box = cm.support_box(ordered, ids) if report["status"] == "conditional_word_window_match" else None
        row = dict(**token, mandatory_regions=[ordered[r]["source_region"] for r in ids],
                   possible_regions=[ordered[r]["source_region"] for r in possible[vid]],
                   is_allah_form=token["kind"] == "verse" and cm.is_name(token["form"]),
                   overlaps_optimal_unique_anchor=False)
        # The v1 optimal-character-anchor flag does not apply to this lattice.
        # False prevents downstream screens from treating it as certification.
        if box is not None:
            row.update(bbox=box, surface_match="".join(recognized[r] for r in ids) == token["normalized"])
        report["words"].append(row)
    verse_words = [w for w in report["words"] if w["kind"] == "verse"]
    report["possible_first_verse"] = verse_words[0]["verse"] if verse_words else None
    report["possible_last_verse"] = verse_words[-1]["verse"] if verse_words else None
    return report


def analyze(selected=None, spec=cm.Spec(), observation_spec=om.ObservationSpec(), row_spec=RowSpec(), word_spec=WordSpec()):
    raw = json.loads(cm.SOURCE.read_text())
    ornaments = {p["page"]: p for p in json.loads(om.ORNAMENTS.read_text())["pages"]}
    tokens, starts, reference = cm.virtual_corpus()
    index = cm.unique_index(reference, spec.anchor_length)
    pages = []
    for page in raw["pages"]:
        if selected is not None and page["page"] not in selected:
            continue
        row = map_page(page, ornaments[page["page"]], tokens, starts, reference, index, spec, observation_spec, row_spec, word_spec)
        pages.append(row)
        print("page", row["page"], row["status"], "word supports", sum("bbox" in w for w in row["words"]), flush=True)
    return dict(version="boundary-aware-word-region-map-v5", spec=asdict(spec), observation_spec=asdict(observation_spec),
                row_spec=asdict(row_spec), word_spec=asdict(word_spec), pages=pages, summary=cm.summary(pages),
                reference_endpoint_units="virtual_token_boundaries",
                character_anchor_policy="Unique anchors retrieve the window; v1 optimal-character-anchor flags are not applicable.",
                inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (cm.SOURCE, om.ORNAMENTS, cm.mt.TOKENS_F)},
                caveat="Experimental word-boundary lattice, character edit cost 4 and extra boundary cost 1, "
                "bounded 1:many/many:1 groups; free ends at canonical word boundaries. All optimal paths retained. "
                "Conditional on retrieved window and selected spatial readings; no calibrated OCR probabilities. "
                "Merged multiword detector regions do not certify individual word boxes. All prior annotations "
                "are exposed development for this model. Optimal-character-anchor flags do not apply.")


def verify(path=OUTPUT, full=False):
    saved = json.loads(path.read_text())
    for p in (cm.SOURCE, om.ORNAMENTS, cm.mt.TOKENS_F):
        if saved["inputs"][p.name] != hashlib.sha256(p.read_bytes()).hexdigest():
            raise AssertionError("word-boundary input hash differs")
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    ornaments = {p["page"]: p for p in json.loads(om.ORNAMENTS.read_text())["pages"]}
    tokens, starts, reference = cm.virtual_corpus()
    spec, obs, rows, words = cm.Spec(**saved["spec"]), om.ObservationSpec(**saved["observation_spec"]), RowSpec(**saved["row_spec"]), WordSpec(**saved["word_spec"])
    index = cm.unique_index(reference, spec.anchor_length)
    if saved["summary"] != cm.summary(saved["pages"]):
        raise AssertionError("word-boundary summary differs")
    for page in saved["pages"]:
        n = page["page"]
        ordered, decision, groups = rm.page_observations(raw[n], ornaments[n], obs, rows)
        if (page["image_sha256"], page["observation_decisions"], page["row_groups"]) != (raw[n]["image_sha256"], decision, groups):
            raise AssertionError("word-boundary image or geometry inputs differ")
        local = {r["source_region"]: i for i, r in enumerate(ordered)}
        for word in page["words"]:
            if any(word[k] != tokens[word["v_id"]][k] for k in tokens[word["v_id"]]):
                raise AssertionError("word-boundary token identity differs")
            ids = [local[i] for i in word["mandatory_regions"]]
            owners = {r["source_region"] for r in page["regions"] if r["mandatory_v_id"] == word["v_id"]}
            if set(word["mandatory_regions"]) != owners:
                raise AssertionError("word-boundary mandatory region inventory differs")
            box = cm.support_box(ordered, ids) if page["status"] == "conditional_word_window_match" else None
            if word.get("bbox") != box:
                raise AssertionError("word-boundary geometry differs")
            if box is not None and word["surface_match"] != ("".join(cm.normalized(ordered[i]["text"]) for i in ids) == word["normalized"]):
                raise AssertionError("word-boundary surface flag differs")
        if full or n in rm.REPLAY:
            if map_page(raw[n], ornaments[n], tokens, starts, reference, index, spec, obs, rows, words) != page:
                raise AssertionError(f"p{n}: word-boundary DP replay differs")
    print("PASS v5 word-boundary map: all identities, geometry, hashes and " + ("full" if full else "fixed review-page") + " DP replay")


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
