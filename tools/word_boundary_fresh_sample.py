"""Scan-first annotation replay for the frozen 54-position v5 plan.

No OCR text or predicted geometry is read. Handwritten row transcriptions
are resolved against the canonical corpus, retaining every scheduled slot.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from semantic_validation import DATA, ROOT
from word_boundary_fresh_plan import OUTPUT as PLAN, plan
from word_union_review import digest

LABELS = DATA / "audit_word_boundary_fresh_labels_v5.json"
MANUAL = DATA / "audit_manual_word_boundary_fresh_v5.json"


def measure_ink(image, partition, ink_class):
    """Same thresholds as earlier edge audits, with an explicit mixed-ink union."""
    if ink_class not in {"black", "colored", "mixed"}:
        raise AssertionError("unknown annotation ink class")
    x0, y0, x1, y1 = partition
    array = np.asarray(image.crop(partition), dtype=np.int16)
    r, g, b = array[..., 0], array[..., 1], array[..., 2]
    black = (r < 120) & (g < 120) & (b < 120)
    colored = (r > 120) & (r-g > 45)
    mask = black if ink_class == "black" else colored if ink_class == "colored" else black | colored
    yy, xx = np.where(mask)
    if not len(xx):
        raise AssertionError("manual partition contains no target ink")
    return dict(ink_pixels=int(mask.sum()),
                horizontal_partition_contact=bool(xx.min() == 0 or xx.max() == x1-x0-1),
                ink_bbox=[x0+int(xx.min()), y0+int(yy.min()), x0+int(xx.max())+1, y0+int(yy.max())+1])


def frozen_plan():
    saved = json.loads(PLAN.read_text())
    if plan() != saved:
        raise AssertionError("frozen v5 inference rules or sample plan differ")
    return saved


def review(directory):
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    directory.mkdir(parents=True, exist_ok=True)
    for page in frozen_plan()["pages"]:
        n = page["page"]
        image = open_rgb(ROOT / "hayrat-pics" / f"page_{n}.png")
        sheet = Image.new("RGB", (image.width, 3*200), "white")
        draw = ImageDraw.Draw(sheet)
        for k, row in enumerate((2, 7, 12)):
            top = (row-1)*110+5
            sheet.paste(image.crop((0, top, image.width, top+145)), (0, k*200+35))
            draw.text((0, k*200), f"p{n} physical row {row}; original y={top}..{top+145}", fill="black")
            for x in range(0, image.width, 50):
                draw.text((x, k*200+18), str(x), fill="black")
        sheet.save(directory / f"page_{n}.png")


def build(scans=True, stored=None):
    from image_io import open_rgb
    import ocr_corpus_map as cm
    frozen = frozen_plan()
    labels = json.loads(LABELS.read_text())
    if labels["plan_sha256"] != digest(PLAN):
        raise AssertionError("fresh v5 labels refer to another plan")
    if [p["page"] for p in labels["pages"]] != [p["page"] for p in frozen["pages"]]:
        raise AssertionError("fresh v5 annotation page inventory differs")
    tokens, _, _ = cm.virtual_corpus()
    pages = []
    for schedule, page in zip(frozen["pages"], labels["pages"]):
        n = page["page"]
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        saved = next(p for p in stored["pages"] if p["page"] == n) if stored else None
        image = open_rgb(path) if scans else None
        samples = []
        for row in page["rows"]:
            # The verse/start word and first-seven sequence are scan readings,
            # not inferred from a page window or predicted OCR alignment.
            start = next(i for i, t in enumerate(tokens) if t["kind"] == "verse"
                         and (t["verse"], t["word_in_verse"]) == (row["first_verse"], row["first_word_in_verse"]))
            sequence = tokens[start:start+len(row["transcription"])]
            if [t["normalized"] for t in sequence] != row["transcription"]:
                raise AssertionError(f'p{n} row {row["physical_row"]}: scan transcription/canonical sequence differs: '
                                     + str([t["normalized"] for t in sequence]))
            for word in row["samples"]:
                k = word["lexical_position_rtl"]
                if word.get("status") == "unavailable":
                    if k <= len(sequence) or not word.get("reason"):
                        raise AssertionError("unavailable word contradicts row transcription")
                    samples.append(dict(**word, physical_row=row["physical_row"]))
                    continue
                if k > len(sequence):
                    raise AssertionError("scheduled position outside transcribed row")
                truth = sequence[k-1]
                partition, core = word["partition"], word["core_rect"]
                if not (partition[0] <= core[0] < core[2] <= partition[2]
                        and partition[1] <= core[1] < core[3] <= partition[3]):
                    raise AssertionError("independent core lies outside manual partition")
                pixels = measure_ink(image, partition, word["ink_class"]) if scans else saved["word_samples"][len(samples)]["pixels"]
                eligible = word["mark_ownership"] == "clear" and not pixels["horizontal_partition_contact"]
                if word["mark_ownership"] not in {"clear", "uncertain"}:
                    raise AssertionError("missing explicit diacritic ownership decision")
                box = pixels["ink_bbox"]
                samples.append(dict(**word, physical_row=row["physical_row"], kind=truth["kind"], t=truth["t"],
                                    v_id=truth["v_id"], verse=truth["verse"], word_in_verse=truth["word_in_verse"],
                                    form=truth["form"], rect=core, pixels=pixels, x_edges=[box[0], box[2]],
                                    boundary_eligible=eligible, x_edge_tolerance=12,
                                    boundary_exclusion_reasons=(["uncertain_mark_ownership"] if word["mark_ownership"] == "uncertain" else [])
                                    + (["horizontal_partition_contact"] if pixels["horizontal_partition_contact"] else [])))
        positions = [dict(physical_row=w["physical_row"], lexical_position_rtl=w["lexical_position_rtl"]) for w in samples]
        if positions != schedule["positions"]:
            raise AssertionError("fresh v5 scheduled positions missing, duplicated or reordered")
        pages.append(dict(page=n, image_sha256=digest(path) if scans else saved["image_sha256"], word_samples=samples))
    available = [w for p in pages for w in p["word_samples"] if w.get("status") != "unavailable"]
    return dict(version="scan-first-physical-position-annotations-v5", pages=pages,
                summary=dict(scheduled=sum(len(p["word_samples"]) for p in pages), labelled=len(available),
                             unavailable=sum(w.get("status") == "unavailable" for p in pages for w in p["word_samples"]),
                             boundary_evaluable=sum(w["boundary_eligible"] for w in available),
                             uncertain_mark_ownership=sum(w["mark_ownership"] == "uncertain" for w in available),
                             horizontal_partition_contact=sum(w["pixels"]["horizontal_partition_contact"] for w in available)),
                annotation_source_sha256=digest(Path(__file__)),
                inputs={p.name: digest(p) for p in (PLAN, LABELS, cm.mt.TOKENS_F)},
                protocol="One AI reader, full scans and ruled crops read before selected v5 predictions. "
                "All 54 frozen positions independently transcribed from the right, ignoring rosettes; "
                "canonical corpus confirms identities. Independent letter-core rectangles score centers. "
                "Separate whitespace partitions supply thresholded ink edges (black RGB<120, colored R>120 "
                "and R-G>45, explicit union for mixed ink), with explicit visual diacritic "
                "ownership decisions. Uncertain ownership or partition-edge contact excludes boundary scoring. "
                "Horizontal edge tolerance remains the earlier 12px convention. Not independent double "
                "annotation, calibrated corpus accuracy or certified pixel-exact segmentation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--review", type=Path)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--corpus-verses", help="comma-separated scan-read verse IDs; canonical text only")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    if args.review:
        review(args.review)
        return
    if args.corpus_verses:
        import ocr_corpus_map as cm
        tokens, _, _ = cm.virtual_corpus()
        for verse in args.corpus_verses.split(","):
            print(verse, [(t["word_in_verse"], t["normalized"]) for t in tokens
                          if t["kind"] == "verse" and t["verse"] == verse])
        return
    saved = json.loads(MANUAL.read_text()) if args.verify else None
    report = build(not args.verify or args.scans, saved)
    if args.verify:
        if report != saved:
            raise AssertionError("fresh v5 scan-first annotations differ")
        print("PASS fresh v5 annotations, complete schedule, corpus identities, frozen hashes and "
              + ("scan pixels" if args.scans else "stored pixels"))
    else:
        MANUAL.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    for page in report["pages"]:
        print(page["page"], [(w["physical_row"], w["lexical_position_rtl"], w.get("verse"), w.get("word_in_verse"),
                              w.get("form"), w.get("x_edges"), w.get("boundary_eligible"), w.get("status", "labelled"))
                             for w in page["word_samples"]])


if __name__ == "__main__":
    main()
