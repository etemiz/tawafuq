"""Independent scalar phrase checks and predeclared, exposed scan diagnostics."""
import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
from pathlib import Path

import broad_phrase_alignment as bp
import same_word_alignment as sw

OUTPUT = sw.DATA / "research_broad_phrase_review_v1.json"


def scalar_pairs(result, words, eligible_t, exact_t):
    lookup = {w["t"]: w for w in words}
    length = result["length"]
    groups = defaultdict(list)
    for start, label, page, row, eligible, surface in result["located_occurrences"]:
        groups[page, label].append((start, row))
        ts = range(start, start+length)
        if eligible != all(t in eligible_t for t in ts) or surface != all(t in exact_t for t in ts):
            raise AssertionError("review occurrence eligibility differs")
    pairs, feasible_pairs = [], []
    flags = {k: set() for k in ("full_mapped", "feasible_rows", "exact_surface", "hull_center_only")}
    for (page, label), values in groups.items():
        phrase = result["per_type"][label]["words"]
        for start, _ in values:
            actual = [lookup[t]["word"] for t in range(start, start+length)]
            if actual != phrase or any(lookup[t]["page"] != page for t in range(start, start+length)):
                raise AssertionError("review phrase identity/page differs")
        for (a, ra), (b, rb) in combinations(values, 2):
            if ra == rb:
                continue
            strict = all(abs(lookup[a+j]["x2"]-lookup[b+j]["x2"]) <= 30 for j in range(length))
            ax2 = min(lookup[a+j]["bbox"][0] for j in range(length))+max(lookup[a+j]["bbox"][2] for j in range(length))
            bx2 = min(lookup[b+j]["bbox"][0] for j in range(length))+max(lookup[b+j]["bbox"][2] for j in range(length))
            if abs(ax2-bx2) <= 30:
                flags["hull_center_only"].update((a, b))
            if strict:
                pairs.append([a, b])
                flags["full_mapped"].update((a, b))
                if all(t in eligible_t for start in (a, b) for t in range(start, start+length)):
                    feasible_pairs.append([a, b])
                    flags["feasible_rows"].update((a, b))
                if all(t in exact_t for start in (a, b) for t in range(start, start+length)):
                    flags["exact_surface"].update((a, b))
    if sorted(pairs) != sorted(result["aligned_pairs"]) or sorted(feasible_pairs) != sorted(result["feasible_aligned_pairs"]):
        raise AssertionError("independent scalar strict pair geometry differs")
    occurrence_type = {r[0]: r[1] for r in result["located_occurrences"]}
    totals = {}
    for name, starts in flags.items():
        non_allah = sum(result["per_type"][occurrence_type[t]]["without_allah_forms"] for t in starts)
        totals[name] = dict(all=len(starts), without_allah_forms=non_allah)
        if totals[name] != result["observed"][name]:
            raise AssertionError("independent scalar endpoint counts differ")
        by_type = Counter(occurrence_type[t] for t in starts)
        if any(t["aligned"][name] != by_type[i] for i, t in enumerate(result["per_type"])):
            raise AssertionError("independent per-type endpoint counts differ")
    return totals


def selected_examples(result):
    occurrences = {r[0]: r for r in result["located_occurrences"]}
    examples, used_pages, used_types = [], set(), set()
    paired_count = 0
    for pair in sorted(result["aligned_pairs"]):
        row = occurrences[pair[0]]
        label, page = row[1], row[2]
        if page in used_pages or label in used_types or not result["per_type"][label]["without_allah_forms"]:
            continue
        examples.append(dict(status="strict_pair", starts=pair, page=page, type_index=label))
        used_pages.add(page)
        used_types.add(label)
        paired_count += 1
        if paired_count == 6:
            break
    unpaired_count = 0
    for start in sorted(result["unpaired_start_ids"]):
        row = occurrences[start]
        label, page = row[1], row[2]
        if page in used_pages or not result["per_type"][label]["without_allah_forms"]:
            continue
        examples.append(dict(status="no_mapped_strict_partner", starts=[start], page=page, type_index=label))
        used_pages.add(page)
        unpaired_count += 1
        if unpaired_count == 2:
            break
    return examples


def analyze():
    report = json.loads(bp.OUTPUT.read_text())
    canonical, words, mapping, original, _, _ = bp.load()
    feasible = json.loads(bp.FEASIBILITY.read_text())
    eligible_t = {words[i]["t"] for p in feasible["pages"] for r in p["rows"] if r["eligible"] for i in r["word_indices"]}
    exact_t = {r[0] for r in original["views"]["exact_surface_v5"]["located_inventory"]}
    lookup = {w["t"]: w for w in words}
    pages = {p["page"]: p for p in mapping["pages"]}
    lengths = {}
    for key, result in report["results"].items():
        for t in result["per_type"]:
            if t["without_allah_forms"] != (not any(sw.is_name(sw.mt.norm(w)) for w in t["words"])):
                raise AssertionError("independent canonical Allah-form exclusion differs")
        totals = scalar_pairs(result, words, eligible_t, exact_t)
        examples = selected_examples(result)
        for example in examples:
            n = result["length"]
            example["words"] = result["per_type"][example["type_index"]]["words"]
            example["image_sha256"] = pages[example["page"]]["image_sha256"]
            example["occurrences"] = [dict(start=start, verse=canonical[start]["verse"],
                token_ids=list(range(start, start+n)), boxes=[lookup[t]["bbox"] for t in range(start, start+n)],
                twice_centers=[lookup[t]["x2"] for t in range(start, start+n)]) for start in example["starts"]]
            if len(example["starts"]) == 2:
                a, b = example["starts"]
                example["corresponding_center_differences_pixels"] = [abs(lookup[a+j]["x2"]-lookup[b+j]["x2"])/2 for j in range(n)]
        # Descriptive ranking only; no individual-type discovery probabilities.
        ranked = sorted((dict(type_index=i, **t) for i, t in enumerate(result["per_type"]) if t["without_allah_forms"]),
                        key=lambda t: (-t["aligned"]["full_mapped"], -t["located"], t["words"]))[:20]
        occurrence_type = {r[0]: r[1] for r in result["located_occurrences"]}
        occurrence_page = {r[0]: r[2] for r in result["located_occurrences"]}
        non_allah_pages = {occurrence_page[a] for a, _ in result["aligned_pairs"]
                           if result["per_type"][occurrence_type[a]]["without_allah_forms"]}
        lengths[key] = dict(independent_scalar_counts=totals, examples=examples, top_types_by_full_aligned_endpoints=ranked,
            non_allah_aligned_distinct_types=sum(t["without_allah_forms"] and t["aligned"]["full_mapped"]>0 for t in result["per_type"]),
            non_allah_aligned_pages=len(non_allah_pages),
            exact_surface_population=result["exact_surface_population"],
            unpaired_non_allah_occurrences=result["located_population"]["without_allah_forms"]-totals["full_mapped"]["without_allah_forms"])
    return dict(version="broad-phrase-independent-review-v1", lengths=lengths,
        inputs={p.name: sw.digest(p) for p in (bp.PLAN, bp.FEASIBILITY, bp.OUTPUT, Path(__file__))},
        caveat="Every strict pair and endpoint total is checked with independent scalar word-by-word geometry. Scan examples follow the predeclared earliest-pair/distinct-page/type rule and are exposed diagnostics, not independent annotation or absence certification. Top-type ranking is descriptive and does not select the population or test statistic.")


def review(directory, report):
    from PIL import Image, ImageDraw
    from image_io import open_rgb
    directory.mkdir(parents=True, exist_ok=True)
    manifest = []
    for length, result in report["lengths"].items():
        for index, example in enumerate(result["examples"]):
            path = sw.ROOT / "hayrat-pics" / f"page_{example['page']}.png"
            if sw.digest(path) != example["image_sha256"]:
                raise AssertionError("broad review scan hash differs")
            image = open_rgb(path)
            boxes = [b for o in example["occurrences"] for b in o["boxes"]]
            left = max(0, min(b[0] for b in boxes)-35)
            right = min(image.width, max(b[2] for b in boxes)+35)
            panels = []
            for o in example["occurrences"]:
                top = max(0, min(b[1] for b in o["boxes"])-20)
                bottom = min(image.height, max(b[3] for b in o["boxes"])+20)
                crop = image.crop((left, top, right, bottom))
                panel = Image.new("RGB", (max(600, crop.width*2), crop.height*2+60), "white")
                panel.paste(crop.resize((crop.width*2, crop.height*2)), (0, 60))
                draw = ImageDraw.Draw(panel)
                draw.text((4, 3), f"n={length}; p{example['page']}; {o['verse']}; t{o['start']}; {example['status']}", fill="black")
                draw.text((4, 20), "Shared original x-frame; 2x raw scan; blue boxes/centers are identity overlays", fill="black")
                draw.text((4, 37), "Color did not select this phrase. Exposed diagnostic, not fresh annotation.", fill="black")
                for b in o["boxes"]:
                    draw.rectangle(((b[0]-left)*2, (b[1]-top)*2+60, (b[2]-left)*2, (b[3]-top)*2+60), outline="#0066ff", width=2)
                    cx = b[0]+b[2]-2*left
                    draw.line((cx, 60, cx, panel.height), fill="#9999ff", width=1)
                panels.append(panel)
            sheet = Image.new("RGB", (max(p.width for p in panels), sum(p.height for p in panels)), "white")
            y = 0
            for p in panels:
                sheet.paste(p, (0, y))
                y += p.height
            filename = f"n{length}_{index:02d}_p{example['page']}_{example['status']}.png"
            sheet.save(directory / filename)
            manifest.append(dict(filename=filename, length=int(length), **example))
    (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    for length in report["lengths"]:
        selected = [r for r in manifest if r["length"] == int(length)]
        contact = Image.new("RGB", (1640, 530*((len(selected)+1)//2)), "white")
        draw = ImageDraw.Draw(contact)
        for index, entry in enumerate(selected):
            with Image.open(directory / entry["filename"]) as im:
                thumbnail = im.copy()
            thumbnail.thumbnail((800, 500))
            x, y = 820*(index%2), 530*(index//2)
            draw.text((x+5, y+3), entry["filename"], fill="black")
            contact.paste(thumbnail, (x, y+25))
        contact.save(directory / f"contact_n{length}.png")
    print("scan diagnostic sheets", len(manifest), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    result = analyze()
    if args.verify:
        if result != json.loads(OUTPUT.read_text()):
            raise AssertionError("broad independent review differs")
        print("PASS independent scalar checks of every phrase/word pair and all endpoint totals")
    else:
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"))+"\n")
    if args.review:
        review(args.review, result)
    for n, r in result["lengths"].items():
        print("length", n, "full counts", r["independent_scalar_counts"]["full_mapped"])
        print("distinct aligned types", r["non_allah_aligned_distinct_types"], "pages", r["non_allah_aligned_pages"],
              "exact-surface counts", r["independent_scalar_counts"]["exact_surface"], "population", r["exact_surface_population"])
        for t in r["top_types_by_full_aligned_endpoints"][:6]:
            print(" ", " ".join(t["words"]), t["aligned"]["full_mapped"], "/", t["located"],
                  "eligible", t["aligned"]["feasible_rows"], "/", t["eligible"], "spacing mean", t["spacing_mean_aligned"])


if __name__ == "__main__":
    main()
