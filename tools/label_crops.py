import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
PICS = ROOT.parent / "hayrat-pics"
DATA = ROOT / "data" / "real_boxes"
FEATS = ROOT / "data" / "red_feats.npz"
OUT = Path("/tmp/opencode/cluster_sheets")
NC = 14

def main():
    d = np.load(FEATS)
    X, lab, C, meta = d["X"], d["lab"], d["C"], d["meta"]
    OUT.mkdir(parents=True, exist_ok=True)
    ims = {}

    def get_page(n):
        if n not in ims:
            ims[n] = Image.open(PICS / f"page_{n}.png").convert("L")
        return ims[n]

    def crop(n, i, pad=8, scale=2):
        r = json.loads((DATA / f"page_{n:03d}.json").read_text())["reds"][i]
        x0, y0, x1, y1 = r["x0"], r["y0"], r["x1"], r["y1"]
        im = get_page(n)
        c = im.crop((max(0, x0 - pad), max(0, y0 - pad),
                     min(im.width, x1 + pad), min(im.height, y1 + pad)))
        return c.resize((c.width * scale, c.height * scale), Image.LANCZOS)

    summary = []
    for c in range(NC):
        idx = np.where(lab == c)[0]
        D = ((X[idx] - C[c]) ** 2).sum(axis=1)
        order = idx[np.argsort(D)]
        near = list(order[:8])
        rng = np.random.default_rng(7)
        rest = order[8:]
        far = list(rng.choice(rest, size=min(4, len(rest)), replace=False)) if len(rest) else []
        sel = near + far
        cells = []
        for i in sel:
            n, j = int(meta[i, 0]), int(meta[i, 1])
            try:
                cells.append((crop(n, j), f"c{c} #{i} p{n}:{j}"))
            except Exception as e:
                print(f"skip {i} p{n}:{j}: {e}")
        cols = 6
        rows = (len(cells) + cols - 1) // cols
        cw, ch = 260, 160
        sheet = Image.new("L", (cols * cw, rows * ch), 255)
        dr = ImageDraw.Draw(sheet)
        for k, (im, tag) in enumerate(cells):
            gx, gy = (k % cols) * cw, (k // cols) * ch
            if im.width > cw or im.height > ch - 20:
                s = min(cw / im.width, (ch - 20) / im.height)
                im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
            sheet.paste(im, (gx + (cw - im.width) // 2, gy + 20))
            dr.text((gx + 6, gy + 4), tag, fill=0)
        sheet.save(OUT / f"cluster_{c:02d}.png")
        summary.append((c, len(idx)))

    for c, n in summary:
        print(f"cluster {c}: n={n} -> {OUT / f'cluster_{c:02d}.png'}")

if __name__ == "__main__":
    main()