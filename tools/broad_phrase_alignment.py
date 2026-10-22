"""Color-independent exact words/phrases, with coherent row-spacing sensitivity.

Phrase partners must align every corresponding word, not merely a colored
component or the phrase's middle. The spacing comparison is a fixed-width
interval model inherited from the finished print, not an origin likelihood.
"""
import argparse
from collections import Counter, defaultdict
from itertools import combinations
import hashlib
import json
from pathlib import Path

import numpy as np

import same_word_alignment as sw
from audit_stats import tail_summary

PLAN = sw.DATA / "research_broad_phrase_plan_v1.json"
FEASIBILITY = sw.DATA / "research_broad_phrase_feasibility_v1.json"
OUTPUT = sw.DATA / "research_broad_phrase_alignment_v1.json"
LENGTHS = tuple(range(1, 7))
REPS = 5000
SEED = 20261021


def load():
    canonical, omitted = sw.canonical_inventory()
    mapping = json.loads(sw.wm.OUTPUT.read_text())
    sites = json.loads(sw.ws.OUTPUT.read_text())
    words, unresolved = sw.locate(canonical, sites, mapping)
    original = json.loads(sw.OUTPUT.read_text())
    inventory = [[w[k] for k in ("t", "page", "row", "x2", "width")] for w in words]
    if inventory != original["views"]["conservative_v5"]["located_inventory"]:
        raise AssertionError("word inventory differs from frozen same-word study")
    return canonical, words, mapping, original, omitted, unresolved


def row_feasibility(canonical, words, mapping):
    """Same conservative whole-row eligibility as the exposed six-page pilot."""
    virtual, _, _ = sw.cm.virtual_corpus()
    grouped = defaultdict(lambda: defaultdict(list))
    for i, w in enumerate(words):
        grouped[w["page"]][w["row"]].append(i)
    pages = []
    for page in mapping["pages"]:
        rows = []
        for row, ids in sorted(grouped[page["page"]].items()):
            ids = sorted(ids, key=lambda i: words[i]["t"])
            tokens = [words[i]["t"] for i in ids]
            gaps = [words[a]["bbox"][0]-words[b]["bbox"][2] for a, b in zip(ids, ids[1:])]
            reasons = []
            if len(tokens) != tokens[-1]-tokens[0]+1:
                reasons.append("missing_or_other_row_internal_tokens")
            if any(words[a]["x2"] <= words[b]["x2"] for a, b in zip(ids, ids[1:])):
                reasons.append("canonical_order_center_inversion")
            if any(g < 0 for g in gaps):
                reasons.append("overlapping_detector_intervals")
            if len(ids) < 2:
                reasons.append("fewer_than_two_words")
            rows.append(dict(row=row, word_indices=ids, token_ids=tokens, gaps_rtl=gaps,
                extent=[words[ids[-1]]["bbox"][0], words[ids[0]]["bbox"][2]],
                exclusion_reasons=reasons))
        for a, b in zip(rows, rows[1:]):
            if a["token_ids"][-1]+1 != b["token_ids"][0]:
                for r in (a, b):
                    r["exclusion_reasons"].append("uncertain_adjacent_row_boundary")
        if rows:
            for row, choices, last in ((rows[0], page["optimal_reference_startpoints"], False),
                                       (rows[-1], page["optimal_reference_endpoints"], True)):
                v = virtual[choices[0]-int(last)] if len(choices) == 1 else None
                if v is None or v["kind"] != "verse" or v["t"] != row["token_ids"][-1 if last else 0]:
                    row["exclusion_reasons"].append("uncertain_page_envelope_boundary")
        for row in rows:
            row["exclusion_reasons"] = sorted(set(row["exclusion_reasons"]))
            row["eligible"] = not row["exclusion_reasons"]
        pages.append(dict(page=page["page"], image_sha256=page["image_sha256"], rows=rows))
    # Reuse the exact old rules, not a favorable new threshold for phrases.
    import text_layout_pilot as fp
    previous = json.loads(fp.FEASIBILITY.read_text())
    for p in previous["pages"]:
        current = next(q for q in pages if q["page"] == p["page"])
        if [(r["row"], r["eligible"], r["exclusion_reasons"]) for r in current["rows"]] != [
                (r["row"], r["eligible"], r["exclusion_reasons"]) for r in p["rows"]]:
            raise AssertionError("corpus row criteria differ from six-page pilot")
    all_rows = [r for p in pages for r in p["rows"]]
    return dict(version="broad-phrase-row-feasibility-v1", pages=pages,
        summary=dict(pages=len(pages), rows=len(all_rows), eligible_rows=sum(r["eligible"] for r in all_rows),
            located_words=len(words), eligible_words=sum(len(r["word_indices"]) for r in all_rows if r["eligible"]),
            exclusion_counts=dict(Counter(s for r in all_rows for s in r["exclusion_reasons"]))),
        caveat="Corpus-wide reuse of exposed development interval rules, not held-out historical validation. All excluded rows retained. Eligibility is independent of word/phrase identity and alignment score.")


def plan():
    paths = (Path(__file__), sw.ROOT / "tools/test_broad_phrase_alignment.py", FEASIBILITY,
        sw.OUTPUT, sw.wm.OUTPUT, sw.ws.OUTPUT, sw.cm.SOURCE, sw.mt.TOKENS_F,
        sw.ROOT / "tools/same_word_alignment.py", sw.ROOT / "tools/map_tokens.py",
        sw.ROOT / "tools/ocr_corpus_map.py", sw.ROOT / "tools/semantic_validation.py",
        sw.ROOT / "tools/divine_census.py", sw.ROOT / "tools/audit_stats.py",
        sw.DATA / "research_text_layout_feasibility_v1.json")
    return dict(version="broad-phrase-plan-v1", date="2026-10-19",
        question="Measure actual repeated words/phrases beyond Allah-name forms, without selecting ink colors; test spacing sensitivity preserving actual text/order.",
        inputs={p.name: sw.digest(p) for p in paths},
        inventory="All canonical scanned verse words, excluding Fatiha and synthetic head basmalas. Exact spelling from the frozen same-word study; prefixes and hamza distinctions retained. Phrases are contiguous 2..6-word windows inside a single verse, with at least two canonical occurrences anywhere. Single words include the full canonical inventory.",
        location="All constituent words must be mapped on one page and one seeded row, in strictly decreasing RTL centers. Missing, page-split, row-split and reversed-order windows remain explicitly accounted for. Partners must be on distinct rows of one page.",
        scoring=dict(primary="Each phrase occurrence is aligned once iff an identical phrase has ALL corresponding word centers within 15px. Single words use the same endpoint rule.",
            secondary="Phrase-hull center within 15px, reported descriptively; does not certify individual word correspondence.",
            primary_groups="Six separate lengths 1..6 excluding any occurrence whose identity contains an Allah-name form under the canonical name predicate. Other divine words, ordinary words and phrases remain included.",
            all_words="Report inclusive counts separately, plus complete per-type tables. Overlapping windows and lengths are not independent evidence."),
        comparison=dict(population="Only complete eligible rows under unchanged six-page interval feasibility rules, extended corpus-wide at the user's request. Full mapped geometry is reported separately and not assigned this subset's tail.",
            fixed="Actual text/order, page/row assignments, detector widths and outer row edges. Permute the observed nonnegative gap multiset independently within each eligible row. No phrase-identity relabeling or target-score optimization.",
            limitations="An exposed development spacing-sensitivity model, not a validated historical renderer. Inherits print widths and line breaks; omits glyph/marker ownership. Gap exchangeability is not independently validated. No origin likelihood.",
            replicates=REPS, seed=SEED, rng="numpy.default_rng/PCG64", multiple_tests="Bonferroni factor six for the six primary non-Allah-form length metrics; report unadjusted and adjusted plus-one MC summaries. No individual-type significance claims or multiplication of tails."),
        sensitivity="Require every constituent's normalized OCR surface to match the exact canonical form, using the frozen exact-surface view; report descriptive outcomes without refitting or new simulations.",
        diagnostics="For each length, select earliest six aligned non-Allah-form pairs with distinct identities and pages, plus earliest two unpaired non-Allah-form occurrences on other pages. Inspect scan-backed side-by-side crops as exposed diagnostics, not fresh annotation. Report unpaired counts and full per-type outcomes, including failures.",
        completion="Finish the full exact-word/phrase inventory, coherence-preserving spacing comparison, independent small-ground-truth tests, replay, scan diagnostics and origin assessment. Do not extrapolate spacing tails into divinity probabilities.")


def windows(canonical, length):
    """Return every within-verse canonical window, not color-selected sites."""
    verses = defaultdict(list)
    for t, w in canonical.items():
        verses[w["verse"]].append(t)
    result = []
    for ids in verses.values():
        ids = sorted(ids)
        for start in range(len(ids)-length+1):
            chosen = ids[start:start+length]
            if chosen != list(range(chosen[0], chosen[0]+length)):
                raise AssertionError("canonical within-verse token IDs are discontinuous")
            result.append((chosen[0], tuple(canonical[t]["word"] for t in chosen)))
    return result


def inventory(canonical, words, length, eligible, exact_surface):
    all_windows = windows(canonical, length)
    counts = Counter(phrase for _, phrase in all_windows)
    vocabulary = sorted(phrase for phrase, count in counts.items() if length == 1 or count >= 2)
    labels = {p: i for i, p in enumerate(vocabulary)}
    lookup = {w["t"]: i for i, w in enumerate(words)}
    ledger, occurrences = [], []
    for start, phrase in all_windows:
        if phrase not in labels:
            continue
        ids = [lookup.get(t) for t in range(start, start+length)]
        selected = [words[i] for i in ids if i is not None]
        status = ("missing_constituent" if None in ids else
                  "cross_page" if len({w["page"] for w in selected}) != 1 else
                  "cross_row" if len({w["row"] for w in selected}) != 1 else
                  "reversed_or_duplicate_centers" if any(a["x2"] <= b["x2"] for a, b in zip(selected, selected[1:])) else "located")
        ledger.append([start, labels[phrase], status])
        if status != "located":
            continue
        occurrences.append(dict(start=start, label=labels[phrase], page=selected[0]["page"], row=selected[0]["row"],
            indices=ids, hull_x2=min(w["bbox"][0] for w in selected)+max(w["bbox"][2] for w in selected),
            eligible=all(i in eligible for i in ids), exact_surface=all(w["t"] in exact_surface for w in selected)))
    family_words = {w["word"] for w in canonical.values() if sw.is_name(w["form"])}
    non_allah = np.array([not any(w in family_words for w in phrase) for phrase in vocabulary], dtype=bool)
    return dict(length=length, total_canonical_windows=len(all_windows), vocabulary=vocabulary,
                expected=[counts[p] for p in vocabulary], ledger=ledger, occurrences=occurrences, non_allah=non_allah)


def candidates(occurrences):
    grouped = defaultdict(list)
    for i, o in enumerate(occurrences):
        grouped[o["page"], o["label"]].append(i)
    pairs = [(i, j) for ids in grouped.values() for i, j in combinations(ids, 2)
             if occurrences[i]["row"] != occurrences[j]["row"]]
    if not pairs:
        return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int32)
    return np.asarray(pairs, dtype=np.int32).T


def aligned(positions, indices, left, right):
    match = np.all(np.abs(positions[indices[left]]-positions[indices[right]]) <= 30, axis=1)
    marked = np.zeros(len(indices), dtype=bool)
    marked[left[match]] = True
    marked[right[match]] = True
    return marked, match


def count_metrics(marked, labels, non_allah):
    return dict(all=int(marked.sum()), without_allah_forms=int(np.count_nonzero(marked & non_allah[labels])))


def packer(words, feasibility):
    """Vectorized row-order-preserving packing with separately permuted gaps."""
    ids, base, prior_gap_indices, offsets, gaps, groups = [], [], [], [], [], []
    running = 0
    row_number = 0
    for p in feasibility["pages"]:
        for r in p["rows"]:
            if not r["eligible"]:
                continue
            width_before = 0
            gap_start = len(gaps)
            for j, i in enumerate(r["word_indices"]):
                width = words[i]["width"]
                ids.append(i)
                base.append(2*r["extent"][1]-2*width_before-width)
                prior_gap_indices.append(gap_start+j-1 if j else -1)
                offsets.append(running if j else 0)
                width_before += width
            gaps.extend(r["gaps_rtl"])
            groups.extend([row_number]*len(r["gaps_rtl"]))
            running += sum(r["gaps_rtl"])
            row_number += 1
    return dict(ids=np.array(ids, dtype=np.int32), base=np.array(base, dtype=np.int64),
        prior=np.array(prior_gap_indices, dtype=np.int32), offsets=np.array(offsets, dtype=np.int64),
        gaps=np.array(gaps, dtype=np.int64), groups=np.array(groups, dtype=np.int32))


def packed_centers(packing, gaps):
    cumulative = np.r_[np.cumsum(gaps), 0]
    return packing["base"]-2*(cumulative[packing["prior"]]-packing["offsets"])


def prepare(canonical, words, length, eligible, exact_surface):
    inv = inventory(canonical, words, length, eligible, exact_surface)
    occurrences = inv["occurrences"]
    indices = np.asarray([o["indices"] for o in occurrences], dtype=np.int32).reshape(-1, length)
    left, right = candidates(occurrences)
    labels = np.array([o["label"] for o in occurrences], dtype=np.int32)
    keep = np.array([o["eligible"] for o in occurrences], dtype=bool)
    surface = np.array([o["exact_surface"] for o in occurrences], dtype=bool)
    pages = np.array([o["page"] for o in occurrences], dtype=np.int32)
    return dict(inv=inv, indices=indices, left=left, right=right, labels=labels, keep=keep, surface=surface, pages=pages,
                sim_left=left[keep[left] & keep[right]], sim_right=right[keep[left] & keep[right]])


def simulate(words, packing, prepared):
    rng = np.random.default_rng(SEED)
    samples = {n: {k: [] for k in ("all", "without_allah_forms")} for n in LENGTHS}
    sums = {n: np.zeros(len(p["inv"]["vocabulary"]), dtype=np.int64) for n, p in prepared.items()}
    page_sums = {n: np.zeros(605, dtype=np.int64) for n in LENGTHS}
    positions = np.array([w["x2"] for w in words], dtype=np.int64)
    sha = hashlib.sha256()
    for trial in range(REPS):
        order = np.lexsort((rng.random(len(packing["gaps"])), packing["groups"]))
        gaps = np.empty_like(packing["gaps"])
        gaps[order] = packing["gaps"]
        positions[packing["ids"]] = packed_centers(packing, gaps)
        sha.update(positions[packing["ids"]].astype("<i8", copy=False).tobytes())
        for n, p in prepared.items():
            marked, _ = aligned(positions, p["indices"], p["sim_left"], p["sim_right"])
            counts = count_metrics(marked, p["labels"], p["inv"]["non_allah"])
            for key, value in counts.items():
                samples[n][key].append(value)
            sums[n] += np.bincount(p["labels"][marked], minlength=len(sums[n]))
            page_sums[n] += np.bincount(p["pages"][marked], minlength=605)
        if (trial+1) % 500 == 0:
            print("spacing trials", trial+1, "/", REPS, flush=True)
    return dict(samples={str(n): s for n, s in samples.items()},
        per_type_aligned_sums={str(n): s.tolist() for n, s in sums.items()},
        per_page_aligned_sums={str(n): s.tolist() for n, s in page_sums.items()},
        generated_centers_sha256=sha.hexdigest())


def summarize(words, p, simulation):
    inv = p["inv"]
    occurrences = inv["occurrences"]
    positions = np.array([w["x2"] for w in words], dtype=np.int64)
    marked, matches = aligned(positions, p["indices"], p["left"], p["right"])
    feasible_marked, feasible_matches = aligned(positions, p["indices"], p["sim_left"], p["sim_right"])
    surface_left, surface_right = p["left"][p["surface"][p["left"]] & p["surface"][p["right"]]], p["right"][p["surface"][p["left"]] & p["surface"][p["right"]]]
    surface_marked, _ = aligned(positions, p["indices"], surface_left, surface_right)
    hull = np.array([o["hull_x2"] for o in occurrences], dtype=np.int64).reshape(-1, 1)
    hull_marked, _ = aligned(hull[:, 0], np.arange(len(hull)).reshape(-1, 1), p["left"], p["right"])
    views = dict(full_mapped=marked, feasible_rows=feasible_marked, exact_surface=surface_marked, hull_center_only=hull_marked)
    selected = inv["non_allah"][p["labels"]]
    totals = {name: count_metrics(flags, p["labels"], inv["non_allah"]) for name, flags in views.items()}
    located = dict(all=len(occurrences), without_allah_forms=int(selected.sum()))
    feasible = dict(all=int(p["keep"].sum()), without_allah_forms=int((p["keep"] & selected).sum()))
    exact_surface = dict(all=int(p["surface"].sum()), without_allah_forms=int((p["surface"] & selected).sum()))
    type_counts = {name: np.bincount(p["labels"][flags], minlength=len(inv["vocabulary"])) for name, flags in views.items()}
    freq = np.bincount(p["labels"], minlength=len(inv["vocabulary"]))
    feasible_freq = np.bincount(p["labels"][p["keep"]], minlength=len(inv["vocabulary"]))
    null_sums = simulation["per_type_aligned_sums"][str(inv["length"])]
    if len(null_sums) != len(freq):
        raise AssertionError("simulation type inventory differs")
    types = [dict(words=list(phrase), canonical_expected=inv["expected"][i], located=int(freq[i]),
        without_allah_forms=bool(inv["non_allah"][i]), eligible=int(feasible_freq[i]),
        aligned={name: int(counts[i]) for name, counts in type_counts.items()},
        spacing_mean_aligned=null_sums[i]/REPS) for i, phrase in enumerate(inv["vocabulary"])]
    inference = {}
    for key in ("all", "without_allah_forms"):
        values = simulation["samples"][str(inv["length"])] [key]
        if len(values) != REPS or any(not isinstance(v, int) or v < 0 or v > feasible[key] for v in values):
            raise AssertionError("invalid broad spacing samples")
        inference[key] = tail_summary(totals["feasible_rows"][key], values)
    inference["without_allah_forms"]["bonferroni_six_plus_one_mc"] = min(1.0, 6*inference["without_allah_forms"]["plus_one_mc"])
    # Aggregate consistency does not replace full replay, available separately.
    if sum(null_sums) != sum(simulation["samples"][str(inv["length"])] ["all"]):
        raise AssertionError("per-type simulation accounting differs")
    if sum(null_sums[i] for i, yes in enumerate(inv["non_allah"]) if yes) != sum(simulation["samples"][str(inv["length"])] ["without_allah_forms"]):
        raise AssertionError("non-Allah simulation accounting differs")
    if sum(simulation["per_page_aligned_sums"][str(inv["length"])]) != sum(null_sums):
        raise AssertionError("per-page simulation accounting differs")
    pairs = [[occurrences[i]["start"], occurrences[j]["start"]] for i, j in zip(p["left"][matches], p["right"][matches])]
    feasible_pairs = [[occurrences[i]["start"], occurrences[j]["start"]] for i, j in zip(p["sim_left"][feasible_matches], p["sim_right"][feasible_matches])]
    return dict(length=inv["length"], total_canonical_windows=inv["total_canonical_windows"],
        expected_analyzed_windows=len(inv["ledger"]), canonical_types=len(types), location_status_counts=dict(Counter(r[2] for r in inv["ledger"])),
        located_population=located, feasible_population=feasible, exact_surface_population=exact_surface,
        observed=totals, inference=inference, per_type=types, occurrence_ledger_schema=["first_token_id", "type_index", "status"],
        occurrence_ledger=inv["ledger"], located_occurrence_schema=["first_token_id", "type_index", "page", "seeded_row", "eligible", "exact_surface"],
        located_occurrences=[[o[k] for k in ("start", "label", "page", "row", "eligible", "exact_surface")] for o in occurrences],
        aligned_pairs=pairs, feasible_aligned_pairs=feasible_pairs,
        unpaired_start_ids=[o["start"] for o, yes in zip(occurrences, marked) if not yes])


def analyze(saved=None, full=False):
    if json.loads(PLAN.read_text()) != plan():
        raise AssertionError("broad study plan/candidate/inputs differ after freeze")
    canonical, words, mapping, original, omitted, unresolved = load()
    feasible = row_feasibility(canonical, words, mapping)
    if feasible != json.loads(FEASIBILITY.read_text()):
        raise AssertionError("broad row feasibility differs")
    packing = packer(words, feasible)
    positions = np.array([w["x2"] for w in words], dtype=np.int64)
    if not np.array_equal(packed_centers(packing, packing["gaps"]), positions[packing["ids"]]):
        raise AssertionError("vectorized packing does not reproduce original word centers")
    eligible = set(packing["ids"].tolist())
    exact_surface = {r[0] for r in original["views"]["exact_surface_v5"]["located_inventory"]}
    prepared = {n: prepare(canonical, words, n, eligible, exact_surface) for n in LENGTHS}
    simulation = simulate(words, packing, prepared) if saved is None or full else saved["simulation"]
    results = {str(n): summarize(words, p, simulation) for n, p in prepared.items()}
    # Every single-word result must reproduce the earlier full mapped ledger.
    old_pairs = sorted(sorted(pair) for pair in original["views"]["conservative_v5"]["same_word_pair_token_ids"])
    if sorted(sorted(pair) for pair in results["1"]["aligned_pairs"]) != old_pairs:
        raise AssertionError("broad single-word pairs differ from original full-corpus study")
    return dict(version="broad-exact-word-phrase-alignment-v1", plan_sha256=sw.digest(PLAN),
        canonical_tokens=len(canonical), located_tokens=len(words), unresolved_tokens=len(unresolved), omitted=omitted,
        feasibility_summary=feasible["summary"], results=results, simulation=simulation,
        caveat="Actual strict words/phrases selected from canonical text, without ink-color selection. Repeated within-verse windows, complete mapped rows for phrases, different-row same-page partners and every-word <=15px correspondence. Whole-corpus geometry and eligible-row spacing sensitivity are distinct populations. Overlapping windows/types/lengths are dependent. Original OCR locations, missingness and interval-model assumptions remain explicit; no divine-origin probability or historical production proof.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        if PLAN.exists() or OUTPUT.exists() or FEASIBILITY.exists():
            raise FileExistsError("broad v1 freeze/results already exist")
        canonical, words, mapping, _, _, _ = load()
        feasible = row_feasibility(canonical, words, mapping)
        FEASIBILITY.write_text(json.dumps(feasible, ensure_ascii=False, separators=(",", ":"))+"\n")
        PLAN.write_text(json.dumps(plan(), ensure_ascii=False, indent=2)+"\n")
        print("FROZEN broad phrase plan/candidate/evaluation; no new phrase scores calculated")
        print(json.dumps(feasible["summary"], indent=2))
        return
    saved = json.loads(OUTPUT.read_text()) if args.verify else None
    if args.build and OUTPUT.exists():
        raise FileExistsError("broad v1 results already exist")
    report = analyze(saved, args.full)
    if args.verify:
        if report != saved:
            raise AssertionError("broad word/phrase report differs")
        print("PASS broad occurrence/phrase geometry, coherence-preserving spacing accounting"+(" and full replay" if args.full else ""))
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":"))+"\n")
    for n, result in report["results"].items():
        print("length", n, "mapped", result["located_population"], "full aligned", result["observed"]["full_mapped"],
              "spacing population", result["feasible_population"], "spacing observed", result["observed"]["feasible_rows"],
              "inference", json.dumps(result["inference"]["without_allah_forms"]), flush=True)


if __name__ == "__main__":
    main()
