"""Shared manual body-center development review of the 33 paired names.

--sheets renders raw full pages and full-width target strips without old x
annotations. --verify reconstructs the scan-free report; --verify-scans checks
the original image hashes. Earlier historical results are never overwritten.
"""

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import historical_copy_analysis as old
import same_word_alignment as sw

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tools/data"
PLAN = DATA / "research_historical_center_plan_v1.json"
LABELS = DATA / "research_historical_center_annotations_v1.json"
OUTPUT = DATA / "research_historical_center_review_v1.json"
SOURCES = DATA / "research_historical_center_sources_v1.json"
PHRASE_PLAN = DATA / "research_historical_phrase_plan_v1.json"
PHRASE_OUTPUT = DATA / "research_historical_phrase_review_v1.json"
SHEETS = ROOT / "logs/historical-center-review-v1"
CACHE = ROOT / "logs/historical-copy-ms-or-422-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def targets():
    original = json.loads(old.OUTPUT.read_text())
    return [r for p in original["pages"] for r in p["tokens"]]


def source_paths():
    labels = json.loads(old.LABELS.read_text())
    paths = {"historical:" + p["folio"]: CACHE / p["file"] for p in labels["pages"]}
    for r in targets():
        page = r["modern_page"]
        paths[f"modern:{page}"] = ROOT / f"hayrat-pics/page_{page}.png"
    return paths


def sheets():
    from PIL import Image, ImageDraw

    SHEETS.mkdir(parents=True, exist_ok=True)
    images = {}
    sources = {}
    for key, path in source_paths().items():
        with Image.open(path) as source:
            sources[key] = dict(sha256=sha(path), width=source.width,
                                height=source.height, scale_to_1000=1000/source.width)
            image = source.convert("RGBA")
            background = Image.new("RGBA", image.size, "white")
            background.alpha_composite(image)
            image = background.convert("RGB")
            image = image.resize((1000, round(image.height * 1000 / image.width)))
        images[key] = image
        ruler = image.copy()
        draw = ImageDraw.Draw(ruler)
        for x in range(0, 1000, 25):
            draw.line((x, 0, x, ruler.height), fill=(150, 190, 210), width=1)
            if x % 50 == 0:
                for y in range(0, ruler.height, 400):
                    draw.text((x+1, y+2), str(x), fill=(0, 0, 200))
        for y in range(0, ruler.height, 100):
            draw.text((1, y), str(y), fill=(0, 0, 200))
        ruler.save(SHEETS / (key.replace(":", "-") + ".png"))
    sites = json.loads(sw.ws.OUTPUT.read_text())
    boxes = {(p["page"], w["t"]): w["bbox"] for p in sites["pages"]
             for w in p["words"] if w["kind"] == "verse"}
    selected = targets()
    # Only y support selects the context strip. No predicted x or alignment
    # results enter the sheet, and the reader also has complete page context.
    for start in range(0, len(selected), 6):
        group = selected[start:start+6]
        panel = Image.new("RGB", (1000, len(group)*160), "white")
        draw = ImageDraw.Draw(panel)
        for i, row in enumerate(group):
            page, t = row["modern_page"], row["t"]
            image = images[f"modern:{page}"]
            box = boxes[page, t]
            with Image.open(ROOT / f"hayrat-pics/page_{page}.png") as source:
                scale = 1000/source.width
            cy = (box[1]+box[3])*scale/2
            top = max(0, round(cy)-65)
            panel.paste(image.crop((0, top, 1000, top+130)), (0, i*160+30))
            draw.text((5, i*160), f't{t} {row["verse"]} name {row["ordinal"]} modern p{page}; y={top}', fill="black")
            for x in range(0, 1000, 25):
                draw.line((x, i*160+25, x, i*160+160), fill=(150, 190, 210))
                if x % 50 == 0:
                    draw.text((x+1, i*160+15), str(x), fill=(0, 0, 200))
        panel.save(SHEETS / f"modern-strips-{start//6+1}.png")
    manifest = dict(source_images=sources, selected_tokens=selected)
    if SOURCES.exists():
        if json.loads(SOURCES.read_text()) != manifest:
            raise ValueError("Source inventory changed")
    else:
        SOURCES.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(selected, ensure_ascii=False, indent=2))
    print("Saved full-page rulers and six modern full-width strip sheets:", SHEETS)


def validate(labels, selected):
    """Require exact paired coverage and physically valid coordinates/rows."""
    expected = {r["t"]: r for r in selected}
    if len(expected) != len(selected):
        raise ValueError("Duplicate selected canonical token")
    for copy in ("historical", "modern"):
        seen = set()
        pages = labels[copy]
        if len({p["page"] for p in pages}) != len(pages):
            raise ValueError("Duplicate physical page")
        for page in pages:
            left, right = page["frame"]
            if not 0 <= left < right <= 1000 or right-left <= 6:
                raise ValueError("Invalid frame")
            if copy == "historical":
                anchors = page.get("row_end_anchors", [])
                nonverse = {int(r) for r in page.get("nonverse_rows", {})}
                if len(anchors) != 15 or {i+1 for i, word in enumerate(anchors) if word is None} != nonverse:
                    raise ValueError("Incomplete physical row anchor accounting")
            for t, row, x0, x1 in page["names"]:
                if t in seen or t not in expected:
                    raise ValueError("Unexpected or duplicate canonical token")
                if not isinstance(row, int) or not 1 <= row <= 15:
                    raise ValueError("Invalid physical row")
                if copy == "historical" and row in nonverse:
                    raise ValueError("Canonical verse name in nonverse row")
                if not left <= x0 < x1 <= right:
                    raise ValueError("Token body outside frame")
                truth = expected[t]
                wanted_page = (truth["historical_page"] if copy == "historical"
                               else truth["modern_page"])
                if page["page"] != wanted_page:
                    raise ValueError("Token assigned to wrong physical page")
                seen.add(t)
        if seen != set(expected):
            raise ValueError("Incomplete paired inventory")


def analyze():
    labels = json.loads(LABELS.read_text())
    sources = json.loads(SOURCES.read_text())["source_images"]
    plan = json.loads(PLAN.read_text())
    original = json.loads(old.OUTPUT.read_text())
    selected = [dict(r, historical_page=p["folio"])
                for p in original["pages"] for r in p["tokens"]]
    validate(labels, selected)
    truth = {r["t"]: r for r in selected}
    occurrences = {}
    for copy in ("historical", "modern"):
        occurrences[copy] = [dict(t=t, page=p["page"], row=row, word=truth[t]["word"],
                                  center=(x0+x1)/2, frame_width=p["frame"][1]-p["frame"][0])
                             for p in labels[copy] for t, row, x0, x1 in p["names"]]
    scores = {}
    for tolerance in (plan["metrics"]["primary_tolerance"], plan["metrics"]["sensitivity_tolerance"]):
        scores[str(tolerance)] = {}
        for group, standalone in (("allah_name_family", False), ("standalone_allah", True)):
            scores[str(tolerance)][group] = {
                copy: old.bounds(rows, tolerance,
                                 plan["uncertainty"]["center_error_pixels"],
                                 plan["uncertainty"]["frame_edge_error_pixels"], standalone)
                for copy, rows in occurrences.items()}
    comparisons = {}
    for copy, key in (("historical", "historical_occurrences"), ("modern", "matched_modern_occurrences")):
        before = {r["t"]: r for r in original[key]}
        after = {r["t"]: r for r in occurrences[copy]}
        comparisons[copy] = []
        for t in sorted(after):
            # Original historical coordinates already use a 1000px sheet;
            # original modern coordinates refer to the source pixel frame.
            scale = 1 if copy == "historical" else sources[f'modern:{after[t]["page"]}']["scale_to_1000"]
            delta = after[t]["center"] - before[t]["center"]*scale
            comparisons[copy].append(dict(t=t, verse=truth[t]["verse"],
                old_center_on_1000_sheet=before[t]["center"]*scale,
                new_body_center=after[t]["center"], signed_center_change=delta,
                qualification="Center-convention change and/or reading error; magnitude alone does not identify which."))
    inputs = [PLAN, LABELS, SOURCES, old.OUTPUT, old.LABELS, Path(__file__),
              Path(old.__file__)]
    return dict(study=plan["study"], inputs={p.name: sha(p) for p in inputs},
                status="Single-reader exposed manual shared-convention development review; independent adjudication remains pending.",
                occurrences=occurrences, scores=scores, center_changes=comparisons,
                confirmed_old_wrong_locations=labels["confirmed_old_wrong_locations"],
                source_images=sources,
                limitations=plan["inference"],
                uncertainty=plan["uncertainty"],
                row_transcription_status="Historical line-end anchors only; complete lexical row transcription and independent modern row audit pending.")


def phrase_bounds(first, second, tolerance, center_error=5, frame_edge_error=3):
    """A strict phrase match needs EVERY corresponding lexical center pair."""
    if not first or len(first) != len(second):
        raise ValueError("Phrase lengths differ or are empty")
    per_word = []
    for a, b in zip(first, second):
        if a["word"] != b["word"]:
            raise ValueError("Corresponding lexical identities differ")
        score = old.bounds([a, b], tolerance, center_error, frame_edge_error)
        per_word.append(dict(word=a["word"], tokens=[a["t"], b["t"]],
                             distance=float(abs(Fraction(str(a["center"]))-Fraction(str(b["center"])))),
                             guaranteed=score["guaranteed_aligned"] == 2,
                             midpoint_match=score["midpoint_aligned"] == 2,
                             possible=score["possibly_aligned"] == 2))
    return dict(words=per_word, guaranteed_phrase_match=all(w["guaranteed"] for w in per_word),
                midpoint_phrase_match=all(w["midpoint_match"] for w in per_word),
                possible_phrase_match=all(w["possible"] for w in per_word))


def analyze_phrase():
    labels = json.loads(LABELS.read_text())
    candidate = labels["phrase_candidate"]
    canonical, _ = sw.canonical_inventory()
    verse = [r for r in canonical.values() if r["verse"] == candidate["verse"]]
    words = candidate["phrase"]
    windows = [verse[i:i+len(words)] for i in range(len(verse)-len(words)+1)
               if [r["word"] for r in verse[i:i+len(words)]] == words]
    if len(windows) != len(candidate["occurrences"]) or len(windows) != 2:
        raise ValueError("Canonical phrase occurrence count differs")
    page = next(p for p in labels["historical"] if p["page"] == candidate["folio"])
    width = page["frame"][1]-page["frame"][0]
    historical = []
    for window, occurrence in zip(windows, candidate["occurrences"]):
        if len(occurrence["bodies"]) != len(words):
            raise ValueError("Incomplete phrase body measurements")
        rows = []
        for truth, (left, right) in zip(window, occurrence["bodies"]):
            if not page["frame"][0] <= left < right <= page["frame"][1]:
                raise ValueError("Phrase word outside frame")
            if truth["word"] == "الله":
                if [truth["t"], occurrence["row"], left, right] not in page["names"]:
                    raise ValueError("Name/phrase annotation conflict")
            rows.append(dict(t=truth["t"], word=truth["word"], page=candidate["folio"],
                             row=occurrence["row"], center=(left+right)/2, frame_width=width))
        historical.append(rows)
    ledger = json.loads(old.MODERN.read_text())["views"]["conservative_v5"]["located_inventory"]
    lookup = {r[0]: r for r in ledger}
    extents = {}
    for _, page_id, _, x2, w in ledger:
        a, b = (x2-w)/2, (x2+w)/2
        lo, hi = extents.get(page_id, (a, b))
        extents[page_id] = min(lo, a), max(hi, b)
    modern = []
    for window in windows:
        rows = []
        for truth in window:
            _, page_id, row, x2, _ = lookup[truth["t"]]
            lo, hi = extents[page_id]
            rows.append(dict(t=truth["t"], word=truth["word"], page=page_id,
                             row=row, center=x2/2, frame_width=hi-lo))
        if len({(r["page"], r["row"]) for r in rows}) != 1:
            raise ValueError("Modern phrase not on one physical row")
        modern.append(rows)
    scores = {str(tau): dict(historical=phrase_bounds(*historical, tau),
                             modern_ledger_context_only=phrase_bounds(*modern, tau, center_error=0, frame_edge_error=0))
              for tau in (0.02, 0.015)}
    # This is an allowance boundary, not a calibrated error estimate.
    maximum_distance = max(w["distance"] for w in scores["0.02"]["historical"]["words"])
    critical = {str(tau): str((Fraction(str(tau))*(width-6)-Fraction(str(maximum_distance)))/2)
                for tau in (0.02, 0.015)}
    inputs = [PHRASE_PLAN, PLAN, LABELS, SOURCES, old.MODERN, sw.mt.TOKENS_F,
              Path(__file__), Path(old.__file__), Path(sw.__file__)]
    return dict(study=json.loads(PHRASE_PLAN.read_text())["study"],
                inputs={p.name: sha(p) for p in inputs},
                source_images=json.loads(SOURCES.read_text())["source_images"],
                historical=historical, modern_ledger_context_only=modern, scores=scores,
                maximum_common_center_error_for_guaranteed_historical_phrase_with_frame_error_3=critical,
                interpretation="A post-hoc complete corresponding-word example in a catalogued 1779 manuscript. Supports pre-project phrase alignment; does not distinguish divine design from ordinary writing/repetition/line-end constraints. Modern detector geometry is context only.",
                historical_uncertainty="Assumed +/-5px center, +/-3px frame edges on 1000px sheet. Not calibrated confidence intervals; full phrase robustness requires all three corresponding pairs.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheets", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-scans", action="store_true")
    parser.add_argument("--candidate-sheet", action="store_true")
    parser.add_argument("--phrase", action="store_true")
    args = parser.parse_args()
    if args.candidate_sheet:
        from PIL import Image, ImageDraw
        with Image.open(CACHE / "ia-leaf-404.jpg") as source:
            image = source.convert("RGB")
            image = image.resize((1000, round(image.height*1000/image.width)))
        crop = image.crop((220, 330, 560, 490)).resize((1020, 480))
        sheet = Image.new("RGB", (1020, 510), "white")
        sheet.paste(crop, (0, 30))
        draw = ImageDraw.Draw(sheet)
        for x in range(225, 560, 25):
            sx = (x-220)*3
            draw.text((sx, 5), str(x), fill="blue")
            draw.line((sx, 30, sx, 510), fill=(100, 180, 200))
        SHEETS.mkdir(parents=True, exist_ok=True)
        sheet.save(SHEETS / "candidate-200r-rows-3-4.png")
        print("Saved candidate context sheet")
        return
    if args.sheets:
        sheets()
        return
    report = analyze_phrase() if args.phrase else analyze()
    output = PHRASE_OUTPUT if args.phrase else OUTPUT
    if args.verify_scans:
        for key, path in source_paths().items():
            if sha(path) != report["source_images"][key]["sha256"]:
                raise ValueError(f"Source image changed: {key}")
        print("All source image hashes match")
    if args.verify or args.verify_scans:
        if report != json.loads(output.read_text()):
            raise ValueError("Shared-convention review replay differs")
        print("Shared-convention scan-free replay passed")
    else:
        if output.exists():
            raise FileExistsError("Frozen report exists; use --verify")
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.phrase:
        print(json.dumps(report["scores"], ensure_ascii=False, indent=2))
        print("Guaranteed-phrase maximum center allowances:", report["maximum_common_center_error_for_guaranteed_historical_phrase_with_frame_error_3"])
        return
    for tolerance, groups in report["scores"].items():
        for group, copies in groups.items():
            print(tolerance, group, {copy: [s["guaranteed_aligned"], s["midpoint_aligned"],
                                               s["possibly_aligned"], s["occurrences"]]
                                     for copy, s in copies.items()})


if __name__ == "__main__":
    main()
