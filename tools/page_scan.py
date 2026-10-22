#!/usr/bin/env python3
"""Scan mushaf page images for colored tawafuq words.

Usage:
    .venv/bin/python tools/page_scan.py PAGES... [--all-colors] [--debug]
    .venv/bin/python tools/page_scan.py --pair A B

PAGES: numbers or ranges, e.g. 422 82-83 540,541
--pair A B: A even + B=A+1 -> facing (mirror); A odd + B=A+1 -> back-to-back (same sheet)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from image_io import open_rgb

PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"


def load_page(n):
    return np.asarray(open_rgb(PICS / f"page_{n}.png"))


def black_mask(a):
    mx = a.max(axis=2).astype(int)
    mn = a.min(axis=2).astype(int)
    return (mx < 110) & ((mx - mn) < 60)


def text_region(bm, line_gap=14, seg_gap=60, max_line_h=90):
    rowfrac = bm.mean(axis=1)
    rp = bm.sum(axis=1)
    dense = (rp >= 100) & (rowfrac < 0.5)
    if dense.sum() < 8:
        dense = (rp >= 40) & (rowfrac < 0.5)
    idx = np.where(dense)[0]
    if not len(idx):
        raise ValueError("no detectable black text rows")
    blocks = []
    s = p = idx[0]
    for r in idx[1:]:
        if r - p > line_gap:
            blocks.append((s, p))
            s = r
        p = r
    blocks.append((s, p))
    def first_line_block(blocks):
        for (b0, b1) in blocks:
            if b1 - b0 <= max_line_h:
                return b0
        return blocks[0][0]
    def last_line_block(blocks):
        for (b0, b1) in reversed(blocks):
            if b1 - b0 <= max_line_h:
                return b1
        return blocks[-1][1]
    ty0 = first_line_block(blocks)
    ty1 = last_line_block(blocks)
    cp = bm[ty0:ty1 + 1].sum(axis=0)
    colfrac = bm.mean(axis=0)
    cols = np.where((cp >= 30) & (colfrac < 0.5))[0]
    if len(cols) == 0:
        cols = np.where(cp >= 10)[0]
    xs = [cols[0]]
    runs = [[cols[0]]]
    for c in cols[1:]:
        if c - runs[-1][-1] > 40:
            runs.append([])
        runs[-1].append(c)
    big = max(runs, key=lambda r: r[-1] - r[0])
    return ty0, ty1, int(big[0]), int(big[-1]) + 1


def dilate(mask, k=6):
    """Disk dilation with zero boundary, never wrapping opposite image edges."""
    yy, xx = np.ogrid[-k:k + 1, -k:k + 1]
    return ndimage.binary_dilation(mask, structure=xx * xx + yy * yy <= k * k)


def components(a, mask_orig, mask_lab, min_px=40):
    """Four-connected label regions measured on their ORIGINAL ink pixels.

    Legacy union-find did not resolve merged roots and omitted the last
    label. Median color now uses only the component, not its bounding box.
    """
    labels, _ = ndimage.label(mask_lab)
    ys, xs = np.where(mask_orig)
    if len(ys) == 0:
        return []
    labs = labels[ys, xs]
    order = np.argsort(labs)
    ys, xs, labs = ys[order], xs[order], labs[order]
    ids, starts = np.unique(labs, return_index=True)
    ends = np.r_[starts[1:], len(labs)]
    comps = []
    for label, start, end in zip(ids, starts, ends):
        if label == 0:
            continue
        ly, lx = ys[start:end], xs[start:end]
        if len(ly) < min_px:
            continue
        c = dict(x0=int(lx.min()), x1=int(lx.max()), y0=int(ly.min()),
                 y1=int(ly.max()), npx=len(ly))
        c["cy"] = (c["y0"] + c["y1"]) / 2.0
        c["cx"] = (c["x0"] + c["x1"]) / 2.0
        sel = a[ly, lx]
        c["med"] = tuple(int(v) for v in np.median(sel, axis=0))
        comps.append(c)
    return comps


def classify(med):
    r, g, b = med
    if r > 185 and g < 45 and b < 125:
        return "red"
    if r > 180 and b > 115 and g < 175:
        return "pink"
    if r > 165 and 45 <= g < 175 and b < 95 and r - b > 90:
        return "orange"
    if g > 95 and g > r and b < g * 0.85:
        return "green"
    if b > 120 and b > r + 25 and b > g + 15:
        return "blue"
    if r > 110 and g > 85 and b < 130 and abs(r - g) < 60 and r - b > 25:
        return "gold"
    return "other"


def merge_words(comps, xgap=25, ygap=30):
    out = [dict(c) for c in comps]
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                if a is None or b is None or a["color"] != b["color"]:
                    continue
                gx = max(a["x0"] - b["x1"], b["x0"] - a["x1"])
                oy = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
                gy = max(a["y0"] - b["y1"], b["y0"] - a["y1"])
                if gx <= xgap and (oy > 0 or gy <= ygap):
                    a["x0"] = min(a["x0"], b["x0"]); a["x1"] = max(a["x1"], b["x1"])
                    a["y0"] = min(a["y0"], b["y0"]); a["y1"] = max(a["y1"], b["y1"])
                    a["npx"] += b["npx"]
                    a["cy"] = (a["y0"] + a["y1"]) / 2.0
                    a["cx"] = (a["x0"] + a["x1"]) / 2.0
                    out[j] = None
                    changed = True
        out = [c for c in out if c is not None]
    return out


def cluster_1d(objs, key, tol):
    objs = sorted(objs, key=key)
    groups = [[objs[0]]] if objs else []
    for c in objs[1:]:
        if key(c) - key(groups[-1][-1]) < tol:
            groups[-1].append(c)
        else:
            groups.append([c])
    return groups


def detect_words(n, all_colors=False):
    a = load_page(n)
    bm = black_mask(a)
    H, W = bm.shape
    ty0, ty1, bx0, bx1 = text_region(bm)
    mx = a.max(axis=2).astype(int)
    mn = a.min(axis=2).astype(int)
    colored = ((mx - mn) > 60) & (mx > 80)
    region = np.zeros(colored.shape, dtype=bool)
    region[ty0:ty1 + 1, bx0:bx1] = True
    colored &= region
    # opener basmala / decorative red bands: a row-band of dense red ink
    # is a layout element, not verse text (text lines peak ~73 red px/row)
    redrows = ((a[:, :, 0].astype(int) > 180) &
               (a[:, :, 1].astype(int) < 60) &
               (a[:, :, 2].astype(int) < 100)).sum(axis=1)
    rows = np.where(redrows >= 200)[0]
    if len(rows):
        s = p = rows[0]
        bands = []
        for y in rows[1:]:
            if y - p > 12:
                bands.append((s, p))
                s = y
            p = y
        bands.append((s, p))
        for (b0, b1) in bands:
            if b1 - b0 <= 130:
                colored[b0:b1 + 1, :] = False
    comps = components(a, colored, dilate(colored, 6), 40)
    # raw stage: drop specks (diacritic-scale noise) and big decorations
    # (medallions, frame bands) before merging
    words = []
    for c in comps:
        w = c["x1"] - c["x0"] + 1
        h = c["y1"] - c["y0"] + 1
        c["color"] = classify(c["med"])
        if w < 30 and h < 14:
            continue
        if h > 120 or w > 0.3 * W:
            continue
        words.append(c)
    if not all_colors:
        words = [c for c in words if c["color"] == "red"]
    comps = merge_words(words)
    # merged stage: recompute geometry/ink on the merged box
    for c in comps:
        c["w"] = c["x1"] - c["x0"] + 1
        c["h"] = c["y1"] - c["y0"] + 1
        px = a[c["y0"]:c["y1"] + 1, c["x0"]:c["x1"] + 1]
        m = colored[c["y0"]:c["y1"] + 1, c["x0"]:c["x1"] + 1]
        if m.any():
            c["med"] = tuple(int(v) for v in np.median(px[m], axis=0))
        c["color"] = classify(c["med"])
        nb = bm[max(0, c["y0"] - 12):min(H, c["y1"] + 12),
                max(0, c["x0"] - 45):min(W, c["x1"] + 45)]
        c["nb_black"] = int(nb.sum())
        c["near_edge"] = (c["x0"] <= 8 or c["x1"] >= W - 8 or
                          c["y0"] <= 8 or c["y1"] >= H - 8)
        c["ornament"] = (c["near_edge"] or
                         (c["w"] < 30 and c["h"] < 14) or
                         (c["w"] > 0.3 * W and c["h"] < 100) or
                         (c["color"] == "gold" and c["w"] < 80 and c["h"] < 80) or
                         (c["color"] != "red" and c["nb_black"] < 40 and c["npx"] < 450))
    return a, (ty0, ty1), (bx0, bx1), comps


def report_page(n, all_colors=False, debug=False):
    a, tyrg, blk, comps = detect_words(n, all_colors)
    keep = [c for c in comps if not c["ornament"]]
    drop = [c for c in comps if c["ornament"]]
    if debug:
        for c in sorted(comps, key=lambda c: (c["y0"], c["x0"])):
            tag = "KEEP" if not c["ornament"] else "drop"
            print(f"   {tag} x{c['x0']}-{c['x1']} y{c['y0']}-{c['y1']} "
                  f"({c['w']}x{c['h']}) npx={c['npx']} "
                  f"nb={c['nb_black']} {c['color']} med={c['med']}")
    if all_colors:
        from collections import Counter
        cnt = Counter(c["color"] for c in keep)
        print(f"page {n}: keep={len(keep)} dropped={len(drop)} colors={dict(cnt)}")
        for c in sorted(keep, key=lambda c: (c["y0"], -c["cx"])):
            print(f"   y{c['y0']}-{c['y1']} x{c['x0']}-{c['x1']} {c['color']}")
        return
    lines = cluster_1d(keep, lambda c: c["cy"], 48) if keep else []
    line_of = {}
    for i, g in enumerate(lines, 1):
        for c in g:
            c["line"] = i
    print(f"page {n}: red words={len(keep)} (dropped {len(drop)} ornaments), "
          f"text y{tyrg[0]}-{tyrg[1]} x{blk[0]}-{blk[1]}")
    for i, g in enumerate(lines, 1):
        ws = sorted(g, key=lambda c: -c["cx"])
        print(f"  line{i:>2} y~{int(g[0]['cy']):>4}: {len(ws)} @ " +
              " ".join(f"{int(c['cx'])}" for c in ws))
    cols = cluster_1d(keep, lambda c: c["cx"], 40)
    for g in cols:
        if len(g) >= 2:
            lns = sorted({c["line"] for c in g})
            print(f"  column x~{int(np.mean([c['cx'] for c in g]))}: lines {lns} ({len(g)} words)")


def text_lines(bm, ty0, ty1, bx0, bx1, gap=30):
    """Black-text line bands inside the text region (ayat berkenar ~15/page)."""
    seg = bm[ty0:ty1 + 1, bx0:bx1]
    dense = np.where(seg.sum(axis=1) >= 100)[0]
    bands = []
    for r in dense:
        if bands and r - bands[-1][1] <= gap:
            bands[-1][1] = r
        else:
            bands.append([r, r])
    return [(ty0 + b0, ty0 + b1) for b0, b1 in bands]


def line_of(cy, bands):
    for i, (b0, b1) in enumerate(bands, 1):
        if b0 - 10 <= cy <= b1 + 10:
            return i
    return 0


def match_sets(w1, w2, tol=32, same_color=True, cy_tol=18):
    """Greedy 1-1 matching: nearest |d-d| within tol, |cy-cy| <= cy_tol."""
    used = set()
    out = []
    for c1 in w1:
        best = None
        for i, c2 in enumerate(w2):
            if i in used:
                continue
            if abs(c1["cy"] - c2["cy"]) > cy_tol:
                continue
            if same_color and c1["color"] != c2["color"]:
                continue
            dd = abs(c1["d"] - c2["d"])
            if best is None or dd < best[0]:
                best = (dd, i)
        if best and best[0] <= tol:
            used.add(best[1])
            out.append((c1, w2[best[1]], best[0]))
    return out


def report_pair(a_num, b_num, tol=32, all_colors=False):
    a1, ty1, blk1, comps1 = detect_words(a_num, all_colors)
    a2, ty2, blk2, comps2 = detect_words(b_num, all_colors)
    W = a1.shape[1]
    bands1 = text_lines(black_mask(a1), ty1[0], ty1[1], blk1[0], blk1[1])
    bands2 = text_lines(black_mask(a2), ty2[0], ty2[1], blk2[0], blk2[1])
    print(f"  text lines: p{a_num}={len(bands1)} p{b_num}={len(bands2)}")
    w1 = [c for c in comps1 if not c["ornament"]]
    w2 = [c for c in comps2 if not c["ornament"]]
    relation = None
    if a_num % 2 == 0 and b_num == a_num + 1:
        relation = "facing (mirror across spine)"
    elif a_num % 2 == 1 and b_num == a_num + 1:
        relation = "back-to-back (same sheet)"
    else:
        print(f"pair {a_num}/{b_num}: not a natural leaf/spread pair")
        return
    # mirror geometry via page edges (even page: spine right, odd: spine left):
    # d = distance from the edge shared under the mirror
    d1 = [dict(c, d=(W - c["cx"]) if a_num % 2 == 0 else c["cx"],
               line=line_of(c["cy"], bands1)) for c in w1]
    d2 = [dict(c, d=c["cx"] if b_num % 2 == 1 else (W - c["cx"]),
               line=line_of(c["cy"], bands2)) for c in w2]
    print(f"pair {a_num}/{b_num}: {relation}"
          + (" [all colors]" if all_colors else " [red only]"))
    print(f"  page {a_num}: {len(w1)} words, block x{blk1[0]}-{blk1[1]}")
    print(f"  page {b_num}: {len(w2)} words, block x{blk2[0]}-{blk2[1]}")
    for same_color in (True, False) if all_colors else (True,):
        matches = match_sets(d1, d2, tol, same_color)
        tag = "same-color" if same_color else "any-color"
        print(f"  -- {tag} matching: {len(matches)} matches")
        for c1, c2, dd in matches:
            print(f"    MATCH L{c1['line']}/L{c2['line']} y~{int(c1['cy'])}: "
                  f"p{a_num} x{c1['x0']}-{c1['x1']} {c1['color']} (d={c1['d']:.0f}) "
                  f"<-> p{b_num} x{c2['x0']}-{c2['x1']} {c2['color']} (d={c2['d']:.0f}) "
                  f"|d-d|={dd:.0f}")


def parse_pages(specs):
    pages = []
    for s in specs:
        for part in s.split(","):
            if "-" in part:
                a, b = part.split("-")
                pages += list(range(int(a), int(b) + 1))
            else:
                pages.append(int(part))
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="*")
    ap.add_argument("--pair", nargs=2, type=int, metavar=("A", "B"))
    ap.add_argument("--all-colors", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    if args.pair:
        report_pair(*args.pair, all_colors=args.all_colors)
        return
    for n in parse_pages(args.pages):
        try:
            report_page(n, args.all_colors, args.debug)
        except FileNotFoundError:
            print(f"page {n}: missing", file=sys.stderr)


if __name__ == "__main__":
    main()
