import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
PICS = ROOT.parent / "hayrat-pics"
DATA = ROOT / "data" / "real_boxes"
FEATS = ROOT / "data" / "red_feats.npz"
OUT = Path("/tmp/opencode/cluster_sheets")

def main():
    d = np.load(FEATS)
    X, lab, C, meta = d["X"], d["lab"], d["C"], d["meta"]
    ims = {}

    def get_page(n):
        if n not in ims:
            ims[n] = Image.open(PICS / f"page_{n}.png").convert("RGB")
        return ims[n]

    for c, nrand in [(3, 8), (10, 12), (11, 4), (5, 4)]:
        idx = np.where(lab == c)[0]
        D = ((X[idx] - C[c]) ** 2).sum(axis=1)
        near = list(idx[np.argsort(D)[:4]])
        rng = np.random.default_rng(7)
        rest = list(idx[np.argsort(D)[4:]])
        far = list(rng.choice(rest, size=min(nrand - 4, len(rest)), replace=False)) if rest else []
        sel = near + far
        cells = []
        for i in sel:
            n, j = int(meta[i, 0]), int(meta[i, 1])
            r = json.loads((DATA / f"page_{n:03d}.json").read_text())["reds"][j]
            x0, y0, x1, y1 = r["x0"], r["y0"], r["x1"], r["y1"]
            pad, pady = 250, 40
            im = get_page(n)
            crop = im.crop((max(0, x0 - pad), max(0, y0 - pady),
                            min(im.width, x1 + pad), min(im.height, y1 + pady)))
            crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
            cells.append((crop, f"c{c} #{i} p{n}:{j} L{r['line']} w={r['w']} h={r['h']}"))
        cols = 2
        rows = (len(cells) + cols - 1) // cols
        cw, ch = 720, 220
        sheet = Image.new("RGB", (cols * cw, rows * ch), (255,255,255))
        dr = ImageDraw.Draw(sheet)
        for k, (im, tag) in enumerate(cells):
            gx, gy = (k % cols) * cw, (k // cols) * ch
            if im.width > cw or im.height > ch - 20:
                s = min(cw / im.width, (ch - 20) / im.height)
                im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
            sheet.paste(im, (gx + (cw - im.width) // 2, gy + 20))
            dr.text((gx + 6, gy + 4), tag, fill=(0,0,0))
        sheet.save(OUT / f"context_{c:02d}.png")
        print(f"context {c} -> {OUT / f'context_{c:02d}.png'}")

if __name__ == "__main__":
    main()