"""Verse-aware and repeated-phrase-block spacing controls on frozen word sites.

These deliberately condition on more of the existing print's geometry. They
measure the residual association and remaining freedom, not historical causes.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

import broad_phrase_alignment as bp
import same_word_alignment as sw
from audit_stats import tail_summary

PLAN = sw.DATA / "research_phrase_structure_plan_v1.json"
OUTPUT = sw.DATA / "research_phrase_structure_controls_v1.json"
MODELS = ("verse_internal", "repeated_phrase_blocks")
REPS = 5000
SEED = 20261022


def repeated_vocabulary(canonical):
    return {n: {p for p, count in Counter(p for _, p in bp.windows(canonical, n)).items() if count >= 2}
            for n in range(2, 7)}


def blocks(identities, vocabulary):
    """Left-to-right in canonical (RTL) order, longest repeated 2..6 first."""
    result = []
    i = 0
    while i < len(identities):
        size = next((n for n in range(min(6, len(identities)-i), 1, -1)
                     if tuple(identities[i:i+n]) in vocabulary.get(n, set())), 1)
        result.append([i, i+size])
        i += size
    return result


def grouping(canonical, words, feasibility, vocabulary, model):
    if model not in MODELS:
        raise ValueError("unknown structure model")
    keys, details = [], []
    gap_offset = 0
    for page in feasibility["pages"]:
        for row in page["rows"]:
            if not row["eligible"]:
                continue
            ids = row["word_indices"]
            protected = set()
            fragment = []
            fragments = []
            for j, i in enumerate(ids):
                verse = canonical[words[i]["t"]]["verse"]
                if fragment and verse != canonical[words[ids[fragment[-1]]]["t"]]["verse"]:
                    fragments.append(fragment)
                    fragment = []
                fragment.append(j)
            if fragment:
                fragments.append(fragment)
            block_details = []
            for number, positions in enumerate(fragments):
                identity = [words[ids[j]]["word"] for j in positions]
                chosen = blocks(identity, vocabulary)
                block_details.append(dict(verse=canonical[words[ids[positions[0]]]["t"]]["verse"],
                    blocks=[[words[ids[positions[a]]]["t"], words[ids[positions[b-1]]]["t"]+1] for a, b in chosen]))
                for a, b in chosen:
                    protected.update(positions[a:b-1])
            for j in range(len(ids)-1):
                va = canonical[words[ids[j]]["t"]]["verse"]
                vb = canonical[words[ids[j+1]]["t"]]["verse"]
                fixed = va != vb or (model == "repeated_phrase_blocks" and j in protected)
                keys.append((page["page"], row["row"], va, j if fixed else -1))
            details.append(dict(page=page["page"], row=row["row"],
                verse_boundary_gap_indices=[gap_offset+j for j in range(len(ids)-1)
                    if canonical[words[ids[j]]["t"]]["verse"] != canonical[words[ids[j+1]]["t"]]["verse"]],
                repeated_block_internal_gap_indices=[gap_offset+j for j in sorted(protected)], fragments=block_details))
            gap_offset += len(ids)-1
    lookup = {key: i for i, key in enumerate(sorted(set(keys)))}
    return np.array([lookup[k] for k in keys], dtype=np.int32), details


def permute_gaps(gaps, groups, rng):
    order = np.lexsort((rng.random(len(gaps)), groups))
    base = np.argsort(groups, kind="stable")
    result = np.empty_like(gaps)
    result[order] = gaps[base]
    return result


def equal_gaps(gaps, groups):
    """Integer equalization in each verse-internal group; singleton gaps fixed."""
    result = gaps.copy()
    order = np.argsort(groups, kind="stable")
    boundaries = np.r_[0, np.flatnonzero(np.diff(groups[order]))+1, len(order)]
    for start, end in zip(boundaries, boundaries[1:]):
        ids = order[start:end]
        if not len(ids):
            continue
        q, r = divmod(int(gaps[ids].sum()), len(ids))
        result[ids] = q
        result[ids[:r]] += 1
    return result


def center_ranges(words, packing, groups):
    """Exact attainable one-word extrema under within-stratum gap permutations."""
    values = defaultdict(list)
    for g, v in zip(groups.tolist(), packing["gaps"].tolist()):
        values[g].append(v)
    lower_prefix, upper_prefix = {}, {}
    for g, vs in values.items():
        ordered = sorted(vs)
        lower_prefix[g] = [0]+np.cumsum(ordered).tolist()
        upper_prefix[g] = [0]+np.cumsum(ordered[::-1]).tolist()
    # Every group is contained in one row. At a word, the number of preceding
    # positions from each stratum fixes how many of its gap values are summed.
    # Complete groups' sums are constants; partial groups attain the smallest
    # or largest prefix sums independently. No continuous-range assumption.
    low, high = [], []
    group_counts = Counter()
    previous_row = None
    for word_index, base, prior in zip(packing["ids"], packing["base"], packing["prior"]):
        word = words[int(word_index)]
        row_key = (word["page"], word["row"])
        if row_key != previous_row:
            group_counts.clear()
            previous_row = row_key
        if prior >= 0:
            group_counts[int(groups[int(prior)])] += 1
        minimum_gap_sum = sum(lower_prefix[g][k] for g, k in group_counts.items())
        maximum_gap_sum = sum(upper_prefix[g][k] for g, k in group_counts.items())
        low.append(int(base)-2*maximum_gap_sum)
        high.append(int(base)-2*minimum_gap_sum)
    return np.array(low, dtype=np.int64), np.array(high, dtype=np.int64)


def guaranteed(p, lower, upper):
    left, right = p["sim_left"], p["sim_right"]
    a, b = p["indices"][left], p["indices"][right]
    distances = np.maximum(np.abs(lower[a]-upper[b]), np.abs(upper[a]-lower[b]))
    match = np.all(distances <= 30, axis=1)
    flags = np.zeros(len(p["indices"]), dtype=bool)
    flags[left[match]] = True
    flags[right[match]] = True
    return flags, match


def freedom(gaps, groups, packing, low, high, words):
    sizes = Counter(groups.tolist())
    values = defaultdict(set)
    for g, v in zip(groups.tolist(), gaps.tolist()):
        values[g].add(v)
    movable_gaps = sum(sizes[g] for g in sizes if len(values[g]) > 1)
    return dict(gaps=len(gaps), strata=len(sizes), multiple_value_strata=sum(len(v)>1 for v in values.values()),
        permutable_gap_sites=movable_gaps, value_fixed_gap_sites=len(gaps)-movable_gaps,
        eligible_words=len(low), movable_word_centers=int(np.count_nonzero(low != high)),
        center_envelope_schema=["token_id", "minimum_twice_center_x", "maximum_twice_center_x"],
        center_envelopes=[[words[int(i)]["t"], int(a), int(b)] for i, a, b in zip(packing["ids"], low, high)])


def plan():
    files = (Path(__file__), sw.ROOT / "tools/test_phrase_structure_controls.py", bp.OUTPUT, bp.FEASIBILITY,
        bp.PLAN, sw.ROOT / "tools/broad_phrase_alignment.py", sw.ROOT / "tools/same_word_alignment.py",
        sw.ROOT / "tools/map_tokens.py", sw.ROOT / "tools/ocr_corpus_map.py",
        sw.ROOT / "tools/audit_stats.py", sw.ROOT / "tools/semantic_validation.py", sw.ROOT / "tools/divine_census.py",
        sw.wm.OUTPUT, sw.ws.OUTPUT, sw.cm.SOURCE, sw.mt.TOKENS_F)
    return dict(version="phrase-structure-control-plan-v1", date="2026-10-19",
        question="Does the broader word/phrase excess remain when verse-boundary gaps and repeated-phrase internal geometry are preserved? Quantify remaining randomization and guaranteed alignment.",
        inputs={p.name: sw.digest(p) for p in files}, models=list(MODELS),
        population="Exactly the prior broad study's complete eligible rows and occurrences. Same actual text/order, widths, row/page membership, outer row edges and strict corresponding-word <=15px statistic. No color selection.",
        verse_internal="Fix all gaps between different canonical verses. Uniformly permute only internal gaps of each single verse fragment within its row, preserving each fragment's total internal spacing.",
        repeated_phrase_blocks="Within each verse fragment, partition canonical text greedily from the first RTL word into the longest repeated 2..6-word block available (otherwise a singleton). Repetition vocabulary is canonical within-verse counts >=2 anywhere, with no geometric score. Fix gaps inside these nonoverlapping blocks and between verses. Uniformly permute only inter-block gaps within the same row/verse fragment. This inherits observed block geometry; it does not generate it independently.",
        deterministic="Equalize each verse-internal gap group to integer floor/ceiling of its mean; allocate remainder to earliest RTL gaps. Preserve verse-boundary gaps. Descriptive outcome only; no probability assigned.",
        primary="Six strict non-Allah-form length metrics 1..6 under each of two models, twelve comparisons total. Retain all/inclusive outcomes and complete per-type/page accounting. Adjust plus-one Monte Carlo summaries by Bonferroni factor 12; do not multiply tails.",
        simulation=dict(replicates=REPS, seed=SEED, generator="numpy.default_rng/PCG64", model_seed_offset="zero-based model index"),
        diagnostics="Exact attainable center extrema from smallest/largest stratum prefix sums; guaranteed pair certificates when every possible corresponding center separation <=15px. Report all fixed/movable gap and word counts, guaranteed endpoints, full model outcomes and retained non-excesses.",
        limits="Exposed development controls; retained widths, line breaks, verse-fragment anchors and phrase shapes may contain design. Conditioning can leave very little freedom. These are interval renderers, not historical calligraphy, independent copies or origin likelihoods.",
        completion="Verify code on exhaustive tiny group permutations, reproduce original packing and old observed counts, fully replay both simulation sets, audit guarantee/freedom arithmetic, and report the causal limitations and separately sourced historical-copy leads.")


def run_simulation(words, packing, prepared, groups, model_index):
    rng = np.random.default_rng(SEED+model_index)
    samples = {str(n): {k: [] for k in ("all", "without_allah_forms")} for n in bp.LENGTHS}
    sums = {str(n): np.zeros(len(p["inv"]["vocabulary"]), dtype=np.int64) for n, p in prepared.items()}
    pages = {str(n): np.zeros(605, dtype=np.int64) for n in bp.LENGTHS}
    positions = np.array([w["x2"] for w in words], dtype=np.int64)
    sha = hashlib.sha256()
    for trial in range(REPS):
        gaps = permute_gaps(packing["gaps"], groups, rng)
        positions[packing["ids"]] = bp.packed_centers(packing, gaps)
        sha.update(positions[packing["ids"]].astype("<i8", copy=False).tobytes())
        for n, p in prepared.items():
            marked, _ = bp.aligned(positions, p["indices"], p["sim_left"], p["sim_right"])
            counts = bp.count_metrics(marked, p["labels"], p["inv"]["non_allah"])
            for key, value in counts.items():
                samples[str(n)][key].append(value)
            sums[str(n)] += np.bincount(p["labels"][marked], minlength=len(sums[str(n)]))
            pages[str(n)] += np.bincount(p["pages"][marked], minlength=605)
        if (trial+1)%500 == 0:
            print(MODELS[model_index], "trial", trial+1, "/", REPS, flush=True)
    return dict(samples=samples, per_type_aligned_sums={n: v.tolist() for n, v in sums.items()},
        per_page_aligned_sums={n: v.tolist() for n, v in pages.items()}, generated_centers_sha256=sha.hexdigest())


def analyze(saved=None, full=False):
    if json.loads(PLAN.read_text()) != plan():
        raise AssertionError("phrase-structure plan/candidate/inputs differ after freeze")
    canonical, words, mapping, original, _, _ = bp.load()
    old = json.loads(bp.OUTPUT.read_text())
    feasible = json.loads(bp.FEASIBILITY.read_text())
    if bp.row_feasibility(canonical, words, mapping) != feasible:
        raise AssertionError("eligible row inventory changed")
    packing = bp.packer(words, feasible)
    positions = np.array([w["x2"] for w in words], dtype=np.int64)
    if not np.array_equal(bp.packed_centers(packing, packing["gaps"]), positions[packing["ids"]]):
        raise AssertionError("packing did not reconstruct original coordinates")
    eligible = set(packing["ids"].tolist())
    surface = {r[0] for r in original["views"]["exact_surface_v5"]["located_inventory"]}
    prepared = {n: bp.prepare(canonical, words, n, eligible, surface) for n in bp.LENGTHS}
    vocabulary = repeated_vocabulary(canonical)
    models = {}
    for model_index, model in enumerate(MODELS):
        groups, rows = grouping(canonical, words, feasible, vocabulary, model)
        if len(groups) != len(packing["gaps"]):
            raise AssertionError("gap grouping omitted positions")
        low, high = center_ranges(words, packing, groups)
        lower, upper = positions.copy(), positions.copy()
        lower[packing["ids"]], upper[packing["ids"]] = low, high
        if np.any(positions[packing["ids"]] < low) or np.any(positions[packing["ids"]] > high):
            raise AssertionError("original center outside attainable range")
        simulation = run_simulation(words, packing, prepared, groups, model_index) if saved is None or full else saved["models"][model]["simulation"]
        results = {}
        for n, p in prepared.items():
            observed_flags, _ = bp.aligned(positions, p["indices"], p["sim_left"], p["sim_right"])
            counts = bp.count_metrics(observed_flags, p["labels"], p["inv"]["non_allah"])
            if counts != old["results"][str(n)]["observed"]["feasible_rows"]:
                raise AssertionError("old eligible-row score changed")
            gf, gp = guaranteed(p, lower, upper)
            if np.any(gf & ~observed_flags):
                raise AssertionError("guaranteed pair not observed")
            guarantee_counts = bp.count_metrics(gf, p["labels"], p["inv"]["non_allah"])
            movable = np.any(lower[p["indices"]] != upper[p["indices"]], axis=1) & p["keep"]
            infer = {}
            for key in ("all", "without_allah_forms"):
                samples = simulation["samples"][str(n)][key]
                population = old["results"][str(n)]["feasible_population"][key]
                if len(samples) != REPS or any(not isinstance(v, int) or not guarantee_counts[key] <= v <= population for v in samples):
                    raise AssertionError("invalid structure-control samples")
                infer[key] = tail_summary(counts[key], samples)
            infer["without_allah_forms"]["bonferroni_twelve_plus_one_mc"] = min(1.0, 12*infer["without_allah_forms"]["plus_one_mc"])
            type_sums = simulation["per_type_aligned_sums"][str(n)]
            if sum(type_sums) != sum(simulation["samples"][str(n)]["all"]) or sum(type_sums) != sum(simulation["per_page_aligned_sums"][str(n)]):
                raise AssertionError("simulation type/page accounting differs")
            if sum(v for v, keep in zip(type_sums, p["inv"]["non_allah"]) if keep) != sum(simulation["samples"][str(n)]["without_allah_forms"]):
                raise AssertionError("non-Allah-form type accounting differs")
            occurrences = p["inv"]["occurrences"]
            results[str(n)] = dict(observed=counts, guaranteed_aligned=guarantee_counts,
                movable_occurrences=bp.count_metrics(movable, p["labels"], p["inv"]["non_allah"]),
                guaranteed_pairs=[[occurrences[int(a)]["start"], occurrences[int(b)]["start"]]
                    for a, b in zip(p["sim_left"][gp], p["sim_right"][gp])],
                observed_type_counts=np.bincount(p["labels"][observed_flags], minlength=len(type_sums)).tolist(),
                guaranteed_type_counts=np.bincount(p["labels"][gf], minlength=len(type_sums)).tolist(), inference=infer)
        models[model] = dict(group_ids=groups.tolist(), rows=rows,
            freedom=freedom(packing["gaps"], groups, packing, low, high, words), results=results, simulation=simulation)
    # This comparator fixes verse-boundary gaps but equalizes internal gaps.
    groups = np.array(models["verse_internal"]["group_ids"], dtype=np.int32)
    deterministic = positions.copy()
    deterministic[packing["ids"]] = bp.packed_centers(packing, equal_gaps(packing["gaps"], groups))
    equal = {}
    for n, p in prepared.items():
        flags, _ = bp.aligned(deterministic, p["indices"], p["sim_left"], p["sim_right"])
        equal[str(n)] = dict(counts=bp.count_metrics(flags, p["labels"], p["inv"]["non_allah"]),
            aligned_start_ids=[o["start"] for o, yes in zip(p["inv"]["occurrences"], flags) if yes])
    return dict(version="phrase-structure-controls-v1", plan_sha256=sw.digest(PLAN),
        feasibility_summary=feasible["summary"], models=models, equalized_verse_internal=equal,
        caveat="Two stronger conditional spacing controls and exact geometric persistence certificates. Actual observed word widths, verse-fragment anchors and (in one model) internal repeated-phrase geometry are inherited. Remaining association is not an origin likelihood; disappearance can reflect conditioning away most freedom, not a sufficient historical explanation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        if PLAN.exists() or OUTPUT.exists():
            raise FileExistsError("phrase structure v1 already frozen")
        PLAN.write_text(json.dumps(plan(), ensure_ascii=False, indent=2)+"\n")
        print("FROZEN verse/phrase-aware candidate and evaluation; no target scores generated")
        return
    if args.build and OUTPUT.exists():
        raise FileExistsError("phrase structure v1 results exist")
    saved = json.loads(OUTPUT.read_text()) if args.verify else None
    report = analyze(saved, args.full)
    if args.verify:
        if report != saved:
            raise AssertionError("phrase structure report differs")
        print("PASS verse/phrase-aware groups, exact ranges/guarantees, observed counts and "+("full replay" if args.full else "saved simulation accounting"))
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":"))+"\n")
    for model, result in report["models"].items():
        print("MODEL", model, {k: v for k, v in result["freedom"].items() if k not in ("center_envelopes", "center_envelope_schema")}, flush=True)
        for n, r in result["results"].items():
            print("length", n, "observed", r["observed"], "guaranteed", r["guaranteed_aligned"], "inference", json.dumps(r["inference"]["without_allah_forms"]), flush=True)
    print("equalized verse-internal counts", {n: r["counts"] for n, r in report["equalized_verse_internal"].items()}, flush=True)


if __name__ == "__main__":
    main()
