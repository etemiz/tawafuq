"""Article figure plates v5 (user-directed): RTL page order (lower page number
on the right, Arabic reads right-to-left), boxes sized from real word bboxes,
page-turn example switched to the p530|531 Ar-Rahman refrain spread.

Outputs docs/articles/figs/*.png. Data: tools/data/real_boxes (reds + grid).
"""
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PICS = ROOT / "hayrat-pics"
FIGS = ROOT / "docs" / "articles" / "figs"

CRI = (228, 41, 107)
BLUE = (40, 60, 200)
MAG = (200, 30, 150)
GOLD = (190, 150, 30)

try:
    FONT = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    FONT_S = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
except OSError:
    FONT = FONT_S = ImageFont.load_default()


def load(p):
    return Image.open(PICS / f"page_{p}.png").convert("RGB")


def boxes_of(p):
    d = json.load(open(ROOT / f"tools/data/real_boxes/page_{p:03d}.json"))
    return d["reds"]


def cluster_columns(reds, tol=110):
    """Group reds into x-clusters (candidate columns); return list of groups."""
    reds = sorted(reds, key=lambda r: (r["x0"] + r["x1"]) / 2)
    groups = []
    for r in reds:
        c = (r["x0"] + r["x1"]) / 2
        if groups and c - (groups[-1][-1]["x0"] + groups[-1][-1]["x1"]) / 2 <= tol:
            groups[-1].append(r)
        else:
            groups.append([r])
    return groups


def wbox(d, r, color, pad_x=10, pad_y=7, width=4):
    """Box a word from its real bbox, padded so the whole word is inside."""
    d.rectangle([r["x0"] - pad_x, r["y0"] - pad_y,
                 r["x1"] + pad_x, r["y1"] + pad_y],
                outline=color + (255,), width=width)


def dashed_vline(d, x, y0, y1, color, dash=16, gap=12, width=3):
    y = y0
    while y < y1:
        d.line([x, y, x, min(y + dash, y1)], fill=color + (220,), width=width)
        y += dash + gap


def labeled_pair(lo, hi, out_name, title, blue_cluster="max", blue_min=3,
                 annotate=True):
    """Two pages side by side, RTL: lower page number on the RIGHT.

    lo = even (right page), hi = odd (left page) for real spreads;
    for far-apart comparison pairs the same convention is applied.
    """
    left_img, right_img = load(hi), load(lo)
    W = left_img.width + right_img.width + 24
    BAND = 52
    canvas = Image.new("RGB", (W, left_img.height + BAND), "white")
    canvas.paste(left_img, (0, BAND))
    canvas.paste(right_img, (left_img.width + 24, BAND))
    d0 = ImageDraw.Draw(canvas)
    d0.rectangle([0, 0, W, BAND], fill=(250, 247, 241))
    d0.text((24, 10), title, fill=(25, 25, 25), font=FONT_S)
    if annotate:
        for img, page, x_off, outer in ((left_img, hi, 0, "left"),
                                        (right_img, lo, left_img.width + 24, "right")):
            d = ImageDraw.Draw(img, "RGBA")
            reds = boxes_of(page)
            groups = cluster_columns(reds)
            if blue_cluster == "max":
                best = max(groups, key=len)
                blues = best if len(best) >= blue_min else []
            else:
                blues = []
            for r in reds:
                if any(r is b for b in blues):
                    wbox(d, r, BLUE, width=5)
                else:
                    wbox(d, r, CRI, width=3)
            if blues:
                xs = [(b["x0"] + b["x1"]) / 2 for b in blues]
                ys0 = min(b["y0"] for b in blues) - 26
                ys1 = max(b["y1"] for b in blues) + 26
                dashed_vline(d, int(np.mean(xs)), ys0, ys1, BLUE)
            canvas.paste(img, (x_off, BAND))
        # page badge in each page's OUTER top corner
        for x_off, page_no, outer in ((0, hi, "left"),
                                      (left_img.width + 24, lo, "right")):
            txt = f"p.{page_no}"
            tw = d0.textlength(txt, font=FONT_S)
            bx = x_off + 10 if outer == "left" else x_off + left_img.width - tw - 26
            by = BAND + 10
            d0.rectangle([bx - 8, by - 6, bx + tw + 10, by + 38],
                         fill=(255, 255, 255), outline=(120, 30, 30), width=2)
            d0.text((bx, by), txt, fill=(120, 30, 30), font=FONT_S)
    if canvas.width > 2100:
        canvas = canvas.resize((2100, round(canvas.height * 2100 / canvas.width)),
                               Image.LANCZOS)
    canvas.save(FIGS / out_name)
    print(out_name, canvas.size)


def strips_530_531():
    """Page-turn example: Ar-Rahman refrain + dual-verb echoes across the leaf.
    Per-row magenta boxes (no union towers); dashed connectors in the gap where
    both strips share x ranges."""
    a = load(530).crop((0, 1455, 1024, 1670))   # bottom strip rows: 55:14, 55:15+refrain
    b = load(531).crop((0, 44, 1024, 322))      # top strip rows: 55:17+refrain, 19-20, refrain 21
    LABEL_H = 46
    GAP = 26
    W = 1024
    canvas = Image.new("RGB", (W, LABEL_H + a.height + GAP + LABEL_H + b.height),
                       "white")
    d = ImageDraw.Draw(canvas)

    def label(y, txt):
        d.rectangle([0, y, W, y + LABEL_H], fill=(250, 247, 241))
        d.rectangle([0, y, 7, y + LABEL_H], fill=(228, 41, 107))
        d.rectangle([0, y + LABEL_H - 2, W, y + LABEL_H], fill=(232, 226, 214))
        d.text((22, y + 9), txt, fill=(25, 25, 25), font=FONT_S)

    label(0, "p.530  BOTTOM strip — Ar-Rahman 55:14-16, ending with the refrain")
    canvas.paste(a, (0, LABEL_H))
    y2 = LABEL_H + a.height + GAP
    label(y2, "p.531  TOP strip — Ar-Rahman 55:17-21, the refrain again")
    canvas.paste(b, (0, y2 + LABEL_H))

    da = ImageDraw.Draw(canvas, "RGBA")

    def mag_mask(im):
        arr = np.asarray(im).astype(int)
        redish = (arr[:, :, 0] - arr[:, :, 1] > 45) & (arr[:, :, 0] > 120)
        return redish & ((arr[:, :, 2] - arr[:, :, 1]) > 90)

    def row_bands(mask, min_ink=25, gap=8):
        rowink = mask.sum(axis=1)
        ys = [y for y in range(len(rowink)) if rowink[y] > min_ink]
        groups = []
        for y in ys:
            if groups and y - groups[-1][-1] <= gap:
                groups[-1].append(y)
            else:
                groups.append([y])
        return [(g[0], g[-1]) for g in groups if g[-1] - g[0] > 20]

    def x_runs(mask, y0, y1, min_px=24, gap=14):
        colsum = mask[y0:y1 + 1].sum(axis=0)
        runs, start, gp = [], None, 0
        for x, v in enumerate(colsum > 3):
            if v:
                if start is None:
                    start = x
                gp = 0
            elif start is not None:
                gp += 1
                if gp > gap:
                    if x - gp + 1 - start >= min_px:
                        runs.append((start, x - gp))
                    start, gp = None, 0
        if start is not None:
            runs.append((start, len(colsum) - 1))
        return runs

    all_runs = {}
    for name, im, y_off in (("a", a, LABEL_H), ("b", b, y2 + LABEL_H)):
        mask = mag_mask(im)
        runs_all = []
        for y0, y1 in row_bands(mask):
            for x0, x1 in x_runs(mask, y0, y1):
                da.rectangle([x0 - 3, y_off + y0 - 4, x1 + 3, y_off + y1 + 4],
                             outline=MAG + (255,), width=4)
                runs_all.append((x0, x1))
        all_runs[name] = runs_all
    # dashed connectors across the white gap where both strips share x ranges
    for x0a, x1a in all_runs["a"]:
        for x0b, x1b in all_runs["b"]:
            lo, hi = max(x0a, x0b), min(x1a, x1b)
            if hi - lo >= 25:
                cx = (lo + hi) // 2
                dashed_vline(da, cx, LABEL_H + a.height - 8, y2 + 8,
                             (120, 120, 130), dash=9, gap=7, width=2)
    canvas.save(FIGS / "strips_p530_531.png")
    print("strips_p530_531.png", canvas.size)


if __name__ == "__main__":
    # labeled_pair(lo, hi): hi is drawn on the LEFT, lo (lower page number) on the RIGHT
    labeled_pair(82, 83, "spread_p82_83.png",
                 "Facing pages 82|83 as the book opens — p.82 on the right (Arabic reads right to left)")
    labeled_pair(62, 63, "pages62_63_columns.png",
                 "Pages 62|63 — p.62 on the right (Arabic reads right to left)")
    labeled_pair(530, 531, "raw_p530_531.png",
                 "Printed pages 530 | 531 — p.530 on the right (Arabic reads right to left)",
                 annotate=False)
    strips_530_531()
    for dead in ("raw_p82_83.png", "raw_p62_63.png", "raw_p422.png",
                 "raw_p154_155.png", "raw_p181_194.png", "p181_columns.png",
                 "raw_p1.png"):
        f = FIGS / dead
        if f.exists():
            f.unlink()
            print("removed", dead)
