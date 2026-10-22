"""New echo-family census (S11 additions): alhamdu_lillah (two-tone) +
waad family, using the rosette-anchored width-walk (phrase_census logic).

Families:
  alhamdu_lillah  [الحمد, لله] and [والحمد, لله]  (S11: crimson الحمد +
                  magenta لله two-tone on p154 7:43)
  waad_allah      [وعد, الله]                     (S11: وعد/وجد family,
                  first occurrence = 7:44 strip فهل وجدتم ما وعد ربكم حقا)

Verdicts are PER TOKEN: each occurrence token gets its own (band, x-window)
from the rosette walk (fallback: dp box); a token is marked if a colored run
covers >=50% of its window (M=magenta, C=crimson, b=black, offpage/noband).
An occurrence is MARKED if >=1 of its tokens is marked.
Appends to phrase_census.json under "families2".
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt
from phrase_census import band_ink, color_runs

DATA = Path(__file__).resolve().parent / "data"

FAMILIES2 = {
    "alhamdu_lillah": [["الحمد", "لله"], ["والحمد", "لله"]],
    "waad_allah": [["وعد", "الله"]],
}


def main():
    verses = mt.load_tokens()
    tm = json.load(open(DATA / "token_map2.json"))
    rec_by_t = {r["t"]: r for r in tm["map"]}
    flat = [(s, a, t) for s, a, ts in verses for t in ts]
    toks = [t for _, _, t in flat]
    n = len(toks)
    all_est = np.array([mt.est_width(t) for t in toks])
    WSCALE = 110.0 / float(all_est.mean())
    vspan = {}
    for i, (s, a, t) in enumerate(flat):
        vspan.setdefault((s, a), [i, i])
        vspan[(s, a)][1] = i
    d = np.load(DATA / "rosette_seq.npz")
    rose = {}
    for r in d["meta"]:
        s, v, pg, cx, cy = int(r[3]), int(r[4]), int(r[0]), r[1], r[2]
        if s > 0 and cx >= 0:
            rose[(s, v)] = (pg, cx, cy)

    res = {}
    for fam, wins in FAMILIES2.items():
        occ = []
        for win in wins:
            m = len(win)
            occ += [[i, i + m - 1] for i in range(n - m + 1)
                    if toks[i:i + m] == win]
        occ.sort()
        rows = []
        for (i0, i1) in occ:
            s, a = flat[i0][0], flat[i0][1]
            vk = f"{s}:{a}"
            vs, ve = vspan[(s, a)]
            est = np.array([mt.est_width(t) for t in toks[vs:ve + 1]]) * WSCALE
            anch = rose.get((s, a))
            dp = [rec_by_t.get(j) for j in range(i0, i1 + 1)]
            dp = [r for r in dp if r and r.get("page") and r.get("y")]
            band_cys, page, src = [], None, None
            if anch:
                page, cx_r, cy_r = anch
                n_lines = None
                prev = rose.get((s, a - 1)) if a > 1 else None
                if prev and prev[0] == page and prev[2] < cy_r:
                    n_lines = int(round((cy_r - prev[2]) / 110.0)) + 1
                nv = len(est)

                def walk(f):
                    line_of, xpos = {}, {}
                    x_left = cx_r + 22.0
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
                if n_lines and max_li != n_lines - 1:
                    lo, hi = WSCALE * 0.4, WSCALE * 3.0
                    for _ in range(40):
                        mid = (lo + hi) / 2
                        _, _, ml = walk(mid)
                        if ml > n_lines - 1:
                            hi = mid
                        else:
                            lo = mid
                    line_of, xpos, max_li = walk((lo + hi) / 2)
                f0, f1 = i0 - vs, i1 - vs
                offs = sorted(set(line_of[k] for k in range(f0, f1 + 1)))
                band_cys = [cy_r - 110.0 * o for o in offs]
                if nv >= 12:
                    band_cys += [b - 110.0 for b in band_cys] + \
                                [b + 110.0 for b in band_cys]
                    band_cys = sorted(set(band_cys))
                xs = [xpos[k][0] for k in range(f0, f1 + 1)] + \
                     [xpos[k][1] for k in range(f0, f1 + 1)]
                px = [min(xs), max(xs)]
                src = "rosette-walk"
            if not band_cys and dp:
                page = dp[0]["page"]
                band_cys = [(r["y"][0] + r["y"][1]) / 2.0 for r in dp]
                xs = [r["x"][0] for r in dp] + [r["x"][1] for r in dp]
                px = [min(xs), max(xs)]
                src = "dp-boxes"
            if not band_cys:
                rows.append(dict(vk=vk, note="no-anchor"))
                continue
            # per-token windows: token k of the occurrence -> (band, x0, x1)
            f0, f1 = i0 - vs, i1 - vs
            tcell = []
            for k in range(f0, f1 + 1):
                if anch:
                    o = line_of[k]
                    xs_t = xpos[k]
                else:
                    rr = rec_by_t.get(i0 + (k - f0))
                    if not rr or not rr.get("y"):
                        continue
                    o = 0
                    xs_t = rr["x"]
                if anch:
                    bcy = cy_r - 110.0 * o
                else:
                    rr = rec_by_t.get(i0 + (k - f0))
                    bcy = (rr["y"][0] + rr["y"][1]) / 2.0
                tcell.append((toks[i0 + (k - f0)], bcy, xs_t[0], xs_t[1]))
            rows_tok = []
            marked = 0
            for tok, bcy, x0, x1 in tcell:
                if bcy < 0 or bcy > 1600:
                    rows_tok.append((tok, "offpage"))
                    continue
                band = band_ink(page, bcy)
                if band is None:
                    rows_tok.append((tok, "noband"))
                    continue
                mruns = color_runs(band, "magenta")
                cruns = color_runs(band, "crimson")
                w = x1 - x0
                cov_m = sum(min(r[2], x1) - max(r[1], x0) for r in mruns
                            if r[2] > x0 and r[1] < x1)
                cov_c = sum(min(r[2], x1) - max(r[1], x0) for r in cruns
                            if r[2] > x0 and r[1] < x1)
                v = ("M" if cov_m >= 0.5 * w else
                     "C" if cov_c >= 0.5 * w else "b")
                if v in ("M", "C"):
                    marked += 1
                rows_tok.append((tok, v, int(cov_m), int(cov_c), int(w)))
            verdict = ("MARKED" if marked >= 1 else "black")
            rows.append(dict(vk=vk, page=page, src=src,
                             n_tok=len(tcell), marked=marked,
                             toks=[list(t) for t in rows_tok],
                             verdict=verdict))
        res[fam] = rows
        nmark = sum(1 for r in rows if r.get("verdict") == "MARKED")
        print(f"== {fam}: {len(rows)} occurrences, {nmark} marked")
        for r in rows:
            if r.get("note"):
                print(f"   {r['vk']:8s} {r['note']}")
                continue
            toks_s = " ".join(f"{t}:{v}" for t, *v in r["toks"])
            print(f"   {r['vk']:8s} p{r['page']:3d} [{r['src'][:6]}] "
                  f"m{r['marked']}/{r['n_tok']} -> {r['verdict']:6s} | {toks_s}")
    pc = json.load(open(DATA / "phrase_census.json"))
    pc["families2"] = res
    DATA.joinpath("phrase_census.json").write_text(json.dumps(pc, indent=1))
    print("appended families2 to phrase_census.json")


if __name__ == "__main__":
    main()
