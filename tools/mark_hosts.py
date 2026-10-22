"""Host-word extraction for the 305 reds-pool small marks (w<30).

For each mark (page, line cy, x): the verse on that line = the verse whose
verse-end rosette is the first rosette at-or-below the line; then the
rosette-anchored width-walk (phrase_census machinery) gives the token
x-ranges on the line; host = token whose range is nearest the mark x.
Reports the host's RAW Uthmani text + which orthographic sign chars it
carries (dagger alif / madda / small waw/ya / hamza-above / shadda).

Output: tools/data/mark_hosts.json + console stats.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt
from phrase_census import band_ink, color_runs

DATA = Path(__file__).resolve().parent / "data"

RAW = {0x670: "dag", 0x653: "madda", 0x6E5: "swaw", 0x6E6: "sya",
       0x654: "hamza", 0x651: "shadda"}


def main():
    verses = mt.load_tokens()
    raw = json.load(open(DATA / "quran-uthmani.json"))
    flat, raw_of = [], []
    for v in raw["verses"]:
        for w in v["text_uthmani"].split():
            if mt.norm(w):
                flat.append(w)
    # raw corpus token list, aligned with filtered tokens (77,433)
    d = np.load(DATA / "rosette_seq.npz")
    rose = {}
    for r in d["meta"]:
        s, v, pg, cx, cy = int(r[3]), int(r[4]), int(r[0]), r[1], r[2]
        if s > 0 and cx >= 0:
            rose[(s, v)] = (pg, cx, cy)
    pvm = json.load(open(DATA / "page_verse_map.json"))

    vspan = {}
    gi = 0
    for s, a, ts in verses:
        for _ in ts:
            vspan[gi] = (s, a)
            gi += 1
    toks = [t for _, _, ts in verses for t in ts]
    all_est = np.array([mt.est_width(t) for t in toks])
    WSCALE = 110.0 / float(all_est.mean())

    tm = json.load(open(DATA / "token_map2.json"))
    reds_types = np.load(DATA / "red_types.npz", allow_pickle=True)
    types, meta = reds_types["types"], reds_types["meta"]
    marks = [i for i, t in enumerate(types) if t == "mark"]

    out = []
    for mi in marks:
        pg, idx, cy_m, line_m, x_m, w_m = meta[mi]
        pg = int(pg)
        x_m = float(x_m)
        r = json.load(open(DATA / "real_boxes" / f"page_{pg:03d}.json"))["reds"][int(idx)]
        cy = (r["y0"] + r["y1"]) / 2.0
        # verse for this line: rosette on this page with smallest cy >= cy - 20
        page_roses = sorted(((cy_, s, v) for (s, v), (p, _, cy_) in rose.items()
                             if p == pg))
        anch = None
        for cy_, s, v in page_roses:
            if cy_ >= cy - 20:
                anch = (s, v, cy_)
                break
        row = dict(page=pg, mark_x=r["x0"], mark_w=r["w"], h=r["h"],
                   deep=bool(reds_types["deep"][mi]), line=r.get("line"))
        if anch is None:
            row["note"] = "no-rosette"
            out.append(row)
            continue
        s, a, cy_r = anch
        prev = rose.get((s, a - 1)) if a > 1 else None
        n_lines = None
        if prev and prev[0] == pg and prev[2] < cy_r:
            n_lines = int(round((cy_r - prev[2]) / 110.0)) + 1
        if s < 1:
            row["note"] = "bad-anchor"
            out.append(row)
            continue
        # verse token list
        vi = None
        for i, (ss, aa, ts) in enumerate(verses):
            if ss == s and aa == a:
                vi = i
                break
        if vi is None:
            row["note"] = "no-verse"
            out.append(row)
            continue
        vt = verses[vi][2]
        nv = len(vt)
        est = np.array([mt.est_width(t) for t in vt]) * WSCALE

        def walk(f):
            line_of, xpos = {}, {}
            x_left = cy_r + 22.0
            li = 0
            for k in range(nv - 1, -1, -1):
                w = est[k] * (f / WSCALE)
                if x_left + w > 993.0 and k < nv - 1:
                    li += 1
                    x_left = 30.0
                line_of[k] = li
                xpos[k] = (x_left, x_left + w)
                x_left = x_left + w + 6.0
            return line_of, xpos, li

        line_of, xpos, max_li = walk(WSCALE)
        if n_lines and n_lines >= 1 and max_li != n_lines - 1:
            lo, hi = WSCALE * 0.4, WSCALE * 3.0
            for _ in range(40):
                mid = (lo + hi) / 2
                _, _, ml = walk(mid)
                if ml > n_lines - 1:
                    hi = mid
                else:
                    lo = mid
            line_of, xpos, max_li = walk((lo + hi) / 2)
        # target line index = (cy_r - cy) / 110 from the rosette line
        li_t = int(round((cy_r - cy) / 110.0))
        cands = [k for k in range(nv) if line_of[k] == li_t]
        if not cands:
            row["note"] = "no-tokens-on-line"
            out.append(row)
            continue
        # nearest token by x-range
        def dist(k):
            a_, b_ = xpos[k]
            if a_ <= x_m <= b_:
                return 0
            return min(abs(x_m - a_), abs(x_m - b_))
        k = min(cands, key=dist)
        t_idx = sum(len(verses[i][2]) for i in range(vi)) + k
        row["host_tok"] = toks[t_idx]
        row["host_raw"] = flat[t_idx]
        row["host_dx"] = round(dist(k), 1)
        row["host_ortho"] = sorted({RAW[ord(c)] for c in flat[t_idx]
                                    if ord(c) in RAW})
        row["verse"] = f"{s}:{a}"
        out.append(row)
    DATA.joinpath("mark_hosts.json").write_text(json.dumps(out, indent=1))
    n = len(out)
    orth = sum(1 for r in out if r.get("host_ortho"))
    dag = sum(1 for r in out if "dag" in r.get("host_ortho", []))
    shadda = sum(1 for r in out if "shadda" in r.get("host_ortho", []))
    print(f"marks: {n}; with note: {sum(1 for r in out if r.get('note'))}")
    print(f"hosts with any small-letter char: {orth} ({orth}/{n})")
    print(f"  dagger-alif: {dag}, shadda: {shadda}")
    for r in out[:25]:
        print(f"  p{r['page']:3d} x{r['mark_x']:4d} L{r.get('line')} "
              f"{r.get('verse','?'):7s} host={r.get('host_tok','?'):8s} "
              f"raw={r.get('host_raw','?'):14s} ortho={r.get('host_ortho',[])} "
              f"dx={r.get('host_dx','?')}")


if __name__ == "__main__":
    main()
