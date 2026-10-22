"""Frozen, hash-ranked review of nonexact v5 unions; no policy retuning.

The sample diagnoses exclusions, not accepted-site accuracy. Review scans
without predicted-box overlays; independently mark a target-word core before
comparing the rejected box center. Full boundaries may remain unresolved.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from rapidfuzz.distance import Levenshtein

import ocr_corpus_map as cm
import ocr_word_boundary_map as wm
import word_boundary_sites as ws
from semantic_validation import DATA, ROOT

PLAN = DATA / "audit_word_union_review_plan_v5.json"
MANUAL = DATA / "audit_manual_word_union_review_v5.json"
OUTPUT = DATA / "audit_word_union_review_v5.json"
SEED = "t2-v5-rejected-unions-2026-10-19"
PER_STRATUM = 4
RULES = ["ocr_corpus_map.py", "ocr_observation_map.py", "ocr_reading_order.py",
         "ocr_row_map.py", "ocr_word_boundary_map.py", "ocr_corpus_sites.py", "word_boundary_sites.py"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(frame):
    """Census the two special categories, hash-rank ordinary split/error strata."""
    groups = defaultdict(list)
    seen = set()
    for row in frame:
        identity = (row["page"], row["v_id"])
        if identity in seen:
            raise AssertionError("duplicate excluded-union identity")
        seen.add(identity)
        if len(row["mandatory_regions"]) < 2 or row["text_distance"] < 1:
            raise AssertionError("frame contains an exact or single-region site")
        if row["kind"] != "verse":
            group = "head_basmala"
        elif row["is_allah_form"]:
            group = "verse_name"
        else:
            group = ("ordinary_2regions" if len(row["mandatory_regions"]) == 2 else "ordinary_3plus_regions")
            group += "_1edit" if row["text_distance"] == 1 else "_2plus_edits"
        groups[group].append(row)
    strata, samples = [], []
    for group, rows in sorted(groups.items()):
        count = len(rows) if group in {"head_basmala", "verse_name"} else min(PER_STRATUM, len(rows))
        rank = lambda r: (hashlib.sha256(f'{SEED}:{r["page"]}:{r["v_id"]}'.encode()).hexdigest(), r["page"], r["v_id"])
        chosen = sorted(rows, key=rank)[:count]
        strata.append(dict(stratum=group, population=len(rows), sampled=count))
        samples.extend(dict(sample_id=f'u{i:02d}', stratum=group, **row)
                       for i, row in enumerate(chosen, len(samples)+1))
    return strata, samples


def plan():
    sites = json.loads(ws.OUTPUT.read_text())
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    frame = []
    for row in sites["excluded_nonexact_unions"]:
        page = raw[row["page"]]
        observed = "".join(cm.normalized(page["regions"][i]["text"]) for i in row["mandatory_regions"])
        if row["surface_match"] or observed == row["normalized"]:
            raise AssertionError("excluded union has exact normalized text")
        frame.append(dict(row, recognized=observed, text_distance=Levenshtein.distance(observed, row["normalized"]),
                          image_sha256=page["image_sha256"]))
    strata, samples = select(frame)
    return dict(version="frozen-rejected-union-review-plan-v5", seed=SEED, per_ordinary_stratum=PER_STRATUM,
                population=len(frame), strata=strata, samples=samples,
                inputs={p.name: digest(p) for p in (ws.OUTPUT, wm.OUTPUT, cm.SOURCE, cm.mt.TOKENS_F)},
                rule_sources={name: digest(ROOT / "tools" / name) for name in RULES},
                protocol="Fixed SHA256(seed:page:v_id) ranks within ordinary 2/3plus-region by 1/2plus-edit strata; "
                "four per nonempty ordinary stratum, census of excluded verse names and head basmala. "
                "Selected before visual inspection. Diagnostic hash sample, no random-design accuracy estimate. "
                "One AI reader sees target identities and context crops without predicted-box overlays. "
                "Mark a target-letter core independently; center localization and full word extent are separate. "
                "No acceptance-policy changes from these labels; previously exposed cases retained as such.")


def frozen_plan():
    saved = json.loads(PLAN.read_text())
    if plan() != saved:
        raise AssertionError("frozen union sample, inputs or inference rules differ")
    return saved


def analyze(scans=False):
    frozen = frozen_plan()
    manual = json.loads(MANUAL.read_text())
    if manual["plan_sha256"] != digest(PLAN):
        raise AssertionError("union annotations refer to another plan")
    labels = {r["sample_id"]: r for r in manual["labels"]}
    if len(labels) != len(manual["labels"]) or set(labels) != {r["sample_id"] for r in frozen["samples"]}:
        raise AssertionError("union labels do not match frozen sample inventory")
    details = []
    for row in frozen["samples"]:
        label = labels[row["sample_id"]]
        if (label["page"], label["v_id"]) != (row["page"], row["v_id"]):
            raise AssertionError("union label identity differs")
        if scans and digest(ROOT / "hayrat-pics" / f'page_{row["page"]}.png') != row["image_sha256"]:
            raise AssertionError("union review scan hash differs")
        rect = label["core_rect"]
        if rect is not None and (len(rect) != 4 or rect[0] >= rect[2] or rect[1] >= rect[3]):
            raise AssertionError("invalid independent target core")
        box = row["bbox"]
        cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
        correct = rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3] if rect else None
        if label["extent"] not in {"plausible_word", "partial_word", "includes_neighbor", "wrong_location", "unresolved"}:
            raise AssertionError("unknown union extent category")
        if label["extent"] == "wrong_location" and correct is not False:
            raise AssertionError("wrong-location annotation contradicts independent core")
        details.append(dict(**row, annotation=label, center_correct=correct))
    summary = dict(reviewed=len(details), center_correct=sum(r["center_correct"] is True for r in details),
                   wrong_center=sum(r["center_correct"] is False for r in details),
                   unresolved_center=sum(r["center_correct"] is None for r in details),
                   extent_counts=dict(Counter(r["annotation"]["extent"] for r in details)))
    return dict(version="rejected-union-scan-review-v5", summary=summary, details=details,
                inputs={p.name: digest(p) for p in (PLAN, MANUAL)},
                caveat="One-reader, target-aware diagnostic review of exclusions, not blind accepted-site validation. "
                "Core localization does not certify diacritic ownership or full word geometry. Hash-stratified "
                "counts are not a corpus accuracy estimate. Conservative automatic predictions remain unchanged.")


def review(directory):
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    directory.mkdir(parents=True, exist_ok=True)
    for row in frozen_plan()["samples"]:
        path = ROOT / "hayrat-pics" / f'page_{row["page"]}.png'
        if digest(path) != row["image_sha256"]:
            raise AssertionError("review crop scan hash differs")
        image = open_rgb(path)
        box = row["bbox"]
        top, bottom = max(0, box[1]-130), min(image.height, box[3]+130)
        sheet = Image.new("RGB", (image.width, bottom-top+40), "white")
        sheet.paste(image.crop((0, top, image.width, bottom)), (0, 40))
        draw = ImageDraw.Draw(sheet)
        draw.text((5, 2), f'{row["sample_id"]} p{row["page"]} {row["verse"]} word {row["word_in_verse"]}; original y={top}..{bottom}', fill="black")
        for x in range(0, image.width, 50):
            draw.text((x, 20), str(x), fill="black")
        sheet.save(directory / f'{row["sample_id"]}.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan", action="store_true")
    modes.add_argument("--review", type=Path)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    parser.add_argument("--scans", action="store_true")
    args = parser.parse_args()
    if args.plan:
        report = plan()
        PLAN.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print("strata", report["strata"])
        for r in report["samples"]:
            print(r["sample_id"], r["page"], r["v_id"], r["verse"], r["word_in_verse"], r["form"], r["recognized"], r["bbox"])
    elif args.review:
        review(args.review)
    else:
        report = analyze(args.scans)
        if args.verify:
            if report != json.loads(OUTPUT.read_text()):
                raise AssertionError("rejected-union review differs")
            print("PASS frozen rejected-union sample, annotations, independent core comparisons and hashes")
        else:
            OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print(report["summary"])


if __name__ == "__main__":
    main()
