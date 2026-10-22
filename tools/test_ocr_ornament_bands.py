import unittest

from PIL import Image, ImageDraw

from ocr_ornament_bands import detect


class OrnamentBandsTests(unittest.TestCase):
    def test_gold_header_is_retained_but_small_rosettes_are_not(self):
        image = Image.new("RGB", (200, 300), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 10, 199, 89], fill=(140, 125, 20))
        draw.rectangle([10, 150, 35, 179], fill=(140, 125, 20))
        draw.rectangle([70, 150, 95, 179], fill=(140, 125, 20))
        draw.rectangle([130, 150, 155, 179], fill=(140, 125, 20))
        self.assertEqual(detect(image), [[10, 90]])

    def test_red_basmala_is_not_gold_ornament(self):
        image = Image.new("RGB", (200, 200), "white")
        ImageDraw.Draw(image).rectangle([0, 30, 199, 110], fill=(236, 43, 101))
        self.assertEqual(detect(image), [])

    def test_small_row_gaps_do_not_split_the_same_header(self):
        image = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 10, 199, 45], fill=(140, 125, 20))
        draw.rectangle([0, 55, 199, 89], fill=(140, 125, 20))
        self.assertEqual(detect(image), [[10, 90]])


if __name__ == "__main__":
    unittest.main()
