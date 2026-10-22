"""Post-hoc geometry-filtered corpus mapping of cached OCR, version 3.

Remove small/invalid/nonlexical observations before text alignment. Resolve
strongly overlapping detector alternatives by maximum confidence-weighted
box area, without consulting canonical text or manual locations. This is a
heuristic choice of observations, not marginalization over OCR uncertainty.
"""
import argparse
from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
from semantic_validation import DATA

ORNAMENTS = DATA / "audit_ocr_ornament_bands_v1.json"
OUTPUT = DATA / "audit_ocr_observation_map_v3.json"


@dataclass(frozen=True)
class ObservationSpec:
    minimum_height: int = 35
    overlap_numerator: int = 3
    overlap_denominator: int = 5
    maximum_component_size: int = 22


def area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def conflict(a, b, spec):
    x = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    y = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return x * y * spec.overlap_denominator >= min(area(a), area(b)) * spec.overlap_numerator


def independent_set(neighbors, weights):
    """Exact maximum-weight independent set; deterministic index-order ties."""
    @lru_cache(None)
    def solve(mask):
        if not mask:
            return 0, ()
        i = max((i for i in range(len(weights)) if mask & (1 << i)),
                key=lambda i: ((neighbors[i] & mask).bit_count(), -i))
        rest = mask & ~(1 << i)
        omit = solve(rest)
        score, ids = solve(rest & ~neighbors[i])
        take = score + weights[i], tuple(sorted((*ids, i)))
        return min((omit, take), key=lambda r: (-r[0], r[1]))
    return solve((1 << len(weights)) - 1)


def observations(regions, bands=(), spec=ObservationSpec()):
    eligible, removed = [], {}
    for i, row in enumerate(regions):
        box = row["bbox"]
        if not row.get("bbox_valid", True) or box[2] <= box[0] or box[3] <= box[1]:
            removed[i] = "invalid_box"
        elif any(lo <= (box[1] + box[3]) / 2 < hi for lo, hi in bands):
            removed[i] = "ornament"
        elif box[3] - box[1] < spec.minimum_height:
            removed[i] = "small_observation"
        elif not cm.normalized(row["text"]):
            removed[i] = "nonlexical_observation"
        else:
            eligible.append(i)
    edges = {i: set() for i in eligible}
    for k, i in enumerate(eligible):
        for j in eligible[k + 1:]:
            if conflict(regions[i]["bbox"], regions[j]["bbox"], spec):
                edges[i].add(j)
                edges[j].add(i)
    unseen, retained, components = set(eligible), [], []
    while unseen:
        seed = min(unseen)
        stack, component = [seed], set()
        while stack:
            i = stack.pop()
            if i in component:
                continue
            component.add(i)
            stack.extend(edges[i] - component)
        unseen -= component
        ids = sorted(component)
        if len(ids) == 1:
            retained.extend(ids)
            continue
        if len(ids) > spec.maximum_component_size:
            for i in ids:
                removed[i] = "unresolved_large_overlap_component"
            components.append(dict(regions=ids, retained=[], status="size_limit_abstention"))
            continue
        local = {i: k for k, i in enumerate(ids)}
        neighbors = [sum(1 << local[j] for j in edges[i]) for i in ids]
        weights = [area(regions[i]["bbox"]) * round(1_000_000 * max(0, min(1, regions[i]["confidence"])))
                   for i in ids]
        score, chosen = independent_set(neighbors, weights)
        keep = [ids[k] for k in chosen]
        retained.extend(keep)
        for i in component - set(keep):
            removed[i] = "overlapping_alternative"
        components.append(dict(regions=ids, retained=keep, status="maximum_weight_choice",
                               weights=weights, selected_weight=score))
    return dict(retained=sorted(retained), removed=[dict(source_region=i, reason=reason)
                for i, reason in sorted(removed.items())], overlap_components=components)


def map_page(page, ornament, tokens, starts, reference, index, spec, observation_spec):
    if page["image_sha256"] != ornament["image_sha256"]:
        raise AssertionError("OCR and ornament image hashes differ")
    decision = observations(page["regions"], ornament["bands"], observation_spec)
    ids = decision["retained"]
    filtered = dict(page, regions=[page["regions"][i] for i in ids])
    report = cm.map_page(filtered, tokens, starts, reference, index, spec)
    for region in report["regions"]:
        region["source_region"] = ids[region["source_region"]]
    for word in report["words"]:
        for key in ("mandatory_regions", "possible_regions"):
            word[key] = [ids[i] for i in word[key]]
    report["observation_decisions"] = decision
    return report


def analyze(selected=None, spec=cm.Spec(), observation_spec=ObservationSpec()):
    raw = json.loads(cm.SOURCE.read_text())
    ornaments = {p["page"]: p for p in json.loads(ORNAMENTS.read_text())["pages"]}
    tokens, starts, reference = cm.virtual_corpus()
    index = cm.unique_index(reference, spec.anchor_length)
    pages = []
    for page in raw["pages"]:
        if selected is not None and page["page"] not in selected:
            continue
        row = map_page(page, ornaments[page["page"]], tokens, starts, reference, index, spec, observation_spec)
        pages.append(row)
        print("page", row["page"], row["status"], "names", sum(w["is_allah_form"] and "bbox" in w for w in row["words"]), flush=True)
    return dict(version="geometry-filtered-observations-corpus-map-v3", spec=asdict(spec),
                observation_spec=asdict(observation_spec), pages=pages, summary=cm.summary(pages),
                inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (cm.SOURCE, ORNAMENTS, cm.mt.TOKENS_F)},
                caveat="Post-hoc observation filtering: small boxes/nonlexical text removed before mapping; "
                "overlap alternatives chosen by confidence-weighted area, not exact corpus spelling. "
                "Not a probabilistic OCR lattice or globally validated word-boundary model. "
                "All previous annotations and targeted failures are exposed development checks.")


def verify(path=OUTPUT, full=False):
    saved = json.loads(path.read_text())
    for p in (cm.SOURCE, ORNAMENTS, cm.mt.TOKENS_F):
        if saved["inputs"][p.name] != hashlib.sha256(p.read_bytes()).hexdigest():
            raise AssertionError("observation-map input hash differs")
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    ornaments = {p["page"]: p for p in json.loads(ORNAMENTS.read_text())["pages"]}
    tokens, starts, reference = cm.virtual_corpus()
    spec, obs_spec = cm.Spec(**saved["spec"]), ObservationSpec(**saved["observation_spec"])
    index = cm.unique_index(reference, spec.anchor_length)
    if saved["summary"] != cm.summary(saved["pages"]):
        raise AssertionError("observation-map summary differs")
    replay = {67, 83, 171, 204, 209, 231, 315, 316, 378, 457, 510, 542, 574}
    for page in saved["pages"]:
        n = page["page"]
        decision = observations(raw[n]["regions"], ornaments[n]["bands"], obs_spec)
        if decision != page["observation_decisions"] or page["image_sha256"] != raw[n]["image_sha256"]:
            raise AssertionError("observation decisions or image hashes differ")
        active = [raw[n]["regions"][i] for i in decision["retained"]]
        local = {i: k for k, i in enumerate(decision["retained"])}
        for word in page["words"]:
            if any(word[k] != tokens[word["v_id"]][k] for k in tokens[word["v_id"]]):
                raise AssertionError("canonical identity differs")
            ids = [local[i] for i in word["mandatory_regions"]]
            box = cm.support_box(active, ids) if page["status"] == "conditional_window_match" else None
            if word.get("bbox") != box:
                raise AssertionError("observation support box differs")
            if box is not None and word["surface_match"] != (
                    "".join(cm.normalized(active[i]["text"]) for i in ids) == word["normalized"]):
                raise AssertionError("observation surface-match flag differs")
        if full or n in replay:
            if map_page(raw[n], ornaments[n], tokens, starts, reference, index, spec, obs_spec) != page:
                raise AssertionError(f"p{n}: observation-map DP differs")
    print("PASS observation-map identities, geometry, input hashes, all filtering decisions and "
          + ("all" if full else "fixed review-page") + " DP replays")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", help="comma-separated development subset")
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
