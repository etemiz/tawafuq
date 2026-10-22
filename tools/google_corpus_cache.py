"""Prepare/review a full-scan Google OCR cache; raw responses stay in logs.

This manifest contains image scope only, not verse identities or ground truth.
Reuse prior responses only when image hash, full-page crop and engine/options
match. Compact derived regions can be exported after all pages complete.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from PIL import Image

from semantic_validation import ROOT, DATA, is_name
from ocr_benchmark import words
from arabic_ocr_cloud import convert

MANIFEST = DATA / "google_corpus_manifest_v1.json"
CACHE = ROOT / "logs" / "ocr-google-corpus-v1"
SOURCES = [DATA / p for p in ("ocr_sample_google_v1", "ocr_heldout_google_v1",
                              "ocr_word_validation_google_v2")]


def prepare(manifest_path, cache):
    cache.mkdir(parents=True, exist_ok=True)
    pages = []
    for n in range(1, 605):
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        with Image.open(path) as image:
            width, height = image.size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        reuse = None
        for source in SOURCES:
            candidate = source / f"page_{n}.json"
            if not candidate.exists():
                continue
            meta = json.loads((source / "metadata.json").read_text())
            row = json.loads(candidate.read_text())
            if (meta["engine"] == "google-cloud-vision" and meta["feature"] == "DOCUMENT_TEXT_DETECTION"
                    and not meta["language_hints"] and row["image_sha256"] == digest
                    and row["crop"] == [0, 0, width, height]):
                reuse = candidate
                break
        destination = cache / f"page_{n}.json"
        if reuse is not None and not destination.exists():
            destination.symlink_to(os.path.relpath(reuse, cache))
        pages.append(dict(page=n, image_sha256=digest, width=width, height=height, ocr_bottom=height,
                          reused_source=str(reuse.relative_to(ROOT)) if reuse else None))
    report = dict(version="google-full-page-image-scope-v1", pages=pages,
                  scope="All 604 scans, full image including ornaments/basmalas. No supplied reference text. "
                  "Not a semantic annotation set. Raw responses stored in gitignored logs.")
    manifest_path.write_text(json.dumps(report, indent=2) + "\n")
    remaining = sum(not (cache / f'page_{p["page"]}.json').exists() for p in pages)
    print("pages", len(pages), "reusable", sum(p["reused_source"] is not None for p in pages),
          "remaining requests", remaining, "estimated USD", remaining * .0015)


def summarize(manifest_path, cache, output):
    manifest = json.loads(manifest_path.read_text())
    pages, missing = [], []
    for page in manifest["pages"]:
        path = cache / f'page_{page["page"]}.json'
        if not path.exists():
            missing.append(page["page"])
            continue
        row = json.loads(path.read_text())
        if row["image_sha256"] != page["image_sha256"] or row["crop"] != [
                0, 0, page["width"], page["height"]]:
            raise AssertionError("corpus cache has wrong image/crop")
        regions = [dict(text=w["text"], bbox=w["bbox"], confidence=w["confidence"],
                        bbox_valid=w["bbox_valid"])
                   for line in row["result"]["text_lines"] for w in line["words"]]
        pages.append(dict(page=page["page"], image_sha256=page["image_sha256"],
                          response_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          regions=regions, raw_name_candidates=sum(
                              len(t := words(w["text"])) == 1 and is_name(t[0]) for w in regions)))
    print("completed", len(pages), "missing", len(missing))
    if missing:
        print("pending page numbers", missing)
        return
    metadata_path = cache / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if metadata["manual_sha256"] != manifest_hash:
        raise AssertionError("acquisition metadata belongs to a different manifest")
    report = dict(version="google-full-corpus-raw-regions-v1", pages=pages,
                  manifest_sha256=manifest_hash,
                  acquisition_metadata_sha256=hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
                  engine=metadata["engine"], feature=metadata["feature"],
                  language_hints=metadata["language_hints"],
                  new_page_requests=sum(not p["cached"] for p in metadata["pages"]),
                  reused_page_responses=sum(p["cached"] for p in metadata["pages"]),
                  estimated_new_cost_usd=metadata["pending_request_estimate_usd"],
                  total_regions=sum(len(p["regions"]) for p in pages),
                  raw_name_candidates=sum(p["raw_name_candidates"] for p in pages),
                  caveat="Uncorrected service regions, including ornaments and surah-head basmalas. "
                  "Raw name candidates have no independently validated whole-corpus identities/completeness. "
                  "Managed model revision unpinned; full responses are cached locally under logs.")
    output.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("regions", report["total_regions"], "raw name candidates", report["raw_name_candidates"],
          "new/reused requests", report["new_page_requests"], report["reused_page_responses"],
          "compact derived output", output)


def verify(manifest_path, output, cache=None):
    manifest = json.loads(manifest_path.read_text())
    report = json.loads(output.read_text())
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != report["manifest_sha256"]:
        raise AssertionError("compact corpus manifest hash differs")
    if [p["page"] for p in manifest["pages"]] != list(range(1, 605)) or [
            p["page"] for p in report["pages"]] != list(range(1, 605)):
        raise AssertionError("corpus page inventory is not exactly 1..604")
    if report["new_page_requests"] + report["reused_page_responses"] != 604:
        raise AssertionError("acquisition request accounting differs")
    if abs(report["estimated_new_cost_usd"] - report["new_page_requests"] * .0015) > 1e-12:
        raise AssertionError("acquisition planning estimate differs")
    if cache is not None and hashlib.sha256((cache / "metadata.json").read_bytes()).hexdigest() != report[
            "acquisition_metadata_sha256"]:
        raise AssertionError("acquisition metadata hash differs")
    for page, expected in zip(report["pages"], manifest["pages"]):
        if page["image_sha256"] != expected["image_sha256"]:
            raise AssertionError("compact page image hash differs")
        if page["raw_name_candidates"] != sum(len(t := words(r["text"])) == 1 and is_name(t[0])
                                               for r in page["regions"]):
            raise AssertionError("raw candidate count differs")
        for region in page["regions"]:
            x0, y0, x1, y1 = region["bbox"]
            if region["bbox_valid"] != (x0 < x1 and y0 < y1):
                raise AssertionError("raw bounding-box validity differs")
            if not (0 <= x0 <= x1 <= expected["width"] and 0 <= y0 <= y1 <= expected["height"]):
                raise AssertionError("raw region is outside its image")
        if cache is not None:
            path = cache / f'page_{page["page"]}.json'
            if hashlib.sha256(path.read_bytes()).hexdigest() != page["response_sha256"]:
                raise AssertionError("cached raw response hash differs")
            raw = json.loads(path.read_text())
            if convert(raw["raw_response"]) != raw["result"]:
                raise AssertionError("cached raw response conversion differs")
            regions = [dict(text=w["text"], bbox=w["bbox"], confidence=w["confidence"],
                            bbox_valid=w["bbox_valid"])
                       for line in raw["result"]["text_lines"] for w in line["words"]]
            if regions != page["regions"]:
                raise AssertionError("compact regions differ from cache")
    if report["total_regions"] != sum(len(p["regions"]) for p in report["pages"]):
        raise AssertionError("compact corpus region denominator differs")
    if report["raw_name_candidates"] != sum(p["raw_name_candidates"] for p in report["pages"]):
        raise AssertionError("compact corpus name-candidate total differs")
    print("PASS compact 604-page OCR inventory, hashes, region bounds and raw candidate arithmetic"
          + ("; every local raw response/conversion replayed" if cache is not None else "; no raw cache required"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--summarize", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--raw", action="store_true", help="also replay local cached raw responses")
    parser.add_argument("--output", type=Path, default=DATA / "ocr_google_corpus_v1.json")
    args = parser.parse_args()
    if args.verify:
        verify(args.manifest, args.output, args.cache if args.raw else None)
    elif args.summarize:
        summarize(args.manifest, args.cache, args.output)
    else:
        prepare(args.manifest, args.cache)


if __name__ == "__main__":
    main()
