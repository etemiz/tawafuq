"""Rebuild the independently read, pre-OCR second six-page annotation sample.

These are manually read image-core windows, not detector-derived boundaries.
Sampling excludes the original training anchors and development sample.
"""
import argparse
import hashlib
import json
from pathlib import Path

from semantic_validation import ROOT, DATA, STRATA, EXCLUDED, corpus_targets
import map_tokens as mt

SEED = "t2-heldout-ocr-localization-v1-2026-10-18"
EXCLUDE = EXCLUDED | {15, 148, 276, 365, 412, 513}
# Recorded from unlabelled full scans before generating new OCR/pin predictions.
# Verse, within-verse name occurrence, normalized form, localized ink-core window.
ANNOTATIONS = {
    74: ("3:187", "3:194", [
        ("3:187", 1, "الله", [714, 31, 793, 106]),
        ("3:189", 1, "ولله", [712, 587, 782, 663]),
        ("3:189", 2, "والله", [24, 587, 107, 657]),
        ("3:191", 1, "الله", [715, 914, 789, 981]),
    ]),
    128: ("6:9", "6:18", [
        ("6:12", 1, "لله", [446, 468, 511, 548]),
        ("6:14", 1, "الله", [437, 804, 512, 874]),
        ("6:17", 1, "الله", [438, 1357, 513, 1421]),
    ]),
    201: ("9:94", "9:99", [
        ("9:94", 1, "الله", [413, 144, 482, 212]),
        ("9:94", 2, "الله", [925, 252, 999, 319]),
        ("9:95", 1, "بالله", [22, 363, 110, 439]),
        ("9:96", 1, "الله", [923, 805, 997, 875]),
        ("9:97", 1, "الله", [22, 916, 99, 982]),
        ("9:97", 2, "والله", [658, 1024, 741, 1096]),
        ("9:98", 1, "والله", [658, 1245, 743, 1320]),
        ("9:99", 1, "بالله", [658, 1356, 737, 1429]),
        ("9:99", 2, "الله", [662, 1466, 735, 1536]),
        ("9:99", 3, "الله", [660, 1578, 735, 1644]),
        ("9:99", 4, "الله", [364, 1576, 439, 1644]),
    ]),
    342: ("23:18", "23:27", [
        ("23:23", 1, "الله", [23, 693, 96, 761]),
        ("23:24", 1, "الله", [24, 914, 98, 980]),
    ]),
    447: ("37:52", "37:76", [
        ("37:56", 1, "تالله", [485, 253, 587, 332]),
        ("37:74", 1, "الله", [497, 1466, 574, 1538]),
    ]),
    529: ("54:28", "54:49", []),
}


def selected_pages():
    return [min((n for n in range(lo, hi + 1) if n not in EXCLUDE),
                    key=lambda n: hashlib.sha256(f"{SEED}:{n}".encode()).hexdigest())
                for lo, hi in STRATA]


def build():
    selected = selected_pages()
    if selected != list(ANNOTATIONS):
        raise AssertionError("annotations differ from independently selected pages")
    verses = mt.load_tokens()
    pages = []
    for n, stratum in zip(selected, STRATA):
        first, last, annotations = ANNOTATIONS[n]
        names = [dict(verse=v, occurrence=i, form=f, rect=r, visually_colored=True)
                 for v, i, f, r in annotations]
        targets = corpus_targets(verses, first, last)
        if [{k: t[k] for k in ("verse", "occurrence", "form")} for t in targets] != [
                {k: t[k] for k in ("verse", "occurrence", "form")} for t in names]:
            raise AssertionError(f"p{n}: manual identities differ from corpus")
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        pages.append(dict(page=n, stratum=list(stratum), first_verse=first, last_verse=last,
                          ocr_bottom=1680, image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          names=names))
    return dict(version="heldout-name-localization-sample-v1", seed=SEED,
                selection="minimum SHA256(seed:page) within each fixed page-number stratum",
                excluded_pages=sorted(EXCLUDE), pages=pages,
                protocol="Unlabelled scans read before new OCR predictions. Exact corpus confirms spelling/order. "
                "One AI reader, approximate ink-core localization windows, not traced boundaries. "
                "The exclusive-region algorithm was developed only on the first sample, before these predictions. "
                "p529 contains no Allah forms and is retained as a negative page control.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=DATA / "audit_manual_ocr_heldout.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = build()
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("held-out annotation/image hashes differ")
        print("PASS held-out selection, exact name census and scan hashes")
    else:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("held-out pages", [p["page"] for p in report["pages"]],
              "names", sum(len(p["names"]) for p in report["pages"]))


if __name__ == "__main__":
    main()
