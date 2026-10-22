"""Article crop images from hayrat-pics (user-approved for the articles).

Outputs docs/articles/figs/*.png. Annotations use committed data:
real_boxes (reds + grid) and mark_identity.json (runs with bands).
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
PICS = ROOT / "hayrat-pics"
FIGS = ROOT / "docs" / "articles" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

CRI = (228, 41, 107)
BLUE = (40, 60, 200)
GREEN = (30, 130, 50)
MAG = (200, 30, 150)
BAND_H = 55  # half-height of a text line for highlight boxes


def load(p):
    return Image.open(PICS / f"page_{p}.png").convert("RGB")


def save(im, name, width=None):
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)),
                       Image.LANCZOS)
    im.save(FIGS / name)
    print(name, im.size)


def grid_of(p):
    return json.load(open(ROOT / f"tools/data/real_boxes/page_{p:03d}.json"))["grid"]["centers"]


def box_run(d, band_cy, x0, x1, color, h=BAND_H, width=4):
    cy = band_cy
    d.rectangle([x0 - 4, cy - h, x1 + 4, cy + h], outline=color + (255,),
                width=width)


def dashed_vline(d, x, y0, y1, color, dash=14, gap=10, width=3):
    y = y0
    while y < y1:
        d.line([x, y, x, min(y + dash, y1)], fill=color + (230,), width=width)
        y += dash + gap


def annotated_422():
    im = load(422)
    d = ImageDraw.Draw(im, "RGBA")
    reds = json.load(open(ROOT / "tools/data/real_boxes/page_422.json"))["reds"]
    for r in reds:
        d.rectangle([r["x0"], r["y0"], r["x1"], r["y1"]],
                    outline=CRI + (255,), width=3)
    d.rectangle([318, 30, 418, 1650], fill=(40, 40, 200, 28),
                outline=(40, 40, 200, 160), width=3)
    save(im, "page422_annotated.png", width=760)
    zoom = im.crop((260, 20, 470, 1660))
    save(zoom, "page422_column_zoom.png", width=300)


def annotated_62_63():
    """Two facing pages, each with a same-page Allah column (claim B2)."""
    a, b = load(62), load(63)
    ga, gb = grid_of(62), grid_of(63)
    da, db = ImageDraw.Draw(a, "RGBA"), ImageDraw.Draw(b, "RGBA")
    # p62: column x475-565 on bands 1,2,3,6,14 (5 words) - BLUE
    for band in (1, 2, 3, 6, 14):
        box_run(da, ga[band], 475, 565, BLUE)
    dashed_vline(da, 520, ga[1] - BAND_H, ga[14] + BAND_H, BLUE)
    # other crimson words on p62: outline crimson
    for x0, x1, band in [(30, 94, 0), (807, 876, 4), (799, 870, 13),
                         (30, 97, 13)]:
        box_run(da, ga[band], x0, x1, CRI, h=48, width=3)
    # p63: column x162-276 on bands 0,2,6,8 (4 words) - BLUE
    for band, x0, x1 in [(0, 162, 234), (2, 181, 276), (6, 163, 236),
                         (8, 166, 230)]:
        box_run(db, gb[band], x0, x1, BLUE)
    dashed_vline(db, 220, gb[0] - BAND_H, gb[8] + BAND_H, BLUE)
    for x0, x1, band in [(902, 993, 0), (924, 994, 11), (345, 417, 7),
                         (351, 419, 14)]:
        box_run(db, gb[band], x0, x1, CRI, h=48, width=3)
    canvas = Image.new("RGB", (a.width + b.width + 24, a.height), "white")
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + 24, 0))
    save(canvas, "pages62_63_columns.png", width=1150)


def annotated_181():
    """Claim C1: right column on claimed line numbers, left column too."""
    im = load(181)
    g = grid_of(181)
    d = ImageDraw.Draw(im, "RGBA")
    # right column members (bands 2,3,8,14 = lines 3,4,9,15 crimson;
    # bands 6,12 = lines 7,13 the Allah rides a magenta phrase run)
    right = [(2, 768, 859), (3, 768, 894), (8, 767, 833), (14, 763, 837),
             (6, 705, 843), (12, 705, 843)]
    left = [(0, 334, 405), (7, 338, 409), (9, 334, 406), (12, 335, 405)]
    for band, x0, x1 in right:
        box_run(d, g[band], x0, x1, BLUE, h=50, width=4)
    for band, x0, x1 in left:
        box_run(d, g[band], x0, x1, GREEN, h=50, width=4)
    dashed_vline(d, 820, g[2] - BAND_H, g[14] + BAND_H, BLUE)
    dashed_vline(d, 371, g[0] - BAND_H, g[12] + BAND_H, GREEN)
    save(im, "p181_columns.png", width=780)


def magenta_runs(im, thresh_px=30):
    """Tight x-ranges of magenta ink clusters in a crop (pixel-true)."""
    a = np.asarray(im).astype(int)
    redish = (a[:, :, 0] - a[:, :, 1] > 45) & (a[:, :, 0] > 120)
    # magenta ink has B-G ~ 120; crimson has B-G ~ 60 -> clean separation,
    # so crimson halos do not leak into the magenta mask
    mag = redish & ((a[:, :, 2] - a[:, :, 1]) > 90)
    colsum = mag.sum(axis=0)
    runs, start = [], None
    gap = 0
    for x, v in enumerate(colsum > 3):
        if v:
            if start is None:
                start = x
            gap = 0
        elif start is not None:
            gap += 1
            if gap > 14:
                if x - gap + 1 - start >= thresh_px:
                    runs.append((start, x - gap))
                start, gap = None, 0
    if start is not None and len(colsum) - start >= thresh_px:
        runs.append((start, len(colsum) - 1))
    return runs, mag


def mag_boxes(d, y_off, im, color=MAG, width=5):
    """Draw tight boxes around magenta ink clusters of a strip crop."""
    runs, mag = magenta_runs(im)
    for x0, x1 in runs:
        ys = np.where(mag[:, x0:x1 + 1].any(axis=1))[0]
        if len(ys) == 0:
            continue
        y0, y1 = ys[0], ys[-1]
        d.rectangle([x0 - 3, y_off + y0 - 3, x1 + 3, y_off + y1 + 3],
                    outline=color + (255,), width=width)
    return runs


def strips_154_155():
    """Page-turn echo, labeled; magenta words boxed by pixel detection."""
    import numpy as np
    a = load(154).crop((0, 1500, 1024, 1680))   # bottom strip = 7:43 tail
    b = load(155).crop((0, 40, 1024, 230))      # top strip = 7:44 head
    LABEL_H = 46
    W = 1024
    canvas = Image.new("RGB", (W, LABEL_H + a.height + LABEL_H + b.height),
                       "white")
    d = ImageDraw.Draw(canvas)
    from PIL import ImageFont
    try:
        font = ImageFont.truetype(
            "/usr/share/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except OSError:
        font = ImageFont.load_default()

    def label(y, txt):
        d.rectangle([0, y, W, y + LABEL_H], fill=(250, 247, 241))
        d.rectangle([0, y, 7, y + LABEL_H], fill=(228, 41, 107))
        d.rectangle([0, y + LABEL_H - 2, W, y + LABEL_H], fill=(232, 226, 214))
        d.text((22, y + 10), txt, fill=(25, 25, 25), font=font)

    label(0, "p.154  BOTTOM strip — the end of verse 7:43")
    canvas.paste(a, (0, LABEL_H))
    y2 = LABEL_H + a.height
    label(y2, "p.155  TOP strip — the beginning of verse 7:44")
    canvas.paste(b, (0, y2 + LABEL_H))
    da = ImageDraw.Draw(canvas, "RGBA")
    mag_boxes(da, LABEL_H, a)          # p154 strip words, pixel-tight
    mag_boxes(da, y2 + LABEL_H, b)     # p155 strip words, pixel-tight
    save(canvas, "strips_p154_155.png", width=1024)


if __name__ == "__main__":
    annotated_422()
    annotated_62_63()
    annotated_181()
    strips_154_155()