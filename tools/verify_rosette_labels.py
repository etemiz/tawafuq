"""Compare an independently transcribed page with detected/inferred rosettes.

Descriptive audit only: this one page is not a population CV estimate.
"""
import argparse
import json
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent / "data"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", type=Path, default=DATA / "rosette_seq.npz")
    parser.add_argument("--detections", type=Path, default=DATA / "rosettes_v2" / "rosette_digits.json")
    parser.add_argument("--output", type=Path, default=DATA / "audit_rosette_labels.json")
    args = parser.parse_args()
    gold = json.loads((DATA / "audit_manual_rosettes.json").read_text())
    detections = json.loads(args.detections.read_text())[str(gold["page"])]
    with np.load(args.sequence, allow_pickle=False) as archive:
        meta = archive["meta"]
    seq = meta[meta[:, 0] == gold["page"]]
    rows = []
    for label in gold["labels"]:
        row = dict(label)
        nearest = min(detections, key=lambda r: (r["cx"] - label["cx"]) ** 2 + (r["cy"] - label["cy"]) ** 2)
        if np.hypot(nearest["cx"] - label["cx"], nearest["cy"] - label["cy"]) <= 12:
            row["detected_digits"] = nearest["ndig"]
            row["digit_count_matches"] = nearest["ndig"] == len(label["verse"].split(":")[1])
        else:
            row["detection"] = "missing"
        dist = np.hypot(seq[:, 1] - label["cx"], seq[:, 2] - label["cy"])
        if len(dist) and dist.min() <= 12:
            found = seq[dist.argmin()]
            row["inferred_label"] = f"{int(found[3])}:{int(found[4])}"
            row["assignment_matches"] = row["inferred_label"] == label["verse"]
        else:
            row["inferred_label"] = "no localized rosette"
            row["assignment_matches"] = False
        rows.append(row)
    out = dict(page=gold["page"], annotated=len(rows),
               detected=sum("detected_digits" in r for r in rows),
               digit_count_matches=sum(r.get("digit_count_matches", False) for r in rows),
               inferred_assignments_matching=sum(r["assignment_matches"] for r in rows),
               sequence=f"{args.sequence.parent.name}/{args.sequence.name}",
               detections=f"{args.detections.parent.name}/{args.detections.name}", rows=rows,
               caveat="One visually transcribed page; not population accuracy or CV.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
