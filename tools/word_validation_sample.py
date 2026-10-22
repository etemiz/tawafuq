"""Fresh pre-OCR validation sample for mandatory-region mapper v2.

Manual windows are from unlabelled scans, not OCR/pin predictions. Besides
all scoped Allah forms, sample the second and fifth lexical words on physical
Quran rows 3, 8 and 13 (RTL, ignoring rosettes). p588 uses only its upper
complete-verse block, excluding the next surah's ornament and basmala.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path

import map_tokens as mt
from semantic_validation import ROOT, DATA, STRATA, corpus_targets
from ocr_heldout_sample import EXCLUDE, selected_pages as previous_pages
from ocr_word_map import map_mandatory_regions

SEED = "t2-mandatory-word-boundary-v2-2026-10-18"
EXCLUDED = EXCLUDE | set(previous_pages())
MANUAL = DATA / "audit_manual_word_validation_v2.json"
# Verse, occurrence within verse, canonical form, name-core rectangle.
NAMES = {
    26: ("2:177", "2:181", 1680, [
        ("2:177", 1, "بالله", [477, 143, 572, 224]),
        ("2:181", 1, "الله", [468, 1572, 545, 1648]),
    ]),
    130: ("6:28", "6:35", 1680, [
        ("6:31", 1, "الله", [517, 472, 593, 548]),
        ("6:33", 1, "الله", [518, 1024, 594, 1099]),
        ("6:34", 1, "الله", [519, 1247, 595, 1320]),
        ("6:35", 1, "الله", [923, 1572, 999, 1646]),
    ]),
    286: ("17:50", "17:58", 1680, []),
    393: ("28:71", "28:77", 1680, [
        ("28:71", 1, "الله", [584, 30, 664, 105]),
        ("28:71", 2, "الله", [584, 142, 664, 215]),
        ("28:72", 1, "الله", [584, 252, 664, 325]),
        ("28:72", 2, "الله", [584, 364, 664, 437]),
        ("28:75", 1, "لله", [585, 917, 663, 988]),
        ("28:76", 1, "الله", [370, 1246, 449, 1320]),
        ("28:77", 1, "الله", [584, 1357, 663, 1430]),
        ("28:77", 2, "الله", [370, 1467, 449, 1539]),
        ("28:77", 3, "الله", [370, 1578, 449, 1650]),
    ]),
    462: ("39:41", "39:47", 1680, [
        ("39:42", 1, "الله", [751, 251, 837, 324]),
        ("39:43", 1, "الله", [749, 584, 837, 657]),
        ("39:44", 1, "لله", [451, 693, 526, 766]),
        ("39:45", 1, "الله", [749, 915, 837, 989]),
        ("39:47", 1, "الله", [458, 1577, 535, 1648]),
    ]),
    588: ("83:27", "83:36", 670, []),
}
# Verse, 1-based canonical word index, expected canonical spelling,
# approximate complete printed-word extent, visually observed ink class.
# Horizontal extent is assessed with a preregistered +/-12px tolerance;
# these are coarse one-reader boundaries, not pixel-exact tracings.
WORDS = {
    26: [
        ("2:177", 18, "والنبين", [707, 246, 850, 337], "black"),
        ("2:177", 21, "علي", [474, 252, 543, 335], "black"),
        ("2:178", 7, "في", [800, 807, 846, 883], "black"),
        ("2:178", 10, "بالحر", [499, 805, 605, 886], "black"),
        ("2:180", 7, "ان", [853, 1354, 904, 1433], "black"),
        ("2:180", 10, "الوصيه", [546, 1350, 682, 1430], "black"),
    ],
    130: [
        ("6:30", 2, "تري", [817, 251, 902, 334], "black"),
        ("6:30", 5, "علي", [612, 250, 687, 340], "magenta"),
        ("6:32", 8, "الاخره", [741, 800, 864, 884], "black"),
        ("6:32", 11, "يتقون", [406, 798, 550, 884], "black"),
        ("6:35", 2, "كان", [804, 1351, 900, 1435], "black"),
        ("6:35", 5, "اعراضهم", [451, 1351, 580, 1435], "black"),
    ],
    286: [
        ("17:51", 17, "رءوسهم", [745, 251, 888, 337], "black"),
        ("17:51", 20, "هو", [441, 265, 484, 327], "black"),
        ("17:54", 11, "وما", [750, 800, 820, 883], "black"),
        ("17:54", 14, "وكيلا", [385, 800, 469, 883], "black"),
        ("17:57", 12, "ويخافون", [648, 1350, 816, 1438], "black"),
        ("17:57", 15, "عذاب", [408, 1350, 498, 1438], "black"),
    ],
    393: [
        ("28:72", 2, "ارءيتم", [816, 248, 923, 334], "magenta"),
        ("28:72", 5, "الله", [584, 250, 664, 327], "crimson"),
        ("28:75", 2, "من", [744, 807, 811, 884], "black"),
        ("28:75", 5, "شهيدا", [407, 799, 563, 884], "black"),
        ("28:77", 2, "فيما", [784, 1350, 857, 1436], "black"),
        ("28:77", 5, "الدار", [487, 1350, 573, 1436], "black"),
    ],
    462: [
        ("39:42", 1, "الله", [751, 250, 838, 327], "crimson"),
        ("39:42", 4, "حين", [417, 254, 500, 335], "black"),
        ("39:44", 7, "السموت", [687, 802, 890, 885], "black"),
        ("39:44", 10, "اليه", [278, 804, 371, 884], "black"),
        ("39:47", 1, "ولو", [727, 1350, 820, 1438], "black"),
        ("39:47", 4, "ظلموا", [358, 1350, 485, 1438], "black"),
        ("39:46", 2, "اللهم", [750, 1137, 866, 1212], "crimson"),
    ],
    588: [
        ("83:31", 1, "واذا", [676, 251, 780, 337], "black"),
        ("83:31", 4, "اهلهم", [362, 249, 492, 341], "black"),
    ],
}


def selected_pages():
    return [min((n for n in range(lo, hi + 1) if n not in EXCLUDED),
                key=lambda n: hashlib.sha256(f"{SEED}:{n}".encode()).hexdigest())
            for lo, hi in STRATA]


def build(scans=True, stored=None):
    selected = selected_pages()
    if selected != list(NAMES):
        raise AssertionError("manual pages differ from fixed selection")
    verses = mt.load_tokens()
    lookup = {f"{s}:{a}": ts for s, a, ts in verses}
    pages = []
    for n, stratum in zip(selected, STRATA):
        first, last, bottom, annotations = NAMES[n]
        names = [dict(verse=v, occurrence=i, form=f, rect=r, visually_colored=True)
                 for v, i, f, r in annotations]
        targets = corpus_targets(verses, first, last)
        if [(x["verse"], x["occurrence"], x["form"]) for x in targets] != [
                (x["verse"], x["occurrence"], x["form"]) for x in names]:
            raise AssertionError(f"p{n}: manual names differ from exact text")
        sampled = []
        for v, index, form, rect, color in WORDS[n]:
            if lookup[v][index - 1] != form:
                raise AssertionError(f"p{n}: manual sample word differs from corpus {v}:{index}")
            sampled.append(dict(verse=v, word_in_verse=index, form=form, rect=rect,
                                x_edges=[rect[0], rect[2]], x_edge_tolerance=12, ink_class=color,
                                selection="supplemental_vocative" if form == "اللهم" else "fixed_row_positions"))
        digest = (hashlib.sha256((ROOT / "hayrat-pics" / f"page_{n}.png").read_bytes()).hexdigest()
                  if scans else next(p["image_sha256"] for p in stored["pages"] if p["page"] == n))
        pages.append(dict(page=n, stratum=list(stratum), first_verse=first, last_verse=last,
                          image_sha256=digest, ocr_bottom=bottom, names=names, word_samples=sampled))
    return dict(version="fresh-name-and-word-boundary-sample-v2", seed=SEED,
                excluded_pages=sorted(EXCLUDED), selection="minimum SHA256(seed:page) in six fixed strata",
                mapper_rule_sha256=hashlib.sha256(inspect.getsource(map_mandatory_regions).encode()).hexdigest(),
                pages=pages,
                protocol="One AI reader inspected unlabelled scans before OCR predictions. All scoped Allah "
                "forms plus 2nd/5th lexical words of Quran rows 3/8/13; missing rows omitted. p588 upper "
                "block only (83:27-36), before the surah ornament/basmala. Supplemental اللهم at 39:46 "
                "is outside the operational Allah-form census. Approximate word extents +/-12px horizontally; "
                "not pixel-exact boundaries or independent human double annotation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=MANUAL)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    parser.add_argument("--review", type=Path, help="unlabelled row crops with an x-coordinate ruler; no OCR read")
    args = parser.parse_args()
    if args.review:
        from PIL import Image, ImageDraw
        from image_io import open_rgb
        args.review.mkdir(parents=True, exist_ok=True)
        for n in selected_pages():
            image = open_rgb(ROOT / "hayrat-pics" / f"page_{n}.png")
            for row in ([3] if n == 588 else [3, 8, 11, 13] if n == 462 else [3, 8, 13]):
                top = (row - 1) * 110 + 10
                crop = image.crop((0, top, image.width, top + 130))
                canvas = Image.new("RGB", (image.width, 154), "white")
                canvas.paste(crop, (0, 24))
                draw = ImageDraw.Draw(canvas)
                for x in range(0, image.width, 50):
                    draw.text((x + 1, 0), str(x), fill="black")
                    draw.line((x, 14, x, 23), fill="black")
                canvas.resize((image.width * 2, 308)).save(args.review / f"page_{n}_row_{row}.png")
        print("Unlabelled ruled crops saved to", args.review)
    elif args.verify:
        stored = json.loads(args.output.read_text())
        if build(args.scans, stored) != stored:
            raise AssertionError("fresh annotation sample does not reproduce")
        print("PASS fresh v2 page selection, corpus identities, frozen rule and annotations"
              + (", scan hashes" if args.scans else "; stored scan hashes"))
    else:
        report = build()
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("pages", selected_pages(), "names", sum(len(p["names"]) for p in report["pages"]),
              "sampled words", sum(len(p["word_samples"]) for p in report["pages"]))


if __name__ == "__main__":
    main()
