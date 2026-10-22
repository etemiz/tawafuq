"""Colored-run pair census v3 (S13).

S6's red-box pair census (z=33) used the sparse real_boxes pool (~700
partner words). mark_identity's band runs are far richer: ~7,400 magenta
word-runs + ~3,700 crimson runs corpus-wide (median width 76px = real
words; the S5 box pool was the strict subset).

Test: cross-page pairs of runs of the same kind at the same layout cell
(y-row bin x x-bin, ABSOLUTE pixel space — no grid-id clashes) against
the S6-style null: each page's runs replaced by random word-slots drawn
from that page's real slot cloud (per-page run counts kept; tests whether
observed colored words collide across pages more than random words of the
same layout would).

Exports the top aligned cells for crop-reading.

Usage: python tools/run_pair_census.py [REPS]
"""
import json
import argparse
import sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rebuild_runs import page_bands
from audit_stats import tail_summary
from word_pair_census import pin_boxes, pin_manifest

DATA = Path(__file__).resolve().parent / "data"
NBINS = 32
ROW = 112.0       # 1680 px / 15 rows


def load_runs(src="mark_identity_semantic.json"):
    mj = json.loads((DATA / src).read_text())
    boxes = pin_boxes(src)
    runs = defaultdict(list)   # kind -> list of (page, ybin, xbin)
    seen = set()
    bands_cache = {}
    for s in mj["segments"]:
        pg = s["page"]
        if pg not in bands_cache:
            try:
                bands_cache[pg] = page_bands(pg, boxes=boxes)
            except Exception:
                bands_cache[pg] = None
        bands = bands_cache[pg]
        for r in s.get("runs", []):
            rp = r.get("page", pg)
            if rp not in bands_cache:
                bands_cache[rp] = page_bands(rp, boxes=boxes)
            bands = bands_cache[rp]
            key = (rp, r["kind"], r["band"], round(r["x0"], 1), round(r["x1"], 1))
            if key in seen:
                continue
            seen.add(key)
            if bands is None or r["band"] >= len(bands):
                continue
            y0, y1, _ = bands[r["band"]]
            yc = (y0 + y1) / 2.0
            xc = (r["x0"] + r["x1"]) / 2.0
            yb = min(14, int(yc // ROW))
            xb = min(NBINS - 1, max(0, int((xc - 26.0) / 30.0)))
            runs[r["kind"]].append((rp, yb, xb, xc))
    return runs


def pair_count(cells):
    """cells: list of (page, ybin, xbin). Cross-page same-cell pairs."""
    by_cell = defaultdict(list)
    for pg, yb, xb, _ in cells:
        by_cell[(yb, xb)].append(pg)
    tot = 0
    for cell, pgs in by_cell.items():
        n = len(pgs)
        if n < 2:
            continue
        pc = Counter(pgs)
        same = sum(m * (m - 1) // 2 for m in pc.values())
        tot += n * (n - 1) // 2 - same
    return tot


def surrogate_null(cells, reps, rng, slots_cache):
    """S6-style null: for each page, replace its runs' cells with random
    word-slot cells from that page's real slot cloud."""
    page_counts = Counter(pg for pg, _, _, _ in cells)
    for pg, cnt in page_counts.items():
        if pg not in slots_cache or len(slots_cache[pg]) < cnt:
            raise ValueError(f"page {pg}: missing/insufficient slots; cannot drop runs")
    out = []
    for _ in range(reps):
        sim_cells = []
        for pg, cnt in page_counts.items():
            sl = slots_cache.get(pg)
            pick = rng.choice(len(sl), size=cnt, replace=False)
            for cy, cx in sl[pick]:
                yb = min(14, int(cy // ROW))
                xb = min(NBINS - 1, max(0, int((cx - 26.0) / 30.0)))
                sim_cells.append((pg, yb, xb, cx))
        out.append(pair_count(sim_cells))
    return np.array(out)


def load_slots(boxes=DATA / "real_boxes"):
    cache = {}
    rb = boxes
    for f in rb.glob("page_*.json"):
        pg = int(f.stem.split("_")[1])
        d = json.loads(f.read_text())
        sl = [(s["cy"], s["cx"]) for s in d.get("slots", [])]
        if sl:
            cache[pg] = np.array(sl)
    return cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reps", type=int, nargs="?", default=1000)
    parser.add_argument("--src", default="mark_identity_semantic.json")
    parser.add_argument("--output", type=Path, default=DATA / "audit_run_pairs.json")
    args = parser.parse_args()
    reps = args.reps
    if reps < 2:
        parser.error("reps >= 2 required")
    runs = load_runs(args.src)
    slots = load_slots(pin_boxes(args.src))
    rng = np.random.default_rng(7)
    report = {}
    for kind in ("mag", "cri"):
        cells = runs[kind]
        obs = pair_count(cells)
        null = surrogate_null(cells, reps, rng, slots)
        mu, sd = null.mean(), null.std()
        z = (obs - mu) / sd if sd > 0 else None
        by_cell = defaultdict(list)
        for pg, yb, xb, xc in cells:
            by_cell[(yb, xb)].append((pg, xc))
        top = sorted(by_cell.items(),
                     key=lambda kv: -len(set(p for p, _ in kv[1])))
        top_rows = []
        for (yb, xb), lst in top[:30]:
            pgs = sorted(set(p for p, _ in lst))
            top_rows.append(dict(row=yb, xbin=xb, n=len(lst),
                                 pages=len(pgs),
                                 x_lo=round(26 + xb * 30),
                                 x_hi=round(26 + (xb + 1) * 30),
                                 y_lo=round(yb * ROW), y_hi=round((yb + 1) * ROW),
                                 pages_head=pgs[:48]))
        report[kind] = dict(n_runs=len(cells), obs=int(obs),
                            inference=tail_summary(obs, null), null_samples=null.tolist(),
                            null_mu=round(float(mu), 1),
                            null_sd=round(float(sd), 1), z=round(float(z), 1) if z is not None else None,
                            top_cells=top_rows)
        z_display = f"{z:.1f}" if z is not None else "undefined"
        print(f"== {kind}: runs={len(cells)} cross-page same-cell pairs "
              f"obs={obs} null={mu:.0f}±{sd:.0f} z={z_display}")
    report["audit"] = dict(source=args.src, seed=7, reps=reps,
                           inputs=pin_manifest(args.src),
                           version="own-page-runs-v2", caveat="Component-slot model, not word identity.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1))
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
