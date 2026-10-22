import numpy as np, re, json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prob_model import load, pack, layout

def page_slots(pages):
    out = []
    for page in pages:
        words = [(t, w) for toks, ws in page for t, w in zip(toks, ws)]
        total = sum(w for _, w in words)
        target = total / 15
        lines, cur, curw = [], [], 0.0
        for t, w in words:
            cur.append((t, w))
            curw += w
            if curw >= target and len(lines) < 14:
                lines.append(cur)
                cur, curw = [], 0.0
        if cur:
            if len(lines) < 15:
                lines.append(cur)
            else:
                lines[-1].extend(cur)
        pl = []
        for li, lnw in enumerate(lines):
            wsum = sum(w for _, w in lnw)
            slack = max(0.0, 974.0 - wsum - 6.0 * (len(lnw) - 1))
            g = slack / max(1, len(lnw) - 1)
            x = 1000.0
            for t, w in lnw:
                x -= w / 2.0
                pl.append((li, x))
                x -= w / 2.0 + 6.0 + g
        out.append(pl)
    return out

def sim_p422(ps, R=200000, k=16, chunk=20000):
    rng = np.random.default_rng(11)
    lens = np.array([len(p) for p in ps])
    counts = np.zeros(17, dtype=np.int64)
    done = 0
    while done < R:
        r = min(chunk, R - done)
        pages_i = rng.integers(0, len(ps), size=r)
        res = np.empty(r, dtype=np.int32)
        for j in range(r):
            sl = ps[pages_i[j]]
            m = len(sl)
            pick = rng.choice(m, size=k, replace=False)
            bins = np.clip(((np.array([s[1] for s in sl])[pick] - 26.0) / 30.0).astype(int), 0, 31)
            res[j] = np.bincount(bins, minlength=32).max()
        for v in range(1, 17):
            counts[v] += int((res == v).sum())
        done += r
    tail = np.cumsum(counts[::-1])[::-1]
    print("conditional P(max col = v | 16 Allah on one page):")
    for v in range(8, 17):
        print(f"  P(>={v}) = {tail[v]/R:.3g}")
    return tail / R

def sim_mirror(ps, R=200000, aA=8, aB=9, chunk=20000):
    rng = np.random.default_rng(13)
    ev_pages = [p for i, p in enumerate(ps) if i % 2 == 0 and i + 1 < len(ps)]
    od_pages = [ps[i + 1] for i, p in enumerate(ps) if i % 2 == 0 and i + 1 < len(ps)]
    hist = np.zeros(20, dtype=np.int64)
    done = 0
    while done < R:
        r = min(chunk, R - done)
        res = np.empty(r, dtype=np.int32)
        for j in range(r):
            t = rng.integers(0, len(ev_pages))
            A, B = ev_pages[t], od_pages[t]
            xa = np.array([26.0, 1000.0])
            ia = rng.choice(len(A), size=min(aA, len(A)), replace=False)
            ib = rng.choice(len(B), size=min(aB, len(B)), replace=False)
            la = np.array([A[i][0] for i in ia]); xb = np.array([A[i][1] for i in ia])
            lb = np.array([B[i][0] for i in ib]); x2 = np.array([B[i][1] for i in ib])
            da = 1000.0 - xb
            db = x2
            cnt = 0
            for u in range(len(ia)):
                same_line = lb == la[u]
                if same_line.any():
                    dd = np.abs(db[same_line] - da[u])
                    cnt += int((dd <= 30).sum())
            res[j] = cnt
        for v in range(0, 20):
            hist[v] += int((res == v).sum())
        done += r
    tail = np.cumsum(hist[::-1])[::-1] / R
    print(f"conditional mirror pairs per spread (aA={aA}, aB={aB}):")
    for v in range(0, 6):
        print(f"  P(>={v}) = {tail[v]:.3g}")
    return tail

def union_bound_p422(ps):
    from math import comb
    total = 0.0
    per_k = {k: 0.0 for k in (8, 10, 12)}
    for pl in ps:
        n = len(pl)
        binc = np.zeros(32, dtype=int)
        for li, x in pl:
            b = int(np.clip((x - 26.0) / 30.0, 0, 31))
            binc[b] += 1
        denom = comb(n, 16)
        for k in per_k:
            s = 0.0
            for m in binc:
                if m >= k:
                    for j in range(k, min(m, 16) + 1):
                        s += comb(m, j) * comb(n - m, 16 - j)
            per_k[k] += s / denom
    for k, v in per_k.items():
        print(f"sum of conditional fixed-page union bounds, threshold {k}: {v:.3g}")
        print(f"  mean bound for a uniformly selected surrogate page: {v/len(ps):.3g}")
    print("No unconditional corpus probability: a distribution of rich-page selection "
          "and a justified count model are required; the old hard-coded factor was unvalidated.")

def type_family():
    d = json.load(open("tools/data/quran-uthmani.json"))
    DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u0653-\u0655\u0640]")
    def strip(t):
        t = DIAC.sub("", t)
        return (t.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا")
                 .replace("آ", "ا").replace("ى", "ي").replace("ة", "ه"))
    toks = [strip(t) for v in d["verses"] for t in v["text_uthmani"].split()]
    c = Counter(toks)
    for thr in (30, 50, 100, 200):
        print("types with count >=", thr, ":", sum(1 for t, n in c.items() if n >= thr))
    print("top types:", c.most_common(8))

if __name__ == "__main__":
    verses = load()
    nch = sum(len(t) for _, toks in verses for t in toks)
    char_w = (15 * 974.0 * 604 - len(verses) * 10.0 - 6.0 * nch) / nch
    pages = pack(verses, 15 * 974.0 * 0.999, char_w)
    ps = page_slots(pages)
    print("pages:", len(ps), "mean slots/page:", np.mean([len(p) for p in ps]).round(1))
    sim_p422(ps)
    for aA, aB in [(8, 9), (5, 5), (12, 12)]:
        sim_mirror(ps, aA=aA, aB=aB)
    union_bound_p422(ps)
    type_family()
