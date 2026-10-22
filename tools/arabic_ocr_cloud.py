"""Google Cloud Vision document OCR with reusable raw responses and word boxes.

Use GOOGLE_CLOUD_VISION_API_KEY, or --credentials with a service-account JSON
file (requires google-auth and requests). Credentials never enter artifacts.
Each uncached page makes one request, with no automatic retries. The planning
estimate uses $1.50/1000 images, ignoring free quota; it is not a billing receipt.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from image_io import open_rgb
from semantic_validation import ROOT, DATA

ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


def error_reasons(error):
    """Return provider reason codes without account IDs or request credentials."""
    reasons = [d.get("reason", "") for d in error.get("details", []) if isinstance(d, dict)]
    return ", ".join(r for r in reasons if isinstance(r, str) and re.fullmatch(r"[A-Z_]+", r)) or "unspecified"


def region(word):
    vertices = word["boundingBox"]["vertices"]
    polygon = [[v.get("x", 0), v.get("y", 0)] for v in vertices]
    bbox = [min(v[0] for v in polygon), min(v[1] for v in polygon),
            max(v[0] for v in polygon), max(v[1] for v in polygon)]
    return dict(text="".join(s["text"] for s in word["symbols"]),
                confidence=word.get("confidence"), polygon=polygon, bbox=bbox,
                bbox_valid=bbox[0] < bbox[2] and bbox[1] < bbox[3])


def convert(response):
    lines = []
    for page in response.get("fullTextAnnotation", {}).get("pages", []):
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                current = []
                for word in paragraph.get("words", []):
                    current.append(region(word))
                    kind = word["symbols"][-1].get("property", {}).get("detectedBreak", {}).get("type")
                    if kind in ("EOL_SURE_SPACE", "LINE_BREAK"):
                        lines.append(combine(current))
                        current = []
                if current:
                    lines.append(combine(current))
    return dict(text_lines=lines)


def combine(items):
    boxes = [w["bbox"] for w in items]
    return dict(text=" ".join(w["text"] for w in items), words=items,
                bbox=[min(b[0] for b in boxes), min(b[1] for b in boxes),
                      max(b[2] for b in boxes), max(b[3] for b in boxes)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual", type=Path, default=DATA / "audit_manual_ocr_heldout.json")
    parser.add_argument("--output", type=Path, default=DATA / "ocr_heldout_google_v1")
    parser.add_argument("--credentials", type=Path)
    parser.add_argument("--budget-usd", type=float, default=20)
    parser.add_argument("--max-pages", type=int, default=12)
    parser.add_argument("--plan", action="store_true", help="list pages and estimate without sending scans")
    args = parser.parse_args()
    manual = json.loads(args.manual.read_text())
    pending = [p for p in manual["pages"] if not (args.output / f'page_{p["page"]}.json').exists()]
    estimate = len(pending) * 1.5 / 1000
    if len(pending) > args.max_pages or estimate > args.budget_usd:
        parser.error("pending pages exceed page limit or planning budget")
    print("pending pages", [p["page"] for p in pending], "estimated OCR charge USD", estimate, flush=True)
    if args.plan:
        return
    if not pending and (args.output / "metadata.json").exists():
        for page in manual["pages"]:
            saved = json.loads((args.output / f'page_{page["page"]}.json').read_text())
            if saved["image_sha256"] != page["image_sha256"]:
                raise AssertionError("cached OCR belongs to a different scan")
        print("All pages cached; preserving raw responses and run metadata")
        return
    headers = {"Content-Type": "application/json"}
    credential = None
    key = os.environ.get("GOOGLE_CLOUD_VISION_API_KEY")
    if key:
        headers["X-Goog-Api-Key"] = key
    elif args.credentials:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        credential = service_account.Credentials.from_service_account_file(
            str(args.credentials), scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credential.refresh(Request())
        headers["Authorization"] = f"Bearer {credential.token}"
    elif pending:
        parser.error("set GOOGLE_CLOUD_VISION_API_KEY or supply --credentials")
    args.output.mkdir(parents=True, exist_ok=True)
    reports = []
    for page in manual["pages"]:
        n = page["page"]
        destination = args.output / f"page_{n}.json"
        if destination.exists():
            saved = json.loads(destination.read_text())
            if saved["image_sha256"] != page["image_sha256"]:
                raise AssertionError("cached OCR belongs to a different scan")
            reports.append(dict(page=n, cached=True))
            continue
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        if hashlib.sha256(path.read_bytes()).hexdigest() != page["image_sha256"]:
            raise AssertionError("scan differs from manifest")
        image = open_rgb(path)
        bottom = page.get("ocr_bottom")
        if bottom is None:
            bottom = min(image.height, max(r["cy"] for r in page["rosettes"]) + 65)
        image = image.crop((0, 0, image.width, bottom))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        payload = dict(requests=[dict(image=dict(content=base64.b64encode(buffer.getvalue()).decode()),
                                     features=[dict(type="DOCUMENT_TEXT_DETECTION")])])
        if credential is not None and not credential.valid:
            credential.refresh(Request())
            headers["Authorization"] = f"Bearer {credential.token}"
        start = time.perf_counter()
        request = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = json.load(response)["responses"][0]
        except urllib.error.HTTPError as error:
            # Do not print request objects, headers, keys, or credential contents.
            try:
                reason = error_reasons(json.load(error).get("error", {}))
            except (ValueError, AttributeError, TypeError):
                reason = "unreadable error body"
            raise RuntimeError(f"Cloud OCR HTTP {error.code}; reason {reason}; no automatic retry") from None
        if "error" in raw:
            raise RuntimeError(f'Cloud OCR response error code {raw["error"].get("code")}; '
                               f'reason {error_reasons(raw["error"])}; no automatic retry')
        row = dict(page=n, image_sha256=page["image_sha256"], crop=[0, 0, image.width, bottom],
                   elapsed_seconds=time.perf_counter() - start, raw_response=raw, result=convert(raw))
        destination.write_text(json.dumps(row, ensure_ascii=False, indent=1) + "\n")
        reports.append(dict(page=n, cached=False, elapsed_seconds=row["elapsed_seconds"]))
        print("page", n, "lines", len(row["result"]["text_lines"]), flush=True)
    metadata = dict(engine="google-cloud-vision", feature="DOCUMENT_TEXT_DETECTION", language_hints=[],
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    manual_sha256=hashlib.sha256(args.manual.read_bytes()).hexdigest(), pages=reports,
                    pending_request_estimate_usd=estimate, budget_usd=args.budget_usd,
                    pricing_url="https://cloud.google.com/vision/pricing",
                    status="Raw service response retained. Model revision is not pinned by this API. "
                    "Planning estimate is not actual billing. No credentials stored.")
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
