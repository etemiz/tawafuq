"""Scan-first annotation of the frozen v6 ink-trim validation positions.

No selected OCR text, predicted boxes or comparison outcomes are read here.
Canonical text confirms handwritten scan transcriptions, not their geometry.
"""
import argparse
import json
from pathlib import Path

from semantic_validation import DATA, ROOT
from word_boundary_extent_review import measure_extent
from word_boundary_ownership_policy import measure_support
from word_ink_trim_fresh_plan import OUTPUT as PLAN, plan
from word_union_review import digest

LABELS = DATA / "audit_word_ink_trim_fresh_labels_v6.json"
MANUAL = DATA / "audit_manual_word_ink_trim_fresh_v6.json"


def frozen_plan():
    saved = json.loads(PLAN.read_text())
    if plan() != saved:
        raise AssertionError("frozen ink-trim inference or physical-position plan differs")
    return saved


def review(directory):
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    directory.mkdir(parents=True, exist_ok=True)
    for page in frozen_plan()["pages"]:
        image = open_rgb(ROOT / "hayrat-pics" / f'page_{page["page"]}.png')
        for row in (2, 7, 12):
            top, bottom = (row-1)*110+10, (row-1)*110+140
            crop = image.crop((0, top, image.width, bottom)).resize((image.width*2, (bottom-top)*2))
            sheet = Image.new("RGB", (crop.width, crop.height+55), "white")
            sheet.paste(crop, (0, 55))
            draw = ImageDraw.Draw(sheet)
            draw.text((0, 0), f'p{page["page"]} physical row {row}; scan y={top}..{bottom}; 2x; no OCR geometry', fill="black")
            for x in range(0, image.width, 10):
                draw.line((x*2, 42, x*2, 54), fill="gray")
                if x % 20 == 0:
                    draw.text((x*2, 25), str(x), fill="black")
            for y in range(top, bottom, 10):
                draw.text((0, 55+(y-top)*2), str(y), fill="gray")
            sheet.save(directory / f'p{page["page"]}_r{row}.png')


def scheduled_samples(schedule, page):
    samples = [dict(physical_row=row["physical_row"], lexical_position_rtl=w["lexical_position_rtl"])
               for row in page["rows"] for w in row["samples"]]
    if samples != schedule["positions"]:
        raise AssertionError("scheduled ink-trim positions missing, duplicated or reordered")


def word_crops(directory):
    """Scan and manual-cut context only; never OCR geometry."""
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    frozen_plan()
    directory.mkdir(parents=True, exist_ok=True)
    for page in json.loads(LABELS.read_text())["pages"]:
        image = open_rgb(ROOT / "hayrat-pics" / f'page_{page["page"]}.png')
        for row in page["rows"]:
            for word in row["samples"]:
                if word.get("status") == "unavailable":
                    continue
                x0, y0, x1, y1 = word["partition"]
                left, top, right, bottom = max(0, x0-45), max(0, y0-10), min(image.width, x1+45), min(image.height, y1+10)
                crop = image.crop((left, top, right, bottom)).resize(((right-left)*3, (bottom-top)*3))
                sheet = Image.new("RGB", (crop.width, crop.height+45), "white")
                sheet.paste(crop, (0, 45))
                draw = ImageDraw.Draw(sheet)
                draw.text((0, 0), f'p{page["page"]} row {row["physical_row"]} word {word["lexical_position_rtl"]}; manual cuts only; 3x', fill="black")
                for x in range(((left+9)//10)*10, right, 10):
                    draw.text(((x-left)*3, 24), str(x), fill="black")
                for x in (x0, x1):
                    draw.line(((x-left)*3, 45, (x-left)*3, sheet.height), fill="blue", width=2)
                sheet.save(directory / f'p{page["page"]}_r{row["physical_row"]}_k{word["lexical_position_rtl"]}.png')


def components(selected):
    import numpy as np
    from scipy.ndimage import label as index_components, find_objects
    from image_io import open_rgb
    frozen_plan()
    wanted = {tuple(map(int, key.split(":"))) for key in selected.split(",")}
    for page in json.loads(LABELS.read_text())["pages"]:
        image = open_rgb(ROOT / "hayrat-pics" / f'page_{page["page"]}.png')
        for row in page["rows"]:
            for word in row["samples"]:
                key = (page["page"], row["physical_row"], word["lexical_position_rtl"])
                if key not in wanted or word.get("status") == "unavailable":
                    continue
                x0, y0, x1, y1 = word["partition"]
                x0, x1 = max(0, x0-40), min(image.width, x1+40)
                pixels = np.asarray(image.crop((x0, y0, x1, y1)), dtype=np.int16)
                r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
                for name, mask in (("black", (r < 120) & (g < 120) & (b < 120)),
                                   ("colored", (r > 120) & (r-g > 45))):
                    indexed, _ = index_components(mask, np.ones((3, 3)))
                    boxes = []
                    for index, slices in enumerate(find_objects(indexed), 1):
                        if slices is not None:
                            ys, xs = slices
                            boxes.append(dict(bbox=[x0+xs.start, y0+ys.start, x0+xs.stop, y0+ys.stop],
                                              pixels=int(np.sum(indexed[slices] == index))))
                    print(key, name, sorted(boxes, key=lambda r: r["bbox"]))


def build(scans=True, stored=None):
    from image_io import open_rgb
    import ocr_corpus_map as cm
    frozen = frozen_plan()
    labels = json.loads(LABELS.read_text())
    if labels["plan_sha256"] != digest(PLAN):
        raise AssertionError("ink-trim labels refer to another plan")
    if [p["page"] for p in labels["pages"]] != [p["page"] for p in frozen["pages"]]:
        raise AssertionError("ink-trim annotation page inventory differs")
    tokens, _, _ = cm.virtual_corpus()
    pages = []
    for schedule, page in zip(frozen["pages"], labels["pages"]):
        scheduled_samples(schedule, page)
        n = page["page"]
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        saved = next(p for p in stored["pages"] if p["page"] == n) if stored else None
        image = open_rgb(path) if scans else None
        samples = []
        for row in page["rows"]:
            start = next(i for i, t in enumerate(tokens) if t["kind"] == "verse" and
                         (t["verse"], t["word_in_verse"]) == (row["first_verse"], row["first_word_in_verse"]))
            sequence = tokens[start:start+len(row["transcription"])]
            if [t["normalized"] for t in sequence] != row["transcription"]:
                raise AssertionError(f'p{n} row {row["physical_row"]}: scan/canonical transcription differs: '
                                     + str([t["normalized"] for t in sequence]))
            for label in row["samples"]:
                k = label["lexical_position_rtl"]
                if label.get("status") == "unavailable":
                    if k <= len(sequence) or not row.get("row_complete") or not label.get("reason"):
                        raise AssertionError("unavailable slot needs a completely read shorter row and reason")
                    samples.append(dict(**label, physical_row=row["physical_row"]))
                    continue
                if k > len(sequence):
                    raise AssertionError("scheduled word missing from scan transcription")
                truth = sequence[k-1]
                partition, core = label["partition"], label["core_rect"]
                if not (0 <= partition[0] <= core[0] < core[2] <= partition[2] <= 1024
                        and 0 <= partition[1] <= core[1] < core[3] <= partition[3] <= 1680):
                    raise AssertionError("scan partition/core outside bounds or not nested")
                if label["mark_ownership"] not in {"clear", "uncertain"} or not label.get("note"):
                    raise AssertionError("explicit mark ownership and scan note required")
                if scans:
                    pixels, bounds = measure_extent(image, label)
                    support = measure_support(image, label)
                else:
                    measured = saved["word_samples"][len(samples)]
                    pixels, bounds, support = measured["pixels"], measured["ownership_bounds"], measured["measured_edge_support"]
                specified = label["mark_ownership"] == "clear" or bounds["alternatives_specified"]
                contact = pixels["horizontal_partition_contact"]
                ownership_evaluable = specified and not contact
                eligible = ownership_evaluable and bounds["horizontal_invariant"]
                reasons = ([] if specified else ["unspecified_mark_ownership_alternatives"])
                reasons += ["horizontal_partition_contact"] if contact else []
                reasons += ["nonunique_horizontal_edges"] if ownership_evaluable and not eligible else []
                samples.append(dict(**label, physical_row=row["physical_row"], kind=truth["kind"], t=truth["t"],
                                    v_id=truth["v_id"], verse=truth["verse"], word_in_verse=truth["word_in_verse"], form=truth["form"],
                                    rect=core, pixels=pixels, ownership_bounds=bounds, measured_edge_support=support,
                                    edge_support=support if ownership_evaluable else None,
                                    x_edges=[pixels["ink_bbox"][0], pixels["ink_bbox"][2]], x_edge_tolerance=12,
                                    boundary_eligible=eligible, ownership_evaluable=ownership_evaluable,
                                    boundary_exclusion_reasons=reasons))
        pages.append(dict(page=n, image_sha256=digest(path) if scans else saved["image_sha256"], word_samples=samples))
    words = [w for p in pages for w in p["word_samples"] if w.get("status") != "unavailable"]
    return dict(version="scan-first-ink-trim-physical-position-annotations-v6", pages=pages,
                summary=dict(scheduled=sum(len(p["word_samples"]) for p in pages), labelled=len(words),
                             unavailable=sum(w.get("status") == "unavailable" for p in pages for w in p["word_samples"]),
                             boundary_evaluable=sum(w["boundary_eligible"] for w in words),
                             ownership_evaluable=sum(w["ownership_evaluable"] for w in words),
                             uncertain_mark_ownership=sum(w["mark_ownership"] == "uncertain" for w in words),
                             horizontal_partition_contact=sum(w["pixels"]["horizontal_partition_contact"] for w in words)),
                annotation_source_sha256=digest(Path(__file__)), inputs={p.name: digest(p) for p in (PLAN, LABELS, cm.mt.TOKENS_F)},
                protocol="One AI reader, scan-only enlarged rows with coordinate rulers and no OCR boxes, before selected predictions. Canonical corpus confirms independently transcribed identities. Original physical slots and 12px horizontal tolerance retained. Independent letter cores score recomputed centers. Full-ink partitions and explicit mandatory/possible alternatives determine fixed edges or exact all-ownership support; unspecified uncertainty or horizontal partition contact excludes scoring. Not independent double annotation, pixel-exact segmentation certification or uniform-word corpus accuracy.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--review", type=Path)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--corpus-verses")
    modes.add_argument("--word-crops", type=Path)
    modes.add_argument("--components")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    if args.review:
        review(args.review)
    elif args.word_crops:
        word_crops(args.word_crops)
    elif args.components:
        components(args.components)
    elif args.corpus_verses:
        import ocr_corpus_map as cm
        tokens, _, _ = cm.virtual_corpus()
        for verse in args.corpus_verses.split(","):
            print(verse, [(t["word_in_verse"], t["normalized"]) for t in tokens if t["kind"] == "verse" and t["verse"] == verse])
    else:
        saved = json.loads(MANUAL.read_text()) if args.verify else None
        report = build(scans=args.build or args.scans, stored=saved)
        if args.verify:
            if report != saved:
                raise AssertionError("scan-first ink-trim annotations differ")
            print("PASS all frozen ink-trim slots, scan labels, ownership assumptions and provenance")
        else:
            MANUAL.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print(report["summary"])
        for page in report["pages"]:
            for word in page["word_samples"]:
                print(page["page"], word["physical_row"], word["lexical_position_rtl"], word.get("verse"), word.get("form"),
                      word.get("x_edges"), word.get("boundary_eligible"), word.get("boundary_exclusion_reasons"), word.get("status", "labelled"))


if __name__ == "__main__":
    main()
