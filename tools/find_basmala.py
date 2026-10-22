"""Candidate basmala bands from colored kashida strokes at inferred surah heads.

The legacy committed script required B<100 and 15 dense consecutive rows;
it found zero bands on the actual magenta ink and did not reproduce its
cached 111-band artifact. This version measures long horizontal strokes,
constrains them to inferred surah-head intervals, and records its inputs.
Candidates still require visual validation; the rosette map is inferred.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from image_io import open_rgb

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data"
PICS = ROOT / "hayrat-pics"


def candidate_bands(image, intervals=None, minimum_stroke=220):
    a = np.asarray(image, dtype=np.int16)
    mask = (a[:, :, 0] - a[:, :, 1] > 45) & (a[:, :, 0] > 120)
    rr = mask.sum(axis=1)
    strokes = np.zeros(len(rr), dtype=int)
    for y in np.flatnonzero(rr >= minimum_stroke):
        x = np.flatnonzero(mask[y])
        groups = np.split(x, np.flatnonzero(np.diff(x) > 3) + 1)
        strokes[y] = max(int(g[-1] - g[0] + 1) for g in groups)
    if intervals is None:
        # One strongest candidate in each separated stroke-bearing band.
        ys = np.flatnonzero(strokes >= minimum_stroke)
        groups = np.split(ys, np.flatnonzero(np.diff(ys) > 25) + 1) if len(ys) else []
        intervals = [(int(g[0]), int(g[-1]) + 1) for g in groups]
    out = []
    for lo, hi in intervals:
        lo, hi = max(0, int(lo)), min(len(rr), int(hi))
        if hi <= lo:
            continue
        peak = lo + int(strokes[lo:hi].argmax())
        if strokes[peak] < minimum_stroke:
            continue
        ink = np.flatnonzero((rr > 3) & (np.arange(len(rr)) >= max(lo, peak - 100))
                             & (np.arange(len(rr)) < min(hi, peak + 101)))
        groups = np.split(ink, np.flatnonzero(np.diff(ink) > 8) + 1)
        group = next(g for g in groups if peak in g)
        out.append((int(group[0]), int(group[-1]) + 1, int(strokes[peak])))
    return out


def page_bands(n, intervals=None):
    f = PICS / f"page_{n}.png"
    if not f.exists():
        return []
    # The decorated opening has a shorter stroke than ordinary page heads.
    return candidate_bands(open_rgb(f), intervals, minimum_stroke=120 if n == 1 else 220)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA / "basmala_bands_v3.json")
    parser.add_argument("--rosettes", type=Path, default=DATA / "rosette_map_v3" / "rosette_seq.npz")
    args = parser.parse_args()
    with np.load(args.rosettes, allow_pickle=False) as archive:
        rows = archive["meta"]
    intervals = defaultdict(list)
    for i, r in enumerate(rows):
        p, cx, cy, s, verse = r[:5]
        if verse != 1 or s == 9:
            continue
        lo = rows[i - 1, 2] + 20 if i and rows[i - 1, 0] == p else 0
        intervals[int(p)].append((lo, cy - 20))
    out = []
    for n, ranges in sorted(intervals.items()):
        out.extend(dict(page=n, y0=y0, y1=y1, kash=stroke)
                   for y0, y1, stroke in page_bands(n, ranges))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    args.output.with_name(args.output.stem + "_report.json").write_text(json.dumps(dict(
        version="head-constrained-color-stroke-v3", candidates=len(out),
        surah_head_intervals=sum(map(len, intervals.values())),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        rosettes_sha256=hashlib.sha256(args.rosettes.read_bytes()).hexdigest(),
        caveat="Candidate geometric bands at inferred surah heads, not certified text recognition."), indent=2) + "\n")
    print(f"candidate basmala bands: {len(out)} / {sum(map(len, intervals.values()))} inferred heads")
    print(out[:4], "...", out[-4:])


if __name__ == "__main__":
    main()
