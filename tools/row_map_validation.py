"""Fresh frozen-rule row/word localization comparison, with uncertain edges.

The twenty labels were read before inspecting these predicted word locations.
V1/v3 are comparison methods; v4's inference files were hash-frozen in advance.
"""
import argparse
import hashlib
import json
from pathlib import Path

import ocr_corpus_map as cm
import ocr_corpus_sites as cs
import ocr_observation_map as om
import ocr_row_map as rm
import row_validation_sample as sample
from semantic_validation import DATA
from word_localization_validation import assess

OUTPUT = DATA / "audit_row_fresh_validation_v4.json"


def analyze():
    manual = json.loads(sample.MANUAL.read_text())
    if sample.build(False, manual) != manual:
        raise AssertionError("fresh labels or frozen inference rules differ")
    raw = {p["page"]: p for p in json.loads(cm.SOURCE.read_text())["pages"]}
    sources = {"preserved_sites_v1": cs.OUTPUT, "observations_v3": om.OUTPUT, "seeded_rows_v4": rm.OUTPUT}
    results = {}
    for method, source in sources.items():
        mapped = {p["page"]: p for p in json.loads(source.read_text())["pages"]}
        details = []
        for page in manual["pages"]:
            n = page["page"]
            if page["image_sha256"] != raw[n]["image_sha256"] or page["image_sha256"] != mapped[n]["image_sha256"]:
                raise AssertionError("fresh annotation and predicted image hashes differ")
            rows = mapped[n]["words"]
            for label in page["word_samples"]:
                matching = [w for w in rows if w["kind"] == label["kind"] and
                            ((w["t"] == label["t"]) if label["kind"] == "verse" else
                             (w["verse"], w["word_in_verse"]) == (label["verse"], label["word_in_verse"]))]
                if len(matching) > 1:
                    raise AssertionError("duplicate token on fresh page")
                row = matching[0] if matching else {}
                if row and method != "preserved_sites_v1":
                    row, _ = cs.site(row, raw[n]["regions"])
                if row and row["form"] != label["form"]:
                    raise AssertionError("fresh predicted token spelling differs")
                details.append(dict(page=n, **label, **assess(row or {}, label)))
        groups = {}
        for name, subset in (("all", details),
                             ("fixed_second_words", [r for r in details if r["selection"] == "fixed_second_word"]),
                             ("basmala_names", [r for r in details if r["selection"] == "supplementary_basmala_name"])):
            groups[name] = dict(total=len(subset), accepted=sum(r["accepted"] for r in subset),
                                correct_centers=sum(r["center_correct"] for r in subset),
                                boundary_evaluable=sum(r["boundary_eligible"] for r in subset),
                                boundary_pass=sum(r["horizontal_boundary_pass"] for r in subset))
        results[method] = dict(groups=groups, details=details)
    paths = [sample.PLAN, sample.MANUAL, cm.SOURCE, *sources.values()]
    return dict(version="fresh-frozen-seeded-row-word-comparison-v4", results=results,
                inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                caveat="Twenty labels on eight deliberately selected fresh pages, one AI reader. Inference "
                "source hashes and selection frozen before annotation; no corresponding predicted word "
                "locations inspected first. Full predictions existed on disk. Eighteen fixed second words "
                "on non-header pages plus two supplementary basmala names, not a representative random sample "
                "of all words or pages. Manual partitions and pixel contacts leave many boundaries unscorable; "
                "centers and +/-12px horizontal edges do not certify complete ink ownership or semantic census.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.verify:
        if report != json.loads(args.output.read_text()):
            raise AssertionError("fresh row/word comparison does not reproduce")
        print("PASS fresh frozen-rule row/word comparison: labels, all outcomes and input hashes")
    else:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for name, row in report["results"].items():
        print(name, row["groups"])
        print("wrong/abstained", [(r["page"], r["verse"], r["form"], r["status"], r.get("bbox"))
                                  for r in row["details"] if not r["center_correct"]])
        print("boundary failures", [(r["page"], r["form"], r.get("signed_x_edge_errors"))
                                    for r in row["details"] if r["boundary_eligible"] and not r["horizontal_boundary_pass"]])


if __name__ == "__main__":
    main()
