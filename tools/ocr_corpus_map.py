"""Anchor full-page OCR to exact Quran text without rosette/page-verse maps.

Globally unique exact character anchors retrieve a bounded reference window.
Within that window, all minimum-cost substring alignments are retained:
reference prefix/suffix are free, all OCR insertions still cost one. Real
surah-head basmalas are explicit synthetic tokens, not verse-name occurrences.
Window retrieval is a heuristic; edit-path guarantees are conditional on it.
"""
import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

import map_tokens as mt
from ocr_benchmark import reading_order, words
from semantic_validation import DATA, is_name

SOURCE = DATA / "ocr_google_corpus_v1.json"
OUTPUT = DATA / "audit_ocr_corpus_map_v1.json"


@dataclass(frozen=True)
class Spec:
    anchor_length: int = 20
    minimum_anchor_coverage: int = 40
    minimum_anchor_advantage: int = 20
    retrieval_span_multiplier: int = 2
    retrieval_extra_chars: int = 128
    reference_margin: int = 64
    maximum_edit_rate: float = .30


def normalized(text):
    return "".join(words(text))


def virtual_corpus(verses=None):
    """Preserve original global token IDs; add 112 unencoded head basmalas."""
    verses = mt.load_tokens() if verses is None else verses
    tokens, t = [], 0
    for s, a, ts in verses:
        if a == 1 and s not in (1, 9):
            for i, token in enumerate(("بسم", "الله", "الرحمن", "الرحيم"), 1):
                tokens.append(dict(t=None, verse=f"{s}:0", word_in_verse=i, form=token,
                                   normalized=normalized(token), kind="surah_head_basmala"))
        for i, token in enumerate(ts, 1):
            tokens.append(dict(t=t, verse=f"{s}:{a}", word_in_verse=i, form=token,
                               normalized=normalized(token), kind="verse"))
            t += 1
    starts = [0]
    for vid, token in enumerate(tokens):
        token["v_id"] = vid
        starts.append(starts[-1] + len(token["normalized"]))
    return tokens, starts, "".join(t["normalized"] for t in tokens)


def unique_index(reference, k):
    index = {}
    for i in range(len(reference) - k + 1):
        key = reference[i:i + k]
        index[key] = None if key in index else i
    return {key: i for key, i in index.items() if i is not None}


def retrieve(observed, reference, index, spec):
    k = spec.anchor_length
    anchors = [(index[observed[j:j + k]], j) for j in range(len(observed) - k + 1)
               if observed[j:j + k] in index]
    if not anchors:
        return dict(status="no_unique_anchor", anchor_count=0)
    ordered = sorted(anchors)
    span = spec.retrieval_span_multiplier * len(observed) + spec.retrieval_extra_chars
    candidates = []
    for left, (start, _) in enumerate(ordered):
        group = []
        mask = 0
        for ref, obs in ordered[left:]:
            if ref > start + span:
                break
            group.append((ref, obs))
            mask |= ((1 << k) - 1) << obs
        candidates.append((mask.bit_count(), group[0][0], group[-1][0] + k, group))
    best = min(candidates, key=lambda c: (-c[0], c[2] - c[1], c[1]))
    runner = max((c[0] for c in candidates if c[2] <= best[1] or c[1] >= best[2]), default=0)
    status = ("weak_anchor_coverage" if best[0] < spec.minimum_anchor_coverage else
              "competing_anchor_windows" if best[0] - runner < spec.minimum_anchor_advantage else "retrieved")
    group = sorted(best[3], key=lambda a: (a[1], a[0]))
    # Estimate unanchored prefix/suffix lengths from observed positions, with
    # explicit padding. No page number, rosette label or historical map is used.
    lo = max(0, min(ref - obs for ref, obs in group) - spec.reference_margin)
    hi = min(len(reference), max(ref + len(observed) - obs for ref, obs in group) + spec.reference_margin)
    return dict(status=status, anchor_count=len(anchors), anchor_covered_chars=best[0],
                competing_disjoint_coverage=runner, reference_char_window=[lo, hi],
                anchors=[dict(reference=ref, observed=obs) for ref, obs in group])


def edit_table(reference, observed, free_reference_prefix=True):
    """Exact Levenshtein rows with vectorized left-neighbor closure.

    If u[j] omits the same-row insertion edge, D[j] = j +
    min(D[0], min_{1<=k<=j}(u[k]-k)). Thus cumulative minimum gives the
    exact recurrence without a Python loop over observed characters.
    """
    n, m = len(reference), len(observed)
    table = np.empty((n + 1, m + 1), dtype=np.int32)
    j = np.arange(1, m + 1, dtype=np.int32)
    obs = np.asarray(list(observed), dtype="U1")
    table[0] = np.arange(m + 1)
    for i, char in enumerate(reference, 1):
        table[i, 0] = 0 if free_reference_prefix else i
        base = np.minimum(table[i - 1, 1:] + 1, table[i - 1, :-1] + (obs != char))
        table[i, 1:] = np.minimum.accumulate(np.minimum(base - j, table[i, 0])) + j
    return table


def semiglobal_support(reference_words, recognized_regions, anchors=()):
    """All-optimal region owners for observed text vs any reference substring."""
    reference = "".join(reference_words)
    observed = "".join(recognized_regions)
    forward = edit_table(reference, observed)
    backward = edit_table(reference[::-1], observed[::-1])[::-1, ::-1]
    optimum = int(forward[:, -1].min())
    if optimum != int(backward[:, 0].min()):
        raise AssertionError("forward/backward substring edit costs differ")
    region_of = np.asarray([r for r, text in enumerate(recognized_regions) for _ in text], dtype=np.int32)
    ref_owner = [i for i, text in enumerate(reference_words) for _ in text]
    obs_chars = np.asarray(list(observed), dtype="U1")
    owners = [set() for _ in recognized_regions]
    supported_ref_chars = []
    for i, char in enumerate(reference):
        valid = (forward[i, :-1] + backward[i + 1, 1:] + (obs_chars != char)) == optimum
        regions = np.unique(region_of[valid])
        if len(regions):
            supported_ref_chars.append(i)
        for r in regions:
            owners[int(r)].add(ref_owner[i])
    rows, start = [], 0
    for r, text in enumerate(recognized_regions):
        end = start + len(text)
        insertion = bool(np.any(forward[:, start] + len(text) + backward[:, end] == optimum))
        choices = sorted(owners[r])
        rows.append(dict(candidate_words=choices, whole_region_insertion_possible=insertion,
                         mandatory_word=choices[0] if len(choices) == 1 and not insertion else None))
        start = end
    optimal_anchors = []
    for i, j, k in anchors:
        if (0 <= i <= len(reference) - k and 0 <= j <= len(observed) - k
                and reference[i:i + k] == observed[j:j + k]
                and int(forward[i, j]) + int(backward[i + k, j + k]) == optimum):
            optimal_anchors.append((i, j, k))
    return dict(edit_cost=optimum, regions=rows, optimal_exact_anchors=optimal_anchors,
                reference_char_support=[min(supported_ref_chars), max(supported_ref_chars) + 1]
                if supported_ref_chars else None,
                optimal_reference_endpoints=np.flatnonzero(forward[:, -1] == optimum).tolist(),
                optimal_reference_startpoints=np.flatnonzero(backward[:, 0] == optimum).tolist())


def support_box(regions, ids):
    if not ids or any(not regions[r].get("bbox_valid", True) for r in ids):
        return None
    boxes = [regions[r]["bbox"] for r in ids]
    top, bottom = max(b[1] for b in boxes), min(b[3] for b in boxes)
    if top >= bottom:
        return None
    box = [min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes)]
    for r, region in enumerate(regions):
        if r not in ids and normalized(region["text"]):
            other = region["bbox"]
            if box[0] < (other[0] + other[2]) / 2 < box[2] and top < (other[1] + other[3]) / 2 < bottom:
                return None
    return box


def map_page(page, tokens, starts, reference, index, spec):
    regions = reading_order([dict(r, source_region=i) for i, r in enumerate(page["regions"])])
    normalized_regions = [normalized(r["text"]) for r in regions]
    observed = "".join(normalized_regions)
    retrieval = retrieve(observed, reference, index, spec)
    report = dict(page=page["page"], image_sha256=page["image_sha256"], retrieval=retrieval,
                  normalized_ocr_chars=len(observed), regions=[], words=[], status=retrieval["status"])
    if retrieval["status"] != "retrieved":
        return report
    lo, hi = retrieval["reference_char_window"]
    v0 = max(0, bisect_right(starts, lo) - 1)
    v1 = min(len(tokens), bisect_left(starts, hi) + 1)
    selected = tokens[v0:v1]
    local = semiglobal_support([t["normalized"] for t in selected], normalized_regions,
                              [(a["reference"] - starts[v0], a["observed"], spec.anchor_length)
                               for a in retrieval["anchors"]])
    anchor_mask = 0
    for _, j, k in local["optimal_exact_anchors"]:
        anchor_mask |= ((1 << k) - 1) << j
    report.update(edit_cost=local["edit_cost"], edit_rate=local["edit_cost"] / max(1, len(observed)),
                  virtual_token_window=[v0, v1],
                  optimal_reference_startpoints=[starts[v0] + i for i in local["optimal_reference_startpoints"]],
                  optimal_reference_endpoints=[starts[v0] + i for i in local["optimal_reference_endpoints"]])
    report["optimal_anchor_covered_chars"] = anchor_mask.bit_count()
    if report["optimal_anchor_covered_chars"] < spec.minimum_anchor_coverage:
        report["status"] = "anchors_not_supported_by_optimum"
    elif report["edit_rate"] > spec.maximum_edit_rate:
        report["status"] = "high_conditional_edit_rate"
    else:
        report["status"] = "conditional_window_match"
    mandatory, possible = {}, {}
    for r, row in enumerate(local["regions"]):
        owners = [selected[i]["v_id"] for i in row["candidate_words"]]
        owner = selected[row["mandatory_word"]]["v_id"] if row["mandatory_word"] is not None else None
        report["regions"].append(dict(source_region=regions[r]["source_region"],
                                      candidate_v_ids=owners, whole_region_insertion_possible=row["whole_region_insertion_possible"],
                                      mandatory_v_id=owner))
        for vid in owners:
            possible.setdefault(vid, []).append(r)
        if owner is not None:
            mandatory.setdefault(owner, []).append(r)
    for vid in sorted(possible):
        token = tokens[vid]
        ids = mandatory.get(vid, [])
        box = support_box(regions, ids) if report["status"] == "conditional_window_match" else None
        row = dict(**token, mandatory_regions=[regions[r]["source_region"] for r in ids],
                   possible_regions=[regions[r]["source_region"] for r in possible[vid]],
                   is_allah_form=token["kind"] == "verse" and is_name(token["form"]))
        start, end = starts[vid] - starts[v0], starts[vid + 1] - starts[v0]
        row["overlaps_optimal_unique_anchor"] = any(start < i + k and end > i
                                                    for i, _, k in local["optimal_exact_anchors"])
        if box is not None:
            row.update(bbox=box, surface_match="".join(normalized_regions[r] for r in ids) == token["normalized"])
        report["words"].append(row)
    verse_words = [w for w in report["words"] if w["kind"] == "verse"]
    report["possible_first_verse"] = verse_words[0]["verse"] if verse_words else None
    report["possible_last_verse"] = verse_words[-1]["verse"] if verse_words else None
    return report


def summary(pages):
    accepted = [w for p in pages for w in p["words"] if "bbox" in w]
    occurrences = Counter(w["t"] for w in accepted if w["kind"] == "verse")
    return dict(pages=len(pages), status_counts=dict(Counter(p["status"] for p in pages)),
                accepted_verse_word_supports=sum(w["kind"] == "verse" for w in accepted),
                accepted_exact_surface_supports=sum(w["surface_match"] for w in accepted),
                accepted_unique_anchor_overlapping_supports=sum(w["overlaps_optimal_unique_anchor"] for w in accepted),
                unique_accepted_canonical_tokens=len(occurrences),
                canonical_tokens_accepted_on_multiple_pages=sum(n > 1 for n in occurrences.values()),
                accepted_head_basmala_supports=sum(w["kind"] == "surah_head_basmala" for w in accepted),
                accepted_verse_name_supports=sum(w["is_allah_form"] for w in accepted))


def map_page_masked(page, tokens, starts, reference, index, spec, ornament):
    if ornament["image_sha256"] != page["image_sha256"]:
        raise AssertionError("ornament and OCR image hashes differ")
    retained = [i for i, r in enumerate(page["regions"])
                if not any(lo <= (r["bbox"][1] + r["bbox"][3]) / 2 < hi for lo, hi in ornament["bands"])]
    filtered = dict(page, regions=[page["regions"][i] for i in retained])
    report = map_page(filtered, tokens, starts, reference, index, spec)
    for region in report["regions"]:
        region["source_region"] = retained[region["source_region"]]
    for word in report["words"]:
        for key in ("mandatory_regions", "possible_regions"):
            word[key] = [retained[r] for r in word[key]]
    report["ornament_bands"] = ornament["bands"]
    report["excluded_ornament_regions"] = sorted(set(range(len(page["regions"]))) - set(retained))
    return report


def analyze(source, spec=Spec(), selected_pages=None, ornament_path=None):
    obj = json.loads(source.read_text())
    tokens, starts, reference = virtual_corpus()
    index = unique_index(reference, spec.anchor_length)
    ornaments = ({p["page"]: p for p in json.loads(ornament_path.read_text())["pages"]}
                 if ornament_path is not None else None)
    pages = []
    for page in obj["pages"]:
        if selected_pages is not None and page["page"] not in selected_pages:
            continue
        row = (map_page(page, tokens, starts, reference, index, spec) if ornaments is None else
               map_page_masked(page, tokens, starts, reference, index, spec, ornaments[page["page"]]))
        pages.append(row)
        print("page", row["page"], row["status"], row.get("possible_first_verse"), row.get("possible_last_verse"),
              "word supports", sum("bbox" in w for w in row["words"]), flush=True)
    report = dict(version="unique-anchor-conditional-substring-map-v1", spec=asdict(spec), pages=pages,
                summary=summary(pages), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                corpus_sha256=hashlib.sha256(mt.TOKENS_F.read_bytes()).hexdigest(),
                virtual_tokens=len(tokens), virtual_characters=len(reference),
                unique_anchor_strings=len(index),
                caveat="Independent per-page retrieval using globally unique exact anchors, then all-optimal "
                "substring edit alignment within a bounded window. No historical verse/rosette map used. "
                "Retrieval is heuristic; support is conditional on window, normalization and reading order. "
                "Synthetic head basmalas are separate from canonical verse tokens. Region support is not "
                "a complete-boundary or corpus-wide semantic-accuracy guarantee.")
    if ornament_path is not None:
        report["version"] = "gold-masked-anchor-conditional-substring-map-v2"
        report["ornament_sha256"] = hashlib.sha256(ornament_path.read_bytes()).hexdigest()
    return report


def verify_report(path, source=SOURCE, full=False, ornament_path=None):
    saved = json.loads(path.read_text())
    if saved["source_sha256"] != hashlib.sha256(source.read_bytes()).hexdigest() or saved[
            "corpus_sha256"] != hashlib.sha256(mt.TOKENS_F.read_bytes()).hexdigest():
        raise AssertionError("corpus-map input hashes differ")
    original = {p["page"]: p for p in json.loads(source.read_text())["pages"]}
    tokens, starts, reference = virtual_corpus()
    spec = Spec(**saved["spec"])
    index = unique_index(reference, spec.anchor_length)
    if (saved["virtual_tokens"], saved["virtual_characters"], saved["unique_anchor_strings"]) != (
            len(tokens), len(reference), len(index)):
        raise AssertionError("virtual corpus/basmala/anchor population differs")
    if saved["summary"] != summary(saved["pages"]):
        raise AssertionError("corpus-map summary arithmetic differs")
    ornaments = None
    if "ornament_sha256" in saved:
        ornament_path = ornament_path or DATA / "audit_ocr_ornament_bands_v1.json"
        if hashlib.sha256(ornament_path.read_bytes()).hexdigest() != saved["ornament_sha256"]:
            raise AssertionError("corpus-map ornament hashes differ")
        ornaments = {p["page"]: p for p in json.loads(ornament_path.read_text())["pages"]}
    if [p["page"] for p in saved["pages"]] != sorted(set(p["page"] for p in saved["pages"])):
        raise AssertionError("corpus-map page inventory duplicates or order differs")
    replay = {1, 11, 199, 239, 304, 402, 427, 517, 570, 588, 600, 604}
    replayed = 0
    for page in saved["pages"]:
        raw = original[page["page"]]
        if raw["image_sha256"] != page["image_sha256"]:
            raise AssertionError("mapped page image hash differs")
        excluded = set(page.get("excluded_ornament_regions", []))
        retained = [i for i in range(len(raw["regions"])) if i not in excluded]
        active = [raw["regions"][i] for i in retained]
        local_id = {source_id: i for i, source_id in enumerate(retained)}
        if ornaments is not None:
            bands = ornaments[page["page"]]["bands"]
            expected = {i for i, r in enumerate(raw["regions"])
                        if any(lo <= (r["bbox"][1] + r["bbox"][3]) / 2 < hi for lo, hi in bands)}
            if excluded != expected or page["ornament_bands"] != bands:
                raise AssertionError("stored ornament region exclusion differs")
        if page["regions"]:
            if {r["source_region"] for r in page["regions"]} != set(retained):
                raise AssertionError("mapped OCR region inventory differs")
        for word in page["words"]:
            truth = tokens[word["v_id"]]
            if any(word[k] != truth[k] for k in truth):
                raise AssertionError("canonical token or synthetic basmala identity differs")
            ids = word["mandatory_regions"]
            owners = {r["source_region"] for r in page["regions"] if r["mandatory_v_id"] == word["v_id"]}
            if set(ids) != owners:
                raise AssertionError("mandatory support-region accounting differs")
            box = (support_box(active, [local_id[r] for r in ids])
                   if page["status"] == "conditional_window_match" else None)
            if word.get("bbox") != box:
                raise AssertionError("stored corpus support geometry differs")
            if box is not None and word["surface_match"] != (
                    "".join(normalized(raw["regions"][r]["text"]) for r in ids) == word["normalized"]):
                raise AssertionError("exact OCR surface flag differs")
        if full or page["page"] in replay:
            current = (map_page(raw, tokens, starts, reference, index, spec) if ornaments is None else
                       map_page_masked(raw, tokens, starts, reference, index, spec, ornaments[page["page"]]))
            if current != page:
                raise AssertionError(f'p{page["page"]}: conditional substring support replay differs')
            replayed += 1
    print(f"PASS {path.name}: all-page identities/geometry/hashes/arithmetic; {replayed} exact DP page replays")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--pages", help="comma-separated pilot subset; no page labels are supplied")
    parser.add_argument("--ornaments", type=Path, help="versioned image-derived gold bands; writes masked v2")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--full", action="store_true", help="replay every page DP rather than the fixed 12-page check")
    args = parser.parse_args()
    if args.verify:
        verify_report(args.output, args.source, args.full, args.ornaments)
        return
    selected = set(map(int, args.pages.split(","))) if args.pages else None
    report = analyze(args.source, selected_pages=selected, ornament_path=args.ornaments)
    args.output.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
