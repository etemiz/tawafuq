import unittest

from arabic_ocr_cloud import convert, error_reasons


def word(text, vertices, end=None):
    symbols = [dict(text=c) for c in text]
    if end:
        symbols[-1]["property"] = dict(detectedBreak=dict(type=end))
    return dict(symbols=symbols, boundingBox=dict(vertices=vertices), confidence=0.9)


class CloudConversionTest(unittest.TestCase):
    def test_error_summary_exposes_reason_without_provider_metadata(self):
        error = dict(message="account-specific provider message", details=[
            dict(reason="BILLING_DISABLED", metadata=dict(consumer="account-specific")),
            dict(reason="https://account-specific.invalid"), None])
        self.assertEqual(error_reasons(error), "BILLING_DISABLED")

    def test_zero_vertices_and_line_breaks_preserve_real_word_boxes(self):
        first = word("قال", [{}, {"x": 30}, {"x": 30, "y": 20}, {"y": 20}])
        second = word("الله", [{"x": 40}, {"x": 70}, {"x": 70, "y": 20}, {"x": 40, "y": 20}],
                      "LINE_BREAK")
        third = word("هو", [{"y": 40}, {"x": 30, "y": 40}, {"x": 30, "y": 60}, {"y": 60}])
        result = convert(dict(fullTextAnnotation=dict(pages=[dict(blocks=[
            dict(paragraphs=[dict(words=[first, second, third])])])])))["text_lines"]
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["words"][0]["bbox"], [0, 0, 30, 20])
        self.assertEqual(result[0]["words"][1]["bbox"], [40, 0, 70, 20])
        self.assertEqual(result[0]["bbox"], [0, 0, 70, 20])
        self.assertEqual(result[1]["text"], "هو")

    def test_empty_response_has_no_invented_words(self):
        self.assertEqual(convert({}), dict(text_lines=[]))


if __name__ == "__main__":
    unittest.main()
