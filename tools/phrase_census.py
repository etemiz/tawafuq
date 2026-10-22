import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt

DATA = Path(__file__).resolve().parent / "data"
PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"

FAMILIES = {
    "la_ilaha_illa_huwa": ["لا", "اله", "الا", "هو"],
    "unzilat_surah": ["واذا", "ما", "انزلت", "سوره"],
    "rabb_alarsh": ["رب", "العرش", "العظيم"],
    "imanan": None,
    "aljanna_bima_kuntum": ["الجنه", "بما", "كنتم"],
    "alaikum_wabima": ["عليكم", "بما", "كنتم"],
}

# strip/echo windows that the ayat-berkenar boundary strips carry (7:43 tail
# on p154 bottom strip, 7:44 head on p155 top strip, mid-strip 7:44b).
STRIP_FAMILIES = {
    "janna_inherit_7_43": ["الجنه", "اورثتموها", "بما", "كنتم"],
    "as7ab_janna_7_44": ["اصحب", "الجنه"],
    "as7ab_nar_7_44": ["اصحب", "النار"],
}

def color_runs(band, kind, min_len=12):
    r = band[..., 0].astype(int)
    g = band[..., 1].astype(int)
    b = band[..., 2].astype(int)
    redish = (r - g > 45) & (r > 120)
    if kind == "magenta":
        mask = redish & (b >= 108)
    elif kind == "crimson":
        mask = redish & (b < 108)
    else:  # colored = magenta | crimson
        mask = redish
    col = mask.sum(axis=0)
    runs = []
    x = 0
    W = len(col)
    while x < W:
        if col[x] >= 3:
            x0 = x
            gap = 0
            while x < W:
                if col[x] >= 2:
                    gap = 0
                else:
                    gap += 1
                    if gap > 22:
                        break
                x += 1
            x1 = x - gap
            if x1 - x0 >= min_len:
                runs.append((x0, x1, int(mask[:, x0:x1 + 1].sum())))
        else:
            x += 1
    return runs

def band_ink(page, cy, half=52):
    f = PICS / f"page_{page}.png"
    if not f.exists():
        return None
    y0, y1 = max(0, int(cy) - half), min(1680, int(cy) + half + 1)
    from image_io import open_rgb
    return np.asarray(open_rgb(f))[y0:y1, :, :]

def main():
    verses = mt.load_tokens()
    tm = json.load(open(DATA / "token_map2.json"))
    rec_by_t = {r["t"]: r for r in tm["map"]}
    flat = [(s, a, t) for s, a, ts in verses for t in ts]
    toks = [t for _, _, t in flat]
    n = len(toks)
    # global width rescale: est_width underestimates true ink width
    all_est = np.array([mt.est_width(t) for t in toks])
    WSCALE = 110.0 / float(all_est.mean())
    # verse token spans
    vspan = {}
    for i, (s, a, t) in enumerate(flat):
        vspan.setdefault((s, a), [i, i])
        vspan[(s, a)][1] = i
    # rosette anchors per (surah, verse)
    d = np.load(DATA / "rosette_seq.npz")
    mm = d["meta"]
    rose = {}
    for r in mm:
        s, v, pg, cx, cy = int(r[3]), int(r[4]), int(r[0]), r[1], r[2]
        if s > 0 and cx >= 0:
            rose[(s, v)] = (pg, cx, cy)
    res = {}
    for fam, win in FAMILIES.items():
        occ = []
        if win is None:
            occ = [[i, i] for i in range(n) if toks[i] == "ايمنا"]
        else:
            m = len(win)
            occ = [[i, i + m - 1] for i in range(n - m + 1)
                   if toks[i:i + m] == win]
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
                # per-verse line count from the previous verse's rosette
                n_lines = None
                prev = rose.get((s, a - 1)) if a > 1 else None
                if prev and prev[0] == page and prev[2] < cy_r:
                    n_lines = int(round((cy_r - prev[2]) / 110.0)) + 1
                elif a == 1:
                    # first verse on the page: page top ~ min rosette cy - 110
                    page_cys = [r[2] for (ss, vv), r in rose.items()
                                if r[0] == page]
                    if page_cys:
                        n_lines = int(round((cy_r - (min(page_cys) - 110)) / 110.0)) + 1
                widths = est  # verse tokens in reading order
                nv = len(widths)

                def walk(f):
                    # f is an absolute width scale; widths[] already has WSCALE
                    g = f / WSCALE
                    line_of, xpos = {}, {}
                    x_left = cx_r + 22.0
                    li = 0
                    for k in range(nv - 1, -1, -1):
                        w = widths[k] * g
                        if x_left + w > 993.0 and k < nv - 1:
                            li += 1
                            x_left = 30.0
                        line_of[k] = li
                        xpos[k] = (x_left, x_left + w)
                        x_left = x_left + w + 6.0
                    return line_of, xpos, li

                line_of, xpos, max_li = walk(WSCALE)
                if n_lines and n_lines >= 1:
                    target = n_lines - 1
                    if max_li != target:
                        lo, hi = WSCALE * 0.4, WSCALE * 3.0
                        for _ in range(40):
                            mid = (lo + hi) / 2
                            _, _, ml = walk(mid)
                            if ml > target:
                                hi = mid
                            else:
                                lo = mid
                        line_of, xpos, max_li = walk((lo + hi) / 2)
                f0, f1 = i0 - vs, i1 - vs
                offs = sorted(set(line_of[k] for k in range(f0, f1 + 1)))
                band_cys = [cy_r - 110.0 * o for o in offs]
                if nv >= 12:
                    # long verses: width-walk has +-1 line error; scan neighbors
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
            est_w = float(est[f0:f1 + 1].sum()) if False else \
                sum(mt.est_width(t) for t in toks[i0:i1 + 1])
            mruns_all, cruns_all, colruns_all = [], [], []
            for bcy in band_cys:
                band = band_ink(page, bcy)
                if band is None:
                    continue
                for r0 in color_runs(band, "magenta"):
                    if r0[1] >= px[0] and r0[0] <= px[1]:
                        mruns_all.append((int(bcy), int(max(r0[0], px[0])), int(min(r0[1], px[1]))))
                for r0 in color_runs(band, "crimson"):
                    if r0[1] >= px[0] and r0[0] <= px[1]:
                        cruns_all.append((int(bcy), int(max(r0[0], px[0])), int(min(r0[1], px[1]))))
                for r0 in color_runs(band, "colored"):
                    if r0[1] >= px[0] and r0[0] <= px[1]:
                        colruns_all.append((int(bcy), int(max(r0[0], px[0])), int(min(r0[1], px[1]))))
            bm = max(mruns_all, key=lambda r: r[2] - r[1], default=None)
            bc = max(cruns_all, key=lambda r: r[2] - r[1], default=None)
            bcol = max(colruns_all, key=lambda r: r[2] - r[1], default=None)
            col_len = (bcol[2] - bcol[1]) if bcol else 0
            mag_len = (bm[2] - bm[1]) if bm else 0
            cri_len = (bc[2] - bc[1]) if bc else 0
            verdict = ("MARKED" if col_len >= 0.40 * est_w else "black")
            if verdict == "MARKED":
                verdict = "MAGENTA" if mag_len >= cri_len else "CRIMSON"
            rows.append(dict(vk=vk, page=page, src=src,
                             audit_status="exploratory predicted-window color, not verified token marking",
                             bands=[int(b) for b in band_cys], px=[int(v) for v in px],
                             est_w=int(est_w),
                             mag_run=bm, cri_run=bc,
                             n_mag=len(mruns_all), n_cri=len(cruns_all),
                             verdict=verdict))
        res[fam] = rows
        nmark = sum(1 for r in rows if r.get("verdict") in ("MAGENTA", "CRIMSON"))
        print(f"== {fam}: {len(rows)} occurrences, {nmark} marked")
        for r in rows:
            if r.get("note"):
                print(f"   {r['vk']:8s} {r['note']}")
                continue
            print(f"   {r['vk']:8s} p{r['page']:3d} [{r['src'][:6]}] "
                  f"bands={r['bands']} x={r['px']} estw={r['est_w']:4d} "
                  f"mag={r['mag_run']} cri={r['cri_run']} -> {r['verdict']}")

    # ---- strip echo census: uses dp token records directly (strips are
    # grid-lined on 154/155 but the rosette width-walk cannot place them) ----
    strip_res = {}
    for fam, win in STRIP_FAMILIES.items():
        m = len(win)
        occ = [[i, i + m - 1] for i in range(n - m + 1)
               if toks[i:i + m] == win]
        rows = []
        for (i0, i1) in occ:
            s, a = flat[i0][0], flat[i0][1]
            vk = f"{s}:{a}"
            recs = [rec_by_t.get(j) for j in range(i0, i1 + 1)]
            good = [r for r in recs if r and r.get("page") and r.get("y")]
            if not good:
                rows.append(dict(vk=vk, note="no-records"))
                continue
            page = good[0]["page"]
            pages = sorted(set(r["page"] for r in good))
            if len(pages) != 1:
                rows.append(dict(vk=vk, pages=pages, note="cross-page phrase needs separate per-page windows"))
                continue
            cys = sorted(set((r["y"][0] + r["y"][1]) / 2 for r in good))
            bands = []
            for cy in cys:
                if bands and cy - bands[-1][-1] <= 55:
                    bands[-1].append(cy)
                else:
                    bands.append([cy])
            xs = [r["x"] for r in good]
            px = [int(min(min(x) for x in xs)), int(max(max(x) for x in xs))]
            est_w = int(sum(mt.est_width(t) for t in toks[i0:i1 + 1]))
            mruns_all, cruns_all = [], []
            for grp in bands:
                bcy = grp[len(grp) // 2]
                band = band_ink(page, bcy)
                if band is None:
                    continue
                for r0 in color_runs(band, "magenta"):
                    mruns_all.append((int(bcy),) + tuple(int(v) for v in r0[:2]))
                for r0 in color_runs(band, "crimson"):
                    cruns_all.append((int(bcy),) + tuple(int(v) for v in r0[:2]))
            bm = max(mruns_all, key=lambda r: r[2] - r[1], default=None)
            bc = max(cruns_all, key=lambda r: r[2] - r[1], default=None)
            # union coverage of colored runs inside the phrase span (strip
            # phrases mark several words; best-single-run undercounts)
            def union_len(runs):
                iv = sorted((max(r[1], px[0]), min(r[2], px[1]))
                            for r in runs if r[2] > px[0] and r[1] < px[1])
                tot, ce, cs = 0, None, None
                for a0, a1 in iv:
                    if ce is None:
                        cs, ce = a0, a1
                    elif a0 <= ce + 6:
                        ce = max(ce, a1)
                    else:
                        tot += ce - cs
                        cs, ce = a0, a1
                if ce is not None:
                    tot += ce - cs
                return tot
            cov_m = union_len(mruns_all)
            cov_c = union_len(cruns_all)
            verdict = "MAGENTA" if cov_m >= 0.40 * est_w else \
                      "CRIMSON" if cov_c >= 0.40 * est_w else "black"
            cxm = (px[0] + px[1]) / 2.0
            rows.append(dict(vk=vk, page=page, pages=pages,
                             bands=[int(b[0]) for b in bands], px=px,
                             cxm=round(cxm, 1), est_w=est_w,
                             nskip=sum(1 for r in recs if not (r and r.get("y"))),
                             cov_m=cov_m, cov_c=cov_c,
                             band_runs_m=[[int(v) for v in r] for r in
                                          sorted(mruns_all)],
                             mag_run=bm, cri_run=bc, verdict=verdict))
        strip_res[fam] = rows
        nmark = sum(1 for r in rows if r.get("verdict") in ("MAGENTA", "CRIMSON"))
        print(f"== strip {fam}: {len(rows)} occurrences, {nmark} marked")
        for r in rows:
            if r.get("note"):
                print(f"   {r['vk']:8s} {r['note']}")
                continue
            print(f"   {r['vk']:8s} p{r['page']:3d} bands={r['bands']} x={r['px']} "
                  f"cxm={r['cxm']:5.1f} skip={r['nskip']} estw={r['est_w']:4d} "
                  f"mag={r['mag_run']} cri={r['cri_run']} -> {r['verdict']}")
    res["strip_echoes"] = strip_res
    res["audit"] = dict(status="Exploratory width-window census. Token positions and identities "
                        "are uncertain; do not use to assert unconditional marking or no selection bias.")
    DATA.joinpath("audit_phrase_census.json").write_text(json.dumps(res, indent=1))
    print("saved audit_phrase_census.json")

if __name__ == "__main__":
    main()
