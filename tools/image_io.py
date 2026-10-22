"""Render page PNG transparency on paper before measuring ink colors."""
from PIL import Image


def on_white(image):
    if "A" in image.getbands() or "transparency" in image.info:
        rgba = image.convert("RGBA")
        paper = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(paper, rgba).convert("RGB")
    return image.convert("RGB")


def open_rgb(path):
    with Image.open(path) as image:
        return on_white(image)
