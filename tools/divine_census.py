"""Divine-name ink census (A4): corpus totals vs ink-verified pins.

Corpus side: exact normalized word-boundary forms. The interrogative
ءالله at 10:59 and 27:59 IS a divine-name form, not a false friend.
1:1 is encoded, 112 other surah-head basmalas are not; 27:30 is embedded
verse text and remains counted under every convention reported here.

Ink side: semantic-mode pins, deduplicated by token identity. Counts remain
conditional on annotation correctness; count matching alone is not proof.

Usage: python tools/divine_census.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u0640\u0610-\u061A]")
# forms with لله inside; true lafzullah vs false friends
TRUE_FORMS = {"لله", "بالله", "والله", "فالله", "ولله", "فلله", "تالله",
              "وتالله", "ابالله", "ءالله"}
FALSE_FORMS = {"اللهم", "اللهو", "اللهب", "للهدي", "خللها", "خلله",
               "خللهما", "يضلله", "ظلله", "ظللها", "وظللهم"}


def norm(t):
    t = DIAC.sub("", t)
    return t.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا") \
            .replace("آ", "ا").replace("ى", "ي")


def corpus_counts():
    d = json.loads((DATA / "quran-uthmani.json").read_text())
    c = Counter()
    nbas = 0
    for ay in d["verses"]:
        n = norm(ay["text_uthmani"])
        if n.startswith("بسم الله الرحمن الرحيم"):
            nbas += 1
            n = n[len("بسم الله الرحمن الرحيم"):].strip()
        for t in n.split():
            if t == "الله" or t in TRUE_FORMS:
                c[t] += 1
            elif t in FALSE_FORMS:
                c["FALSE:" + t] += 1
    return c, nbas


def pin_counts():
    d = json.loads((DATA / "mark_identity_semantic.json").read_text())
    pin = Counter()
    seen = set()
    for s in d["segments"]:
        for p in s.get("pins", []):
            key = (p["t"], p["kind"])
            if key in seen:
                continue
            seen.add(key)
            pin[(p["tok"], p["kind"])] += 1
    return pin


def main():
    c, nbas = corpus_counts()
    pin = pin_counts()
    lah_forms = {k: v for k, v in c.items() if not k.startswith("FALSE:")}
    total_lah = sum(lah_forms.values())
    pins_lah = {}
    for (tok, kind), n in pin.items():
        if tok == "الله" or tok in TRUE_FORMS:
            pins_lah[f"{tok}/{kind}"] = pins_lah.get(f"{tok}/{kind}", 0) + n
    out = {
        "corpus_totals": dict(sorted(lah_forms.items(), key=lambda z: -z[1])),
        "false_friends_excluded": {k.split(":")[1]: v for k, v in c.items()
                                   if k.startswith("FALSE:")},
        "note_basalas": "Excluding opening basmala means remove encoded 1:1 only; "
                         "embedded 27:30 remains. Add 1 for the encoded corpus, "
                         "then 112 for unencoded surah heads (113 heads total).",
        "total_excluding_encoded_opening_basmala": total_lah,
        "encoded_opening_basmalas_removed": nbas,
        "total_encoded_corpus": total_lah + nbas,
        "total_with_all_surah_head_basmalas": total_lah + nbas + 112,
        "interrogative_divine_name_references": ["10:59", "27:59"],
        "pin_source": "mark_identity_semantic.json",
        "pins_lafzullah": pins_lah,
        "pins_total_lafzullah": sum(pins_lah.values()),
        "pin_count_divided_by_encoded_corpus_total": round(
            sum(pins_lah.values()) / (total_lah + nbas), 4),
        "coverage_caveat": "Not a certified lower bound: pin identities require "
                           "independent validation; a token can carry both kinds.",
        "other_crimson_members": {f"{tok}/{kind}": n
                                  for (tok, kind), n in pin.items()
                                  if tok in ("محمد", "اذكروا", "هو", "هوَ",
                                             "رب", "ربكم", "ربك", "ربهم",
                                             "ربه", "ربي", "ربنا")},
        "hamdallah": {
            "status": "historical manual census; not recomputed by this script",
            "total_instances": 23, "measured": 22,
            "cri_side": 15, "mag_side": 12, "dual": 5,
            "unmeasured": ["1:2 (Fatiha page is not among the 604 scans)"],
            "see": "probability-model.md S16 A4.1 and A4.5",
        },
    }
    (DATA / "divine_census.json").write_text(json.dumps(
        out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
