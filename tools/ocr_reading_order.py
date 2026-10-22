"""Geometry-only text-row ordering with tall-region seeds and median centers.

Short observations can join an existing row but cannot shift its center or
split it. This is an experimental spatial heuristic, independent of Quran
identities and manual word locations.
"""
import argparse
from dataclasses import asdict, dataclass
import json
from statistics import median

import ocr_corpus_map as cm
import ocr_observation_map as om
from ocr_benchmark import reading_order as legacy_order


@dataclass(frozen=True)
class RowSpec:
    seed_height_fraction: float = .75
    maximum_seed_center_gap: float = 40


def center(row):
    return (row["bbox"][1] + row["bbox"][3]) / 2


def row_groups(regions, spec=RowSpec()):
    if not regions:
        return []
    cutoff = median(r["bbox"][3] - r["bbox"][1] for r in regions) * spec.seed_height_fraction
    seeds = [i for i, r in enumerate(regions) if r["bbox"][3] - r["bbox"][1] >= cutoff]
    groups = []
    for i in sorted(seeds, key=lambda i: (center(regions[i]), i)):
        if groups and center(regions[i]) - median(center(regions[j]) for j in groups[-1]["seeds"]) < spec.maximum_seed_center_gap:
            groups[-1]["seeds"].append(i)
        else:
            groups.append(dict(seeds=[i], satellites=[]))
    centers = [median(center(regions[i]) for i in g["seeds"]) for g in groups]
    for i in sorted(set(range(len(regions))) - set(seeds)):
        box = regions[i]["bbox"]
        eligible = [k for k, group in enumerate(groups) if group["seeds"]
                    and max(box[1], median(regions[j]["bbox"][1] for j in group["seeds"]))
                    < min(box[3], median(regions[j]["bbox"][3] for j in group["seeds"]))]
        if eligible:
            k = min(eligible, key=lambda k: (abs(center(regions[i]) - centers[k]), k))
            groups[k]["satellites"].append(i)
        else:
            groups.append(dict(seeds=[], satellites=[i]))
            centers.append(center(regions[i]))
    result = []
    for group, cy in zip(groups, centers):
        ids = sorted(group["seeds"] + group["satellites"], key=lambda i: (-regions[i]["bbox"][2], i))
        result.append(dict(center_y=cy, seeds=group["seeds"], satellites=group["satellites"], ordered_indices=ids))
    return sorted(result, key=lambda g: (g["center_y"], g["ordered_indices"]))


def reading_order(regions, spec=RowSpec()):
    return [regions[i] for group in row_groups(regions, spec) for i in group["ordered_indices"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", default="67,171,378,542")
    args = parser.parse_args()
    selected = set(map(int, args.pages.split(",")))
    ornaments = {p["page"]: p for p in json.loads(om.ORNAMENTS.read_text())["pages"]}
    print("spec", asdict(RowSpec()))
    for page in json.loads(cm.SOURCE.read_text())["pages"]:
        n = page["page"]
        if n not in selected:
            continue
        decision = om.observations(page["regions"], ornaments[n]["bands"])
        active = [dict(page["regions"][i], source_region=i) for i in decision["retained"]]
        old = legacy_order(active)
        new = reading_order(active)
        print("page", n, "order_changed", [r["source_region"] for r in old] != [r["source_region"] for r in new])
        for label, rows in (("legacy", old), ("seeded", new)):
            print(label, [(r["source_region"], r["text"], r["bbox"]) for r in rows
                          if n != 542 or 580 <= center(r) <= 790])


if __name__ == "__main__":
    main()
