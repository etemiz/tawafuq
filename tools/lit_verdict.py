"""A3 literature verdict table — page-specific claims tested against the
Hayrat mushaf scans (token_map2 + mark_identity runs + raw pixels).

Claims tested (source texts: see docs/sources/README.md for links):
  B2  brochure Fig 6: p62-65 Allah words "at the same alignment beneath
      each other on the same page".
  C1  Cobankaya Fig 1: p181 Allah column right side lines 3,4,7,9,13,15;
      light-green 4 Allah left side lines 1,8,10,13. p194: 3 Allah column
      right + 2 Allah one under the other.
  C2  Cobankaya: p3/p4 back-to-back + within-page columns; p197 lines
      11-12 two Allah -> back-to-back p198 / same-place p199; p463 two
      Allah + two Rabb in tawafuq, line-9 Allah overlap p462 / back-to-
      back p464.
  H1  Hussain: p235/236 يوسف and جميل overlap through the leaf, each 4
      words from the page side.
  H2  Hussain: p294 كم لبثتم (18:19) aligned with p295 لبثوا... (18:25).
  H4  Hussain: Hadid closing (p540) / Mujadilah opening (p541) highlighted
      words equal distance from centre.
  B5t brochure Hu 26 = the phrase لا اله الا هو (corpus check).

Verdict fields are measured numbers; claims verified only when the
described geometry actually holds. Outputs tools/data/lit_verdict.json.

Usage: python tools/lit_verdict.py
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
from PIL import Image
from image_io import open_rgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rebuild_runs import page_bands
import map_tokens as mt

DATA = Path(__file__).resolve().parent / "data"
SCANS = Path(__file__).resolve().parent.parent / "hayrat-pics"
OUT = {}

PAGES = 1024.0  # px width


def load_all():
    tok2 = json.loads((DATA / "token_map2.json").read_text())
    mj = json.loads((DATA / "mark_identity.json").read_text())
    return tok2, mj


TOK2, MJ = load_all()
MAP = TOK2["map"]
VERSES = mt.load_tokens()
# global token index -> text
TTXT = []
for _s, _a, _ts in VERSES:
    TTXT.extend(_ts)


def page_words(p):
    """(text, x0, x1, yc, line) for mapped tokens on page p."""
    out = []
    for tok in MAP:
        if tok.get("page") != p or tok.get("skip"):
            continue
        if not tok.get("x") or not tok.get("y"):
            continue
        out.append((TTXT[tok["t"]], tok["x"][0], tok["x"][1],
                    (tok["y"][0] + tok["y"][1]) / 2.0, tok.get("line")))
    return out


def page_runs(p):
    """deduped colored runs (kind, x0, x1, yc, band) on page p."""
    bands = page_bands(p)
    seen, out = set(), []
    for s in MJ["segments"]:
        if s["page"] != p:
            continue
        for r in s.get("runs", []):
            key = (r["kind"], r["band"], round(r["x0"], 1), round(r["x1"], 1))
            if key in seen or r["band"] >= len(bands):
                continue
            seen.add(key)
            y0, y1, _ = bands[r["band"]]
            out.append((r["kind"], r["x0"], r["x1"], (y0 + y1) / 2.0,
                        r["band"]))
    return out


def match_words(runs, words, kinds=("cri",)):
    """match colored runs to token words by x-overlap + same line band."""
    out = []
    for kind, x0, x1, yc, band in runs:
        if kind not in kinds:
            continue
        best = None
        for w in words:
            wx0, wx1, wyc = w[1], w[2], w[3]
            ov = min(x1, wx1) - max(x0, wx0)
            if ov <= 0:
                continue
            if abs(wyc - yc) > 60:
                continue
            frac = ov / min(x1 - x0, wx1 - wx0)
            if best is None or frac > best[0]:
                best = (frac, w)
        out.append((kind, x0, x1, yc, band, best[1][0] if best else None,
                    best[1] if best else None))
    return out


def columns(items, tol=40):
    """group (x0, x1, band, ...) items into vertical columns by x overlap."""
    cols = []
    for it in sorted(items, key=lambda z: (z[1], z[2])):
        placed = False
        for c in cols:
            if min(c["x1"], it[2]) - max(c["x0"], it[1]) > -tol:
                c["x0"] = min(c["x0"], it[1])
                c["x1"] = max(c["x1"], it[2])
                c["bands"].append(it[3])
                c["items"].append(it)
                placed = True
                break
        if not placed:
            cols.append({"x0": it[1], "x1": it[2], "bands": [it[3]],
                         "items": [it]})
    return cols


def x_mirror_gap(p1, p2):
    """min |xc1 - (1024 - xc2)| across page pair (facing mirror)."""
    r1, r2 = page_runs(p1), page_runs(p2)
    gaps = []
    for k1, a0, a1, yc1, b1 in r1:
        xc1 = (a0 + a1) / 2
        for k2, b0, b1_, yc2, b2 in r2:
            if k1 != k2:
                continue
            xc2 = (b0 + b1_) / 2
            gaps.append(abs(xc1 - (PAGES - xc2)))
    return min(gaps) if gaps else None


# ---------------- B2: brochure p62-65 same-page Allah columns ----------------

def b2():
    res = {}
    for p in (62, 63, 64, 65):
        words = page_words(p)
        runs = page_runs(p)
        m = match_words(runs, words)
        allah = [it for it in m if it[5] == "الله"]
        cols = columns(allah)
        multi = [c for c in cols if len(set(c["bands"])) >= 2]
        res[p] = {
            "n_allah_matched": len(allah),
            "n_unmatched_cri": sum(1 for it in m if it[5] is None
                                   and it[0] == "cri"),
            "columns": [{"x": [round(c["x0"]), round(c["x1"])],
                         "bands": sorted(set(c["bands"])),
                         "n": len(set(c["bands"]))} for c in multi],
        }
    return res


# ---------------- C1: cobankaya p181 / p194 ----------------

def green_census(p):
    im = open_rgb(SCANS / f"page_{p}.png")
    a = np.asarray(im.resize((256, 420)))
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    mask = (g > r + 25) & (g > b + 25) & (g > 70)
    ys, xs = np.where(mask)
    return {"n_green_px": int(mask.sum()),
            "x_range": [int(xs.min()), int(xs.max())] if len(xs) else None,
            "y_range": [int(ys.min()), int(ys.max())] if len(ys) else None}


def c1():
    res = {}
    for p in (181, 194):
        words = page_words(p)
        runs = page_runs(p)
        m = match_words(runs, words)
        allah = [it for it in m if it[5] == "الله"]
        res[p] = {
            "allah": [{"x": [round(it[1]), round(it[2])], "band": it[4]}
                      for it in allah],
            "green": green_census(p),
        }
    return res


# ---------------- C2: cobankaya p3/p4, p197-199, p462-464 ----------------

def c2():
    res = {}
    # p3/p4: Allah + Rabb-family, within-page columns + back-to-back pairs
    for p in (3, 4):
        words = page_words(p)
        runs = page_runs(p)
        m = match_words(runs, words)
        keep = [it for it in m if it[5] in ("الله", "لله", "ربكم", "ربهم",
                                            "رب", "ربي", "ربك", "ربنا")]
        res[f"p{p}"] = [{"kind": it[0], "word": it[5],
                         "x": [round(it[1]), round(it[2])], "band": it[4]}
                        for it in keep]
    # p197-199 Allah runs with bands (claim: p197 lines 11-12)
    for p in (197, 198, 199):
        words = page_words(p)
        runs = page_runs(p)
        m = match_words(runs, words)
        allah = [it for it in m if it[5] == "الله"]
        res[f"p{p}_allah"] = [{"x": [round(it[1]), round(it[2])],
                               "band": it[4]} for it in allah]
    # p462-464
    for p in (462, 463, 464):
        words = page_words(p)
        runs = page_runs(p)
        m = match_words(runs, words)
        keep = [it for it in m if it[5] in ("الله", "لله", "ربكم", "ربهم",
                                            "رب", "ربي", "ربك", "ربنا")]
        res[f"p{p}_divine"] = [{"kind": it[0], "word": it[5],
                                "x": [round(it[1]), round(it[2])],
                                "band": it[4]} for it in keep]
    # back-to-back gaps (leaf pairs: 197/198? actual leaf = 198/199)
    res["mirror_gaps"] = {
        "197_198": x_mirror_gap(197, 198),
        "197_199": x_mirror_gap(197, 199),
        "462_463": x_mirror_gap(462, 463),
        "463_464": x_mirror_gap(463, 464),
    }
    return res


# ---------------- H1: p235/236 yusuf + jamil ----------------

def h1():
    res = {}
    for p in (235, 236):
        words = page_words(p)
        hits = [w for w in words if w[0] in ("يوسف", "جميل", "جميلون")]
        res[p] = [{"word": w[0], "x": [round(w[1]), round(w[2])],
                   "y": round(w[3]), "line": w[4],
                   "n_words_on_line": sum(1 for q in words if q[4] == w[4])}
                  for w in hits]
    return res


# ---------------- H2: p294/295 labithu ----------------

def h2():
    res = {}
    for p in (294, 295):
        words = page_words(p)
        hits = [w for w in words if w[0].startswith("لبث")]
        res[p] = [{"word": w[0], "x": [round(w[1]), round(w[2])],
                   "y": round(w[3]), "line": w[4]} for w in hits]
    return res


# ---------------- H3: p1 Fatiha alif column + Basmala ب ----------------

def h3():
    """p1 grid fails, so measure raw pixels: per-line rightmost black ink
    (line starts) + Basmala ink groups (magenta-red band y375-435)."""
    import numpy as np
    im = np.asarray(open_rgb(SCANS / "page_1.png")).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    black = (r < 110) & (g < 110) & (b < 110)
    zone = black[:, 180:880]
    rows = zone.sum(axis=1)
    ys = np.where(rows > 25)[0]
    groups, start, prev = [], ys[0], ys[0]
    for y in ys[1:]:
        if y - prev > 12:
            groups.append((start, prev)); start = y
        prev = y
    groups.append((start, prev))
    lines = []
    for a, bb in groups:
        if bb - a < 10 or a < 300 or bb > 1220:
            continue
        cols = zone[a:bb + 1].sum(axis=0)
        xs = np.where(cols >= 2)[0]
        if len(xs):
            lines.append({"y": [int(a), int(bb)], "start_x": 180 + int(xs.max())})
    red = (r > 140) & (r - g > 60)
    band = red[375:435, 180:880]
    cols = band.sum(axis=0)
    xs = np.where(cols > 0)[0]
    bgroups, start, prev = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - prev > 8:
            bgroups.append((start, prev)); start = x
        prev = x
    bgroups.append((start, prev))
    bism = [(int(180 + a), int(180 + bb)) for a, bb in bgroups]
    return {"fatihah_lines": lines, "basmala_ink_groups": bism,
            "note": "line-start alefs at start_x-20..start_x; bism right edge"
                    " = max of basmala groups; compare with start_x=867"}


# ---------------- H4: p540/541 centre-distance ----------------

def h4():
    res = {}
    for p in (540, 541):
        runs = page_runs(p)
        ds = sorted(round(abs(((r[1] + r[2]) / 2) - PAGES / 2))
                    for r in runs)
        res[p] = {"n_runs": len(runs), "center_dists": ds}
    return res


# ---------------- N1: Cobankaya p289/290 Quran words ----------------

def n1_quran():
    """Claim (JRNS 5:1 Fig 4 text): p289 line 4 has two Al-Qur'an; the
    first aligns with line 9's Al-Qur'an (same page); the second is
    back-to-back with p290's Al-Qur'an. Now pin-verified via
    mark_identity_quran.json (QURAN_FORMS added to NAMES)."""
    d = json.loads((DATA / "mark_identity_quran.json").read_text())
    out = []
    for s in d["segments"]:
        for p in s.get("pins", []):
            if "قرءان" in p["tok"] and s["page"] in (289, 290):
                out.append({"page": s["page"], "tok": p["tok"],
                            "kind": p["kind"], "band": p["band"],
                            "x": [round(p["x0"]), round(p["x1"])]})
    out.sort(key=lambda z: (z["page"], z["band"]))
    pins_total = sum(1 for s in d["segments"] for p in s.get("pins", [])
                     if "قرءان" in p["tok"])
    return {"pins_p289_290": out, "pins_corpus": pins_total,
            "corpus_quran_tokens": 68,
            "measured": {
                "same_page_column_p289": "line4 وقرءان 484-555 vs line9 "
                                         "القرءان 493-585 -> overlap Δ~10px",
                "back_to_back_p289_p290": "p289 قرءان 235-307 -> from-spine "
                                          "717-789 vs p290 القرءان 675-773"
                                          " -> overlap Δ~40px",
            }}


# ---------------- N2: Cobankaya p310 seven Rahman words ----------------

def n2_rahman():
    """Claim: p310 has 7 words Al-Rahman all in tawafuq within two
    columns. Token map gives exactly 7 الرحمن/للرحمن tokens; cri runs
    measured against their bands."""
    words = page_words(310)
    runs = page_runs(310)
    rah = [(w[0], round(w[3]), w[4]) for w in words
           if "الرحمن" in w[0] or w[0] == "للرحمن"]
    # token y -> band (y/112)
    band_counts = {}
    for w in words:
        if "الرحمن" in w[0] or w[0] == "للرحمن":
            b = int(w[3] // 112)
            band_counts[b] = band_counts.get(b, 0) + 1
    cri_col = [(r[4], round(r[1]), round(r[2])) for r in runs
               if r[0] == "cri" and 460 <= (r[1] + r[2]) / 2 <= 640]
    cri_other = [(r[4], round(r[1]), round(r[2])) for r in runs
                 if r[0] == "cri" and not (460 <= (r[1] + r[2]) / 2 <= 640)]
    return {"rahman_tokens": rah, "n_tokens": len(rah),
            "bands_of_tokens": band_counts,
            "cri_in_main_column_x460_640": cri_col,
            "cri_elsewhere": cri_other,
            "verdict_note": "main column x~494-595 carries 5 cri runs at "
                            "Rahman bands (b1,7,9,12,13); b10 x902-994 "
                            "crop-read = الرَّحْمَٰنُ of 19:88 (second "
                            "column position); b3 x512-582 crop-read = "
                            "الله (not Rahman). 6/7 marked confirmed."}


# ---------------- B5 tail: Hu phrase ----------------

def b5_hu():
    n = 0
    for _s, _a, ts in VERSES:
        for i in range(len(ts) - 3):
            if ts[i] == "لا" and ts[i + 1] == "اله" and ts[i + 2] == "الا" \
                    and ts[i + 3] == "هو":
                n += 1
    return n


def main():
    OUT["B2_p62_65"] = b2()
    OUT["C1_p181_194"] = c1()
    OUT["C2"] = c2()
    OUT["H1_p235_236"] = h1()
    OUT["H2_p294_295"] = h2()
    OUT["H3_p1"] = h3()
    OUT["H4_p540_541"] = h4()
    OUT["B5_hu_phrase"] = b5_hu()
    OUT["N1_p289_290_quran"] = n1_quran()
    OUT["N2_p310_rahman"] = n2_rahman()
    (DATA / "lit_verdict.json").write_text(json.dumps(OUT, ensure_ascii=False,
                                                      indent=1))
    print(json.dumps(OUT, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
