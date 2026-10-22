"""Descriptive inspection of 9:128-129 on archived semantic pins.

This is not a statistical test of verse authenticity. The legacy script
mixed raw/normalized token indices, guessed target ink boxes, and used
untracked features. Here token identity is explicit and missing pins remain
unknown, not black or unaligned by assumption.
"""
import json
from pathlib import Path

import map_tokens as mt
from word_pair_census import load_pins

DATA = Path(__file__).resolve().parent / "data"


def main():
    verses = mt.load_tokens()
    flat = [(s, a, tok) for s, a, ts in verses for tok in ts]
    pins = load_pins("mark_identity_semantic.json")
    rows = []
    for t, (s, a, word) in enumerate(flat):
        if s != 9 or a not in (128, 129):
            continue
        matches = [p for p in pins if p["t"] == t]
        for p in matches:
            p = dict(p)
            p["same_word_cell_other_pages"] = sum(
                q["page"] != p["page"] and q["word"] == p["word"]
                and (q["yb"], q["xb"]) == (p["yb"], p["xb"]) for q in pins)
            rows.append(dict(verse=f"{s}:{a}", t=t, word=word, pin=p))
        if not matches:
            rows.append(dict(verse=f"{s}:{a}", t=t, word=word,
                             status="no semantic pin; ink and position not determined"))
    out = dict(source="mark_identity_semantic.json", rows=rows,
               verdict="Descriptive selected-pin inspection only; no inference about insertion, "
                       "authenticity or absence of alignment is supported.")
    (DATA / "audit_19er.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
