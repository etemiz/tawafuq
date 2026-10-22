"""Predeclared six-page interval-layout spacing pilot; no score optimization.

Each eligible row keeps exact token order, original detector widths and outer
extent. Equal gaps and permutations of the empirical gap multiset are toy
comparators, not a historical Arabic justification or glyph-rendering model.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import text_layout_pilot as fp
import same_word_alignment as sw
from audit_stats import tail_summary

PLAN = sw.DATA / "research_text_layout_plan_v1.json"
OUTPUT = sw.DATA / "research_text_layout_comparison_v1.json"
REPS = 5000
SEED = 20261020
METRICS = ("standalone_allah", "all_identical_words", "allah_name_family")


def plan():
    paths = (fp.FEASIBILITY, Path(__file__), Path(fp.__file__), Path(sw.__file__),
             sw.wm.OUTPUT, sw.ws.OUTPUT, sw.cm.SOURCE, sw.mt.TOKENS_F,
             sw.ROOT / "tools/audit_stats.py", sw.ROOT / "tools/test_text_layout.py")
    return dict(version="text-order-spacing-pilot-plan-v1", date="2026-10-19",
        pages=list(fp.PAGES), development_only=True,
        inputs={p.name: sw.digest(p) for p in paths},
        feasibility="Use exactly eligible=true rows in the saved feasibility report. Every excluded row and its words stays in the coverage ledger, never counted as generated.",
        fixed=["canonical token identity and order", "page and seeded row membership", "original horizontal detector/support widths", "outermost word-box edges per eligible row"],
        generators=dict(equal_gaps="Set all n-1 gaps to their exact rational average; no score is consulted.",
            empirical_gap_permutation="Independently uniformly permute the observed n-1 nonnegative gaps per eligible row; keep their multiset and sum. Duplicate gap values give repeated permutations with equal multiset probability."),
        parameters=dict(replicates=REPS, seed=SEED, rng="numpy.default_rng/PCG64", tolerance_pixels=15),
        evaluation=dict(primary=list(METRICS[:2]), secondary=[METRICS[2]],
            population="Eligible rows only, partners restricted to that same population. Report actual excluded-row name counts separately; never impute a full-page comparison.",
            statistic="Count each endpoint once with an identical-word (or declared family) partner on another row of its page, horizontal center distance <=15px. Original support centers; equal-gap centers exact rational, random centers exact half-pixel.",
            outputs="Observed/equal-gap endpoints and pairs; all per-page and pooled random scores; first random trial centers per page, selected before scoring; finite-MC summaries; exact possible center ranges; gap-arrangement counts and exclusions. Report both successful and unsuccessful comparisons.",
            selection="No target-score optimization, parameter search, favorable page removal, or additional tolerance search."),
        interpretation="Gap exchangeability is a declared toy assumption, not independently established historical evidence. Gaps may contain verse/stop markers or diacritics; this interval renderer does not reconstruct their ink, kashida, glyph joins or vertical placement. Frozen widths and line breaks may already encode design. Success establishes interval feasibility only; failure excludes only these spacing rules, not human production. Neither outcome supplies origin likelihoods.",
        stop_rule="Complete this six-page feasibility and spacing report, verify it, and decide whether a more realistic independently validated comparator merits held-out evaluation. No automatic corpus expansion.")


def place(row, gaps):
    """Exact twice-centers, right to left; supports rational equal spacing."""
    words = row["words"]
    if len(gaps) != len(words)-1 or any(g < 0 for g in gaps):
        raise ValueError("nonnegative n-1 gaps required")
    if sum(gaps) != sum(row["gaps_rtl"]):
        raise ValueError("gap sum must preserve line extent")
    edge = row["extent"][1]
    centers = []
    for i, word in enumerate(words):
        centers.append(2*edge-word["width"])
        edge -= word["width"]
        if i < len(gaps):
            edge -= gaps[i]
    if edge != row["extent"][0]:
        raise AssertionError("interval packing did not reach fixed left extent")
    return centers


def candidate_pairs(words):
    exact, family = [], []
    for i, a in enumerate(words):
        for j in range(i+1, len(words)):
            b = words[j]
            if a["page"] != b["page"] or a["row"] == b["row"]:
                continue
            if a["word"] == b["word"]:
                exact.append((i, j))
            if sw.is_name(sw.spelling(a["word"])) and sw.is_name(sw.spelling(b["word"])):
                family.append((i, j))
    return exact, family


def score(centers, words, pairs):
    """Rational-safe scorer for saved endpoints and the deterministic layout."""
    exact_pairs, family_pairs = pairs
    exact = [(i, j) for i, j in exact_pairs if abs(centers[i]-centers[j]) <= 30]
    fam = [(i, j) for i, j in family_pairs if abs(centers[i]-centers[j]) <= 30]
    ends = set(i for pair in exact for i in pair)
    fam_ends = set(i for pair in fam for i in pair)
    selected = dict(standalone_allah=sorted(i for i in ends if words[i]["word"] == "الله"),
                    all_identical_words=sorted(ends), allah_name_family=sorted(fam_ends))
    return dict(counts={k: len(v) for k, v in selected.items()},
                endpoint_token_ids={k: [words[i]["t"] for i in v] for k, v in selected.items()},
                same_word_pairs=[[words[i]["t"], words[j]["t"]] for i, j in exact],
                family_pairs=[[words[i]["t"], words[j]["t"]] for i, j in fam])


def freedom(row):
    gaps = row["gaps_rtl"]
    ascending = sorted(gaps)
    descending = ascending[::-1]
    edge = row["extent"][1]
    result = []
    for i, w in enumerate(row["words"]):
        base = 2*edge-w["width"]
        lo = base-2*sum(descending[:i])
        hi = base-2*sum(ascending[:i])
        result.append(dict(t=w["t"], word=w["word"], original_x2=w["x2"],
            minimum_x2=lo, maximum_x2=hi, movable=lo != hi,
            maximum_displacement_pixels=max(abs(lo-w["x2"]), abs(hi-w["x2"]))/2))
        edge -= w["width"]
    # Divide by the complete multinomial denominator with integer arithmetic.
    arrangements = math.factorial(len(gaps)) // math.prod(math.factorial(k) for k in Counter(gaps).values())
    return dict(distinct_gap_arrangements=arrangements, centers=result)


def analyze():
    frozen = json.loads(PLAN.read_text())
    if frozen != plan():
        raise AssertionError("candidate, inputs or evaluation changed after plan freeze")
    feasibility = json.loads(fp.FEASIBILITY.read_text())
    if feasibility != fp.feasibility():
        raise AssertionError("feasibility does not reproduce")
    rng = np.random.default_rng(SEED)
    pages = []
    samples = {m: [0]*REPS for m in METRICS}
    layout_hash = hashlib.sha256()
    for page in feasibility["pages"]:
        eligible = [r for r in page["rows"] if r["eligible"]]
        words = [w for r in eligible for w in r["words"]]
        pairs = candidate_pairs(words)
        original = [w["x2"] for w in words]
        equal = []
        freedoms = []
        for row in eligible:
            if place(row, row["gaps_rtl"]) != [w["x2"] for w in row["words"]]:
                raise AssertionError("original gap list did not reconstruct input")
            equal.extend(place(row, [Fraction(sum(row["gaps_rtl"]), len(row["gaps_rtl"]))]*len(row["gaps_rtl"])))
            freedoms.append(dict(row=row["row"], **freedom(row)))
        observed = score(original, words, pairs)
        equal_score = score(equal, words, pairs)
        page_samples = {m: [] for m in METRICS}
        first_trial = None
        # Integer half-pixel coordinates throughout the randomized layouts.
        for trial in range(REPS):
            centers = [x for row in eligible for x in place(row, rng.permutation(row["gaps_rtl"]).tolist())]
            layout_hash.update(np.asarray(centers, dtype="<i8").tobytes())
            counts = score(centers, words, pairs)["counts"]
            if trial == 0:
                first_trial = dict(centers=[[w["t"], x] for w, x in zip(words, centers)], counts=counts)
            for metric in METRICS:
                page_samples[metric].append(counts[metric])
                samples[metric][trial] += counts[metric]
        available = dict(standalone_allah=sum(w["word"] == "الله" for w in words),
                         all_identical_words=len(words), allah_name_family=sum(sw.is_name(w["word"]) for w in words))
        excluded_words = [w for r in page["rows"] if not r["eligible"] for w in r["words"]]
        pages.append(dict(page=page["page"], eligible_rows=[r["row"] for r in eligible],
            excluded_rows=[dict(row=r["row"], reasons=r["exclusion_reasons"], token_ids=r["token_ids"]) for r in page["rows"] if not r["eligible"]],
            population=available, excluded_located_words=len(excluded_words),
            excluded_standalone_allah=sum(w["word"] == "الله" for w in excluded_words),
            observed=observed, equal_gaps=equal_score,
            first_random_trial=first_trial,
            equal_gap_centers=[[w["t"], str(x)] for w, x in zip(words, equal)],
            freedom=freedoms, samples=page_samples,
            comparison={m: tail_summary(observed["counts"][m], page_samples[m]) for m in METRICS}))
    totals = {m: sum(p["observed"]["counts"][m] for p in pages) for m in METRICS}
    equal_totals = {m: sum(p["equal_gaps"]["counts"][m] for p in pages) for m in METRICS}
    population = {m: sum(p["population"][m] for p in pages) for m in METRICS}
    return dict(version="text-order-spacing-pilot-v1", plan_sha256=sw.digest(PLAN), pages=pages,
        summary=dict(population=population, observed=totals, equal_gaps=equal_totals,
            comparison={m: tail_summary(totals[m], samples[m]) for m in METRICS}),
        pooled_samples=samples, generated_twice_centers_sha256=layout_hash.hexdigest(),
        caveat=frozen["interpretation"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        if PLAN.exists() or OUTPUT.exists():
            raise FileExistsError("v1 plan/results already exist; create a new version rather than overwrite a freeze")
        PLAN.write_text(json.dumps(plan(), ensure_ascii=False, indent=2)+"\n")
        print("FROZEN plan, candidate and evaluation; no target scores generated")
        return
    report = analyze()
    if args.verify:
        if json.loads(OUTPUT.read_text()) != report:
            raise AssertionError("text/order spacing pilot differs")
        print("PASS complete deterministic spacing replay, all layouts and scores")
    else:
        if OUTPUT.exists():
            raise FileExistsError("v1 comparison already exists")
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":"))+"\n")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for p in report["pages"]:
        print("page", p["page"], "population", p["population"], "observed", p["observed"]["counts"],
              "equal", p["equal_gaps"]["counts"], "random means", {m: sum(p["samples"][m])/REPS for m in METRICS})


if __name__ == "__main__":
    main()
