"""CPU scoring of raw Arabic OCR against exact Quran text and manual locations.

Diacritics, tatweel, digits and punctuation are removed; the normalization
otherwise follows the audited corpus normalizer. CER excludes whitespace;
WER retains token boundaries, so split prefixes count as word errors.
No recognized text is silently corrected to the expected Quran text.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import map_tokens as mt
from semantic_validation import MANUAL, DATA, is_name, localized


def words(text):
    return re.sub(r"[^\u0621-\u063a\u0641-\u064a\s]", " ", mt.norm(text)).split()


def edit_counts(reference, recognized):
    """Unit-cost edit distance with deterministic substitution/deletion ties."""
    previous = [(j, 0, 0, j) for j in range(len(recognized) + 1)]
    for i, a in enumerate(reference, 1):
        current = [(i, 0, i, 0)]
        for j, b in enumerate(recognized, 1):
            score, s, d, ins = previous[j - 1]
            diagonal = (score + (a != b), s + (a != b), d, ins)
            score, s, d, ins = previous[j]
            deletion = (score + 1, s, d + 1, ins)
            score, s, d, ins = current[j - 1]
            insertion = (score + 1, s, d, ins + 1)
            current.append(min((diagonal, deletion, insertion), key=lambda x: x[0]))
        previous = current
    distance, s, d, ins = previous[-1]
    return dict(distance=distance, substitutions=s, deletions=d, insertions=ins,
                reference_length=len(reference), recognized_length=len(recognized),
                error_rate=distance / len(reference) if reference else None)


def reading_order(lines):
    groups = []
    for line in sorted(lines, key=lambda x: (x["bbox"][1] + x["bbox"][3]) / 2):
        cy = (line["bbox"][1] + line["bbox"][3]) / 2
        if groups and cy - groups[-1][0] < 40:
            groups[-1][1].append(line)
        else:
            groups.append((cy, [line]))
    return [line for _, group in groups for line in sorted(group, key=lambda x: -x["bbox"][2])]


def analyze(source, manual_path=MANUAL):
    manual = json.loads(manual_path.read_text())
    corpus = json.loads((DATA / "quran-uthmani.json").read_text())["verses"]
    index = {v["verse_key"]: i for i, v in enumerate(corpus)}
    rows, inputs = [], {}
    for page in manual["pages"]:
        n = page["page"]
        path = source / f"page_{n}.json"
        raw = json.loads(path.read_text())
        if raw["image_sha256"] != page["image_sha256"]:
            raise AssertionError("OCR image differs from annotated image")
        lines = reading_order(raw["result"]["text_lines"])
        recognized = " ".join(line["text"] for line in lines)
        expected = " ".join(v["text_uthmani"] for v in
                            corpus[index[page["first_verse"]]:index[page["last_verse"]] + 1])
        ref_words, rec_words = words(expected), words(recognized)
        word_records = [word for line in lines for word in (line.get("words") or [])]
        if not word_records:
            raise ValueError(f"p{n}: OCR returned no word records; run with return_words=True before localization scoring")
        candidates = []
        for line in lines:
            for word in line.get("words") or []:
                token = words(word["text"])
                if len(token) != 1 or not is_name(token[0]):
                    continue
                x0, y0, x1, y1 = word["bbox"]
                candidates.append(dict(text=word["text"], normalized=token[0], bbox=word["bbox"],
                                       bbox_valid=word["bbox_valid"], confidence=word["confidence"],
                                       cx=(x0 + x1) / 2, cy=(y0 + y1) / 2))
        matched, name_details = set(), []
        for pred in candidates:
            matching = [i for i, label in enumerate(page["names"])
                        if pred["bbox_valid"] and localized(pred, label)]
            fresh = [i for i in matching if i not in matched]
            if len(fresh) == 1:
                matched.add(fresh[0])
            name_details.append(dict(**pred, matching_manual_indices=matching))
        rows.append(dict(page=n, lines=len(lines), word_records=len(word_records),
                         valid_word_records=sum(w["bbox_valid"] for w in word_records),
                         reference_text=expected, recognized_text=recognized,
                         word_errors=edit_counts(ref_words, rec_words),
                         character_errors=edit_counts("".join(ref_words), "".join(rec_words)),
                         expected_name_occurrences=len(page["names"]), ocr_name_words=len(candidates),
                         localized_name_occurrences=len(matched), name_predictions=name_details))
        inputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = source / "metadata.json"
    inputs[metadata.name] = hashlib.sha256(metadata.read_bytes()).hexdigest()
    summary = {}
    for metric in ("word_errors", "character_errors"):
        sums = {key: sum(row[metric][key] for row in rows) for key in
                ("distance", "substitutions", "deletions", "insertions", "reference_length", "recognized_length")}
        sums["error_rate"] = sums["distance"] / sums["reference_length"]
        summary[metric] = sums
    return dict(version="arabic-ocr-benchmark-v1", pages=rows, summary=summary,
                expected_name_occurrences=sum(r["expected_name_occurrences"] for r in rows),
                localized_name_occurrences=sum(r["localized_name_occurrences"] for r in rows),
                ocr_name_words=sum(r["ocr_name_words"] for r in rows),
                inputs=inputs, manual_sha256=hashlib.sha256(manual_path.read_bytes()).hexdigest(),
                corpus_sha256=hashlib.sha256((DATA / "quran-uthmani.json").read_bytes()).hexdigest(),
                caveat="Uncorrected OCR on six annotated pages. Token splitting affects WER. "
                "Correctly reading a name does not guarantee its predicted bounding box is correct. "
                "No full-corpus word-map accuracy is inferred from this pilot.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DATA / "ocr_sample_v1")
    parser.add_argument("--manual", type=Path, default=MANUAL)
    parser.add_argument("--output", type=Path, default=DATA / "audit_arabic_ocr.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze(args.source, args.manual)
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("Arabic OCR benchmark does not reproduce")
        print("PASS Arabic OCR benchmark: exact text, edit counts, manual name locations, input hashes")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report["summary"], indent=2))
        print("localized names", report["localized_name_occurrences"], "/", report["expected_name_occurrences"])
        for row in report["pages"]:
            print(row["page"], "CER", row["character_errors"]["error_rate"], "WER", row["word_errors"]["error_rate"],
                  "localized names", row["localized_name_occurrences"], "/", row["expected_name_occurrences"])


if __name__ == "__main__":
    main()
