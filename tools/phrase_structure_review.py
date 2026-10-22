"""Independent row-prefix and pair-certificate audit of phrase-aware controls."""
import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
from pathlib import Path

import numpy as np

import broad_phrase_alignment as bp
import phrase_structure_controls as pc
import same_word_alignment as sw

OUTPUT = sw.DATA / "research_phrase_structure_review_v1.json"


def pair_envelopes(reference, pairs, length):
    """Sufficient guaranteed pairs and an outer bound on feasible pairs.

    Interval overlap can overestimate joint feasibility when different word
    positions are correlated. It is used only as an upper certificate.
    """
    guaranteed, not_ruled_out = [], []
    for a, b in pairs:
        farthest, nearest = [], []
        for j in range(length):
            alo, ahi = reference[a+j]
            blo, bhi = reference[b+j]
            farthest.append(max(abs(alo-bhi), abs(ahi-blo)))
            nearest.append(max(0, alo-bhi, blo-ahi))
        if max(farthest) <= 30:
            guaranteed.append([a, b])
        if max(nearest) <= 30:
            not_ruled_out.append([a, b])
    return guaranteed, not_ruled_out


def reference_ranges(words, feasible, groups):
    """Reference relative to each measured center, not packer's base formula."""
    result = {}
    cursor = 0
    for page in feasible["pages"]:
        for row in page["rows"]:
            if not row["eligible"]:
                continue
            ids = row["word_indices"]
            gaps = row["gaps_rtl"]
            row_groups = groups[cursor:cursor+len(gaps)]
            by_group = defaultdict(list)
            for group, gap in zip(row_groups, gaps):
                by_group[group].append(gap)
            for j, index in enumerate(ids):
                counts = Counter(row_groups[:j])
                minimum = sum(sum(sorted(by_group[g])[:k]) for g, k in counts.items())
                maximum = sum(sum(sorted(by_group[g], reverse=True)[:k]) for g, k in counts.items())
                measured = words[index]["x2"]
                original_prefix = sum(gaps[:j])
                result[words[index]["t"]] = (measured+2*(original_prefix-maximum), measured+2*(original_prefix-minimum))
            cursor += len(gaps)
    if cursor != len(groups):
        raise AssertionError("reference gap-group inventory differs")
    return result


def structural_reference(canonical, words, feasible, groups, model):
    """Check groups against verse boundaries and greedy canonical blocks."""
    # Count directly on literal canonical windows; independent of bp.windows.
    vocabulary = {n: Counter() for n in range(2, 7)}
    for t in canonical:
        for n in range(2, 7):
            selected = [canonical.get(t+j) for j in range(n)]
            if all(w is not None and w["verse"] == canonical[t]["verse"] for w in selected):
                vocabulary[n][tuple(w["word"] for w in selected)] += 1
    cursor = 0
    context_by_group = defaultdict(set)
    expected_fixed = set()
    for page in feasible["pages"]:
        for row in page["rows"]:
            if not row["eligible"]:
                continue
            ids = row["word_indices"]
            row_groups = groups[cursor:cursor+len(ids)-1]
            position = 0
            protected = set()
            while position < len(ids):
                largest = 1
                for n in range(2, 7):
                    selected = ids[position:position+n]
                    if len(selected) != n:
                        continue
                    ts = [words[i]["t"] for i in selected]
                    if len({canonical[t]["verse"] for t in ts}) != 1:
                        continue
                    identity = tuple(words[i]["word"] for i in selected)
                    if vocabulary[n][identity] >= 2:
                        largest = n
                protected.update(range(position, position+largest-1))
                position += largest
            for j, group in enumerate(row_groups):
                va = canonical[words[ids[j]]["t"]]["verse"]
                vb = canonical[words[ids[j+1]]["t"]]["verse"]
                fixed = va != vb or (model == "repeated_phrase_blocks" and j in protected)
                if fixed:
                    expected_fixed.add(cursor+j)
                    context = (page["page"], row["row"], "fixed", j)
                else:
                    context = (page["page"], row["row"], "variable", va)
                context_by_group[group].add(context)
            cursor += len(ids)-1
    if any(len(contexts) != 1 for contexts in context_by_group.values()):
        raise AssertionError("groups mix fixed gaps, rows, verses or phrase-block contexts")
    # Context-to-group also must be unique, otherwise unintended singleton
    # splitting would condition away more freedom than the declared model.
    group_by_context = defaultdict(set)
    for group, contexts in context_by_group.items():
        group_by_context[next(iter(contexts))].add(group)
    if any(len(groups) != 1 for groups in group_by_context.values()):
        raise AssertionError("grouping overconditions a declared variable context")
    return dict(structurally_fixed_gap_indices=sorted(expected_fixed), groups=len(context_by_group))


def analyze():
    report = json.loads(pc.OUTPUT.read_text())
    if json.loads(pc.PLAN.read_text()) != pc.plan() or report["plan_sha256"] != sw.digest(pc.PLAN):
        raise AssertionError("phrase structure source/plan changed")
    canonical, words, _, _, _, _ = bp.load()
    original = json.loads(bp.OUTPUT.read_text())
    feasible = json.loads(bp.FEASIBILITY.read_text())
    lookup = {w["t"]: w for w in words}
    models = {}
    for model, result in report["models"].items():
        groups = result["group_ids"]
        structure = structural_reference(canonical, words, feasible, groups, model)
        reference = reference_ranges(words, feasible, groups)
        stored = {t: (a, b) for t, a, b in result["freedom"]["center_envelopes"]}
        if reference != stored:
            raise AssertionError("independent measured-center prefix extrema differ")
        lengths = {}
        for n, outcomes in result["results"].items():
            length = int(n)
            baseline = original["results"][n]
            occurrence_type = {r[0]: r[1] for r in baseline["located_occurrences"]}
            grouped = defaultdict(list)
            for start, label, page, row, eligible, _ in baseline["located_occurrences"]:
                if eligible:
                    grouped[page, label].append((start, row))
            candidates = [[a, b] for values in grouped.values() for (a, ar), (b, br) in combinations(values, 2) if ar != br]
            expected_pairs, not_ruled_out_pairs = pair_envelopes(reference, candidates, length)
            guaranteed_starts = set()
            for a, b in expected_pairs:
                guaranteed_starts.update((a, b))
            if sorted(expected_pairs) != sorted(outcomes["guaranteed_pairs"]):
                raise AssertionError("independent guaranteed-pair certificate differs")
            guaranteed_types = Counter(occurrence_type[t] for t in guaranteed_starts)
            if any(outcomes["guaranteed_type_counts"][i] != guaranteed_types[i] for i in range(len(baseline["per_type"]))):
                raise AssertionError("guaranteed endpoint type counts differ")
            guaranteed_counts = dict(all=len(guaranteed_starts), without_allah_forms=sum(baseline["per_type"][occurrence_type[t]]["without_allah_forms"] for t in guaranteed_starts))
            if guaranteed_counts != outcomes["guaranteed_aligned"]:
                raise AssertionError("guaranteed endpoint group totals differ")
            upper_starts = {t for pair in not_ruled_out_pairs for t in pair}
            upper_counts = dict(all=len(upper_starts), without_allah_forms=sum(
                baseline["per_type"][occurrence_type[t]]["without_allah_forms"] for t in upper_starts))
            invariant = {key: guaranteed_counts[key] == upper_counts[key] for key in upper_counts}
            # Original locations cannot leave the exact feasible envelopes.
            if any(not lo <= lookup[t]["x2"] <= hi for t, (lo, hi) in reference.items()):
                raise AssertionError("observed token outside independent feasible envelope")
            null_sums = result["simulation"]["per_type_aligned_sums"][n]
            types = []
            for i, source in enumerate(baseline["per_type"]):
                types.append(dict(words=source["words"], eligible=source["eligible"], without_allah_forms=source["without_allah_forms"],
                    observed=source["aligned"]["feasible_rows"], guaranteed=guaranteed_types[i], mean=null_sums[i]/pc.REPS))
            candidates = [r for r in types if r["without_allah_forms"] and r["eligible"] >= 10]
            positives = sorted(candidates, key=lambda r: (-(r["observed"]-r["mean"]), r["words"]))[:10]
            negatives = sorted(candidates, key=lambda r: (r["observed"]-r["mean"], r["words"]))[:10]
            lengths[n] = dict(observed=outcomes["observed"], guaranteed=guaranteed_counts,
                envelope_upper_bound=upper_counts, exact_score_invariance_certified=invariant,
                movable=outcomes["movable_occurrences"], inference=outcomes["inference"]["without_allah_forms"],
                largest_positive_residual_types=positives, largest_negative_residual_types=negatives)
        models[model] = dict(structural_audit=structure, independent_extrema_checked=len(reference), lengths=lengths,
            freedom={k: v for k, v in result["freedom"].items() if k not in ("center_envelopes", "center_envelope_schema")})
    return dict(version="phrase-structure-independent-review-v1", models=models,
        inputs={p.name: sw.digest(p) for p in (pc.OUTPUT, pc.PLAN, bp.OUTPUT, bp.FEASIBILITY, Path(__file__))},
        caveat="Independent canonical-window/structural grouping and measured-center prefix extrema; every guaranteed and interval-not-ruled-out pair is checked. Guaranteed endpoints give lower bounds, interval envelopes give upper bounds (not exact feasible sets). Equal bounds certify exact score invariance for every allowed layout. This post-score envelope diagnostic is not a fresh primary test. Residual type rankings are exposed descriptions, not individual significance tests or origin odds.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = analyze()
    if args.verify:
        if result != json.loads(OUTPUT.read_text()):
            raise AssertionError("independent phrase structure review differs")
        print("PASS independent verse/block grouping, all attainable center extrema and guaranteed pairs/endpoints")
    else:
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"))+"\n")
    for model, r in result["models"].items():
        print(model, "freedom", r["freedom"])
        for n, outcome in r["lengths"].items():
            print("length", n, "observed", outcome["observed"]["without_allah_forms"], "guaranteed", outcome["guaranteed"]["without_allah_forms"],
                  "upper", outcome["envelope_upper_bound"]["without_allah_forms"],
                  "invariant", outcome["exact_score_invariance_certified"]["without_allah_forms"],
                  "mean", outcome["inference"]["null_mean"], "exceedances", outcome["inference"]["exceedances"])


if __name__ == "__main__":
    main()
