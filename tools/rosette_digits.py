import json
import argparse
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"
OUT = Path(__file__).resolve().parent / "data" / "rosette_digits.npz"

def gold_mask(im):
    im = np.asarray(im, dtype=np.int16)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (R > 90) & (R - B > 70) & (G - B > 70) & (B < 90) & (np.abs(R - G) < 45)

def pale_mask(im):
    im = np.asarray(im, dtype=np.int16)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (R > 175) & (R < 250) & (G > 222) & (B > 210) & (B - R > 3) & (G - R > 10)

def extract_page_disk(im, cy_lo=0, cy_hi=None, centers=None, min_digit_pixels=5):
    if cy_hi is None:
        cy_hi = im.shape[0] - 1
    pm = pale_mask(im)
    plab, pn = ndimage.label(pm, structure=np.ones((3, 3)))
    if pn == 0:
        return []
    psizes = ndimage.sum(pm, plab, range(1, pn + 1))
    pobjs = ndimage.find_objects(plab)
    gm = gold_mask(im)
    gd = ndimage.binary_dilation(gm, np.ones((9, 9)))
    # collect disk fragments, merge nearby ones, then filter
    frags = []
    for pid, (sl, psz) in enumerate(zip(pobjs, psizes), start=1):
        if psz < 50:
            continue
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if not (10 <= h <= 48 and 8 <= w <= 74):
            continue
        cy = (sl[0].start + sl[0].stop) / 2.0
        cx = (sl[1].start + sl[1].stop) / 2.0
        if not (cy_lo <= cy <= cy_hi):
            continue
        if centers is not None and min(abs(cy - c) for c in centers) > 32:
            continue
        frags.append(dict(cy=cy, cx=cx, size=int(psz),
                          box=(int(sl[0].start), int(sl[0].stop),
                               int(sl[1].start), int(sl[1].stop))))
    frags.sort(key=lambda r: (r["cy"], r["cx"]))
    groups = []
    for f in frags:
        placed = False
        for g in groups:
            if abs(g["cy"] - f["cy"]) <= 13 and abs(g["cx"] - f["cx"]) <= 18:
                g["size"] += f["size"]
                g["box"] = (min(g["box"][0], f["box"][0]),
                            max(g["box"][1], f["box"][1]),
                            min(g["box"][2], f["box"][2]),
                            max(g["box"][3], f["box"][3]))
                g["cy"] = (g["cy"] + f["cy"]) / 2
                g["cx"] = (g["cx"] + f["cx"]) / 2
                placed = True
                break
        if not placed:
            groups.append(dict(f))
    rosettes = []
    for g in groups:
        if not (110 <= g["size"] <= 1300):
            continue
        by0, by1, bx0, bx1 = g["box"]
        h = by1 - by0
        w = bx1 - bx0
        if not (14 <= h <= 44 and 12 <= w <= 74):
            continue
        y0e, y1e = max(0, by0 - 5), min(gd.shape[0], by1 + 5)
        x0e, x1e = max(0, bx0 - 5), min(gd.shape[1], bx1 + 5)
        ring = gd[y0e:y1e, x0e:x1e]
        edge = np.concatenate([ring[0], ring[-1], ring[:, 0], ring[:, -1]])
        if edge.mean() < 0.25:
            continue
        rosettes.append(dict(cx=round(g["cx"], 1), cy=round(g["cy"], 1),
                             w=int(w), h=int(h), inner=int(g["size"]),
                             box=g["box"]))
    # merge fragmented disks (same rosette split by digits crossing)
    rosettes.sort(key=lambda r: (r["cy"], r["cx"]))
    out = []
    for r in rosettes:
        dup = None
        for q in out:
            if abs(q["cy"] - r["cy"]) <= 10 and abs(q["cx"] - r["cx"]) <= 26:
                dup = q
                break
        if dup is None:
            out.append(r)
        else:
            if r["inner"] > dup["inner"]:
                out[out.index(dup)] = r
    # digits per rosette: dark non-gold pixels inside disk bbox
    for r in out:
        (by0, by1, bx0, bx1) = r["box"]
        y0, y1 = max(0, by0 - 1), by1 + 1
        x0, x1 = max(0, bx0 - 1), bx1 + 1
        dsub = im[y0:y1, x0:x1]
        mx = dsub.max(axis=2)
        Rb, Gb, Bb = dsub[..., 0], dsub[..., 1], dsub[..., 2]
        dark = (mx < 140) & ~((Rb - Bb > 60) & (Gb - Bb > 60))
        dark &= ~ndimage.binary_dilation(
            gold_mask(dsub), np.ones((5, 5)))
        dlab, dn = ndimage.label(dark, structure=np.ones((3, 3)))
        digits = []
        if dn:
            dsz = ndimage.sum(dark, dlab, range(1, dn + 1))
            dobj = ndimage.find_objects(dlab)
            for li, (ds, do) in enumerate(zip(dsz, dobj), start=1):
                # Printed zero dots can have only 8-9 dark pixels (p567).
                if ds < min_digit_pixels or ds > 340:
                    continue
                by0b, by1b = max(0, do[0].start - 1), min(dark.shape[0], do[0].stop + 1)
                bx0b, bx1b = max(0, do[1].start - 1), min(dark.shape[1], do[1].stop + 1)
                bm = (dlab[by0b:by1b, bx0b:bx1b] == li).astype(np.uint8)
                axc = x0 + (do[1].start + do[1].stop) / 2.0
                ayb = y0 + do[0].stop
                digits.append((do[1].start, ds, bm, axc, ayb))
        if not digits:
            continue
        digits.sort(key=lambda t: t[0])
        merged = []
        for d in digits:
            if merged:
                if abs(merged[-1][3] - d[3]) <= 3 and d[4] - merged[-1][4] <= 3:
                    m1 = merged[-1][2]
                    hh = max(m1.shape[0], d[2].shape[0])
                    ww = max(m1.shape[1], d[2].shape[1])
                    mm = np.zeros((hh, ww), dtype=np.uint8)
                    mm[:m1.shape[0], :m1.shape[1]] |= m1
                    mm[:d[2].shape[0], :d[2].shape[1]] |= d[2]
                    merged[-1] = (merged[-1][0], int(mm.sum()), mm,
                                  (merged[-1][3] + d[3]) / 2, d[4])
                    continue
            merged.append(d)
        digits = merged
        if len(digits) > 3:
            digits = [d for d in digits if d[1] >= 15] or digits
        digits = digits[:3]
        r["ndig"] = len(digits)
        r["dsizes"] = [d[1] for d in digits]
        r["masks"] = [d[2] for d in digits]
    return [r for r in out if r.get("ndig", 0) > 0]



def extract_page_gold(im, cy_lo=0, cy_hi=None, centers=None, min_digit_pixels=5):
    if cy_hi is None:
        cy_hi = im.shape[0] - 1
    m = gold_mask(im)
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    if n == 0:
        return []
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    objs = ndimage.find_objects(lab)
    rosettes = []
    for s, o in zip(sizes, objs):
        if s < 380:
            continue
        h = o[0].stop - o[0].start
        w = o[1].stop - o[1].start
        if not (24 <= h <= 52 and 24 <= w <= 170):
            continue
        if s < 0.20 * w * h:
            continue
        cy = (o[0].start + o[0].stop) / 2.0
        cx = (o[1].start + o[1].stop) / 2.0
        if not (cy_lo <= cy <= cy_hi):
            continue
        if centers is not None and min(abs(cy - c) for c in centers) > 32:
            continue
        sh = 7 if h >= 32 else 5
        sw = 7 if w >= 34 else 5
        y0, y1 = o[0].start + sh, o[0].stop - sh
        x0, x1 = o[1].start + sw, o[1].stop - sw
        if y1 - y0 < 10 or x1 - x0 < 10:
            continue
        dsub = im[y0:y1, x0:x1]
        mx = dsub.max(axis=2)
        Rb, Gb, Bb = dsub[..., 0], dsub[..., 1], dsub[..., 2]
        pale = (Rb > 175) & (Rb < 250) & (Gb > 222) & (Bb > 210) & (Bb - Rb > 3)
        if pale.sum() < 0.25 * ((y1 - y0) * (x1 - x0)):
            continue
        dark = (mx < 140) & ~((Rb - Bb > 60) & (Gb - Bb > 60))
        dlab, dn = ndimage.label(dark, structure=np.ones((3, 3)))
        digits = []
        if dn:
            dsz = ndimage.sum(dark, dlab, range(1, dn + 1))
            dobj = ndimage.find_objects(dlab)
            for li, (ds, do) in enumerate(zip(dsz, dobj), start=1):
                if ds < min_digit_pixels or ds > 320:
                    continue
                by0b, by1b = max(0, do[0].start - 1), min(dark.shape[0], do[0].stop + 1)
                bx0b, bx1b = max(0, do[1].start - 1), min(dark.shape[1], do[1].stop + 1)
                bm = (dlab[by0b:by1b, bx0b:bx1b] == li).astype(np.uint8)
                axc = x0 + (do[1].start + do[1].stop) / 2.0
                ayb = y0 + do[0].stop
                digits.append((do[1].start, ds, bm, axc, ayb))
        if not digits:
            continue
        digits.sort(key=lambda t: t[0])
        merged = []
        for d in digits:
            if merged:
                if abs(merged[-1][3] - d[3]) <= 3 and d[4] - merged[-1][4] <= 3:
                    m1 = merged[-1][2]
                    hh = max(m1.shape[0], d[2].shape[0])
                    ww = max(m1.shape[1], d[2].shape[1])
                    mm = np.zeros((hh, ww), dtype=np.uint8)
                    mm[:m1.shape[0], :m1.shape[1]] |= m1
                    mm[:d[2].shape[0], :d[2].shape[1]] |= d[2]
                    merged[-1] = (merged[-1][0], int(mm.sum()), mm,
                                  (merged[-1][3] + d[3]) / 2, d[4])
                    continue
            merged.append(d)
        digits = merged
        if len(digits) > 3:
            digits = [d for d in digits if d[1] >= 15] or digits
        digits = digits[:3]
        rosettes.append(dict(cx=round(cx, 1), cy=round(cy, 1), w=int(w), h=int(h),
                             ndig=len(digits),
                             dsizes=[d[1] for d in digits],
                             masks=[d[2] for d in digits]))
    rosettes.sort(key=lambda r: (r["cy"], -r["cx"]))
    out = []
    for r in rosettes:
        dup = None
        for q in out:
            if abs(q["cy"] - r["cy"]) <= 6 and abs(q["cx"] - r["cx"]) <= 14:
                dup = q
                break
        if dup is None:
            out.append(r)
        else:
            if (r["ndig"], sum(r["dsizes"])) > (dup["ndig"], sum(dup["dsizes"])):
                out[out.index(dup)] = r
    return out

def pad24(c):
    out = np.zeros((22, 22), dtype=np.uint8)
    h, w = c.shape
    h = min(h, 22)
    w = min(w, 22)
    oy, ox = (22 - h) // 2, (22 - w) // 2
    out[oy:oy + h, ox:ox + w] = c[:h, :w]
    return out

def main():
    parser = argparse.ArgumentParser(description="Versioned CPU rosette digit extraction; not certified verse labels.")
    parser.add_argument("--output-directory", type=Path, default=OUT.parent)
    parser.add_argument("--min-digit-pixels", type=int, default=5,
                        help="5 retains small zero dots; 10 reproduces the v2 diagnostic")
    args = parser.parse_args()
    if args.min_digit_pixels < 1:
        parser.error("min-digit-pixels must be positive")
    args.output_directory.mkdir(parents=True, exist_ok=True)
    pages = {}
    crops = []
    meta = []
    for p in range(1, 605):
        f = PICS / f"page_{p}.png"
        if not f.exists():
            continue
        from image_io import open_rgb
        im = np.asarray(open_rgb(f)).astype(np.int16)
        cy_lo, cy_hi = 0, im.shape[0] - 1
        ros = extract_page_gold(im, cy_lo, cy_hi, min_digit_pixels=args.min_digit_pixels)
        ros_d = extract_page_disk(im, cy_lo, cy_hi, min_digit_pixels=args.min_digit_pixels)
        gm_ = gold_mask(im)
        for rd_ in ros_d:
            near = any(abs(rd_["cy"] - rg["cy"]) <= 14 and
                       abs(rd_["cx"] - rg["cx"]) <= 20 for rg in ros)
            if near:
                continue
            by0, by1, bx0, bx1 = rd_["box"]
            y0, y1 = max(0, by0 - 6), min(im.shape[0], by1 + 6)
            x0, x1 = max(0, bx0 - 6), min(im.shape[1], bx1 + 6)
            gf = gm_[y0:y1, x0:x1].mean()
            w_, h_ = rd_["w"], rd_["h"]
            if (gf >= 0.20 and rd_["inner"] >= 105 and w_ >= 19 and h_ >= 19
                    and 0.55 <= w_ / max(h_, 1) <= 1.8):
                ros.append(rd_)
        for r in ros:
            for bm in r["masks"]:
                crops.append(pad24(bm))
                meta.append((p, r["cx"], r["cy"], r["w"], r["h"], r["ndig"]))
        pages[str(p)] = [{k: v for k, v in r.items() if k != "masks"}
                         for r in ros]
        if p % 100 == 0:
            print("page", p, flush=True)
    arr = np.array(crops, dtype=np.uint8)
    np.savez_compressed(args.output_directory / "rosette_digits.npz", digits=arr,
                        meta=np.array(meta, dtype=np.float64))
    (args.output_directory / "rosette_digits.json").write_text(
         json.dumps(pages))
    (args.output_directory / "_rosette_extraction_report.json").write_text(json.dumps(dict(
        version="white-alpha-full-height-small-zero-v3", pages=len(pages),
        min_digit_pixels=args.min_digit_pixels,
        rosettes=sum(len(v) for v in pages.values()), digit_crops=len(crops),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        caveat="Detected rosettes and digit images, not independently verified identities."), indent=2) + "\n")
    print("pages:", len(pages), "rosettes:", sum(len(v) for v in pages.values()),
          "digit crops:", arr.shape)

if __name__ == "__main__":
    main()
