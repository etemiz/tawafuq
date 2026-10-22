"""Frozen-rule fresh row/word sample, read before inspecting v4 predictions.

Six stratified non-ornament pages: second canonical lexical word on printed
text rows 3, 8 and 13. Two separately hash-selected top-ornament pages check
their unencoded basmala name. One AI reader supplies independent partitions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import ocr_observation_map as om
import ocr_corpus_map as cm
from semantic_validation import DATA, ROOT

PLAN = DATA / "audit_row_sample_plan_v4.json"
MANUAL = DATA / "audit_manual_row_sample_v4.json"
SEED = "t2-seeded-rows-fresh-words-v4-2026-10-19"
STRATA = [(101, 180), (181, 260), (261, 340), (341, 420), (421, 500), (501, 579)]
SOURCES = ["ocr_reading_order.py", "ocr_row_map.py", "ocr_observation_map.py", "ocr_corpus_map.py"]

# Directly read from unlabelled full scans and ruler crops before predictions.
# Entries: verse, normalized token (or explicit word number), occurrence,
# horizontal whitespace partition, ink class. Rows are 3, 8 and 13.
LABELS = {
    163: [("7:106", "كنت", 1, (860, 957), "black"),
          ("7:112", "بكل", 1, (742, 847), "black"),
          ("7:117", "عصاك", 1, (790, 923), "colored")],
    252: [("13:30", "اوحينا", 1, (786, 916), "black"),
          ("13:31", "من", 1, (839, 906), "black"),
          ("13:33", "القول", 1, (819, 932), "black")],
    317: [("20:89", "ولا", 1, (800, 918), "black"),
          ("20:94", 2, 1, (806, 925), "black"),
          ("20:97", "موعدا", 1, (792, 920), "black")],
    355: [("24:45", "من", 3, (790, 845), "black"),
          ("24:48", "اذا", 1, (820, 882), "black"),
          ("24:52", "الله", 1, (832, 902), "colored")],
    448: [("37:81", "المؤمنين", 1, (728, 877), "black"),
          ("37:92", "لكم", 1, (886, 953), "black"),
          ("37:101", "حليم", 1, (766, 875), "black")],
    543: [("58:13", "ان", 1, (815, 860), "black"),
          ("58:16", "اتخذوا", 1, (697, 807), "black"),
          ("58:19", "ذكر", 1, (736, 827), "black")],
}
HEADS = {311: ("20:0", [250, 570, 338, 674]), 321: ("21:0", [225, 235, 315, 340])}


def plan():
    excluded = {67, 83, 171, 204, 209, 231, 315, 316, 378, 457, 510, 542, 574,
                1, 49, 154, 186, 206, 207, 422, 489, 567, 604}
    for name in ("audit_manual_semantic_sample.json", "audit_manual_ocr_heldout.json",
                 "audit_manual_word_validation_v2.json", "audit_manual_corpus_map_sample_v1.json",
                 "audit_manual_ornament_scope_v2.json"):
        excluded.update(p["page"] for p in json.loads((DATA / name).read_text())["pages"])
    bands = {p["page"]: p["bands"] for p in json.loads(om.ORNAMENTS.read_text())["pages"]}
    rank = lambda n: hashlib.sha256(f"{SEED}:{n}".encode()).hexdigest()
    ordinary = [min((n for n in range(lo, hi+1) if n not in excluded and not bands[n]), key=rank)
                for lo, hi in STRATA]
    headers = sorted((n for n, rows in bands.items() if 101 <= n <= 579 and n not in excluded
                      and n not in ordinary and any(lo < 400 for lo, hi in rows)), key=rank)[:2]
    return dict(version="seeded-row-fresh-sample-plan-v4", seed=SEED, ordinary_pages=ordinary,
                basmala_pages=headers, strata=[list(s) for s in STRATA], excluded_pages=sorted(excluded),
                rule_sources={name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest() for name in SOURCES},
                ornament_sha256=hashlib.sha256(om.ORNAMENTS.read_bytes()).hexdigest(),
                protocol="Selection and inference code frozen before this reader inspects the selected pages' "
                "v4 word predictions. Six non-ornament pages, second canonical lexical word on text rows "
                "3/8/13; two supplementary top-header basmala names. Prior labels and targeted failures excluded. "
                "Full v4 predictions may already exist on disk but are not read to supply annotation truth.")


def build(scans=True, stored=None):
    from adjudicate_word_sample import measure
    from image_io import open_rgb
    frozen = json.loads(PLAN.read_text())
    if plan() != frozen or frozen["ordinary_pages"] != list(LABELS) or frozen["basmala_pages"] != list(HEADS):
        raise AssertionError("frozen rule/selection differs")
    tokens, _, _ = cm.virtual_corpus()
    pages = []
    for n in frozen["ordinary_pages"] + frozen["basmala_pages"]:
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        saved = next(p for p in stored["pages"] if p["page"] == n) if stored else None
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if scans else saved["image_sha256"]
        image = open_rgb(path) if scans else None
        samples = []
        if n in LABELS:
            labels = []
            for row, (verse, token, occurrence, (left, right), ink) in zip((3, 8, 13), LABELS[n]):
                candidates = [t for t in tokens if t["verse"] == verse and t["kind"] == "verse"
                              and (t["word_in_verse"] == token if isinstance(token, int) else t["normalized"] == token)]
                if len(candidates) < occurrence:
                    raise AssertionError(f"{verse}: token {token!r} missing; corpus: "
                                         + str([(t["word_in_verse"], t["normalized"]) for t in tokens if t["verse"] == verse]))
                truth = candidates[occurrence-1]
                labels.append((truth, [left, (row-1)*110+5, right, (row-1)*110+125], ink, row))
        else:
            verse, partition = HEADS[n]
            truth = next(t for t in tokens if t["verse"] == verse and t["word_in_verse"] == 2)
            labels = [(truth, partition, "colored", None)]
        for i, (truth, partition, ink, row) in enumerate(labels):
            pixels = measure(image, partition, ink) if scans else saved["word_samples"][i]["pixels"]
            box = pixels["ink_bbox"]
            samples.append(dict(t=truth["t"], kind=truth["kind"], verse=truth["verse"],
                                word_in_verse=truth["word_in_verse"], form=truth["form"], row=row,
                                selection="fixed_second_word" if row else "supplementary_basmala_name",
                                ink_class=ink, partition=partition, pixels=pixels,
                                rect=[box[0]-2, box[1]-2, box[2]+2, box[3]+2], x_edges=[box[0], box[2]],
                                boundary_eligible=not pixels["horizontal_partition_contact"], x_edge_tolerance=12))
        pages.append(dict(page=n, image_sha256=digest, word_samples=samples))
    return dict(version="fresh-seeded-row-word-annotation-v4", plan_sha256=hashlib.sha256(PLAN.read_bytes()).hexdigest(),
                pages=pages,
                protocol="One AI reader read unlabelled full scans and ruled crops, before inspecting selected "
                "pages' v4 word predictions, under frozen inference-source hashes. Exact corpus verifies token "
                "identity. Horizontal ink extents measured within manual whitespace partitions, not OCR boxes. "
                "Partition-edge contact excludes boundary evaluation; other overhanging diacritics can remain "
                "uncertain. This small deliberately stratified sample is not double annotation or corpus accuracy.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    if args.plan:
        report = plan()
        PLAN.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("ordinary pages", report["ordinary_pages"], "basmala pages", report["basmala_pages"])
        print("rule sources", report["rule_sources"])
    elif args.build or args.verify:
        saved = json.loads(MANUAL.read_text()) if args.verify else None
        report = build(not args.verify or args.scans, saved)
        if args.verify:
            if report != saved:
                raise AssertionError("fresh row/word annotation differs")
            print("PASS frozen fresh row/word sample and " + ("scan pixel measurements" if args.scans else "stored pixel measurements"))
        else:
            MANUAL.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        for p in report["pages"]:
            print(p["page"], [(w["verse"], w["word_in_verse"], w["form"], w["x_edges"], w["boundary_eligible"])
                              for w in p["word_samples"]])
    elif args.review:
        from PIL import Image, ImageDraw
        from image_io import open_rgb
        if plan() != json.loads(PLAN.read_text()):
            raise AssertionError("frozen row-sample plan differs")
        args.review.mkdir(parents=True, exist_ok=True)
        for n in plan()["ordinary_pages"]:
            image = open_rgb(ROOT / "hayrat-pics" / f"page_{n}.png")
            sheet = Image.new("RGB", (748, 990), "white")
            draw = ImageDraw.Draw(sheet)
            for k, row in enumerate((3, 8, 13)):
                top = (row-1)*110+5
                crop = image.crop((650, top, 1024, top+145)).resize((748, 290))
                sheet.paste(crop, (0, k*330+25))
                draw.text((0, k*330), f"p{n}, text row {row}, original y={top}..{top+145}", fill="black")
                for x in range(650, 1025, 10):
                    px = (x-650)*2
                    draw.line((px, k*330+307, px, k*330+315), fill="gray")
                    if x % 50 == 0:
                        draw.text((px, k*330+317), str(x), fill="black")
            sheet.save(args.review / f"page_{n}.png")


if __name__ == "__main__":
    main()
