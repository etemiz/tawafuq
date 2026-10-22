"""Local GPU OCR pilot on independently annotated Quran pages.

Run in the optional .venv/ocr environment. CUDA_VISIBLE_DEVICES must select a
GPU UUID. No scans or text are sent to an OCR service; weights download once.
Raw OCR is a hypothesis to benchmark, not replacement Quran text.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import time
from pathlib import Path

from image_io import open_rgb

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / "tools" / "data" / "audit_manual_semantic_sample.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", help="comma-separated subset of the annotated pages")
    parser.add_argument("--manual", type=Path, default=MANUAL)
    parser.add_argument("--output", type=Path, default=ROOT / "logs" / "arabic-ocr")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if not os.environ.get("CUDA_VISIBLE_DEVICES", "").startswith("GPU-"):
        parser.error("set CUDA_VISIBLE_DEVICES to a GPU UUID")
    os.environ.setdefault("MODEL_CACHE_DIR", str(ROOT / "logs" / "ocr-models"))
    os.environ.setdefault("HF_HOME", str(ROOT / "logs" / "huggingface"))
    os.environ.setdefault("TORCH_DEVICE", "cuda")
    os.environ.setdefault("RECOGNITION_BATCH_SIZE", str(args.batch_size))
    os.environ.setdefault("DETECTOR_BATCH_SIZE", "1")
    os.environ.setdefault("FOUNDATION_MAX_TOKENS", "768")
    import torch
    from surya.foundation import FoundationPredictor
    from surya.recognition import RecognitionPredictor
    from surya.detection import DetectionPredictor
    from surya.settings import settings

    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(0.18)
    args.output.mkdir(parents=True, exist_ok=True)
    manual = json.loads(args.manual.read_text())
    wanted = set(map(int, args.pages.split(","))) if args.pages else None
    started = time.perf_counter()
    foundation = FoundationPredictor()
    recognizer = RecognitionPredictor(foundation)
    detector = DetectionPredictor()
    reports = []
    for page in manual["pages"]:
        n = page["page"]
        if wanted is not None and n not in wanted:
            continue
        path = ROOT / "hayrat-pics" / f"page_{n}.png"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != page["image_sha256"]:
            raise AssertionError("sample image hash mismatch")
        image = open_rgb(path)
        # Exclude the next-surah ornament/header on p365 using the independently
        # transcribed final verse endpoint; leave all sampled Quran text intact.
        bottom = page.get("ocr_bottom")
        if bottom is None:
            bottom = min(image.height, max(r["cy"] for r in page["rosettes"]) + 65)
        image = image.crop((0, 0, image.width, bottom))
        start = time.perf_counter()
        result = recognizer([image], det_predictor=detector, math_mode=False, return_words=True)[0]
        row = dict(page=n, image_sha256=digest, crop=[0, 0, image.width, bottom],
                   elapsed_seconds=time.perf_counter() - start, result=result.model_dump())
        (args.output / f"page_{n}.json").write_text(json.dumps(row, ensure_ascii=False, indent=1) + "\n")
        reports.append(dict(page=n, lines=len(result.text_lines), elapsed_seconds=row["elapsed_seconds"]))
        print("page", n, "lines", len(result.text_lines), "seconds", row["elapsed_seconds"], flush=True)
    metadata = dict(engine="surya-ocr", python=platform.python_version(),
                    packages={p: importlib.metadata.version(p) for p in
                              ("surya-ocr", "torch", "transformers", "pillow")},
                    gpu=torch.cuda.get_device_name(), peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    recognition_batch_size=args.batch_size,
                    detection_checkpoint=settings.DETECTOR_MODEL_CHECKPOINT,
                    recognition_checkpoint=settings.RECOGNITION_MODEL_CHECKPOINT,
                    model_files={str(p.relative_to(settings.MODEL_CACHE_DIR)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted(Path(settings.MODEL_CACHE_DIR).rglob("*")) if p.is_file()},
                     manual_sha256=hashlib.sha256(args.manual.read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    elapsed_seconds=time.perf_counter() - started, pages=reports,
                    status="Unvalidated OCR hypotheses; compare with exact Quran and independent image annotations.")
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
