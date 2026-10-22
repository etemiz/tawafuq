"""Anchor-count marked-token identity (S13; S15 tint-layer extension).

Prerequisite (S12 next-step 1): token identity <-> ink position for MARKED
words only, without geometry (pitfalls 12/14 killed width models).

Design (count-matched hypotheses, no width model; not independently validated):
1. Rosette segments: spans = verses ENDING on each page (non-overlapping,
   token_map2 spans = inferred rosette mapping). Between consecutive rosettes
   the token list is exact. Verses spanning a page turn are merged JOINTLY:
   the head ink sits in the previous page's trailing (carry) zone, the tail
   in the next page's first window -> one block, full tokens <-> full ink.
   Digit-misread rosettes are skipped: their verses merge into the next
   matched block (pending); off-band rosettes are dropped (block stays
   open; the next matched rosette's window starts at page top).
2. Per-band colored runs, per-column dominant color (crimson B<108 vs
   magenta B>=108; the raw split leaks anti-aliasing -> dominant wins).
   S15: runs carry ink y-extent; runs confined to the bottom of the band
   are HANGING-COLUMN pieces (Hayrat justification columns, e.g. the هُم
   of أولئك هُمُ الْخَاسِرُونَ hangs below the line).
3. Count matching per block per color class:
   n_runs == n_candidates -> forced 1:1 (reading order);
   n_runs == 0            -> no detected runs (not certified unmarked text);
   runs but no candidates -> amb (S15: honest, was silent "none");
   else                   -> ambiguous. S15: when the mag class is in
   surplus, neutral tokens ending in هم join the candidate pool (their
   suffix may be the hanging ink) — never applied to clean blocks, so
   exact matches can't be broken.

Basmala lines (fully magenta, NO tokens in the stream) are excluded via
basmala_bands.json. Black ink (headers etc.) is invisible to matching.

Default output: tools/data/mark_identity_semantic.json
  segments: per closed block (verses, counts, verdict, pins, black list)
  families: per family occurrence verdict table
  divine:   per divine-token verdict (cri-pinned / mag-pinned / black)
Validate: p154/155 pixel truths + crops.

Usage: python tools/mark_identity.py [PAGES]  (e.g. "154,155,105"; default all)
"""
import json
import argparse
import hashlib
import sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from PIL import Image
from image_io import open_rgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt
from rebuild_runs import page_bands
from rosette_map import reading_order
from divine_census import TRUE_FORMS

DATA = Path(__file__).resolve().parent / "data"
PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"

NAMES = {"الله", "لله", "رب", "ربنا", "ربكم", "ربك", "ربهم", "ربه", "ربي"} | TRUE_FORMS
HAMD = {"الحمد", "والحمد"}

# S13 semantic families (rare phrase windows; exact-count matching is
# ink-true for these). S15 tint claims (frequent single words) live in
# TINT_FAMILIES: with them ON, count matching in (0,k) blocks assigns
# runs to claimed words ARBITRARILY -> large-scale false pins (e.g. من
# "marked" 1,545x vs ~200 atlas-verified runs). Use --semantic for the
# honest S13 pin set; the tint census must be ink-first (mine_surplus).
SEMANTIC_FAMILIES = {
    "la_ilaha_illa_huwa": (["لا", "اله", "الا", "هو"], "mag"),
    "unzilat_surah": (["واذا", "ما", "انزلت", "سوره"], "mag"),
    "rabb_alarsh": (["رب", "العرش", "العظيم"], "mag"),
    "imanan": (["ايمنا"], "mag"),
    "aljanna_bima_kuntum": (["الجنه", "بما", "كنتم"], "mag"),
    "alaikum_wabima": (["عليكم", "بما", "كنتم"], "mag"),
    "janna_inherit_7_43": (["الجنه", "اورثتموها", "بما", "كنتم"], "mag"),
    "as7ab_janna_7_44": (["اصحب", "الجنه"], "mag"),
    "as7ab_nar_7_44": (["اصحب", "النار"], "mag"),
    "nada_as7ab": (["ونادي"], "mag"),   # strips mark the family head too
    "rahman_refrain": (["فباي", "ءالاء", "ربكما", "تكذبان"], "mag"),
    # mix windows carry per-token color specs (colspec = list)
    "hamdallah": (["الحمد", "لله"], ["cri", "mag"]),
    "hamdallah_wa": (["والحمد", "لله"], ["cri", "mag"]),
    "wada_allah": (["وعد", "الله"], ["mag", "cri"]),
}

TINT_FAMILIES = {
    # S15 frequent-word tint layer (verified via surplus atlas reads).
    "inna_an": (["ان"], "mag"),
    "illa": (["الا"], "mag"),
    "alladhina": (["الذين"], "mag"),
    "alladhi": (["الذي"], "mag"),
    "hum": (["هم"], "mag"),
    "lahu": (["له"], "mag"),
    "lahum": (["لهم"], "mag"),
    "lakum": (["لكم"], "mag"),
    "qala": (["قال"], "mag"),
    "qalu": (["قالوا"], "mag"),
    "kana": (["كان"], "mag"),
    "kanu": (["كانوا"], "mag"),
    "fi": (["في"], "mag"),
    "fiha": (["فيها"], "mag"),
    "min": (["من"], "mag"),
    "minhum": (["منهم"], "mag"),
    "an_an": (["عن"], "mag"),
    "ala": (["علي"], "mag"),
    "hatta": (["حتي"], "mag"),
    "ma": (["ما"], "mag"),
    "huwa": (["هو"], "mag"),
    "aw": (["او"], "mag"),
    "thalika": (["ذلك"], "mag"),
    "hatha": (["هذا"], "mag"),
    "kuntum": (["كنتم"], "mag"),
    "qul": (["قل"], "mag"),
    "fiha_alard": (["الارض"], "mag"),
    "aya_h": (["ءايه"], "mag"),
    "aya": (["ايه"], "mag"),
    "ayat": (["الايت"], "mag"),
    "haulai": (["هؤلاء"], "mag"),
    "muminin": (["مؤمنين"], "mag"),
    # challenge refrain ان كنتم (pixel truth 2:31: ان black, كنتم mag);
    # must come AFTER inna_an so the override re-neutralizes ان here
    "kuntum_ch": (["ان", "كنتم"], [None, "mag"]),
    # Moses-staff sign family (7:107 pixel truth: فاذا هي ثعبان all mag)
    "thu_ban": (["فاذا", "هي", "ثعبان"], "mag"),
}

FAMILIES = dict(SEMANTIC_FAMILIES)
FAMILIES.update(TINT_FAMILIES)

# family-window offsets known BLACK from pixel truth (S11): excluded from
# candidacy so count matching stays exact
OVERRIDES = {
    "janna_inherit_7_43": {1: None},  # اورثتموها black in 7:43
    "kuntum_ch": {0: None},           # ان black in the challenge refrain
}

GAP = 12           # colored column gap -> separate runs (word-ish)
MIN_LEN = 25       # min run width (kills 13-17px colored pause-mark glyphs)
MIN_NPX = 60       # min colored px in run
MIN_COL = 10       # strong-column threshold (word strokes)
MIN_STRONG = 4     # min strong columns in a run
ROSE_M = 46        # rosette disk clearance for windows/trailing zones


def band_col_runs(im, y0, y1):
    """Colored runs of a band slice. Runs split at column gaps (GAP),
    color = per-run pixel dominance (S5 box rule: crimson B<108 core vs
    magenta B>=108; AA halos never outvote the core within a word).
    Returns [(x0, x1, kind, npx, ymin, ymax)] in x-ASC order (ink y-extent
    absolute; ymin/ymax needed for the hanging-column hem rule, S15).
    kind: cri|mag."""
    band = np.asarray(im)[y0:y1, :, :]
    if band.shape[0] == 0:
        return []
    r = band[..., 0].astype(int)
    g = band[..., 1].astype(int)
    b = band[..., 2].astype(int)
    redish = (r - g > 45) & (r > 120)
    cc = (redish & (b < 108)).sum(axis=0)
    mc = (redish & (b >= 108)).sum(axis=0)
    ac = cc + mc
    runs = []
    x = 0
    W = len(ac)
    while x < W:
        if ac[x] >= 3:
            x0 = x
            gap = 0
            while x < W:
                if ac[x] >= 1:
                    gap = 0
                else:
                    gap += 1
                    if gap > GAP:
                        break
                x += 1
            runs.append((x0, x - gap))
        else:
            x += 1
    out = []
    for x0, x1 in runs:
        if x1 - x0 < MIN_LEN:
            continue
        npx = int(ac[x0:x1 + 1].sum())
        if npx < MIN_NPX:
            continue
        col = ac[x0:x1 + 1]
        if int((col >= MIN_COL).sum()) < MIN_STRONG:
            continue
        kind = "cri" if cc[x0:x1 + 1].sum() > mc[x0:x1 + 1].sum() else "mag"
        # pause-mark shape filter (S15): big pause glyphs (قَفْ ~28px,
        # ~220px) leak past MIN_LEN; real words of that width (ما) carry
        # >=400px. Runs are checked BEFORE the y-extent filter.
        if (x1 - x0) < 34 and npx < 320:
            continue
        ys = np.where(redish[:, x0:x1 + 1].any(axis=1))[0]
        ymin = int(ys.min()) + y0 if len(ys) else y0
        ymax = int(ys.max()) + y0 if len(ys) else y0
        out.append((int(x0), int(x1), kind, npx, ymin, ymax))
    return out


def load_rosettes(path=DATA / "rosette_seq.npz"):
    d = np.load(path, allow_pickle=False)["meta"]
    by_page = {}
    for row in d:
        pg, cx, cy, s, v = int(row[0]), row[1], row[2], int(row[3]), int(row[4])
        if cx < 0 or s <= 0:
            continue
        by_page.setdefault(pg, []).append(dict(cy=cy, cx=cx, s=s, v=v))
    for pg in by_page:
        by_page[pg] = [(r["cy"], -r["cx"], r["cx"], r["s"], r["v"])
                       for r in reading_order(by_page[pg])]
    return by_page


def band_of_cy(cy, bands):
    for i, (y0, y1, _st) in enumerate(bands):
        if y0 <= cy <= y1:
            return i
    best, bd = None, 1e9
    for i, (y0, y1, _st) in enumerate(bands):
        c = (y0 + y1) / 2
        d = abs(cy - c)
        if d < bd:
            bd, best = d, i
    return best if bd <= 60 else None


def window_runs(bcr, win, page, bands):
    """Colored runs inside window entries [(bi, xlo, xhi)], reading order
    (band asc, x desc). Runs clipped to window. Each run carries page
    (carried blocks mix pages; S14), its band's y-range and strip flag
    (hem rule + merge rule)."""
    out = []
    for (bi, xlo, xhi) in win:
        by0, by1, st = bands[bi]
        grp = []
        for (x0, x1, kind, npx, ymin, ymax) in bcr.get(bi, []):
            if x1 < xlo or x0 > xhi:
                continue
            c0, c1 = max(x0, xlo), min(x1, xhi)
            if c1 - c0 < MIN_LEN:
                continue
            grp.append(dict(x0=c0, x1=c1, kind=kind, npx=npx, band=bi,
                            page=page, ymin=ymin, ymax=ymax,
                            band_y0=by0, band_h=by1 - by0,
                            strip=bool(st)))
        grp.sort(key=lambda r: -r["x0"])  # x desc = reading order
        out.extend(grp)
    return out


def is_hanging(run):
    """Hanging-column piece: ink confined to the bottom of the band
    (measured: hanging hem ink starts ~0.75 of band height; inline words
    start ~0.25). S15."""
    return (run["ymin"] - run["band_y0"]) > 0.55 * run["band_h"]


def merge_split_runs(runs, target_n, max_gap=30):
    """S15: try to reconcile a surplus class by merging adjacent same-page
    same-band same-color runs (kashida/ornamental splits). Greedy: merge
    the closest pair while len > target_n; only non-strip bands. Returns
    merged run list or None if target unreachable."""
    runs = [dict(r) for r in runs]
    if len(runs) < target_n:
        return None
    while len(runs) > target_n:
        best = None
        for i in range(len(runs) - 1):
            a, b = runs[i], runs[i + 1]
            if a["page"] != b["page"] or a["band"] != b["band"]:
                continue
            if a["strip"] or b["strip"]:
                continue
            gap = a["x0"] - b["x1"]  # a is right of b (reading order)
            if 0 <= gap <= max_gap:
                if best is None or gap < best[0]:
                    best = (gap, i)
        if best is None:
            return None
        _, i = best
        a, b = runs[i], runs[i + 1]
        runs[i] = dict(a, x0=min(a["x0"], b["x0"]), x1=max(a["x1"], b["x1"]),
                       ymin=min(a["ymin"], b["ymin"]), ymax=max(a["ymax"], b["ymax"]),
                       npx=a["npx"] + b["npx"], merged=True)
        del runs[i + 1]
    return runs


def match_class(toks, runs, page, hem_toks=None):
    """Count matching for one color class.
    toks: candidate token indices (order); runs: run dicts (reading order).
    hem_toks: neutral tokens ending in هم (S15) — only pooled when the
    class is in surplus, so clean matches can never be broken by them.
    Returns (verdict, pins, unlocated_toks). Missing runs do not certify black ink."""
    pool = list(toks)
    hem_set = set()
    if hem_toks and len(runs) > len(toks):
        pool = sorted(toks + hem_toks)
        hem_set = set(hem_toks)
    if not pool:
        if not runs:
            return "none", [], []
        return "amb", [], []  # runs with no candidates: honest surplus
    if not runs:
        return "no_detected_run", [], pool
    if len(runs) != len(pool):
        merged = merge_split_runs(runs, len(pool))
        if merged is None or len(merged) != len(pool):
            return "amb", [], []
        runs = merged
    pins = []
    for t, r in zip(pool, runs):
        s, a, tok = flat[t]
        pins.append(dict(t=t, s=s, a=a, tok=tok,
                         page=r.get("page", page),
                         x0=r["x0"], x1=r["x1"], kind=r["kind"],
                         band=r["band"], npx=r["npx"],
                         hem=t in hem_set, merged=r.get("merged", False)))
    return "full", pins, []


QURAN_FORMS = {"القرءان", "والقرءان", "بقرءان", "قرءان", "قرءانا",
               "وقرءان", "وقرءانا", "بالقرءان", "لقرءان", "وقرءانه",
               "قرءانه"}


def main():
    global flat, NAMES, FAMILIES, OVERRIDES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pages", nargs="?", help="comma-separated page subset")
    parser.add_argument("--semantic", action="store_true", help="semantic candidates (now default)")
    parser.add_argument("--quran", action="store_true")
    parser.add_argument("--tint-exploration", action="store_true",
                        help="legacy broad tint candidate set; identities are unvalidated")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verse-map", type=Path, default=DATA / "page_verse_map.json")
    parser.add_argument("--rosettes", type=Path, default=DATA / "rosette_seq.npz")
    parser.add_argument("--boxes", type=Path, default=DATA / "real_boxes")
    parser.add_argument("--basmala", type=Path, default=DATA / "basmala_bands.json")
    args = parser.parse_args()
    if args.semantic and args.tint_exploration:
        parser.error("choose semantic or tint-exploration candidates")
    only = {int(x) for x in args.pages.split(",")} if args.pages else None
    semantic = not args.tint_exploration
    quran = args.quran
    if quran:
        NAMES = NAMES | QURAN_FORMS
    if semantic:
        FAMILIES = dict(SEMANTIC_FAMILIES)
        OVERRIDES = {"janna_inherit_7_43": {1: None}}
    verses = mt.load_tokens()
    cumtok = [0]
    for s, a, toks in verses:
        cumtok.append(cumtok[-1] + len(toks))
    flat = [(s, a, t) for s, a, ts in verses for t in ts]
    ntok = len(flat)
    # expected ink color per token from family windows
    exp = [None] * ntok
    fam_at = defaultdict(set)
    for fam, (win, col) in FAMILIES.items():
        m = len(win)
        for i in range(ntok - m + 1):
            if [t for _, _, t in flat[i:i + m]] == win:
                for k in range(i, i + m):
                    if isinstance(col, list):
                        kind = col[k - i]
                    else:
                        kind = col
                    exp[k] = kind
                    fam_at[k].add(fam)
                    if k - i in OVERRIDES.get(fam, {}):
                        exp[k] = OVERRIDES[fam][k - i]
    for i, (_, _, t) in enumerate(flat):
        if exp[i] is None and (t in NAMES or t in HAMD):
            exp[i] = "cri"
    # family occurrence token ranges
    fam_occ = defaultdict(list)
    for fam, (win, _col) in FAMILIES.items():
        m = len(win)
        for i in range(ntok - m + 1):
            if [t for _, _, t in flat[i:i + m]] == win:
                fam_occ[fam].append((i, i + m - 1))
    # Rahman refrain verses: whole-line magenta, ornamental over-split
    # runs; identity = the whole verse (S9/S12 pixel truth)
    refrain_set = {tuple(range(i0, i0 + 4))
                   for (i0, _i1) in fam_occ.get("rahman_refrain", [])}
    vm = json.loads(args.verse_map.read_text())
    v_index = {(verses[i][0], verses[i][1]): i for i in range(len(verses))}
    spans = []
    for p in range(604):
        e = vm.get(str(p + 1))
        if e is None:
            spans.append(None)
            continue
        f = tuple(int(x) for x in e["first"].split(":"))
        l = tuple(int(x) for x in e["last"].split(":"))
        spans.append((v_index[f], v_index[l]) if f in v_index and l in v_index
                     else None)
    roses = load_rosettes(args.rosettes)
    basm = defaultdict(list)
    for e in json.loads(args.basmala.read_text()):
        basm[e["page"]].append((e["y0"], e["y1"]))
    segs_out = []
    open_toks, open_runs, open_valid = [], [], True
    n_pins = n_unlocated = n_amb = n_refrain = 0
    for p in range(604):
        if only and (p + 1) not in only:
            open_toks, open_runs, open_valid = [], [], False
            continue
        sp = spans[p]
        page = p + 1
        f = PICS / f"page_{page}.png"
        if sp is None or not f.exists():
            open_toks, open_runs, open_valid = [], [], False
            continue
        s0, s1 = sp
        vtoks = [(verses[i][0], verses[i][1], i, verses[i][2])
                 for i in range(s0, s1 + 1)]
        try:
            bands = page_bands(page, boxes=args.boxes)
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            bands = None
        if bands is None:
            open_toks, open_runs, open_valid = [], [], False
            continue
        im = open_rgb(f)
        bcr = {}
        for bi, (y0, y1, _st) in enumerate(bands):
            bcr[bi] = band_col_runs(im, y0, y1)
        excl = set()
        for bi, (y0, y1, _st) in enumerate(bands):
            for (by0, by1) in basm.get(page, []):
                if not (y1 < by0 or y0 > by1):
                    excl.add(bi)
        # The legacy code constructed excl but never applied it, so complete
        # unencoded basmala lines could enter verse-level matching as text.
        for bi in excl:
            bcr[bi] = []
        ros = []
        for (cy, _nc, cx, s, v) in roses.get(page, []):
            ros.append((band_of_cy(cy, bands), cx, s, v))
        # iterate expected verses, closing blocks at matched rosettes.
        # S15 fix: search ros[ri:] per verse; on miss DO NOT advance ri
        # (the old code exhausted the pointer on the first missing
        # rosette, merging every later verse of the page into one
        # mega-block — Rahman pages 530-537 collapsed this way).
        ri = 0
        prev = None
        cur_toks, cur_runs = list(open_toks), list(open_runs)
        cur_valid = open_valid
        open_toks, open_runs = [], []
        closed = []
        for (s, a, vi, toks) in vtoks:
            bt = cur_toks + [cumtok[vi] + k for k in range(len(toks))]
            cur_toks = []
            j = ri
            while j < len(ros) and (ros[j][2], ros[j][3]) != (s, a):
                j += 1
            if j >= len(ros):
                cur_toks, cur_runs = bt, cur_runs  # stays open (no rosette)
                continue
            bi, cx, _s, _v = ros[j]
            ri = j + 1
            if bi is None:
                cur_toks = bt  # drop rosette, block stays open
                continue
            if prev is None:
                win = [(i, 0, 1023) for i in range(bi)]
                win.append((bi, cx + ROSE_M, 1023))
            else:
                pbi, pcx = prev
                win = []
                if pbi == bi:
                    win.append((pbi, cx + ROSE_M, pcx - ROSE_M))
                else:
                    win.append((pbi, 0, pcx - ROSE_M))
                    for i in range(pbi + 1, bi):
                        win.append((i, 0, 1023))
                    win.append((bi, cx + ROSE_M, 1023))
            cur_runs = cur_runs + window_runs(bcr, win, page, bands)
            closed.append(dict(page=page, s=s, a=a, toks=bt, runs=cur_runs,
                               valid=cur_valid, bi=bi, cx=cx))
            cur_runs = []
            cur_valid = True  # boundary is now a real rosette
            prev = (bi, cx)
        # trailing zone after last matched rosette (whole page if none)
        if prev is not None:
            bi, cx = prev
            zone = [(i, 0, 1023) for i in range(bi + 1, len(bands))]
            zone.insert(0, (bi, 0, cx - ROSE_M))
        else:
            zone = [(i, 0, 1023) for i in range(len(bands))]
        zone_runs = window_runs(bcr, zone, page, bands)
        open_toks, open_runs, open_valid = cur_toks, cur_runs + zone_runs, True
        # ---- count matching for closed blocks ----
        for sg in closed:
            rec = dict(page=page, verses=f"{sg['s']}:{sg['a']}",
                       n_toks=len(sg["toks"]), valid=sg["valid"])
            if not sg["valid"]:
                rec["verdict"] = "invalid"
                segs_out.append(rec)
                n_amb += 1
                continue
            cri_r = [r for r in sg["runs"] if r["kind"] == "cri"]
            mag_r = [r for r in sg["runs"] if r["kind"] == "mag"]
            cri_t = [t for t in sg["toks"] if exp[t] == "cri"]
            mag_t = [t for t in sg["toks"] if exp[t] == "mag"]
            rec["n_cri_t"], rec["n_cri_r"] = len(cri_t), len(cri_r)
            rec["n_mag_t"], rec["n_mag_r"] = len(mag_t), len(mag_r)
            cls_state = {}
            rec["pins"], rec["black"], rec["hem_pins"], rec["unlocated"] = [], [], [], []
            for cls, toks_, runs_ in (("cri", cri_t, cri_r),
                                      ("mag", mag_t, mag_r)):
                hem_t = None
                if cls == "mag":
                    hem_t = [t for t in sg["toks"]
                             if flat[t][2].endswith("هم") and exp[t] is None
                             and t not in mag_t]
                v, pins_, black_ = match_class(toks_, runs_, page, hem_t)
                cls_state[cls] = v
                rec["pins"] += pins_
                rec["hem_pins"] += [p for p in pins_ if p.get("hem")]
                rec["unlocated"] += black_
                n_pins += len(pins_)
                n_unlocated += len(black_)
            if (tuple(sg["toks"]) in refrain_set and len(mag_t) == 4
                    and len(mag_r) >= 4):
                cls_state["mag"] = "full"
                n_refrain += 1
            rec["cls_state"] = cls_state
            rec["toks"] = sg["toks"]
            rec["runs"] = [dict(kind=r["kind"], x0=r["x0"], x1=r["x1"],
                                band=r["band"], npx=r["npx"],
                                page=r.get("page", page))
                           for r in sg["runs"]]
            rec["verdict"] = "amb" if "amb" in cls_state.values() else "full"
            if rec["verdict"] == "amb":
                n_amb += 1
            segs_out.append(rec)
    # corpus tail: close the final open block (S13 next-step 3)
    if open_toks and open_valid:
        n_ct = sum(1 for t in open_toks if exp[t] == "cri")
        n_mt = sum(1 for t in open_toks if exp[t] == "mag")
        n_cr = sum(1 for r in open_runs if r["kind"] == "cri")
        n_mr = sum(1 for r in open_runs if r["kind"] == "mag")

        def tail_state(n_t, n_r):
            if n_t == 0 and n_r == 0:
                return "none"
            if n_t == 0 or n_r == 0:
                return "amb" if n_t == 0 and n_r else "no_detected_run"
            return "amb"
        rec = dict(page=None, verses="tail", n_toks=len(open_toks),
                   valid=True, n_cri_t=n_ct, n_cri_r=n_cr,
                   n_mag_t=n_mt, n_mag_r=n_mr,
                   cls_state={"cri": tail_state(n_ct, n_cr),
                              "mag": tail_state(n_mt, n_mr)},
                   pins=[], black=[], hem_pins=[], toks=list(open_toks),
                   runs=[dict(kind=r["kind"], x0=r["x0"], x1=r["x1"],
                              band=r["band"], npx=r["npx"],
                              page=r.get("page")) for r in open_runs],
                   verdict="amb")
        segs_out.append(rec)
        n_amb += 1
    # divine verdict table
    div_rows = {}
    for rec in segs_out:
        for pin in rec.get("pins", []):
            div_rows[pin["t"]] = dict(verdict=pin["kind"], page=pin["page"],
                                      x0=pin["x0"], x1=pin["x1"],
                                      band=pin["band"], s=pin["s"],
                                      a=pin["a"], tok=pin["tok"])
        for t in rec.get("black", []):
            s, a, tok = flat[t]
            div_rows[t] = dict(verdict="black", s=s, a=a, tok=tok)
        for t in rec.get("unlocated", []):
            s, a, tok = flat[t]
            div_rows[t] = dict(verdict="no_detected_run", s=s, a=a, tok=tok)
    # family verdict table (windows are always inside one block)
    block_of_t = {}
    for rec in segs_out:
        for t in rec.get("toks", []):
            block_of_t[t] = rec
    fam_rows = defaultdict(list)
    for fam, occs in fam_occ.items():
        for (i0, i1) in occs:
            ts = list(range(i0, i1 + 1))
            if any(t not in block_of_t for t in ts):
                fam_rows[fam].append(dict(vk=f"{flat[i0][0]}:{flat[i0][1]}",
                                          verdict="cross"))
                continue
            rec = block_of_t[ts[0]]
            if any(block_of_t[t] is not rec for t in ts):
                fam_rows[fam].append(dict(vk=f"{flat[i0][0]}:{flat[i0][1]}", verdict="cross"))
                continue
            if rec.get("verdict") in ("amb", "invalid"):
                verdict = "unknown"
            else:
                st = []
                for t in ts:
                    cls = exp[t]
                    if cls is None:
                        st.append("neu")
                    elif rec.get("cls_state", {}).get(cls) == "full":
                        st.append("mark")
                    else:
                        st.append("unknown")
                if all(x in ("mark", "neu") for x in st) and "mark" in st:
                    verdict = "marked"
                else:
                    verdict = "unknown"
            fam_rows[fam].append(dict(vk=f"{flat[i0][0]}:{flat[i0][1]}",
                                      page=rec.get("page"),
                                      verdict=verdict))
    out = dict(segments=segs_out,
               families=dict(fam_rows),
               divine=div_rows,
               audit=dict(mode="semantic" if semantic else "tint-exploration",
                           version="countmatch-v4-prefixes-no-deficit-no-black-inference",
                          pin_status="Count-matched identity hypotheses, not independently verified labels.",
                          component_source=args.boxes.name,
                          verse_map_source=f"{args.verse_map.parent.name}/{args.verse_map.name}",
                          rosette_source=f"{args.rosettes.parent.name}/{args.rosettes.name}",
                          basmala_source=args.basmala.name,
                          pages=sorted(only) if only else "all",
                          input_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in (args.verse_map, args.rosettes, args.basmala)},
                          source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    outname = "mark_identity.json"
    if quran:
        outname = "mark_identity_quran.json"
    elif semantic:
        outname = "mark_identity_semantic.json"
    target = args.output or DATA / outname
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out))
    print(f"segments={len(segs_out)} pins={n_pins} unlocated={n_unlocated} "
          f"amb={n_amb} refrain={n_refrain}")
    for fam, rows in sorted(fam_rows.items()):
        c = Counter(r["verdict"] for r in rows)
        print(f"  {fam}: {len(rows)} occ {dict(c)}")


if __name__ == "__main__":
    main()
