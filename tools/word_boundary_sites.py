"""Conservative v5 site view: exact normalized text for multi-region unions.

This geometry/lexical policy reads no manual annotations. Single mandatory
regions retain the earlier site policy; unions must reproduce the exact
canonical normalized token. Missing support never implies absent or black ink.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_corpus_sites as cs
import ocr_word_boundary_map as wm
from semantic_validation import DATA

OUTPUT = DATA / "audit_word_boundary_sites_v5.json"


def exact_union(word):
    return len(word["mandatory_regions"]) <= 1 or word["surface_match"]


def analyze(mapping_path=wm.OUTPUT):
    mapping = json.loads(mapping_path.read_text())
    for path in (cm.SOURCE, cm.mt.TOKENS_F):
        if mapping["inputs"][path.name] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise AssertionError("boundary site/map input hashes differ")
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    pages, excluded, outcomes = [], [], Counter()
    for page in mapping["pages"]:
        if page["image_sha256"] != raw[page["page"]]["image_sha256"]:
            raise AssertionError("boundary site/map image hashes differ")
        rows = []
        if page["status"] == "conditional_word_window_match":
            for word in page["words"]:
                row, status = cs.site(word, raw[page["page"]]["regions"])
                if row is not None and not exact_union(row):
                    excluded.append(dict(page=page["page"], **row))
                    row, status = None, "nonexact_multiregion_union"
                outcomes[status] += 1
                if row is not None:
                    rows.append(row)
        pages.append(dict(page=page["page"], image_sha256=page["image_sha256"], status=page["status"], words=rows))
    canonical = Counter(w["t"] for p in pages for w in p["words"] if w["kind"] == "verse")
    tokens, _, _ = cm.virtual_corpus()
    missing = [dict(t=w["t"], verse=w["verse"], form=w["form"]) for w in tokens
               if w["kind"] == "verse" and not w["verse"].startswith("1:") and cm.is_name(w["form"])
               and w["t"] not in canonical]
    return dict(version="boundary-aware-conservative-sites-v5", pages=pages, summary=cm.summary(pages),
                policy_outcomes=dict(outcomes), excluded_nonexact_unions=excluded,
                missing_scanned_name_ids=missing, duplicate_canonical_ids={str(t): n for t, n in canonical.items() if n > 1},
                inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (mapping_path, cm.SOURCE, cm.mt.TOKENS_F)},
                caveat="Post-hoc conservative view: multi-region union support must spell the exact normalized "
                "canonical token, single regions retain the existing geometry policy and 35px height minimum. "
                "Uses no manual annotations. Rejected unions may be legitimate OCR spelling errors too. "
                "These are word-site hypotheses, not full-boundary or corpus-wide semantic certification.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("conservative boundary-aware site view differs")
        print("PASS conservative v5 sites: policy, source hashes, exclusions and missing-name inventory")
    else:
        args.output.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("summary", report["summary"])
    print("excluded unions", len(report["excluded_nonexact_unions"]))
    print("missing names", report["missing_scanned_name_ids"])


if __name__ == "__main__":
    main()
