import sys, json, argparse, hashlib, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_scan import (load_page, black_mask, text_region, components, dilate,
                       text_lines, classify)

OUT = Path(__file__).resolve().parent / "data" / "real_boxes"

def rebuild_lines(bands, ty0, ty1):
    if not bands:
        return None
    bands = [list(b) for b in bands]
    if not bands:
        return None
    merged = [list(bands[0])]
    for b in bands[1:]:
        if b[0] - merged[-1][1] < 35:
            merged[-1][1] = max(merged[-1][1], b[1])
        else:
            merged.append(b)
    tall = [b for b in merged if b[1] - b[0] >= 40]
    if not tall:
        return None
    best_run, run = [], []
    for i in range(1, len(merged)):
        gap = merged[i][0] - merged[i - 1][1]
        if 40 <= gap <= 150:
            if not run:
                run = [merged[i - 1], merged[i]]
            else:
                run.append(merged[i])
        else:
            if len(run) > len(best_run):
                best_run = run
            run = []
    if len(run) > len(best_run):
        best_run = run
    if len(best_run) < 8:
        return None
    y_top, y_bot = best_run[0][0], best_run[-1][1]
    inner = [b for b in merged if b[0] >= y_top - 12 and b[1] <= y_bot + 12]
    final = []
    for b in inner:
        if final and b[0] - final[-1][1] < 42:
            final[-1][1] = max(final[-1][1], b[1])
        else:
            final.append(list(b))
    centers = [float((b[0] + b[1]) / 2.0) for b in final]
    pitch = float(np.median(np.diff(centers))) if len(centers) > 2 else 100.0
    def line_of(cy):
        best, bd = None, 1e9
        for i, c in enumerate(centers):
            d = abs(cy - c)
            if d < bd:
                best, bd = i, d
        return best if bd <= pitch * 0.6 else None
    return dict(centers=centers, pitch=pitch, n_bands=len(final),
                line_of=line_of)

def extract_page(n):
    a = load_page(n)
    bm = black_mask(a)
    H, W = bm.shape
    ty0, ty1, bx0, bx1 = text_region(bm)
    mx = a.max(axis=2).astype(int)
    mn = a.min(axis=2).astype(int)
    colored = ((mx - mn) > 60) & (mx > 80)
    colored[0:ty0, :] = False
    colored[ty1 + 1:, :] = False
    colored[:, 0:bx0] = False
    colored[:, bx1:] = False
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
    ink = (bm | colored)
    ink[0:ty0, :] = False
    ink[ty1 + 1:, :] = False
    ink[:, 0:bx0] = False
    ink[:, bx1:] = False
    comps = components(a, ink, dilate(ink, 5), 20)
    raw_slots = []
    for c in comps:
        w = c["x1"] - c["x0"] + 1
        h = c["y1"] - c["y0"] + 1
        if w < 30 and h < 14:
            continue
        if h > 120 or w > 0.30 * W:
            continue
        c["color"] = classify(c["med"])
        c["w"] = w
        c["h"] = h
        raw_slots.append(c)
    words = [c for c in raw_slots if c["npx"] >= 120 or (c["h"] >= 15 and c["w"] >= 30)]
    out = [dict(c) for c in words]
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                p, q = out[i], out[j]
                if p is None or q is None or p["color"] != q["color"]:
                    continue
                gx = max(p["x0"] - q["x1"], q["x0"] - p["x1"])
                oy = min(p["y1"], q["y1"]) - max(p["y0"], q["y0"])
                gy = max(p["y0"] - q["y1"], q["y0"] - p["y1"])
                if gx <= 25 and (oy > 0 or gy <= 30):
                    p["x0"] = min(p["x0"], q["x0"]); p["x1"] = max(p["x1"], q["x1"])
                    p["y0"] = min(p["y0"], q["y0"]); p["y1"] = max(p["y1"], q["y1"])
                    p["npx"] += q["npx"]
                    p["cy"] = (p["y0"] + p["y1"]) / 2.0
                    p["cx"] = (p["x0"] + p["x1"]) / 2.0
                    out[j] = None
                    changed = True
        out = [c for c in out if c is not None]
    for c in out:
        c["color"] = classify(c["med"])
        c["w"] = c["x1"] - c["x0"] + 1
        c["h"] = c["y1"] - c["y0"] + 1
    grid = rebuild_lines(text_lines(ink, ty0, ty1, bx0, bx1, gap=28), ty0, ty1)
    def line_of(cy):
        return grid["line_of"](cy) if grid else None
    reds, slots = [], []
    for c in out:
        li = line_of(c["cy"])
        rec = dict(x0=int(c["x0"]), x1=int(c["x1"]), y0=int(c["y0"]), y1=int(c["y1"]),
                   cx=round(c["cx"], 1), cy=round(c["cy"], 1),
                   w=int(c["w"]), h=int(c["h"]), color=c["color"], line=li)
        if c["color"] == "red":
            reds.append(rec)
    for c in raw_slots:
        li = line_of(c["cy"])
        slots.append(dict(x0=int(c["x0"]), x1=int(c["x1"]), y0=int(c["y0"]),
                          y1=int(c["y1"]), cx=round(c["cx"], 1),
                          cy=round(c["cy"], 1), npx=int(c["npx"]),
                          line=li, color=c["color"]))
    return dict(page=n, extractor_version="components-v3-white-alpha", grid=None if grid is None else dict(
                    centers=grid["centers"], pitch=round(grid["pitch"], 2),
                    n_bands=grid["n_bands"]),
                reds=reds, slots=slots)

def main():
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description="Extract colored components and raw ink slots.")
    parser.add_argument("first", type=int, nargs="?", default=1)
    parser.add_argument("last", type=int, nargs="?", default=604)
    parser.add_argument("--overwrite", action="store_true",
                        help="explicitly regenerate existing artifacts")
    parser.add_argument("--output-directory", type=Path, default=OUT)
    args = parser.parse_args()
    first, last = args.first, args.last
    if not 1 <= first <= last <= 604:
        parser.error("require 1 <= first <= last <= 604")
    args.output_directory.mkdir(parents=True, exist_ok=True)
    report = dict(first=first, last=last, written=[], skipped=[], failures={},
                  extractor_version="components-v3-white-alpha")
    for n in range(first, last + 1):
        f = args.output_directory / f"page_{n:03d}.json"
        if f.exists() and not args.overwrite:
            report["skipped"].append(n)
            continue
        try:
            d = extract_page(n)
        except Exception as e:
            print(f"page {n}: ERROR {e}", flush=True)
            report["failures"][str(n)] = f"{type(e).__name__}: {e}"
            continue
        f.write_text(json.dumps(d))
        report["written"].append(n)
        print(f"page {n}: red={len(d['reds'])} slots={len(d['slots'])} "
               f"grid={d['grid']}", flush=True)
    report["elapsed_seconds"] = time.perf_counter() - started
    report["source_hashes"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), Path(__file__).with_name("page_scan.py"),
                                         Path(__file__).with_name("image_io.py"))}
    (args.output_directory / "_extraction_report.json").write_text(json.dumps(report, indent=2) + "\n")
    if report["failures"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
