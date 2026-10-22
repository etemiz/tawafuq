"""Explicit auxiliary-mark policies and exact all-ownership boundary scoring.

Separate post-exposure analysis; original annotations and predictions are inputs.
Optional pixels are only those already designated in the extent review. Color
alone never makes a letter/vowel optional, including fully colored lexical words.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from semantic_validation import DATA, ROOT
from word_boundary_extent_review import (
    LABELS, MANUAL, OUTPUT as EXTENT, analyze as extent_analyze, measure_extent,
)
from word_union_review import digest

OUTPUT = DATA / "audit_word_boundary_ownership_policy_v5.json"


def edge_support(mandatory, possible, x0=0):
    """Attainable L/R values; their Cartesian product is exactly attainable.

    Nonempty mandatory ink anchors L <= L(M) <= R(M)-1 < R. Any possible
    column at/before L(M) can establish L, and independently any possible
    column at/after R(M)-1 can establish R. Keep M and add one witness pixel
    at each selected extreme. No intervening columns need contain ink.
    """
    mandatory, possible = np.asarray(mandatory, bool), np.asarray(possible, bool)
    if (mandatory.ndim != 2 or mandatory.shape != possible.shape
            or np.any(mandatory & ~possible) or not mandatory.any()):
        raise AssertionError("need nonempty mandatory ink contained in possible ink")
    mcols = np.flatnonzero(mandatory.any(axis=0))
    pcols = np.flatnonzero(possible.any(axis=0))
    return [[x0+int(x) for x in pcols if x <= mcols[0]],
            [x0+int(x)+1 for x in pcols if x >= mcols[-1]]]


def measure_support(image, label):
    """Reconstruct the frozen explicit ownership alternatives, then cross-check."""
    partition = label["partition"]
    array = np.asarray(image.crop(partition), dtype=np.int16)
    r, g, b = array[..., 0], array[..., 1], array[..., 2]
    black = (r < 120) & (g < 120) & (b < 120)
    colored = (r > 120) & (r-g > 45)
    possible = {"black": black, "colored": colored, "mixed": black | colored}[label["ink_class"]]
    mandatory = possible.copy()
    if label.get("optional_colored"):
        mandatory &= ~colored
    for x0, y0, x1, y1 in label.get("optional_rects", []):
        mandatory[y0-partition[1]:y1-partition[1], x0-partition[0]:x1-partition[0]] = False
    support = edge_support(mandatory, possible, partition[0])
    _, bounds = measure_extent(image, label)
    if ([[min(s), max(s)] for s in support] != bounds["x_edge_ranges"]
            or int(mandatory.sum()) != bounds["mandatory_ink_pixels"]
            or int(possible.sum()-mandatory.sum()) != bounds["optional_ink_pixels"]):
        raise AssertionError("support reconstruction disagrees with frozen mask bounds")
    return support


def score_support(predicted_edges, support, tolerance):
    """Exact best/worst max-absolute edge error, including holes in support."""
    if (len(predicted_edges) != 2 or len(support) != 2 or any(not s or s != sorted(set(s)) for s in support)
            or max(support[0]) >= min(support[1]) or tolerance < 0):
        raise AssertionError("invalid attainable edge support or tolerance")
    errors = [[abs(pred-value) for value in values] for pred, values in zip(predicted_edges, support)]
    best, worst = max(min(e) for e in errors), max(max(e) for e in errors)
    return dict(best_max_abs_error=best, worst_max_abs_error=worst,
                ownership_outcome="all_pass" if worst <= tolerance else
                "all_fail" if best > tolerance else "ownership_sensitive")


def assess_policy(row, support):
    """Keep line, availability and abstention requirements for every policy."""
    if row.get("status") == "unavailable":
        return dict(status="unavailable")
    if not row["accepted"]:
        return dict(status="abstained", mandatory_only_pass=False,
                    include_optional_pass=False, all_ownership_pass=False)
    if not row["correct_line"]:
        return dict(status="wrong_line", mandatory_only_pass=False,
                    include_optional_pass=False, all_ownership_pass=False)
    if support is None:
        return dict(status="unscorable", mandatory_only_pass=None,
                    include_optional_pass=None, all_ownership_pass=None)
    edges, tolerance = [row["bbox"][0], row["bbox"][2]], row["x_edge_tolerance"]
    scored = score_support(edges, support, tolerance)
    mandatory_edges = [max(support[0]), min(support[1])]
    possible_edges = [min(support[0]), max(support[1])]
    def passes(target):
        return max(abs(p-t) for p, t in zip(edges, target)) <= tolerance
    return dict(status=scored["ownership_outcome"], **scored,
                mandatory_only_edges=mandatory_edges, include_optional_edges=possible_edges,
                mandatory_only_pass=passes(mandatory_edges), include_optional_pass=passes(possible_edges),
                all_ownership_pass=scored["ownership_outcome"] == "all_pass")


def analyze(scans=False, stored=None):
    source = json.loads(EXTENT.read_text())
    if extent_analyze() != source:
        raise AssertionError("original extent review or frozen predictions differ")
    manual = json.loads(MANUAL.read_text())
    measurements = {}
    for page in manual["pages"]:
        image = None
        if scans:
            from image_io import open_rgb
            path = ROOT / "hayrat-pics" / f'page_{page["page"]}.png'
            if digest(path) != page["image_sha256"]:
                raise AssertionError("ownership-policy scan hash differs")
            image = open_rgb(path)
        for word in page["word_samples"]:
            if "extent_review" not in word:
                continue
            key = f'{page["page"]}:{word["physical_row"]}:{word["lexical_position_rtl"]}'
            support = measure_support(image, word["extent_review"]) if scans else stored["edge_support"][key]
            if [[min(s), max(s)] for s in support] != word["ownership_bounds"]["x_edge_ranges"]:
                raise AssertionError("attainable support differs from frozen edge bounds")
            measurements[key] = support
    methods = {}
    for name, method in source["methods"].items():
        details = []
        for row in method["details"]:
            key = f'{row["page"]}:{row["physical_row"]}:{row["lexical_position_rtl"]}'
            support = measurements.get(key)
            if support is None and row.get("boundary_eligible"):
                support = [[edge] for edge in row["x_edges"]]
            # Existing partition-contact exclusions are never overridden.
            if row.get("pixels", {}).get("horizontal_partition_contact"):
                support = None
            outcome = assess_policy(row, support)
            detail = {k: row[k] for k in ("page", "physical_row", "lexical_position_rtl")}
            detail.update(form=row.get("form"), bbox=row.get("bbox"),
                          original_boundary_eligible=row.get("boundary_eligible"),
                          original_boundary_pass=row.get("horizontal_boundary_pass"), **outcome)
            details.append(detail)
            if row.get("boundary_eligible") and outcome["all_ownership_pass"] != row["horizontal_boundary_pass"]:
                raise AssertionError("policy changed a previously evaluable boundary outcome")
        available = [r for r in details if r["status"] != "unavailable"]
        summary = dict(scheduled=len(details), labelled=len(available),
                       unavailable=len(details)-len(available),
                       all_ownership_evaluable=sum(r["all_ownership_pass"] is not None for r in available),
                       nonunique_edge_support=sum(len(s[0]) > 1 or len(s[1]) > 1 for s in measurements.values()),
                       abstentions=sum(r["status"] == "abstained" for r in available),
                       unscorable=sum(r["status"] == "unscorable" for r in available),
                       ownership_sensitive=sum(r["status"] == "ownership_sensitive" for r in available),
                       accepted_all_fail=sum(r["status"] in {"all_fail", "wrong_line"} for r in available))
        for policy in ("mandatory_only", "include_optional", "all_ownership"):
            summary[policy+"_pass"] = sum(r[policy+"_pass"] is True for r in available)
        methods[name] = dict(summary=summary, previous_summary=method["summary"], details=details,
                             retained_failures=[r for r in available if r["all_ownership_pass"] is False])
    return dict(version="post-exposure-auxiliary-ownership-policy-v5",
                policy={
                    "mandatory_only": "Exclude only the explicit optional pixels in the prior review; retain mandatory letters and vowels of either ink color. This is a mask convention, not certified linguistic ownership.",
                    "include_optional": "Include all explicitly optional pixels within each reviewed partition; already excluded neighboring words and signs stay excluded.",
                    "all_ownership": "Pass only if every subset between the nonempty mandatory and possible masks passes both horizontal edges, the original line rule and unchanged 12px tolerance. Abstentions remain failures; physical unavailable slots stay separate.",
                },
                edge_support=measurements, methods=methods,
                inputs={p.name: digest(p) for p in (LABELS, MANUAL, EXTENT, Path(__file__))},
                caveat="Same-reader post-exposure policy sensitivity, conditional on the prior manual partitions and ownership masks. Full mark ownership and exact edges may remain uncertain even when every allowed edge passes. No change to OCR geometry, acceptance, center results, original annotations or fresh-validation report.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    saved = json.loads(OUTPUT.read_text()) if args.verify else None
    report = analyze(scans=args.build or args.scans, stored=saved)
    if args.verify:
        if report != saved:
            raise AssertionError("auxiliary ownership policy report differs")
        print("PASS explicit auxiliary policies, attainable edge supports, all-ownership scores and retained failures")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    for method, result in report["methods"].items():
        print(method, result["summary"])


if __name__ == "__main__":
    main()
