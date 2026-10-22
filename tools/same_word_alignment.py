"""Color-independent identical-word geometry and row/width-conditioned comparisons.

Canonical identity and location coverage are separate. No word-color label or
colored-component pin set enters this analysis. Stored locations remain OCR
mapping hypotheses, evaluated against existing annotations without repair.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import map_tokens as mt
import ocr_corpus_map as cm
import ocr_word_boundary_map as wm
import word_boundary_sites as ws
from audit_stats import tail_summary
from semantic_validation import DATA, ROOT, is_name

PLAN = DATA / "research_same_word_plan_v1.json"
OUTPUT = DATA / "research_same_word_alignment_v1.json"
METRICS = ("standalone_allah", "all_identical_words", "alrahman", "alrahim", "allah_name_family")
MODELS = ("page_row", "page_row_width20")


@dataclass(frozen=True)
class Spec:
    tolerance_pixels: int = 15
    width_bin: int = 20
    reps: int = 5000
    seed: int = 20261019


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spelling(token):
    return mt.DIAC.sub("", token).replace("ٱ", "ا")


def canonical_inventory():
    """Keep the existing global token IDs, but avoid its lossy identity grouping."""
    result, omitted = {}, Counter()
    t = 0
    corpus = json.loads(mt.TOKENS_F.read_text())
    for verse in corpus["verses"]:
        for raw in verse["text_uthmani"].split():
            normalized = mt.norm(raw)
            if not normalized:
                continue
            row = dict(t=t, verse=verse["verse_key"], word=spelling(raw), form=normalized)
            if row["verse"].startswith("1:"):
                omitted["fatiha_tokens"] += 1
            else:
                result[t] = row
            t += 1
    virtual, _, _ = cm.virtual_corpus()
    for row in virtual:
        if row["kind"] != "verse":
            omitted["synthetic_head_basmala_tokens"] += 1
        elif row["t"] in result:
            if any(result[row["t"]][k] != row[k] for k in ("t", "verse", "form")):
                raise AssertionError("strict spelling inventory does not match canonical token IDs")
    return result, dict(omitted)


def locate(canonical, sites, mapping, exact_surface=False):
    candidates, raw_candidates = defaultdict(list), defaultdict(list)
    pages = {p["page"]: p for p in mapping["pages"]}
    for page in mapping["pages"]:
        for word in page["words"]:
            if word["kind"] == "verse" and word["t"] in canonical:
                raw_candidates[word["t"]].append(page["page"])
    for page in sites["pages"]:
        row_of = {}
        for index, group in enumerate(pages[page["page"]]["row_groups"]):
            if group["seeds"]:
                for region in group["ordered_indices"]:
                    row_of[region] = index
        claims = Counter(region for w in page["words"] for region in w["mandatory_regions"])
        for word in page["words"]:
            if word["kind"] != "verse" or word["t"] not in canonical:
                continue
            truth = canonical[word["t"]]
            if word["form"] != truth["form"] or word["verse"] != truth["verse"]:
                raise AssertionError("site identity disagrees with canonical text")
            ids = word["mandatory_regions"]
            rows = {row_of.get(i) for i in ids}
            status = ("nonexact_surface" if exact_surface and not word["surface_match"] else
                      "shared_mandatory_region" if any(claims[i] != 1 for i in ids) else
                      "ambiguous_seeded_row" if not ids or None in rows or len(rows) != 1 else "located")
            candidates[word["t"]].append(dict(page=page["page"], row=next(iter(rows)) if status == "located" else None,
                bbox=word["bbox"], status=status, surface_match=word["surface_match"]))
    accepted, unresolved = [], []
    for t, truth in canonical.items():
        choices = candidates[t]
        if len(choices) == 1 and choices[0]["status"] == "located":
            row = choices[0]
            box = row["bbox"]
            accepted.append(dict(t=t, page=row["page"], row=row["row"], x2=box[0]+box[2],
                                 width=box[2]-box[0], bbox=box, word=truth["word"]))
        else:
            status = ("multiple_page_candidates" if len(choices) > 1 else choices[0]["status"] if choices
                      else "no_conservative_site" if raw_candidates[t] else "no_mapped_token")
            unresolved.append(dict(t=t, status=status, candidate_pages=sorted(set(raw_candidates[t]))))
    # Distinct canonical words cannot silently acquire the same physical box.
    physical = defaultdict(list)
    for row in accepted:
        physical[row["page"], tuple(row["bbox"])].append(row["t"])
    duplicate = {t for values in physical.values() if len(values) > 1 for t in values}
    if duplicate:
        for row in accepted:
            if row["t"] in duplicate:
                unresolved.append(dict(t=row["t"], status="duplicate_physical_box", candidate_pages=[row["page"]]))
        accepted = [r for r in accepted if r["t"] not in duplicate]
    if {r["t"] for r in accepted} | {r["t"] for r in unresolved} != set(canonical):
        raise AssertionError("incomplete canonical occurrence accounting")
    return accepted, sorted(unresolved, key=lambda r: r["t"])


def geometry_edges(rows, tolerance):
    """Every unordered same-page, different-row pair within center tolerance."""
    grouped = defaultdict(list)
    for i, row in enumerate(rows):
        grouped[row["page"]].append(i)
    left, right = [], []
    for ids in grouped.values():
        ordered = sorted(ids, key=lambda i: (rows[i]["x2"], i))
        for position, i in enumerate(ordered):
            for j in ordered[position+1:]:
                if rows[j]["x2"]-rows[i]["x2"] > 2*tolerance:
                    break
                if rows[i]["row"] != rows[j]["row"]:
                    left.append(i)
                    right.append(j)
    return np.array(left, dtype=np.int32), np.array(right, dtype=np.int32)


def flags(labels, left, right, family=None):
    match = labels[left] == labels[right] if family is None else family[labels[left]] & family[labels[right]]
    result = np.zeros(len(labels), dtype=bool)
    result[left[match]] = True
    result[right[match]] = True
    return result, match


def metric_counts(labels, left, right, vocabulary, family):
    marked, _ = flags(labels, left, right)
    counts = np.bincount(labels[marked], minlength=len(vocabulary))
    lookup = {w: i for i, w in enumerate(vocabulary)}
    family_marked, _ = flags(labels, left, right, family)
    return dict(standalone_allah=int(counts[lookup["الله"]]) if "الله" in lookup else 0,
                all_identical_words=int(marked.sum()),
                alrahman=int(counts[lookup["الرحمن"]]) if "الرحمن" in lookup else 0,
                alrahim=int(counts[lookup["الرحيم"]]) if "الرحيم" in lookup else 0,
                allah_name_family=int(family_marked.sum()))


def strata(rows, model, width_bin):
    keys = [(r["page"], r["row"], r["width"]//width_bin if model == "page_row_width20" else 0) for r in rows]
    unique = {key: i for i, key in enumerate(sorted(set(keys)))}
    return np.array([unique[key] for key in keys], dtype=np.int32)


def permute(labels, groups, rng):
    base = np.argsort(groups, kind="stable")
    destinations = np.lexsort((rng.random(len(labels)), groups))
    result = np.empty_like(labels)
    result[destinations] = labels[base]
    return result


def analytic_means(labels, groups, left, right, nwords):
    """Hypergeometric avoidance, without independent endpoint assumptions.

    Strata are within a single row. Thus a candidate's different-row
    neighbors belong to other, independent strata; its own inclusion weight
    is simply the stratum frequency of its word.
    """
    sizes = Counter(groups.tolist())
    word_counts = defaultdict(Counter)
    for label, group in zip(labels.tolist(), groups.tolist()):
        word_counts[group][label] += 1
    neighbors = [Counter() for _ in labels]
    for i, j in zip(left.tolist(), right.tolist()):
        if groups[i] == groups[j]:
            raise AssertionError("analytic avoidance requires row-contained strata")
        neighbors[i][int(groups[j])] += 1
        neighbors[j][int(groups[i])] += 1
    avoidance, means = {}, np.zeros(nwords, dtype=float)
    for i, group in enumerate(groups.tolist()):
        for word, count in word_counts[group].items():
            no_partner = 1.0
            for other, potential in neighbors[i].items():
                selected = word_counts[other].get(word, 0)
                if not selected:
                    continue
                key = (sizes[other], selected, potential)
                if key not in avoidance:
                    n, k, m = key
                    avoidance[key] = math.comb(n-m, k)/math.comb(n, k) if n-m >= k else 0.0
                no_partner *= avoidance[key]
            means[word] += count/sizes[group]*(1-no_partner)
    return means


def simulate(rows, labels, vocabulary, family, left, right, model, spec):
    groups = strata(rows, model, spec.width_bin)
    base = np.argsort(groups, kind="stable")
    rng = np.random.default_rng(spec.seed+MODELS.index(model))
    samples = {name: [] for name in METRICS}
    for _ in range(spec.reps):
        destination = np.lexsort((rng.random(len(labels)), groups))
        trial = np.empty_like(labels)
        trial[destination] = labels[base]
        counts = metric_counts(trial, left, right, vocabulary, family)
        for name in METRICS:
            samples[name].append(counts[name])
    return samples


def evaluate_annotations(rows):
    from word_ownership_evidence_audit import cases
    from word_boundary_ink_audit import outcome
    lookup = {r["t"]: r for r in rows}
    groups = defaultdict(list)
    seen = set()
    for case in cases():
        label = case["label"]
        t = label.get("t")
        if t is None or label.get("kind", "verse") != "verse":
            continue
        signature = (case["cohort"], t, label["page"], json.dumps(label.get("rect", label.get("core_rect"))))
        if signature in seen:
            continue
        seen.add(signature)
        row = lookup.get(t)
        scored = outcome(row["bbox"] if row is not None and row["page"] == label["page"] else None, label, case["support"])
        groups[case["cohort"]].append(dict(t=t, expected_page=label["page"], accepted_page=row["page"] if row else None,
            bbox=row["bbox"] if row else None, accepted=scored["accepted"], center_correct=scored["center_correct"]))
    return {name: dict(scheduled=len(details), located=sum(r["accepted"] for r in details),
                      correct_centers=sum(r["center_correct"] for r in details),
                      details=details) for name, details in groups.items()}


def analyze(stored=None, resimulate=False, spec=Spec()):
    plan = json.loads(PLAN.read_text())
    if plan["simulation"]["replicates"] != spec.reps or plan["simulation"]["seed"] != spec.seed:
        raise AssertionError("simulation parameters differ from saved plan")
    canonical, omitted = canonical_inventory()
    mapping, sites = json.loads(wm.OUTPUT.read_text()), json.loads(ws.OUTPUT.read_text())
    if sites["inputs"][wm.OUTPUT.name] != digest(wm.OUTPUT):
        raise AssertionError("conservative site mapping hash differs")
    for path in (cm.SOURCE, mt.TOKENS_F):
        if mapping["inputs"][path.name] != digest(path) or sites["inputs"][path.name] != digest(path):
            raise AssertionError("same-word source identity differs")
    vocabulary = sorted({r["word"] for r in canonical.values()})
    word_ids = {word: i for i, word in enumerate(vocabulary)}
    forms = {r["word"]: r["form"] for r in canonical.values()}
    family = np.array([is_name(forms[w]) for w in vocabulary], dtype=bool)
    expected = Counter(row["word"] for row in canonical.values())
    views = {}
    for view in ("conservative_v5", "exact_surface_v5"):
        rows, unresolved = locate(canonical, sites, mapping, view == "exact_surface_v5")
        labels = np.array([word_ids[r["word"]] for r in rows], dtype=np.int32)
        left, right = geometry_edges(rows, spec.tolerance_pixels)
        marked, matches = flags(labels, left, right)
        family_marked, family_matches = flags(labels, left, right, family)
        counts = np.bincount(labels, minlength=len(vocabulary))
        aligned = np.bincount(labels[marked], minlength=len(vocabulary))
        pairs = np.bincount(labels[left[matches]], minlength=len(vocabulary))
        observed = metric_counts(labels, left, right, vocabulary, family)
        all_family_expected = sum(expected[w] for w, yes in zip(vocabulary, family) if yes)
        located_family = int(family[labels].sum())
        targets = {}
        for name, word in (("standalone_allah", "الله"), ("alrahman", "الرحمن"), ("alrahim", "الرحيم")):
            wid = word_ids[word]
            targets[name] = dict(word=word, canonical_expected=expected[word], located=int(counts[wid]), aligned=int(aligned[wid]),
                unresolved=expected[word]-int(counts[wid]))
        targets["all_identical_words"] = dict(canonical_expected=len(canonical), located=len(rows), aligned=int(marked.sum()), unresolved=len(unresolved))
        targets["allah_name_family"] = dict(canonical_expected=all_family_expected, located=located_family,
            aligned=int(family_marked.sum()), unresolved=all_family_expected-located_family)
        comparisons, word_means = {}, {}
        if view == "conservative_v5":
            for model in MODELS:
                groups = strata(rows, model, spec.width_bin)
                means = analytic_means(labels, groups, left, right, len(vocabulary))
                family_mean = analytic_means(family[labels].astype(np.int32), groups, left, right, 2)[1]
                expectation = dict(standalone_allah=float(means[word_ids["الله"]]), all_identical_words=float(means.sum()),
                    alrahman=float(means[word_ids["الرحمن"]]), alrahim=float(means[word_ids["الرحيم"]]), allah_name_family=float(family_mean))
                word_means[model] = means.tolist()
                samples = (simulate(rows, labels, vocabulary, family, left, right, model, spec) if stored is None or resimulate
                           else stored["views"][view]["comparisons"][model]["samples"])
                details = {}
                for name in METRICS:
                    values = samples[name]
                    if len(values) != spec.reps or any(not isinstance(v, int) or not 0 <= v <= targets[name]["located"] for v in values):
                        raise AssertionError("invalid same-word null sample")
                    inference = tail_summary(observed[name], values)
                    selection = (np.ones(len(labels), dtype=bool) if name == "all_identical_words" else family[labels]
                                 if name == "allah_name_family" else labels == word_ids[targets[name]["word"]])
                    per_page = Counter(r["page"] for r, yes in zip(rows, selection) if yes)
                    ranges = sum(k*k for k in per_page.values())
                    gap = max(0.0, observed[name]-expectation[name])
                    details[name] = dict(analytic_expected_aligned=expectation[name], inference=inference,
                        column_hoeffding_log10_upper_bound=-2*gap*gap/ranges/math.log(10) if ranges else 0.0,
                        sum_squared_page_ranges=ranges)
                group_words = defaultdict(set)
                for group, label in zip(groups.tolist(), labels.tolist()):
                    group_words[group].add(label)
                fixed = sum(len(words) == 1 for words in group_words.values())
                comparisons[model] = dict(strata=len(set(groups.tolist())), single_identity_strata=fixed,
                    metrics=details, samples=samples)
        word_table = [dict(word=word, canonical_expected=expected[word], located=int(counts[i]), aligned=int(aligned[i]),
            matching_pairs=int(pairs[i]), unresolved=expected[word]-int(counts[i]),
            analytic_expected_aligned={model: values[i] for model, values in word_means.items()}) for i, word in enumerate(vocabulary)]
        views[view] = dict(targets=targets, per_word=word_table,
            inventory_schema=["t", "page", "seeded_row", "twice_center_x", "box_width"],
            located_inventory=[[r[k] for k in ("t", "page", "row", "x2", "width")] for r in rows], unresolved_inventory=unresolved,
            unresolved_by_reason=dict(Counter(r["status"] for r in unresolved)),
            same_word_pair_token_ids=[[rows[i]["t"], rows[j]["t"]] for i, j in zip(left[matches].tolist(), right[matches].tolist())],
            family_pair_token_ids=[[rows[i]["t"], rows[j]["t"]] for i, j in zip(left[family_matches].tolist(), right[family_matches].tolist())],
            same_word_unpaired_located_token_ids=[rows[i]["t"] for i in np.flatnonzero(~marked)],
            comparisons=comparisons, diagnostic_existing_annotations=evaluate_annotations(rows))
    inputs = [PLAN, wm.OUTPUT, ws.OUTPUT, cm.SOURCE, mt.TOKENS_F, Path(__file__)]
    inputs += [ROOT / "tools" / name for name in ("map_tokens.py", "ocr_corpus_map.py", "semantic_validation.py", "audit_stats.py",
              "word_boundary_ink_audit.py", "word_boundary_ownership_policy.py", "word_localization_validation.py",
              "word_ownership_evidence_audit.py", "divine_census.py")]
    # The frozen annotation inputs are separately hashed so coverage diagnostics
    # cannot change silently when manual data are edited.
    from word_boundary_ink_audit import INPUTS
    inputs.extend(INPUTS)
    from word_ink_trim_fresh_validation import OUTPUT as FRESH
    inputs.append(FRESH)
    return dict(version="color-independent-same-word-alignment-v1", spec=asdict(spec),
        inputs={p.name: digest(p) for p in inputs}, canonical_expected=len(canonical), vocabulary_size=len(vocabulary),
        excluded_from_scanned_verse_inventory=omitted, views=views,
        caveat="Canonical word identities and detector/support-box centers, selected without word-ink color. Frozen OCR hypotheses are not a complete certified geometry census. Missing partners and wrong boxes can alter scores. Exact spelling keeps prefixes and hamza distinctions; the explicitly separate Allah family is broader. Reference word-identity permutations preserve every page/row count and optionally coarse width-bin counts, not syntax or text order. Finite simulation tails and independent-page Hoeffding bounds are conditional on accepted locations and those models, not probabilities of divine origin. All geometry and prior annotations are exposed data; no independent new accuracy claim.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    parser.add_argument("--full", action="store_true", help="resimulate every null score")
    args = parser.parse_args()
    saved = json.loads(OUTPUT.read_text()) if args.verify else None
    report = analyze(saved, args.full)
    if args.verify:
        if report != saved:
            raise AssertionError("color-independent same-word analysis differs")
        print("PASS same-word identities, every occurrence, pairs, analytic expectations and null arithmetic")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":"))+"\n")
    print("expected", report["canonical_expected"], "word types", report["vocabulary_size"], flush=True)
    for view, results in report["views"].items():
        print(view, json.dumps(results["targets"], ensure_ascii=False), flush=True)
        print("unresolved", results["unresolved_by_reason"], flush=True)
        for model, row in results["comparisons"].items():
            for name, metric in row["metrics"].items():
                print(model, name, json.dumps(metric), flush=True)
        print("existing annotations", {name: {k: v for k, v in group.items() if k != "details"}
              for name, group in results["diagnostic_existing_annotations"].items()}, flush=True)


if __name__ == "__main__":
    main()
