"""Alternative local GPU Arabic OCR pilot using EasyOCR's Arabic recognizer.

Raw regions are preserved. A multiword region is not silently divided into
word boxes; the shared benchmark only tests single-name region locations.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import time
from pathlib import Path

import numpy as np

from image_io import open_rgb

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / "tools" / "data" / "audit_manual_semantic_sample.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "logs" / "easyocr-arabic")
    parser.add_argument("--manual", type=Path, default=MANUAL)
    args = parser.parse_args()
    if not os.environ.get("CUDA_VISIBLE_DEVICES", "").startswith("GPU-"):
        parser.error("set CUDA_VISIBLE_DEVICES to a GPU UUID")
    import torch
    import easyocr
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(0.18)
    model_dir = ROOT / "logs" / "easyocr-models"
    args.output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    reader = easyocr.Reader(["ar", "en"], gpu=True, model_storage_directory=str(model_dir),
                            user_network_directory=str(ROOT / "logs" / "easyocr-networks"))
    manual = json.loads(args.manual.read_text())
    summaries = []
    for page in manual["pages"]:
        n = page["page"]
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        if hashlib.sha256(path.read_bytes()).hexdigest() != page["image_sha256"]:
            raise AssertionError("sample image hash mismatch")
        im = open_rgb(path)
        bottom = page.get("ocr_bottom")
        if bottom is None:
            bottom = min(im.height, max(r["cy"] for r in page["rosettes"]) + 65)
        im = im.crop((0, 0, im.width, bottom))
        before = time.perf_counter()
        predictions = reader.readtext(np.asarray(im), batch_size=8, workers=0, detail=1,
                                      paragraph=False, width_ths=0.0)
        lines = []
        for polygon, text, confidence in predictions:
            polygon = [[float(x), float(y)] for x, y in polygon]
            bbox = [min(p[0] for p in polygon), min(p[1] for p in polygon),
                    max(p[0] for p in polygon), max(p[1] for p in polygon)]
            region = dict(text=text, confidence=float(confidence), polygon=polygon, bbox=bbox, bbox_valid=True)
            lines.append(dict(**region, words=[dict(region)]))
        row = dict(page=n, image_sha256=page["image_sha256"], crop=[0, 0, im.width, bottom],
                   elapsed_seconds=time.perf_counter() - before,
                   result=dict(text_lines=lines, image_bbox=[0, 0, im.width, bottom]),
                   coordinate_scope="OCR regions, potentially multiword; no interpolated word positions")
        (args.output / f"page_{n}.json").write_text(json.dumps(row, ensure_ascii=False, indent=1) + "\n")
        summaries.append(dict(page=n, regions=len(lines), elapsed_seconds=row["elapsed_seconds"]))
        print("page", n, "regions", len(lines), "seconds", row["elapsed_seconds"], flush=True)
    metadata = dict(engine="easyocr", languages=["ar", "en"], width_ths=0.0, batch_size=8,
                    gpu=torch.cuda.get_device_name(), peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    packages={p: importlib.metadata.version(p) for p in ("easyocr", "torch", "torchvision", "pillow")},
                    model_files={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted(model_dir.glob("*")) if p.is_file()},
                     manual_sha256=hashlib.sha256(args.manual.read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    elapsed_seconds=time.perf_counter() - start, pages=summaries,
                    status="Raw Arabic OCR hypotheses; benchmark against exact text and manual locations.")
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
