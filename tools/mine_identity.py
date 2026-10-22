"""Analysis + mining for mark_identity.json (S13).

Reads tools/data/mark_identity.json and reports:
1. Block resolution stats (full/amb/invalid) by color class.
2. Family occurrence verdict table (the SOLID echo-family rates).
3. Divine-name census (pinned/black/unknown per name) — the first
   ink-true corpus-wide marking rate.
4. Mining lists for the undefined-ink problem:
   a. blocks with magenta/crimson runs but NO candidates of that class
      (undefined families — crop these to read the words),
   b. amb blocks (counts mismatch),
   c. per-band colored-run histogram to size the work.

Usage: python tools/mine_identity.py [--crops N]  (N = sample crops to /tmp)
"""
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from PIL import Image

DATA = Path(__file__).resolve().parent / "data"
PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"
OUT = Path("/tmp/opencode")


def main():
    d = json.loads((DATA / "mark_identity.json").read_text())
    segs = d["segments"]
    print("== 1. block resolution")
    c = Counter(s.get("verdict") for s in segs)
    print("   ", dict(c))
    amb = [s for s in segs if s.get("verdict") == "amb"]
    print(f"    amb by class diff (toks-runs):",
          dict(Counter((s["verses"], k, s[f"n_{k}_t"] - s[f"n_{k}_r"])
                       for s in amb for k in ("cri", "mag")
                       if s.get("cls_state", {}).get(k) == "amb")))
    print("== 2. family table")
    for fam, rows in sorted(d["families"].items()):
        c = Counter(r["verdict"] for r in rows)
        n = len(rows)
        det = [f"{k}={v}" for k, v in sorted(c.items())]
        print(f"    {fam:22s} {n:4d} occ: {' '.join(det)}")
        for r in rows:
            if r["verdict"] in ("partial",):
                print(f"        PARTIAL {r['vk']} p{r.get('page')}")
    print("== 3. divine census")
    dv = d["divine"]
    c = Counter(v["verdict"] for v in dv.values())
    print("    verdicts:", dict(c))
    bytok = defaultdict(Counter)
    for v in dv.values():
        bytok[v["tok"]][v["verdict"]] += 1
    for tok, cc in sorted(bytok.items(), key=lambda x: -sum(x[1].values())):
        tot = sum(cc.values())
        print(f"    {tok:10s} {dict(cc)}  marked="
              f"{cc.get('cri',0)+cc.get('mag',0)}/{tot}")
    print("== 4. mining: undefined-family blocks (runs, no candidates)")
    undef = [s for s in segs
             if s.get("verdict") == "full" and s.get("runs")
             and ((s.get("n_mag_r", 0) and not s.get("n_mag_t"))
                  or (s.get("n_cri_r", 0) and not s.get("n_cri_t")))]
    mag_extra = Counter()
    for s in undef:
        for r in s["runs"]:
            mag_extra[r["kind"]] += 1
    print(f"    {len(undef)} blocks, runs by kind: {dict(mag_extra)}")
    pages = Counter(s["page"] for s in undef)
    print("    worst pages:", pages.most_common(12))
    # sample: print runs of first few blocks grouped by band
    for s in undef[:8]:
        print(f"    p{s['page']} {s['verses']}: "
              + " ".join(f"{r['kind']}[{r['x0']}-{r['x1']}]b{r['band']}"
                         for r in s["runs"][:8]))
    print("== 4b. amb blocks detail (first 25)")
    for s in amb[:25]:
        extra = [k for k in ("cri", "mag")
                 if s.get("cls_state", {}).get(k) == "amb"]
        print(f"    p{s['page']} {s['verses']:7s} "
              + " ".join(f"{k}:{s[f'n_{k}_t']}t/{s[f'n_{k}_r']}r" for k in extra))
    if "--crops" in sys.argv:
        n = int(sys.argv[sys.argv.index("--crops") + 1])
        OUT.mkdir(exist_ok=True)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from rebuild_runs import page_bands
        k = 0
        band_cache = {}
        for s in undef:
            page = s["page"]
            if page not in band_cache:
                try:
                    band_cache[page] = page_bands(page)
                except Exception:
                    band_cache[page] = None
            if band_cache[page] is None:
                continue
            im = Image.open(PICS / f"page_{page}.png").convert("RGB")
            for r in s["runs"][:4]:
                if k >= n * 4:
                    break
                y0, y1 = band_cache[page][r["band"]][:2]
                im.crop((max(0, r["x0"] - 50), y0, min(1024, r["x1"] + 50), y1)
                        ).save(OUT / f"mine_p{page}_b{r['band']}_{r['x0']}.png")
                k += 1
        print(f"saved {k} crops to {OUT}")


if __name__ == "__main__":
    main()
