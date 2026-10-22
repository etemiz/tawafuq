"""Word-identity pair census (S15): do the SAME pinned words land at the
same layout cells across pages?

Input: mark_identity.json pins (crimson divine + magenta echo/tint, each
with page, band, x-range). Cell = (y-row 112px, x-bin 30px) absolute
pixel space, identical to run_pair_census v3.

Tests:
- obs: cross-page pairs of pins with the same (word, cell).
- null_slot: S6-style — each page's pins replaced by random word-slots
  from that page's real slot cloud (layout-chance baseline).
- null_perm: keep every pin's (page, cell), permute word labels within
  kind (habit baseline: how often would random labels coincide?).

Exports the top (word, cell) alignments for inspection.

Usage: python tools/word_pair_census.py [REPS] [SOURCE.json]
Pin identities remain hypotheses; component source follows input metadata.
"""
import json
import hashlib
import sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt
from rebuild_runs import page_bands
from pair_statistics import word_cell_pairs
from audit_stats import tail_summary

DATA = Path(__file__).resolve().parent / "data"
NBINS = 32
ROW = 112.0


def pin_boxes(src):
    obj = json.loads((DATA / src).read_text())
    return DATA / obj.get("audit", {}).get("component_source", "real_boxes")


def pin_manifest(src):
    from real_stats import input_manifest
    return dict(pins_sha256=hashlib.sha256((DATA / src).read_bytes()).hexdigest(),
                corpus_sha256=hashlib.sha256((DATA / "quran-uthmani.json").read_bytes()).hexdigest(),
                component_directory=pin_boxes(src).name, components=input_manifest(pin_boxes(src)))


def cell_of(band, x0, x1, bands):
    y0, y1, _ = bands[band]
    yc = (y0 + y1) / 2.0
    xc = (x0 + x1) / 2.0
    yb = min(14, int(yc // ROW))
    xb = min(NBINS - 1, max(0, int((xc - 26.0) / 30.0)))
    return yb, xb


def load_pins(path=None):
    verses = mt.load_tokens()
    flat = [(s, a, t) for s, a, ts in verses for t in ts]
    mj = json.loads((DATA / (path or "mark_identity_semantic.json")).read_text())
    boxes = DATA / mj.get("audit", {}).get("component_source", "real_boxes")
    pins = []
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
        for p in s.get("pins", []):
            key = (p["t"], p.get("page", pg), p["band"],
                   round(p["x0"], 1), round(p["x1"], 1))
            if key in seen:
                continue
            seen.add(key)
            rp = p.get("page", pg)
            if rp not in bands_cache:
                try:
                    bands_cache[rp] = page_bands(rp, boxes=boxes)
                except Exception:
                    bands_cache[rp] = None
            rb = bands_cache[rp]
            if rb is None or p["band"] >= len(rb):
                continue
            yb, xb = cell_of(p["band"], p["x0"], p["x1"], rb)
            if not 0 <= p["t"] < len(flat) or flat[p["t"]][2] != p["tok"]:
                raise ValueError("pin token identity does not match corpus stream")
            y0, y1, _ = rb[p["band"]]
            pins.append(dict(word=flat[p["t"]][2], kind=p["kind"],
                              t=p["t"],
                              page=rp, yb=yb, xb=xb,
                              yc=(y0 + y1) / 2, xc=(p["x0"] + p["x1"]) / 2,
                             hem=bool(p.get("hem"))))
    return pins


def pair_count(items):
    """items: list of (word, page, yb, xb). Cross-page same-(word,cell)."""
    return word_cell_pairs(items)


def slot_null(pins, reps, rng, slots):
    by_page = defaultdict(list)
    for p in pins:
        by_page[p["page"]].append(p)
    for pg, ps in by_page.items():
        if pg not in slots or len(slots[pg]) < len(ps):
            raise ValueError(f"page {pg}: missing or insufficient slots; cannot silently drop pins")
    out = np.empty(reps)
    for i in range(reps):
        sim = []
        for pg, ps in by_page.items():
            sl = slots[pg]
            pick = rng.choice(len(sl), size=len(ps), replace=False)
            for p, (cy, cx) in zip(ps, sl[pick]):
                yb = min(14, int(cy // ROW))
                xb = min(NBINS - 1, max(0, int((cx - 26.0) / 30.0)))
                sim.append((p["word"], pg, yb, xb))
        out[i] = pair_count(sim)
    return out


def perm_null(pins, reps, rng):
    """Keep (page, cell) fixed; permute word labels within kind."""
    by_kind = defaultdict(list)
    for p in pins:
        by_kind[p["kind"]].append(p)
    words_by_kind = {k: [p["word"] for p in v] for k, v in by_kind.items()}
    out = np.empty(reps)
    for i in range(reps):
        sim = []
        for k, lst in by_kind.items():
            w = words_by_kind[k]
            perm = rng.permutation(len(w))
            for p, wi in zip(lst, perm):
                sim.append((w[wi], p["page"], p["yb"], p["xb"]))
        out[i] = pair_count(sim)
    return out


def load_slots(boxes=DATA / "real_boxes"):
    cache = {}
    for f in boxes.glob("page_*.json"):
        pg = int(f.stem.split("_")[1])
        d = json.loads(f.read_text())
        sl = [(s["cy"], s["cx"]) for s in d.get("slots", [])]
        if sl:
            cache[pg] = np.array(sl)
    return cache


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    src = sys.argv[2] if len(sys.argv) > 2 else "mark_identity_semantic.json"
    out_name = src.replace(".json", "") + "_word_pairs.json"
    pins = load_pins(src)
    slots = load_slots(pin_boxes(src))
    rng = np.random.default_rng(11)
    report = {}
    for kind in ("mag", "cri"):
        sub = [p for p in pins if p["kind"] == kind]
        obs = pair_count([(p["word"], p["page"], p["yb"], p["xb"])
                          for p in sub])
        ns = slot_null(sub, reps, rng, slots)
        np_ = perm_null(sub, reps, rng)
        row = dict(n_pins=len(sub),
                   slot_inference=tail_summary(obs, ns),
                   permutation_inference=tail_summary(obs, np_),
                   slot_samples=ns.tolist(), permutation_samples=np_.tolist(),
                   obs=int(obs),
                   slot_mu=round(float(ns.mean()), 1),
                   slot_sd=round(float(ns.std()), 1),
                   slot_z=round(float((obs - ns.mean()) / ns.std()), 1)
                    if ns.std() > 0 else None,
                   perm_mu=round(float(np_.mean()), 1),
                   perm_sd=round(float(np_.std()), 1),
                   perm_z=round(float((obs - np_.mean()) / np_.std()), 1)
                    if np_.std() > 0 else None)
        report[kind] = row
        print(f"== {kind}: pins={row['n_pins']} obs={row['obs']} "
              f"slot_null={row['slot_mu']}±{row['slot_sd']} "
              f"z={row['slot_z']} | perm_null={row['perm_mu']}±"
              f"{row['perm_sd']} z={row['perm_z']}")
    # top (word, cell) alignments
    by = defaultdict(list)
    for p in pins:
        by[(p["kind"], p["word"], p["yb"], p["xb"])].append(p["page"])
    top = sorted(by.items(), key=lambda kv: -len(set(kv[1])))
    rows = []
    for (kind, w, yb, xb), pgs in top[:60]:
        rows.append(dict(kind=kind, word=w, row=yb, xbin=xb,
                         n=len(pgs), pages=len(set(pgs)),
                         x_lo=round(26 + xb * 30),
                         x_hi=round(26 + (xb + 1) * 30),
                         y_lo=round(yb * ROW), y_hi=round((yb + 1) * ROW),
                         pages_head=sorted(set(pgs))[:40]))
    report["top_alignments"] = rows
    report["audit"] = dict(source=src, seed=11, reps=reps,
                           inputs=pin_manifest(src),
                           interpretation="Conditional on selected pin labels; non-rejection "
                           "does not prove absence of word-specific structure. Global label "
                           "permutation does not preserve page/surah word frequencies.")
    (DATA / out_name).write_text(json.dumps(report))
    print("top alignments (word, row, xbin, pages):")
    for r in rows[:20]:
        print(f"  {r['kind']} {r['word']} row{r['row']} x{r['xbin']} "
              f"pages={r['pages']}")


if __name__ == "__main__":
    main()
