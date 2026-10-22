"""Post-score coverage/geometry audit and explicitly schematic pilot sheets."""
import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import text_layout_comparator as lc
import text_layout_pilot as fp
import same_word_alignment as sw

OUTPUT = sw.DATA / "research_text_layout_review_v1.json"


def reference(words, coordinates):
    """Independent all-pairs endpoint reference, using exact fractions."""
    exact, family = set(), set()
    for a in words:
        for b in words:
            if a["page"] == b["page"] and a["row"] != b["row"] and abs(coordinates[a["t"]]-coordinates[b["t"]]) <= 30:
                if a["word"] == b["word"]:
                    exact.add(a["t"])
                if sw.is_name(sw.mt.norm(a["word"])) and sw.is_name(sw.mt.norm(b["word"])):
                    family.add(a["t"])
    return dict(standalone_allah=sorted(w["t"] for w in words if w["t"] in exact and w["word"] == "الله"),
                all_identical_words=sorted(exact), allah_name_family=sorted(family))


def analyze():
    comparison = json.loads(lc.OUTPUT.read_text())
    feasibility = json.loads(fp.FEASIBILITY.read_text())
    if comparison["plan_sha256"] != sw.digest(lc.PLAN) or json.loads(lc.PLAN.read_text()) != lc.plan():
        raise AssertionError("pilot plan changed")
    canonical, _ = sw.canonical_inventory()
    baseline = json.loads(sw.OUTPUT.read_text())["views"]["conservative_v5"]
    baseline_inventory = {r[0]: r for r in baseline["located_inventory"]}
    baseline_pairs = baseline["same_word_pair_token_ids"]
    pages = []
    for page, result in zip(feasibility["pages"], comparison["pages"]):
        if page["page"] != result["page"]:
            raise AssertionError("page mismatch")
        words = [w for r in page["rows"] for w in r["words"]]
        eligible = [w for r in page["rows"] if r["eligible"] for w in r["words"]]
        for w in words:
            expected = [w[k] for k in ("t", "page", "row", "x2", "width")]
            if expected != baseline_inventory[w["t"]]:
                raise AssertionError("pilot word differs from frozen full-corpus inventory")
            if sw.is_name(w["word"]) != sw.is_name(canonical[w["t"]]["form"]):
                raise AssertionError("strict-spelling family predicate differs on pilot population")
        full_observed = reference(words, {w["t"]: w["x2"] for w in words})
        eligible_ids = {w["t"] for w in eligible}
        paired = set(t for pair in baseline_pairs if pair[0] in eligible_ids and pair[1] in eligible_ids for t in pair)
        for label, coordinates, report in (
                ("original", {w["t"]: w["x2"] for w in eligible}, result["observed"]),
                ("equal", {t: Fraction(x) for t, x in result["equal_gap_centers"]}, result["equal_gaps"])):
            checked = reference(eligible, coordinates)
            if checked != report["endpoint_token_ids"]:
                raise AssertionError(f"{label} independent all-pairs score differs")
            if label == "original" and sorted(paired) != checked["all_identical_words"]:
                raise AssertionError("pilot restricted pairs differ from frozen full-corpus pairs")
        first = result["first_random_trial"]
        checked = reference(eligible, dict(first["centers"]))
        if {m: len(ids) for m, ids in checked.items()} != first["counts"]:
            raise AssertionError("first random layout score differs")
        by_t = {w["t"]: w for w in eligible}
        for centers in (dict(first["centers"]), {t: Fraction(x) for t, x in result["equal_gap_centers"]}):
            for r in page["rows"]:
                if not r["eligible"]:
                    continue
                for a, b in zip(r["words"], r["words"][1:]):
                    right_word_left = (centers[a["t"]]-a["width"])/2
                    left_word_right = (centers[b["t"]]+b["width"])/2
                    if right_word_left < left_word_right:
                        raise AssertionError("generated interval order/overlap failure")
        freedoms = [c for r in result["freedom"] for c in r["centers"]]
        names = [c for c in freedoms if c["word"] == "الله"]
        guaranteed = set()
        guaranteed_pairs = []
        for i, a in enumerate(names):
            for b in names[i+1:]:
                if by_t[a["t"]]["row"] == by_t[b["t"]]["row"]:
                    continue
                maximum_distance2 = max(abs(a["minimum_x2"]-b["maximum_x2"]), abs(a["maximum_x2"]-b["minimum_x2"]))
                if maximum_distance2 <= 30:
                    guaranteed.update((a["t"], b["t"]))
                    guaranteed_pairs.append([a["t"], b["t"]])
        pages.append(dict(page=page["page"], full_located_words=len(words), eligible_words=len(eligible),
            full_located_standalone_allah=sum(w["word"] == "الله" for w in words),
            full_mapped_observed={m: len(ids) for m, ids in full_observed.items()},
            eligible_observed=result["observed"]["counts"],
            names_with_spacing_freedom=sum(c["movable"] for c in names),
            names_fixed_by_spacing_model=sum(not c["movable"] for c in names),
            all_words_with_spacing_freedom=sum(c["movable"] for c in freedoms),
            name_center_envelopes=names,
            guaranteed_standalone_aligned_token_ids=sorted(guaranteed), guaranteed_standalone_pairs=guaranteed_pairs,
            distinct_row_gap_arrangements=[[r["row"], r["distinct_gap_arrangements"]] for r in result["freedom"]],
            missing_internal_tokens=[w for r in page["rows"] for w in r["missing_internal"]],
            boundary_missing_token_ids=sorted(set(t for r in page["discontinuous_row_transitions"] for t in r["missing_token_ids"]))))
    return dict(version="text-order-spacing-post-score-review-v1", pages=pages,
        inputs={p.name: sw.digest(p) for p in (fp.FEASIBILITY, lc.PLAN, lc.OUTPUT, sw.OUTPUT, Path(__file__))},
        summary=dict(full_mapped_standalone=sum(p["full_located_standalone_allah"] for p in pages),
            eligible_standalone=comparison["summary"]["population"]["standalone_allah"],
            eligible_movable_standalone=sum(p["names_with_spacing_freedom"] for p in pages),
            guaranteed_standalone_endpoints=sum(len(p["guaranteed_standalone_aligned_token_ids"]) for p in pages),
            movable_eligible_words=sum(p["all_words_with_spacing_freedom"] for p in pages)),
        caveat="Exposed diagnostics after frozen scores. Full mapped scores do not have a full-page spacing comparator. Guaranteed pairs use exact attainable center extrema and are sufficient, not exhaustive, certificates of endpoint persistence. Interval sheets are schematics, not regenerated Arabic calligraphy or independent word annotation.")


def sheets(directory):
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    directory.mkdir(parents=True, exist_ok=True)
    feasible = json.loads(fp.FEASIBILITY.read_text())
    comparison = json.loads(lc.OUTPUT.read_text())
    for p, result in zip(feasible["pages"], comparison["pages"]):
        scan_path = sw.ROOT / "hayrat-pics" / f"page_{p['page']}.png"
        if sw.digest(scan_path) != p["image_sha256"]:
            raise AssertionError("review scan hash differs")
        image = open_rgb(scan_path)
        width, height = image.size
        canvas = Image.new("RGB", (width*3, height+100), "white")
        canvas.paste(image, (0, 100))
        draw = ImageDraw.Draw(canvas)
        draw.text((20, 10), f"p{p['page']} | scan + original boxes | EQUAL-GAP INTERVAL SCHEMATIC | FIRST RANDOM INTERVAL SCHEMATIC", fill="black")
        draw.text((20, 30), "Blue=exact Allah; purple=other Allah family; black=ordinary; gray=excluded. NOT rendered glyphs.", fill="black")
        draw.text((20, 50), f"Standalone counts: original={result['observed']['counts']['standalone_allah']} equal={result['equal_gaps']['counts']['standalone_allah']} random={result['first_random_trial']['counts']['standalone_allah']}", fill="black")
        equal = {t: Fraction(x)/2 for t, x in result["equal_gap_centers"]}
        first = {t: Fraction(x, 2) for t, x in result["first_random_trial"]["centers"]}
        for row in p["rows"]:
            y = row["center_y"]+100
            for panel in range(3):
                draw.text((panel*width+2, y), str(row["row"]), fill="black")
            for word in row["words"]:
                color = ("#aaaaaa" if not row["eligible"] else "#0066ee" if word["word"] == "الله" else "#b000a0" if sw.is_name(word["word"]) else "#222222")
                box = word["bbox"]
                draw.rectangle((box[0], box[1]+100, box[2], box[3]+100), outline=color, width=2)
                for panel, positions in ((1, equal), (2, first)):
                    if row["eligible"]:
                        x = float(positions[word["t"]])
                        a, b = x-word["width"]/2, x+word["width"]/2
                        draw.rectangle((panel*width+a, y-14, panel*width+b, y+14), outline=color, width=2)
                        draw.line((panel*width+x, y-18, panel*width+x, y+18), fill=color, width=2)
                        if sw.is_name(word["word"]):
                            draw.text((panel*width+a, y+18), str(word["t"]), fill=color)
            if not row["eligible"]:
                for panel in (1, 2):
                    draw.text((panel*width+60, y), "EXCLUDED: "+", ".join(row["exclusion_reasons"]), fill="#999999")
        canvas.resize((1536, round(canvas.height*1536/canvas.width))).save(directory / f"page_{p['page']}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    report = analyze()
    if args.verify:
        if json.loads(OUTPUT.read_text()) != report:
            raise AssertionError("post-score spacing diagnostics differ")
        print("PASS independent pair/packing reference, frozen-inventory cross-check and coverage/freedom audit")
    else:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":"))+"\n")
    if args.review:
        sheets(args.review)
    print(json.dumps(report["summary"], indent=2))
    for p in report["pages"]:
        print("page", p["page"], "full names", p["full_located_standalone_allah"], "full observed", p["full_mapped_observed"],
              "movable names", p["names_with_spacing_freedom"], "fixed names", p["names_fixed_by_spacing_model"],
              "guaranteed aligned names", len(p["guaranteed_standalone_aligned_token_ids"]))


if __name__ == "__main__":
    main()
