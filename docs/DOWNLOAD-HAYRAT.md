# Downloading the Hayrat page scans (not redistributed here)

This repository does **not** include the 604 page images of the Hayrat
Nesriyat *"Qur'an in Tawafuq"* mushaf. They are published commercial scans;
download them yourself from the publisher's public reader, for personal study
and replication. Everything in `tools/` that needs pixels reads them from a
local `hayrat-pics/` directory (gitignored).

## Source

- Publisher reader: <https://kuran.hayrat.com.tr/kuran-oku/?sayfa=0>
- Page images: `https://kuran.hayrat.com.tr/Sayfalar/<N>.jpg`
- The reader is 0-indexed and serves 609 pages (`pageCount: 609` in
  `assets/js/quran-reader-data.js`): index 0 = Sura Fatiha, index 1 = start of
  Bakara, …, index 604 = Ihlas/Falak/Nas, index 605 = Hatim prayer, plus a
  few trailing pages.

## What this project used

The project corpus is **indices 1–604** (604 files, named `page_N.png` in the
original working copy). Index 0 (Fatiha) is **not** part of the corpus: local
`page_1` begins with the Basmala and Baqara 2:1–5.

Index mapping verified on 2026-10-21 by crimson-ornament mask IoU between the
local PNGs and the publisher JPEGs for N ∈ {1, 2, 3, 4, 62, 63, 422, 602, 603,
604} (IoU 0.79–0.997; page 1 lower because of crop-height differences).

## Download

```bash
mkdir -p hayrat-pics
for i in $(seq 1 604); do
  curl -fsSL -o "hayrat-pics/page_${i}.jpg" \
    "https://kuran.hayrat.com.tr/Sayfalar/${i}.jpg"
done
```

Roughly 450 MB total (JPEGs ~0.7–0.8 MB each, typically 1024×1680; the first
pages are shorter, 1024×1531).

## Important caveats

- **Byte-identity:** the publisher currently serves JPEGs. The original
  project corpus was re-encoded palette PNGs of the same pages (Adobe
  ImageReady metadata). The pages match visually (mean absolute gray
  difference ≈ 22–34/255 on spot checks) but **file hashes and
  threshold-dependent pixel measurements are encoding-specific**. Any
  committed sha256 over PNG scans describes that encoding, not the JPEGs.
  Analysis code renders images on white (`tools/image_io.py`); transparent
  PNGs must not be read as RGB directly.
- **Page numbering:** file `page_N.png` / URL index N is the *reader index*,
  not necessarily the printed folio number. The reader numbers from 0, so
  reader index N corresponds to printed page N+1 of this edition. The
  article's phrase "file N = printed page N" refers to the local file naming.
- **Verse map:** `tools/data/page_verse_map.json` maps each corpus index to
  the sura:verse range that starts on that page (built from the gold rosette
  chain, not from the reader).
- **Self-check (optional):** to confirm your copies are the same pages, run
  the crimson-ornament IoU comparison described above against a few pages you
  also cross-check by eye in the publisher reader.

## Rights

The scans remain Hayrat Nesriyat's published material. This repository
redistributes neither the images nor derived watermarked copies; figures in
`media/` and `docs/articles/figs/` are measurement graphics and annotated
crops used under fair-study/quotation practice with attribution.
