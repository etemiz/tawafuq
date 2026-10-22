import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt

DATA = Path(__file__).resolve().parent / "data"

def main():
    verses = mt.load_tokens()
    nv = len(verses)
    vidx = [0]
    for i, (s_, a_, ts) in enumerate(verses):
        if a_ == 1 and i > 0:
            vidx.append(i)
    sur_of = []
    for i, (s_, a_, ts) in enumerate(verses):
        sur_of.append(s_)
    pvm = json.load(open(DATA / "page_verse_map.json"))
    # map verse-key -> global verse index
    key2idx = {}
    for i, (s_, a_, ts) in enumerate(verses):
        key2idx[(s_, a_)] = i
    # initial spans from rosette map
    spans = []
    for p in range(1, 605):
        rec = pvm.get(str(p))
        if rec is None:
            spans.append(None)
            continue
        s1, v1 = map(int, rec["first"].split(":"))
        s2, v2 = map(int, rec["last"].split(":"))
        a = key2idx.get((s1, v1))
        b = key2idx.get((s2, v2))
        spans.append((a, b) if a is not None and b is not None else None)
    # violations: page p last +1 != p+1 first
    viols = []
    for p in range(1, 604):
        if spans[p - 1] is None or spans[p] is None:
            continue
        end_p = spans[p - 1][1]
        start_n = spans[p][0]
        if end_p + 1 != start_n:
            viols.append((p, end_p + 1, start_n - 1))  # missing verses
    print("violations:", len(viols))
    # arbitration: distribute missing verses between the two pages by DP cost
    cache = {}
    def pdcost(p, a, b):
        if a > b:
            return 1e9
        key = (p, a, b)
        if key in cache:
            return cache[key]
        ntok = sum(len(verses[i][2]) for i in range(a, b + 1))
        lp = mt.load_page(p)
        if lp is None:
            c = 0.0 if ntok == 0 else 1e9
        else:
            d, stream = lp
            toks = [t for i in range(a, b + 1) for t in verses[i][2]]
            res = mt.page_dp(stream, toks)
            c = res[0] if res[0] is not None else 500.0
        cache[key] = c
        return c
    for (p, lo, hi) in viols:
        k = hi - lo + 1
        sp, sn = spans[p - 1], spans[p]
        best = None
        for t in range(k + 1):
            a1, b1 = sp[0], sp[1] + t
            a2, b2 = lo + t, sn[1]
            if a2 > b2:
                continue
            c = pdcost(p, a1, b1) + pdcost(p + 1, a2, b2)
            if best is None or c < best[0]:
                best = (c, t)
        if best is None:
            continue
        t = best[1]
        spans[p - 1] = (sp[0], sp[1] + t)
        spans[p] = (lo + t, sn[1])
    # fill Nones: propagate neighbors
    for p in range(604):
        if spans[p] is None:
            a = spans[p - 1][1] + 1 if p > 0 and spans[p - 1] else None
            b = spans[p + 1][0] - 1 if p < 603 and spans[p + 1] else None
            if a is not None and b is not None and a <= b:
                spans[p] = (a, b)
    # global check: contiguity
    bad = 0
    for p in range(603):
        if spans[p] and spans[p + 1] and spans[p][1] + 1 != spans[p + 1][0]:
            bad += 1
    print("post-arbitration tile violations:", bad)
    # save spans + run page token DP
    out = []
    tok_idx = 0
    first_sp = next((sp for sp in spans if sp), None)
    if first_sp:
        tok_idx = sum(len(verses[i][2]) for i in range(first_sp[0]))
    total_wres = []
    nfail = 0
    for p in range(604):
        sp = spans[p]
        if sp is None:
            continue
        s0, s1 = sp
        ntok = sum(len(verses[i][2]) for i in range(s0, s1 + 1))
        lp = mt.load_page(p + 1)
        if lp is None:
            for _ in range(ntok):
                out.append(dict(t=tok_idx, page=p + 1, boxes=[], skip=True))
                tok_idx += 1
            continue
        d, stream = lp
        toks = [t for i in range(s0, s1 + 1) for t in verses[i][2]]
        cost, mapping = mt.page_dp(stream, toks)
        if mapping is None:
            nfail += 1
            for _ in range(ntok):
                out.append(dict(t=tok_idx, page=p + 1, boxes=[], skip=True))
                tok_idx += 1
            continue
        for gi, g in enumerate(mapping):
            if g is None or len(g) == 0:
                out.append(dict(t=tok_idx, page=p + 1, boxes=[], skip=True))
            else:
                bs = [stream[j] for j in g]
                out.append(dict(t=tok_idx, page=p + 1,
                                boxes=[b["cx"] for b in bs],
                                x=[min(b["x0"] for b in bs), max(b["x1"] for b in bs)],
                                y=[int(min(b["y0"] for b in bs)),
                                   int(max(b["y1"] for b in bs))],
                                line=bs[0]["line"],
                                n=len(bs),
                                npx=sum(b["npx"] for b in bs),
                                span=bs[0]["x1"] - bs[-1]["x0"] + 1))
                wres = abs((bs[0]["x1"] - bs[-1]["x0"] + 1) - mt.est_width(toks[gi]))
                total_wres.append(wres / max(mt.est_width(toks[gi]), 24.0))
            tok_idx += 1
    print("pages failed:", nfail, "mean width residual:",
          round(float(np.mean(total_wres)), 3) if total_wres else None)
    Path(DATA / "token_map2.json").write_text(json.dumps(
        dict(spans={str(k + 1): (int(v[0]), int(v[1])) for k, v in enumerate(spans) if v},
             map=out)))
    print("saved token_map2.json;", len(out), "token records")
    # spot check spans
    for p in (1, 23, 206, 207, 300, 422, 599, 604):
        print(f"p{p}:", verses[spans[p-1][0]][0], ":",
              verses[spans[p-1][0]][1], "..",
              verses[spans[p-1][1]][0], ":", verses[spans[p-1][1]][1])

if __name__ == "__main__":
    main()
