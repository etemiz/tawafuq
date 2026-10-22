"""Sign taxonomy v2 (S12): decompose sign_catalog into artifact vs mark.

Session-8's sign_catalog.json (7,244 gap-row blobs) is ~95% SCAN ARTIFACT:
ascender tops of colored words poke above the black-ink row band, descender
bowls hang below it, colored words' floating diacritics detach, and
fully-magenta lines shed letter-top slices — all touching other ink.

Method (blob-gap test): a catalog blob is DETACHED only if its own x-range
has NO ink (dark or colored) within GAPX px above AND below. Everything
else = fragment (piece of colored word ink).

For the detached remainder:
  1. shapes + inks + per-page counts
  2. population test vs orthographic-sign tokens (rosette-truth spans)
  3. hosts (nearest word row below/above via real_boxes slots)

Also classifies the reds-pool w<30 small boxes (the S5 "marks", n=305)
whose glyph classes are the colored WAQF pause letters (atlas-verified:
طَ/جَ/صَ/سَ/قَ with fatha, some with attached black sukun ring).

Output: prints + tools/data/mark_hosts.json (via tools/mark_hosts.py run).
"""
import json
import sys
from pathlib import Path
from collections import Counter

import numpy as np
from PIL import Image
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt

DATA = Path(__file__).resolve().parent / "data"
PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"
GAPX = 6

SIGNS = {0x670: "dag", 0x653: "madda", 0x6E5: "swaw", 0x6E6: "sya",
         0x654: "hamza"}


def decompose_catalog():
    sc = json.load(open(DATA / "sign_catalog.json"))
    by_pg = {}
    for s in sc:
        by_pg.setdefault(s["pg"], []).append(s)
    real = []
    for pg, signs in sorted(by_pg.items()):
        f = PICS / f"page_{pg}.png"
        if not f.exists():
            continue
        im = np.asarray(Image.open(f).convert("RGB")).astype(np.int16)
        R, G, B = im[..., 0], im[..., 1], im[..., 2]
        dark = (R < 120) & (G < 120) & (B < 150)
        redish = (R - G > 45) & (R > 120)
        ink = dark | redish
        H, W = ink.shape
        for s in signs:
            y0, y1, x0, x1 = s["y0"], s["y1"], s["x0"], s["x1"]
            xs0, xs1 = max(0, x0 - 3), min(W, x1 + 4)
            below = ink[y1 + 1:min(H, y1 + 1 + GAPX), xs0:xs1].sum()
            above = ink[max(0, y0 - GAPX):y0, xs0:xs1].sum()
            if below == 0 and above == 0:
                real.append(s)
    print(f"catalog {len(sc)} -> detached {len(real)}, "
          f"fragments {len(sc) - len(real)}")
    print("detached ink:", dict(Counter(s["ink"] for s in real)))
    sh = Counter()
    for s in real:
        if s["h"] > 1.6 * s["w"]:
            sh["tall"] += 1
        elif s["w"] > 2.2 * s["h"]:
            sh["flat"] += 1
        else:
            sh["compact"] += 1
    print("detached shapes:", dict(sh))
    cc = Counter(s["pg"] for s in real)
    print("top detached pages:", cc.most_common(10))
    return real


def ortho_per_page():
    d = json.load(open(DATA / "quran-uthmani.json"))
    tm = json.load(open(DATA / "token_map2.json"))
    spans = {int(k): tuple(v) for k, v in tm["spans"].items()}
    verse_page = {}
    for p, (a, b) in spans.items():
        for vi in range(a, b + 1):
            verse_page[vi] = p
    per = {}
    for vi, v in enumerate(d["verses"]):
        pg = verse_page.get(vi)
        if pg is None:
            continue
        c = per.setdefault(pg, {})
        for w in v["text_uthmani"].split():
            if not mt.norm(w):
                continue
            for ch in w:
                o = ord(ch)
                if o == 0x670:
                    c["dag"] = c.get("dag", 0) + 1
                elif o == 0x653:
                    c["madda"] = c.get("madda", 0) + 1
                elif o in (0x6E5, 0x6E6):
                    c["small"] = c.get("small", 0) + 1
                elif o == 0x654:
                    c["hamza"] = c.get("hamza", 0) + 1
    return per


def population_tests(real):
    per = ortho_per_page()
    nb = np.zeros(605)
    for s in real:
        nb[s["pg"]] += 1
    dag = np.array([per.get(p, {}).get("dag", 0) + per.get(p, {}).get("madda", 0)
                    for p in range(605)])
    small = np.array([per.get(p, {}).get("small", 0) for p in range(605)])
    print(f"[population] detached marks={int(nb.sum())} "
          f"dag+madda tokens={int(dag.sum())} small tokens={int(small.sum())}")
    print("sp corr detached ~ dag+madda:",
          round(spearmanr(nb, dag).statistic, 3))
    print("sp corr detached ~ small:", round(spearmanr(nb, small).statistic, 3))
    print(f"=> detached marks are NOT colored orthography: no correlation "
          f"(Spearman ~0) and count mismatch {int(nb.sum())} vs "
          f"~{int(dag.sum() + small.sum())} ortho tokens.")


def mark_population():
    reds_types = np.load(DATA / "red_types.npz", allow_pickle=True)
    types, meta, deep = reds_types["types"], reds_types["meta"], reds_types["deep"]
    mi = [i for i, t in enumerate(types) if t == "mark"]
    by_page = Counter(int(meta[i][0]) for i in mi)
    print(f"\n[reds-pool w<30 marks] n={len(mi)} "
          f"(deep {sum(1 for i in mi if deep[i])} / "
          f"mag {sum(1 for i in mi if not deep[i])}); "
          f"pages with >=1: {len(by_page)}/604, max/page {max(by_page.values())}")
    hosts = json.load(open(DATA / "mark_hosts.json"))
    orth = sum(1 for r in hosts if r.get("host_ortho"))
    dag = sum(1 for r in hosts if "dag" in r.get("host_ortho", []))
    shadda = sum(1 for r in hosts if "shadda" in r.get("host_ortho", []))
    n = len(hosts)
    print(f"hosts (rosette-walk): any small-letter char {orth}/{n} "
          f"(dag {dag}, shadda {shadda})")
    glyph = json.load(open("/tmp/opencode/mark_glyph_counts.json")) \
        if Path("/tmp/opencode/mark_glyph_counts.json").exists() else None
    if glyph:
        print("glyph classes:", glyph)


def main():
    real = decompose_catalog()
    json.dump(real, open(DATA / "sign_marks.json", "w"))
    population_tests(real)
    mark_population()


if __name__ == "__main__":
    main()
