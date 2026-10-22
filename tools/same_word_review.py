"""Post-count diagnostic crops for same-word witnesses and unpaired locations.

Select the earliest six standalone-Allah pairs on distinct pages and six
unpaired mapped occurrences on other distinct pages. This is exposed review,
not an independent accuracy sample. It never edits the measured inventory.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

import map_tokens as mt
from image_io import open_rgb
from same_word_alignment import OUTPUT, canonical_inventory, digest
from semantic_validation import ROOT
import ocr_word_boundary_map as wm


def review(directory):
    report = json.loads(OUTPUT.read_text())
    if digest(wm.OUTPUT) != report["inputs"][wm.OUTPUT.name]:
        raise AssertionError("same-word review mapping differs")
    source = json.loads(wm.OUTPUT.read_text())
    pages = {p["page"]: p for p in source["pages"]}
    canonical, _ = canonical_inventory()
    measured = report["views"]["conservative_v5"]
    located = {row[0]: row for row in measured["located_inventory"]}
    accepted = set(located)
    boxes = {(p["page"], w["t"]): w["bbox"] for p in source["pages"] for w in p["words"]
             if w["kind"] == "verse" and w["t"] in accepted and "bbox" in w}
    # Frozen site policy can use a single mandatory raw-region box when the
    # mapper has no support union. Reconstruct that explicit geometry too.
    import word_boundary_sites as ws
    if digest(ws.OUTPUT) != report["inputs"][ws.OUTPUT.name]:
        raise AssertionError("same-word review site source differs")
    for p in json.loads(ws.OUTPUT.read_text())["pages"]:
        for word in p["words"]:
            if word["kind"] == "verse" and word["t"] in accepted:
                boxes[p["page"], word["t"]] = word["bbox"]
    chosen, used_pages = [], set()
    for t, u in sorted(measured["same_word_pair_token_ids"], key=lambda pair: tuple(sorted(pair))):
        if canonical[t]["word"] != "الله":
            continue
        page = located[t][1]
        if page in used_pages:
            continue
        chosen.append(("paired", [t, u]))
        used_pages.add(page)
        if len(chosen) == 6:
            break
    unpaired = 0
    for t in sorted(measured["same_word_unpaired_located_token_ids"]):
        page = located[t][1]
        if canonical[t]["word"] == "الله" and page not in used_pages:
            chosen.append(("no_mapped_partner", [t]))
            used_pages.add(page)
            unpaired += 1
            if unpaired == 6:
                break
    directory.mkdir(parents=True, exist_ok=True)
    manifest = []
    for status, ids in chosen:
        page = located[ids[0]][1]
        path = ROOT / "hayrat-pics" / f"page_{page}.png"
        if digest(path) != pages[page]["image_sha256"]:
            raise AssertionError("same-word review scan hash differs")
        image = open_rgb(path)
        panels, details = [], []
        for t in ids:
            box = boxes[page, t]
            if box[0]+box[2] != located[t][3] or box[2]-box[0] != located[t][4]:
                raise AssertionError("same-word review center/width differs")
            left, top = max(0, box[0]-80), max(0, box[1]-25)
            right, bottom = min(image.width, box[2]+80), min(image.height, box[3]+25)
            crop = image.crop((left, top, right, bottom))
            crop = crop.resize((crop.width*3, crop.height*3))
            panel = Image.new("RGB", (max(520, crop.width), crop.height+65), "white")
            panel.paste(crop, (0, 65))
            draw = ImageDraw.Draw(panel)
            draw.text((2, 2), f"p{page}; {canonical[t]['verse']}; t={t}; standalone Allah; {status}", fill="black")
            draw.text((2, 18), f"3x raw scan; seeded row={located[t][2]}; center x={located[t][3]/2}", fill="black")
            draw.text((2, 34), "Gray detector/support box; geometric diagnosis, not new annotation", fill="black")
            draw.rectangle(((box[0]-left)*3, (box[1]-top)*3+65,
                            (box[2]-left)*3-1, (box[3]-top)*3+64), outline="gray", width=2)
            panels.append(panel)
            details.append(dict(t=t, verse=canonical[t]["verse"], page=page, bbox=box, x=located[t][3]/2))
        sheet = Image.new("RGB", (sum(p.width for p in panels), max(p.height for p in panels)), "white")
        offset = 0
        for panel in panels:
            sheet.paste(panel, (offset, 0))
            offset += panel.width
        filename = f"p{page}_{status}_"+"_".join(map(str, ids))+".png"
        sheet.save(directory / filename)
        manifest.append(dict(filename=filename, status=status, occurrences=details))
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    from semantic_validation import is_name
    unresolved_names = [dict(**r, **{k: canonical[r["t"]][k] for k in ("verse", "word", "form")})
                        for r in measured["unresolved_inventory"] if is_name(canonical[r["t"]]["form"])]
    groups = []
    for model in ("page_row", "page_row_width20"):
        grouped = {}
        for t, page, row, x2, width in measured["located_inventory"]:
            key = (page, row, width//20 if model == "page_row_width20" else 0)
            grouped.setdefault(key, []).append(canonical[t])
        metrics = {}
        for name, selected in (("standalone_allah", lambda w: w["word"] == "الله"),
                               ("allah_name_family", lambda w: is_name(w["form"]))):
            fixed, movable, sites = 0, 0, 0
            for words in grouped.values():
                count = sum(selected(w) for w in words)
                if count == len(words):
                    fixed += count
                elif count:
                    movable += count
                    sites += len(words)
            metrics[name] = dict(fixed_target_occurrences=fixed, movable_target_occurrences=movable,
                                 mixed_stratum_sites=sites)
        groups.append(dict(model=model, metrics=metrics))
    focused_words = sorted((row for row in measured["per_word"] if is_name(mt.norm(row["word"]))),
                           key=lambda r: (-r["canonical_expected"], r["word"]))
    diagnostics = dict(unresolved_names=unresolved_names, name_spelling_counts=focused_words,
                       randomization_diagnostics=groups,
                       paired_sheets=sum(r["status"] == "paired" for r in manifest),
                       unpaired_sheets=sum(r["status"] == "no_mapped_partner" for r in manifest))
    (directory / "diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2)+"\n")
    print("same-word diagnostic sheets", len(manifest))
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    review(parser.parse_args().directory)
