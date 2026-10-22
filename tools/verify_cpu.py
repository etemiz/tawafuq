"""Scan-free CPU verification of audited component statistics.

Quick: python tools/verify_cpu.py
Full deterministic global null replay: python tools/verify_cpu.py --full
Reads committed data, runs independent reference scoring and exact tests.
It does not certify semantic pins or the correctness of historical images.
"""
import argparse
import ast
import json
import unittest
from fractions import Fraction
from pathlib import Path

import numpy as np

from alignment import ScoreSpec, batch_flags, reference_flags, score_flags
from real_stats import DATA, load_all, input_manifest, observed_counts, simulate
from slot_expectation import expectation, column_hoeffding
from audit_stats import tail_summary
from exact_column import analyze as exact_column_analysis
from word_pair_census import load_pins, pin_manifest, pair_count
from grain_sweep import make_cells
from pair_statistics import word_cell_pairs

ROOT = Path(__file__).resolve().parent.parent


def check_summary(observed, samples, stored):
    np.testing.assert_allclose(observed, stored["observed"])
    current = tail_summary(observed, samples)
    for key in ("reps", "exceedances", "null_mean", "null_sd", "plus_one_mc", "tail_interval"):
        np.testing.assert_allclose(current[key], stored[key])


def check_conditional_results():
    """Check inputs, observed counts and stored MC arithmetic on pin hypotheses."""
    src = "mark_identity_semantic_v3.json"
    source_path = DATA.parent / src
    if not source_path.exists():
        return
    pins = load_pins(src)
    manifest = pin_manifest(src)
    path = DATA.parent / "mark_identity_semantic_v3_word_pairs.json"
    if path.exists():
        rep = json.loads(path.read_text())
        if rep["audit"]["inputs"] != manifest:
            raise AssertionError("word-pair input hashes differ")
        for kind in ("mag", "cri"):
            sub = [p for p in pins if p["kind"] == kind]
            obs = pair_count([(p["word"], p["page"], p["yb"], p["xb"]) for p in sub])
            if obs != rep[kind]["obs"]:
                raise AssertionError("word-pair observed count differs")
            for samples, summary in (("slot_samples", "slot_inference"),
                                     ("permutation_samples", "permutation_inference")):
                check_summary(obs, rep[kind][samples], rep[kind][summary])
        print("PASS v3 conditional word pairs: inputs, observed counts, stored MC inference", flush=True)
    path = DATA.parent / "audit_grain_sweep_v3.json"
    if path.exists():
        rep = json.loads(path.read_text())
        if rep["inputs"] != manifest:
            raise AssertionError("grain input hashes differ")
        for key, row in rep["results"].items():
            kind = key.split(":")[-1]
            sub = [p for p in pins if p["kind"] == kind]
            nb = row["n_columns"]
            # Use saved exact bin count directly to avoid ceil round-off.
            cells = [(p["page"], int(p["yc"] // row["row_width"]) if row["row_width"] else 0,
                      min(nb - 1, max(0, int(p["xc"] // (1024 / nb))))) for p in sub]
            obs = word_cell_pairs([(p["word"], *cell) for p, cell in zip(sub, cells)],
                                  nb if row["mirror"] else None)
            check_summary(obs, row["null_samples"], row["inference"])
        print("PASS v3 conditional grain sweep: inputs, all observed counts, stored MC inference", flush=True)
    path = DATA.parent / "audit_phrase_mirror_v3.json"
    if path.exists():
        from phrase_mirror_test import PAIRS, pair_stats
        rep = json.loads(path.read_text())
        if rep["inputs"] != manifest:
            raise AssertionError("phrase-pair input hashes differ")
        cells, nb = make_cells(pins, 112, 30)
        for name, (a, b) in PAIRS.items():
            items = [(pg, row, col, 0 if p["word"] in a else 1)
                     for p, (pg, row, col) in zip(pins, cells) if p["word"] in a | b]
            obs = pair_stats(items, bins=nb)
            row = rep["pairs"][name]
            if tuple(row[k] for k in ("obs_same", "obs_mirror", "obs_facing_same", "obs_facing_mirror")) != obs:
                raise AssertionError("phrase-pair observed counts differ")
            for k, summary, observed in (("slot_same", "slot_same_inference", obs[0]),
                                         ("slot_mirror", "slot_mirror_inference", obs[1]),
                                         ("pairperm_same", "pairperm_same_inference", obs[0]),
                                         ("pairperm_mirror", "pairperm_mirror_inference", obs[1])):
                check_summary(observed, row["null_samples"][k], row[summary])
        print("PASS v3 conditional phrase pairs: inputs, observed counts, stored MC inference", flush=True)
    path = DATA.parent / "audit_page_turn_v3.json"
    if path.exists():
        rep = json.loads(path.read_text())
        if rep["inputs"] != manifest:
            raise AssertionError("page-turn input hashes differ")
        for key, summary in rep["inference"].items():
            obs = rep["obs_mirror"] if key.endswith("mirror") else rep["obs_same"]
            check_summary(obs, rep["null_samples"][key], summary)
        print("PASS v3 conditional page turn: inputs and stored MC inference", flush=True)
    path = DATA.parent / "audit_run_pairs_v3.json"
    if path.exists():
        rep = json.loads(path.read_text())
        if rep["audit"]["inputs"] != manifest:
            raise AssertionError("run-pair input hashes differ")
        for kind in ("mag", "cri"):
            check_summary(rep[kind]["obs"], rep[kind]["null_samples"], rep[kind]["inference"])
        print("PASS v3 conditional run pairs: inputs and stored MC inference", flush=True)


def check_manual_rosette_page():
    sequence = DATA.parent / "rosette_map_v3" / "rosette_seq.npz"
    detections = DATA.parent / "rosettes_v3" / "rosette_digits.json"
    if not sequence.exists() or not detections.exists():
        return
    gold = json.loads((DATA.parent / "audit_manual_rosettes.json").read_text())
    with np.load(sequence, allow_pickle=False) as archive:
        meta = archive["meta"]
    meta = meta[meta[:, 0] == gold["page"]]
    found = json.loads(detections.read_text())[str(gold["page"])]
    for label in gold["labels"]:
        distance = np.hypot(meta[:, 1] - label["cx"], meta[:, 2] - label["cy"])
        row = meta[distance.argmin()]
        if distance.min() > 12 or f"{int(row[3])}:{int(row[4])}" != label["verse"]:
            raise AssertionError("manual rosette location/identity mismatch")
        r = min(found, key=lambda x: np.hypot(x["cx"] - label["cx"], x["cy"] - label["cy"]))
        if np.hypot(r["cx"] - label["cx"], r["cy"] - label["cy"]) > 12:
            raise AssertionError("manual rosette detection missing")
        if r["ndig"] != len(label["verse"].split(":")[1]):
            raise AssertionError("manual rosette digit count mismatch")
    print("PASS p567: 28/28 provided visual transcriptions match v3 locations, "
          "digit counts and verse assignments (one-page check)", flush=True)


def check_reference_controls(full=False):
    from reference_controls import prepare
    path = DATA.parent / "audit_reference_controls.json"
    if not path.exists():
        return
    report = json.loads(path.read_text())
    data = DATA.parent / report["data_directory"]
    if input_manifest(data) != report["inputs"]:
        raise AssertionError("unit-control input hashes differ")
    for name, row in report["cases"].items():
        pages, details = prepare(data, row["raw_observations"], row["word_size_filter"], row["exclude_gold"])
        spec = ScoreSpec(**row["score"])
        reference = reference_flags({n: p["reds"] for n, p in pages.items()}, spec)
        counts = score_flags({n: (c[None], m[None]) for n, (c, m) in reference.items()})
        observed = {k: int(v[0]) for k, v in counts.items()}
        if observed != row["observed"]:
            raise AssertionError("unit-control independent observed score differs")
        total = sum(len(p["reds"]) for p in pages.values())
        if total != row["total_components"] or len(pages) != row["pages"]:
            raise AssertionError("unit-control population differs")
        np.testing.assert_allclose(observed["aligned"] / total, row["observed_rate"])
        if details["observed_positions_are_reference_subset"] != row["observed_positions_are_reference_subset"]:
            raise AssertionError("unit-control subset property differs")
        means, _ = expectation(pages, spec, row["null_model"])
        for key, mean in means.items():
            np.testing.assert_allclose(mean, row["analytic_expectation"][key], atol=1e-9)
            check_summary(observed[key], row["null_samples"][key], row["results"][key])
        bound = column_hoeffding(observed["column"], means["column"], pages)
        np.testing.assert_allclose(bound["log10_upper_bound"], row["column_hoeffding"]["log10_upper_bound"])
        if full:
            replay = simulate(pages, row["results"]["aligned"]["reps"], report["seed"],
                              report["batch_size"], spec, row["null_model"])
            for key in replay:
                np.testing.assert_array_equal(replay[key], row["null_samples"][key])
        print(f"PASS unit control {name}: independent scores, analytic means, stored inference"
              + (", full MC replay" if full else ""), flush=True)


def check_report(path, data, full=False):
    report = json.loads(path.read_text())
    if input_manifest(data) != report["inputs"]:
        raise AssertionError(f"input hash mismatch for {path.name}")
    pages = load_all(include_empty=True, data=data)
    spec = ScoreSpec(**report["score"])
    positions = {n: p["reds"] for n, p in pages.items()}
    reference = reference_flags(positions, spec)
    fast = batch_flags({n: p[None] for n, p in positions.items()}, spec)
    for n in positions:
        for expected, actual in zip(reference[n], fast[n]):
            np.testing.assert_array_equal(expected, actual[0])
    observed = {k: int(v[0]) for k, v in score_flags(fast).items()}
    if observed != report["observed"]:
        raise AssertionError("stored observed score differs from independent reference")
    if sum(len(p) for p in positions.values()) != report["total_components"]:
        raise AssertionError("component denominator mismatch")
    model = report.get("null_model", "page")
    exact, _ = expectation(pages, spec, model)
    for k, value in exact.items():
        np.testing.assert_allclose(value, report["analytic_expectation"][k], atol=1e-8, rtol=1e-12)
        recalculated = tail_summary(observed[k], report["null_samples"][k])
        for key in ("exceedances", "null_mean", "null_sd", "tail_upper_one_sided", "plus_one_mc"):
            np.testing.assert_allclose(recalculated[key], report["results"][k][key])
    bound = column_hoeffding(observed["column"], exact["column"], pages)
    np.testing.assert_allclose(bound["log10_upper_bound"], report["column_hoeffding"]["log10_upper_bound"])
    if full:
        reps = report["results"]["aligned"]["reps"]
        replay = simulate(pages, reps, report["seed"], report["batch_size"], spec, model)
        for k in replay:
            np.testing.assert_array_equal(replay[k], report["null_samples"][k])
    print(f"PASS {path.name}: {observed['aligned']}/{report['total_components']}, "
          f"independent flags, analytic mean, hashes, stored inference"
          + (", full MC replay" if full else ""), flush=True)


def check_cloud_ocr_samples():
    """Replay saved service responses without credentials, network or scans."""
    from arabic_ocr_cloud import convert
    from ocr_benchmark import analyze as analyze_ocr
    from ocr_word_map import analyze as analyze_words
    for directory, manual_name, benchmark, mapping in (
            ("ocr_sample_google_v1", "audit_manual_semantic_sample.json",
             "audit_ocr_google.json", "audit_ocr_google_word_map.json"),
            ("ocr_heldout_google_v1", "audit_manual_ocr_heldout.json",
             "audit_ocr_heldout_google.json", "audit_ocr_heldout_google_word_map.json"),
            ("ocr_word_validation_google_v2", "audit_manual_word_validation_v2.json",
             "audit_ocr_word_validation_google_v2.json", None)):
        source = DATA.parent / directory
        if not source.exists():
            continue
        manual_path = DATA.parent / manual_name
        for page in json.loads(manual_path.read_text())["pages"]:
            row = json.loads((source / f'page_{page["page"]}.json').read_text())
            if convert(row["raw_response"]) != row["result"]:
                raise AssertionError("saved cloud coordinate conversion differs from raw response")
        for analyze, filename in ((analyze_ocr, benchmark), (analyze_words, mapping)):
            if filename is None:
                continue
            if analyze(source, manual_path) != json.loads((DATA.parent / filename).read_text()):
                raise AssertionError(f"{filename} replay differs")
            print(f"PASS {filename}: raw service geometry, exact text, manual outcomes and hashes", flush=True)
    for source, manual, filename in (
            ("ocr_sample_google_v1", "audit_manual_semantic_sample.json", "audit_ocr_google_word_map_v2.json"),
            ("ocr_heldout_google_v1", "audit_manual_ocr_heldout.json", "audit_ocr_heldout_google_word_map_v2.json")):
        path = DATA.parent / filename
        if path.exists():
            if analyze_words(DATA.parent / source, DATA.parent / manual, "mandatory-v2") != json.loads(path.read_text()):
                raise AssertionError("v2 development mapper replay differs")
            print(f"PASS {filename}: mandatory bidirectional support and all name outcomes", flush=True)
    if (DATA.parent / "audit_manual_word_validation_v2.json").exists():
        from word_validation_sample import build, MANUAL
        manual = json.loads(MANUAL.read_text())
        if build(False, manual) != manual:
            raise AssertionError("fresh v2 sample selection/annotation/rule hash differs")
        from adjudicate_word_sample import build as adjudicate
        adjudicated_path = DATA.parent / "audit_manual_word_validation_v2_adjudicated.json"
        adjudicated = json.loads(adjudicated_path.read_text())
        if adjudicate(adjudicated) != adjudicated:
            raise AssertionError("adjudicated label/pixel provenance differs")
        from word_localization_validation import verify
        for annotation, filename in ((MANUAL, "audit_word_localization_v2.json"),
                                      (adjudicated_path, "audit_word_localization_v2_adjudicated.json")):
            verify(DATA.parent / filename, DATA.parent / "ocr_word_validation_google_v2", annotation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    for required in ("audit_global_v3.json", "audit_exact_columns.json",
                     "audit_reference_controls.json", "audit_exact_columns_raw_wordlike.json",
                     "audit_geometry_controls.json"):
        if not (DATA.parent / required).exists():
            raise FileNotFoundError(f"required audit artifact missing: {required}")
    sources = list((ROOT / "tools").glob("*.py"))
    for p in sources:
        ast.parse(p.read_text(), filename=str(p))
    print(f"Syntax: {len(sources)} Python files", flush=True)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tools"), pattern="test_*.py")
    if not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful():
        raise SystemExit(1)
    reports = [("audit_global.json", DATA),
               ("audit_global_facing.json", DATA),
               ("audit_global_leaf.json", DATA),
               ("audit_global_shifted_columns.json", DATA),
               ("audit_global_line_null.json", DATA),
               ("audit_global_v3.json", DATA.parent / "real_boxes_v3"),
               ("audit_global_v3_line_null.json", DATA.parent / "real_boxes_v3")]
    for filename, data in reports:
        path = DATA.parent / filename
        if path.exists():
            check_report(path, data, args.full)
    for exact_name in ("audit_exact_columns.json", "audit_exact_columns_raw_wordlike.json"):
        exact_path = DATA.parent / exact_name
        if not exact_path.exists():
            continue
        saved = json.loads(exact_path.read_text())
        data = DATA.parent / saved["data_directory"]
        if input_manifest(data) != saved["inputs"]:
            raise AssertionError("exact-column input hashes differ")
        if "reference_preprocessing" in saved:
            from reference_controls import prepare
            pages, _ = prepare(data, **saved["reference_preprocessing"])
        else:
            pages = load_all(include_empty=True, data=data)
        current = exact_column_analysis(pages, saved["observed"], ScoreSpec(**saved["score"]),
                                        bases=tuple(map(int, saved["bounds"])))
        for key in ("page_distributions", "best_base"):
            if current[key] != saved[key]:
                raise AssertionError(f"exact-rational proof replay failed: {key}")
        for base, bound in current["bounds"].items():
            for key in ("numerator_hex", "denominator_hex"):
                if bound[key] != saved["bounds"][base][key]:
                    raise AssertionError("exact-rational tail bound differs")
            # The rational integers are exact; log10 is only display metadata
            # and may differ by a few libm ulps across CPU/OS implementations.
            np.testing.assert_allclose(bound["log10_upper_bound"],
                                       saved["bounds"][base]["log10_upper_bound"], atol=1e-9)
        if saved["observed"] == 3271 and saved["score"] == ScoreSpec().to_dict():
            best = current["bounds"][str(current["best_base"])]
            if Fraction(int(best["numerator_hex"], 16), int(best["denominator_hex"], 16)) > Fraction(2, 10 ** 726):
                raise AssertionError("published conservative 2e-726 bound not satisfied")
        if saved.get("reference_preprocessing") and saved["observed"] == 3522:
            best = current["bounds"][str(current["best_base"])]
            if Fraction(int(best["numerator_hex"], 16), int(best["denominator_hex"], 16)) > Fraction(1, 10 ** 814):
                raise AssertionError("published raw-component 1e-814 bound not satisfied")
        mean, by_page = expectation(pages, ScoreSpec(**saved["score"]))
        np.testing.assert_allclose(current["analytic_column_mean"], mean["column"])
        for n, d in current["page_distributions"].items():
            dp_mean = sum(i * int(c) for i, c in enumerate(d["counts"])) / int(d["denominator"])
            np.testing.assert_allclose(dp_mean, by_page[int(n)]["column"], atol=1e-10)
        print(f"PASS {exact_name}: exact integer coefficient accounting, "
              "independent per-page means, exact rational tail bounds", flush=True)
    check_reference_controls(args.full)
    constructive_path = DATA.parent / "research_constructive_selection_v1.json"
    if constructive_path.exists():
        from constructive_selection import analyze as check_constructive_selection
        if check_constructive_selection() != json.loads(constructive_path.read_text()):
            raise AssertionError("constructive fixed-geometry selection differs")
        print("PASS constructive fixed-site witnesses, exact page maxima and uniform-null maximum probability", flush=True)
    geometry_path = DATA.parent / "audit_geometry_controls.json"
    if geometry_path.exists():
        from geometry_controls import verify_report
        verify_report(geometry_path, args.full)
    check_conditional_results()
    check_manual_rosette_page()
    semantic_path = DATA.parent / "audit_semantic_validation.json"
    if semantic_path.exists():
        from semantic_validation import verify_report as verify_semantic_report
        verify_semantic_report(semantic_path)
    for filename, directory in (("audit_arabic_ocr.json", "ocr_sample_v1"),
                                ("audit_easyocr_arabic.json", "ocr_easy_sample_v1")):
        path = DATA.parent / filename
        if path.exists():
            from ocr_benchmark import analyze as analyze_ocr
            if analyze_ocr(DATA.parent / directory) != json.loads(path.read_text()):
                raise AssertionError("Arabic OCR benchmark replay differs")
            print(f"PASS {filename}: exact-text edit counts, name locations and hashes", flush=True)
    line_path = DATA.parent / "audit_ocr_line_map.json"
    if line_path.exists():
        from ocr_line_map import analyze as analyze_line_map
        if analyze_line_map(DATA.parent / "ocr_sample_v1") != json.loads(line_path.read_text()):
            raise AssertionError("exact-corpus OCR line map replay differs")
        print("PASS exact-corpus OCR line map: optimal-path ambiguity and manual name lines", flush=True)
    heldout_manual = DATA.parent / "audit_manual_ocr_heldout.json"
    if heldout_manual.exists():
        from ocr_heldout_sample import selected_pages, SEED
        manual = json.loads(heldout_manual.read_text())
        if manual["seed"] != SEED or [p["page"] for p in manual["pages"]] != selected_pages():
            raise AssertionError("held-out sample differs from predeclared selection")
        from heldout_semantics import verify as verify_heldout
        verify_heldout(DATA.parent / "audit_semantic_heldout.json")
        from ocr_benchmark import analyze as analyze_ocr
        from ocr_line_map import analyze as analyze_lines
        from ocr_word_map import analyze as analyze_words
        cases = [(analyze_ocr, "audit_ocr_heldout_easy.json", "ocr_heldout_easy_v1", heldout_manual),
                 (analyze_ocr, "audit_ocr_heldout_surya.json", "ocr_heldout_surya_v1", heldout_manual),
                 (analyze_lines, "audit_ocr_heldout_line_map.json", "ocr_heldout_surya_v1", heldout_manual),
                 (analyze_words, "audit_ocr_heldout_word_map.json", "ocr_heldout_easy_v1", heldout_manual),
                 (analyze_words, "audit_ocr_word_map.json", "ocr_easy_sample_v1",
                  DATA.parent / "audit_manual_semantic_sample.json")]
        for analyze, filename, directory, annotation in cases:
            if analyze(DATA.parent / directory, annotation) != json.loads((DATA.parent / filename).read_text()):
                raise AssertionError(f"{filename} replay differs")
            print(f"PASS {filename}: exact text, all saved outcomes and input hashes", flush=True)
    check_cloud_ocr_samples()
    corpus_path = DATA.parent / "ocr_google_corpus_v1.json"
    if corpus_path.exists():
        from google_corpus_cache import verify as verify_ocr_corpus
        verify_ocr_corpus(DATA.parent / "google_corpus_manifest_v1.json", corpus_path)
    corpus_map = DATA.parent / "audit_ocr_corpus_map_v1.json"
    if corpus_map.exists():
        from ocr_corpus_map import verify_report as verify_corpus_map
        verify_corpus_map(corpus_map, full=args.full)
        from corpus_map_validation import analyze as check_corpus_names, MANUAL as corpus_manual, build as build_corpus_labels
        manual = json.loads(corpus_manual.read_text())
        if build_corpus_labels(False, manual) != manual:
            raise AssertionError("independent corpus-map labels/rule hashes differ")
        for filename, mapping in (("audit_corpus_map_validation_v1.json", corpus_map),
                                  ("audit_corpus_map_masked_development_v2.json",
                                   DATA.parent / "audit_ocr_corpus_map_masked_v2.json")):
            if check_corpus_names(mapping) != json.loads((DATA.parent / filename).read_text()):
                raise AssertionError("corpus-map annotation comparison differs")
            print(f"PASS {filename}: independent name locations, page scopes and basmala checks", flush=True)
        verify_corpus_map(DATA.parent / "audit_ocr_corpus_map_masked_v2.json", full=args.full)
        from ornament_scope_validation import analyze as check_fresh_scopes
        if check_fresh_scopes() != json.loads((DATA.parent / "audit_ornament_scope_validation_v2.json").read_text()):
            raise AssertionError("fresh masked scope checks differ")
        print("PASS fresh masked-v2 scope checks, including unresolved endpoint/basmala cases", flush=True)
        from ocr_corpus_sites import analyze as check_wordlike_sites
        if check_wordlike_sites() != json.loads((DATA.parent / "audit_ocr_corpus_sites_v1.json").read_text()):
            raise AssertionError("post-hoc wordlike-site view differs")
        print("PASS post-hoc corpus sites, duplicate conflict, missing support and exposed names", flush=True)
        review_path = DATA.parent / "audit_corpus_site_review_v1.json"
        if review_path.exists():
            from corpus_site_review import analyze as check_site_review
            if check_site_review() != json.loads(review_path.read_text()):
                raise AssertionError("targeted corpus-site review differs")
            print("PASS targeted site review: omissions, wrong location, duplicate resolution and name-ID coverage", flush=True)
        observation_path = DATA.parent / "audit_ocr_observation_map_v3.json"
        if observation_path.exists():
            from ocr_observation_map import verify as verify_observation_map
            verify_observation_map(observation_path, args.full)
            from ocr_observation_validation import analyze as check_observation_validation, OUTPUT as observation_validation
            if check_observation_validation() != json.loads(observation_validation.read_text()):
                raise AssertionError("exposed observation-map comparison differs")
            print("PASS exposed observation-map comparison, including wrong accepted sites and screening losses", flush=True)
        row_path = DATA.parent / "audit_ocr_row_map_v4.json"
        if row_path.exists():
            from ocr_row_map import verify as verify_row_map
            from ocr_observation_validation import analyze as check_observation_validation
            verify_row_map(row_path, args.full)
            if check_observation_validation(row_path) != json.loads((DATA.parent / "audit_ocr_row_development_v4.json").read_text()):
                raise AssertionError("exposed seeded-row development comparison differs")
            from row_validation_sample import build as build_fresh_rows, MANUAL as fresh_row_manual
            manual = json.loads(fresh_row_manual.read_text())
            if build_fresh_rows(False, manual) != manual:
                raise AssertionError("frozen fresh row sample differs")
            from row_map_validation import analyze as check_fresh_rows, OUTPUT as fresh_row_output
            if check_fresh_rows() != json.loads(fresh_row_output.read_text()):
                raise AssertionError("fresh row/word comparison differs")
            print("PASS v4 development and frozen fresh row/word checks, including unscorable boundaries", flush=True)
        word_path = DATA.parent / "audit_ocr_word_boundary_map_v5.json"
        if word_path.exists():
            from ocr_word_boundary_map import verify as verify_word_boundary_map
            verify_word_boundary_map(word_path, args.full)
            from word_boundary_sites import analyze as check_boundary_sites, OUTPUT as boundary_sites_output
            sites = check_boundary_sites()
            if sites != json.loads(boundary_sites_output.read_text()):
                raise AssertionError("conservative word-boundary site view differs")
            from word_boundary_validation import analyze as check_boundary_development, OUTPUT as boundary_development_output
            comparison = check_boundary_development()
            if comparison != json.loads(boundary_development_output.read_text()):
                raise AssertionError("word-boundary development comparison differs")
            if sites["summary"] != comparison["results"]["v5_exact_multiregion_unions"]["summary"]:
                raise AssertionError("conservative site/comparison summaries differ")
            print("PASS v5 conservative site policy, all exposed annotations and retained exclusions", flush=True)
            union_review_path = DATA.parent / "audit_word_union_review_v5.json"
            if union_review_path.exists():
                from word_union_review import analyze as check_union_review
                if check_union_review() != json.loads(union_review_path.read_text()):
                    raise AssertionError("frozen rejected-union scan review differs")
                print("PASS v5 frozen rejected-union sample and scan-core comparisons", flush=True)
            fresh_plan_path = DATA.parent / "audit_word_boundary_fresh_plan_v5.json"
            if fresh_plan_path.exists():
                from word_boundary_fresh_plan import plan as check_fresh_v5_plan
                if check_fresh_v5_plan() != json.loads(fresh_plan_path.read_text()):
                    raise AssertionError("frozen v5 physical-position plan differs")
                print("PASS v5 frozen physical-position plan", flush=True)
            fresh_v5_path = DATA.parent / "audit_word_boundary_fresh_validation_v5.json"
            if fresh_v5_path.exists():
                from word_boundary_fresh_sample import build as build_fresh_v5, MANUAL as fresh_v5_manual
                manual = json.loads(fresh_v5_manual.read_text())
                if build_fresh_v5(False, manual) != manual:
                    raise AssertionError("scan-first v5 physical-position annotations differ")
                from word_boundary_fresh_validation import analyze as check_fresh_v5
                if check_fresh_v5() != json.loads(fresh_v5_path.read_text()):
                    raise AssertionError("fresh v5 physical-position validation differs")
                print("PASS fresh v5 physical-position labels, evaluation lock, all outcomes and unavailable slots", flush=True)
            extent_review_path = DATA.parent / "audit_word_boundary_extent_validation_v5.json"
            if extent_review_path.exists():
                from word_boundary_extent_review import analyze as check_extent_review
                if check_extent_review() != json.loads(extent_review_path.read_text()):
                    raise AssertionError("post-exposure v5 boundary-extent review differs")
                print("PASS post-exposure v5 boundary review, exact ownership ranges, retained failures and originals", flush=True)
            ownership_policy_path = DATA.parent / "audit_word_boundary_ownership_policy_v5.json"
            if ownership_policy_path.exists():
                from word_boundary_ownership_policy import analyze as check_ownership_policy
                policy = json.loads(ownership_policy_path.read_text())
                if check_ownership_policy(stored=policy) != policy:
                    raise AssertionError("auxiliary ownership policy comparison differs")
                print("PASS explicit auxiliary policies, exact attainable edges, all-ownership scores and retained failures", flush=True)
            ink_trim_path = DATA.parent / "audit_word_boundary_ink_trim_development_v6.json"
            if ink_trim_path.exists():
                from word_boundary_ink_audit import analyze as check_ink_trim
                ink_trim = json.loads(ink_trim_path.read_text())
                if check_ink_trim(stored=ink_trim) != ink_trim:
                    raise AssertionError("horizontal ink-trim development diagnostic differs")
                print("PASS ink-trim projections, all exposed cohorts, original outcomes and retained counterexamples", flush=True)
            ink_trim_plan = DATA.parent / "audit_word_ink_trim_fresh_plan_v6.json"
            if ink_trim_plan.exists():
                from word_ink_trim_fresh_plan import plan as check_ink_trim_plan
                if check_ink_trim_plan() != json.loads(ink_trim_plan.read_text()):
                    raise AssertionError("frozen ink-trim untouched validation plan differs")
                print("PASS frozen ink-trim candidate rules, untouched-page selection and 54-slot schedule", flush=True)
            ink_trim_fresh = DATA.parent / "audit_word_ink_trim_fresh_validation_v6.json"
            if ink_trim_fresh.exists():
                from word_ink_trim_fresh_validation import analyze as check_ink_trim_fresh
                fresh_trim = json.loads(ink_trim_fresh.read_text())
                if check_ink_trim_fresh(stored=fresh_trim) != fresh_trim:
                    raise AssertionError("locked fresh paired ink-trim validation differs")
                print("PASS scan-first ink-trim labels/evaluator lock, all 54 slots, four methods and every paired transition", flush=True)
            ink_trim_diagnostics = DATA.parent / "audit_word_ink_trim_fresh_diagnostics_v6.json"
            if ink_trim_diagnostics.exists():
                from word_ink_trim_fresh_diagnostics import analyze as check_ink_trim_diagnostics
                if check_ink_trim_diagnostics() != json.loads(ink_trim_diagnostics.read_text()):
                    raise AssertionError("fresh ink-trim failure provenance differs")
                print("PASS every fresh ink-trim failure, raw OCR provenance, unchanged labels and ownership exclusions", flush=True)
            ownership_evidence_path = DATA.parent / "audit_word_ownership_evidence_development_v7.json"
            if ownership_evidence_path.exists():
                from word_ownership_evidence_audit import analyze as check_ownership_evidence
                evidence = json.loads(ownership_evidence_path.read_text())
                if check_ownership_evidence(stored=evidence) != evidence:
                    raise AssertionError("automatic ownership evidence diagnostic differs")
                print("PASS ownership evidence, exact conditional supports, all prior cohorts, clipping and center-regression counterexamples", flush=True)
            component_path = DATA.parent / "audit_word_ink_components_development_v8.json"
            if component_path.exists():
                from word_ink_component_audit import analyze as check_components
                components = json.loads(component_path.read_text())
                if check_components(stored=components) != components:
                    raise AssertionError("scan-component separability diagnostic differs")
                print("PASS scan-component accounting, exact whole-component oracle errors and all frozen context links", flush=True)
    same_word_path = DATA.parent / "research_same_word_alignment_v1.json"
    if same_word_path.exists():
        from same_word_alignment import analyze as check_same_words
        same_words = json.loads(same_word_path.read_text())
        if check_same_words(same_words, resimulate=args.full) != same_words:
            raise AssertionError("color-independent same-word analysis differs")
        print("PASS color-independent same-word occurrence ledger, exact identity geometry, conditioned expectations and null scores", flush=True)
    exact_word_path = DATA.parent / "research_same_word_exact_bounds_v1.json"
    if exact_word_path.exists():
        from same_word_exact_bounds import analyze as check_exact_words
        if check_exact_words() != json.loads(exact_word_path.read_text()):
            raise AssertionError("exact same-word expectation/bound certificates differ")
        print("PASS exact-rational same-word expectations and certified decimal Hoeffding bounds", flush=True)
    layout_path = DATA.parent / "research_text_layout_comparison_v1.json"
    if layout_path.exists():
        from text_layout_comparator import analyze as check_text_layout
        if check_text_layout() != json.loads(layout_path.read_text()):
            raise AssertionError("text/order-preserving spacing pilot differs")
        print("PASS text/order-preserving six-page spacing pilot: complete deterministic layout/score replay", flush=True)
        from text_layout_review import analyze as check_layout_review, OUTPUT as layout_review_path
        if check_layout_review() != json.loads(layout_review_path.read_text()):
            raise AssertionError("text/order spacing coverage/geometry review differs")
        print("PASS independent spacing-pilot pair/packing reference, frozen-inventory cross-check and exact freedom ranges", flush=True)
    broad_path = DATA.parent / "research_broad_phrase_alignment_v1.json"
    if broad_path.exists():
        from broad_phrase_alignment import analyze as check_broad_phrases
        broad = json.loads(broad_path.read_text())
        if check_broad_phrases(broad, full=args.full) != broad:
            raise AssertionError("broad word/phrase geometry and spacing comparison differs")
        from broad_phrase_review import analyze as check_broad_review, OUTPUT as broad_review_path
        if check_broad_review() != json.loads(broad_review_path.read_text()):
            raise AssertionError("independent broad word/phrase scalar review differs")
        print("PASS broad non-color word/phrase inventory, all exact scalar pairs, spacing accounting and coverage", flush=True)
    structure_path = DATA.parent / "research_phrase_structure_controls_v1.json"
    if structure_path.exists():
        from phrase_structure_controls import analyze as check_phrase_structure
        structure = json.loads(structure_path.read_text())
        if check_phrase_structure(structure, full=args.full) != structure:
            raise AssertionError("verse/phrase-aware spacing controls differ")
        from phrase_structure_review import analyze as check_structure_review, OUTPUT as structure_review_path
        if check_structure_review() != json.loads(structure_review_path.read_text()):
            raise AssertionError("independent phrase-structure certificate audit differs")
        print("PASS verse/phrase-aware controls, independent canonical grouping, exact envelopes and invariance certificates", flush=True)
    print("Verification complete. This verifies the explicit statistical models, not causal claims.")


if __name__ == "__main__":
    main()
