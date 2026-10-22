"""Force-align approximate OCR lines to the exact Quran, retaining ambiguity.

Only text-line membership is inferred; no word x-coordinates are invented.
All minimum unit-edit-cost paths are considered. A word gets a stable line
only if every possible nondeleted character assignment uses that line and
no optimal path can delete the entire word. This is algorithmic stability,
not a calibrated probability that the image interpretation is correct.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import map_tokens as mt
from ocr_benchmark import words, reading_order
from semantic_validation import DATA, MANUAL, corpus_targets


def costs(a, b):
    table = np.empty((len(a) + 1, len(b) + 1), dtype=np.int32)
    table[:, 0] = np.arange(len(a) + 1)
    table[0, :] = np.arange(len(b) + 1)
    for i, char in enumerate(a, 1):
        for j, other in enumerate(b, 1):
            table[i, j] = min(table[i - 1, j] + 1, table[i, j - 1] + 1,
                              table[i - 1, j - 1] + (char != other))
    return table


def align_words(reference_words, recognized_lines):
    reference = "".join(reference_words)
    observed = "".join(recognized_lines)
    line_of = [i for i, line in enumerate(recognized_lines) for _ in line]
    forward = costs(reference, observed)
    backward = costs(reference[::-1], observed[::-1])[::-1, ::-1]
    optimum = int(forward[-1, -1])
    possible = []
    for i, char in enumerate(reference):
        valid = (forward[i, :-1] + backward[i + 1, 1:]
                 + np.fromiter((char != c for c in observed), dtype=np.int32)) == optimum
        possible.append({line_of[j] for j in np.flatnonzero(valid)})
    result, start = [], 0
    for word in reference_words:
        end = start + len(word)
        lines = set().union(*possible[start:end])
        deletion = bool(np.any(forward[start] + len(word) + backward[end] == optimum))
        result.append(dict(word=word, line_candidates=sorted(lines),
                           whole_word_deletion_possible=deletion,
                           stable_line=next(iter(lines)) if len(lines) == 1 and not deletion else None))
        start = end
    return result, optimum


def analyze(source, manual_path=MANUAL):
    manual = json.loads(manual_path.read_text())
    verses = mt.load_tokens()
    flat = [(f"{s}:{a}", token) for s, a, ts in verses for token in ts]
    reports, inputs = [], {}
    for page in manual["pages"]:
        n = page["page"]
        path = source / f"page_{n}.json"
        obj = json.loads(path.read_text())
        if obj["image_sha256"] != page["image_sha256"]:
            raise AssertionError("OCR/manual image mismatch")
        lines = reading_order(obj["result"]["text_lines"])
        first, last = page["first_verse"], page["last_verse"]
        i0 = next(i for i, (verse, _) in enumerate(flat) if verse == first)
        i1 = max(i for i, (verse, _) in enumerate(flat) if verse == last) + 1
        tokens = flat[i0:i1]
        mapped, optimum = align_words(["".join(words(token)) for _, token in tokens],
                                       ["".join(words(line["text"])) for line in lines])
        for i, row in enumerate(mapped):
            row.update(t=i0 + i, verse=tokens[i][0], canonical_token=tokens[i][1])
            if row["stable_line"] is not None:
                row["line_bbox"] = lines[row["stable_line"]]["bbox"]
        name_results = []
        for target, label in zip(corpus_targets(verses, first, last), page["names"]):
            row = mapped[target["t"] - i0]
            box = row.get("line_bbox")
            correct = box is not None and label["rect"][1] <= (box[1] + box[3]) / 2 <= label["rect"][3]
            name_results.append(dict(t=target["t"], verse=target["verse"],
                                     stable_line=row["stable_line"], correct_line=bool(correct)))
        reports.append(dict(page=n, edit_cost=optimum, total_words=len(mapped),
                            stable_words=sum(x["stable_line"] is not None for x in mapped),
                            name_total=len(name_results),
                            name_correct_lines=sum(x["correct_line"] for x in name_results),
                            name_unstable=sum(x["stable_line"] is None for x in name_results),
                            name_results=name_results, words=mapped))
        inputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(version="all-optimal-edit-path-line-map-v1", pages=reports, inputs=inputs,
                manual_sha256=hashlib.sha256(manual_path.read_bytes()).hexdigest(),
                corpus_sha256=hashlib.sha256((DATA / "quran-uthmani.json").read_bytes()).hexdigest(),
                total_words=sum(p["total_words"] for p in reports),
                stable_words=sum(p["stable_words"] for p in reports),
                name_total=sum(p["name_total"] for p in reports),
                name_correct_lines=sum(p["name_correct_lines"] for p in reports),
                name_unstable=sum(p["name_unstable"] for p in reports),
                caveat="Exact text forced onto approximate OCR by minimum-edit alignment. "
                "All-optimal-path stability is conditional on this alignment model. "
                "Only the provided Allah-name line locations are independently checked; "
                "other stable word lines remain hypotheses. Word x-coordinates are not inferred.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DATA / "ocr_sample_v1")
    parser.add_argument("--manual", type=Path, default=MANUAL)
    parser.add_argument("--output", type=Path, default=DATA / "audit_ocr_line_map.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze(args.source, args.manual)
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("OCR-to-exact-corpus line map does not reproduce")
        print("PASS exact-text OCR line map, all-optimal-path ambiguity and manual name-line checks")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print({k: v for k, v in report.items() if k not in ("pages", "inputs")})
        for row in report["pages"]:
            print(row["page"], "stable words", row["stable_words"], "/", row["total_words"],
                  "correct name lines", row["name_correct_lines"], "/", row["name_total"],
                  "unstable names", row["name_unstable"])


if __name__ == "__main__":
    main()
