import json, re, sys
import numpy as np

DATA = "tools/data/quran-uthmani.json"
P_PAGES, L_LINES = 604, 15
X_RIGHT, X_LEFT = 1000.0, 26.0
WIDTH = X_RIGHT - X_LEFT
GAP = 6.0
TOL = 30.0
NB = int(round(WIDTH / TOL))

DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u0653-\u0655\u0640]")

def strip(t):
    t = DIAC.sub("", t)
    return (t.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا")
             .replace("آ", "ا").replace("ى", "ي").replace("ة", "ه"))

def load():
    d = json.load(open(DATA))
    out = []
    for v in d["verses"]:
        s, a = v["verse_key"].split(":")
        out.append((int(s), [strip(t) for t in v["text_uthmani"].split()]))
    return out

def pack(verses, cap, char_w):
    prepared = []
    for s, toks in verses:
        ws = [10.0 + char_w * len(t) for t in toks]
        prepared.append((toks, ws))
    pages, cur, curw = [], [], 0.0
    for toks, ws in prepared:
        w = sum(ws) + GAP * len(ws)
        if cur and curw + w > cap:
            pages.append(cur)
            cur, curw = [], 0.0
        cur.append((toks, ws))
        curw += w
    if cur:
        pages.append(cur)
    return pages

def layout(pages):
    slots = []
    for pi, page in enumerate(pages):
        words = [(t, w) for toks, ws in page for t, w in zip(toks, ws)]
        total = sum(w for _, w in words)
        target = total / L_LINES
        lines, cur, curw = [], [], 0.0
        for t, w in words:
            cur.append((t, w))
            curw += w
            if curw >= target and len(lines) < L_LINES - 1:
                lines.append(cur)
                cur, curw = [], 0.0
        if cur:
            if len(lines) < L_LINES:
                lines.append(cur)
            else:
                lines[-1].extend(cur)
        for li, ln in enumerate(lines):
            wsum = sum(w for _, w in ln)
            slack = max(0.0, WIDTH - wsum - GAP * (len(ln) - 1))
            g = slack / max(1, len(ln) - 1)
            x = X_RIGHT
            for t, w in ln:
                x -= w / 2.0
                slots.append((pi, li, x, t))
                x -= w / 2.0 + GAP + g
    return slots

def col_stat(pg, xx):
    key = pg * NB + np.clip(((xx - X_LEFT) / TOL).astype(int), 0, NB - 1)
    cnt = np.bincount(key, minlength=P_PAGES * NB).reshape(P_PAGES, NB)
    per = cnt.max(axis=1)
    return int(per.max()), per

def pair_matches(pg, ln, xx, facing):
    d = np.where(pg % 2 == 0, WIDTH - xx, xx)
    pair = pg // 2 if facing else (pg - 1) // 2
    ok = (pair >= 0) & (pair < P_PAGES // 2)
    key = ((pair[ok] * L_LINES + ln[ok]) * NB + np.clip((d[ok] / TOL).astype(int), 0, NB - 1))
    ev = (pg[ok] % 2 == 0)
    size = (P_PAGES // 2) * L_LINES * NB
    ce = np.bincount(key[ev], minlength=size)
    co = np.bincount(key[~ev], minlength=size)
    full = (ce * co).reshape(P_PAGES // 2, L_LINES * NB).sum(axis=1)
    return int(full.max()), full

def run_null(rng, pg, ln, xx, mask, n_allah, reps):
    N = len(pg)
    colmax = np.empty(reps, dtype=np.int32)
    col5 = np.empty(reps, dtype=np.int32)
    fmax = np.empty(reps, dtype=np.int32)
    bmax = np.empty(reps, dtype=np.int32)
    for r in range(reps):
        idx = rng.choice(N, size=n_allah, replace=False)
        p_, l_, x_ = pg[idx], ln[idx], xx[idx]
        cm, per = col_stat(p_, x_)
        colmax[r] = cm
        col5[r] = int((per >= 5).sum())
        fmax[r], _ = pair_matches(p_, l_, x_, True)
        bmax[r], _ = pair_matches(p_, l_, x_, False)
    return colmax, col5, fmax, bmax

def report(name, arr, thresholds=(2, 3, 4, 5, 6, 8, 10, 12)):
    print(f"{name}: max={arr.max()} p50={np.median(arr)} p99={np.percentile(arr,99)}")
    for t in thresholds:
        f = float((arr >= t).mean())
        if f > 0:
            print(f"  P(>={t}) = {f:.4g}  1 in {1/f:,.0f}")

def main():
    rng = np.random.default_rng(7)
    verses = load()
    nch = sum(len(t) for _, toks in verses for t in toks)
    char_w = (L_LINES * WIDTH * 604 - len(verses) * 10.0 - GAP * nch) / nch
    pages = pack(verses, L_LINES * WIDTH * 0.999, char_w)
    print("CHAR_W:", round(char_w, 2), "surrogate pages:", len(pages))
    slots = layout(pages)
    pg = np.array([s[0] for s in slots])
    ln = np.array([s[1] for s in slots])
    xx = np.array([s[2] for s in slots])
    toks = [s[3] for s in slots]
    mask = np.array([t == "الله" for t in toks])
    n_allah = int(mask.sum())
    print("slots:", len(slots), "standalone Allah:", n_allah)
    cm, per = col_stat(pg[mask], xx[mask])
    print("surrogate-as-if-real: col max =", cm, "| pages with col>=5:", int((per >= 5).sum()))
    fm, _ = pair_matches(pg[mask], ln[mask], xx[mask], True)
    bm, _ = pair_matches(pg[mask], ln[mask], xx[mask], False)
    print("surrogate-as-if-real: facing max =", fm, "b2b max =", bm)
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    colmax, col5, fmax, bmax = run_null(rng, pg, ln, xx, mask, n_allah, reps)
    report("colmax", colmax)
    report("pages_col>=5", col5, (1, 2, 3, 5, 10))
    report("facing_max", fmax, (1, 2, 3, 4))
    report("b2b_max", bmax, (1, 2, 3, 4))
    np.save("/tmp/opencode/nullA_colmax.npy", colmax)
    np.save("/tmp/opencode/nullA_facing.npy", fmax)
    np.save("/tmp/opencode/nullA_b2b.npy", bmax)

if __name__ == "__main__":
    main()
