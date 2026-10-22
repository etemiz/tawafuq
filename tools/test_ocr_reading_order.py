"""Spatial fixtures independent of Quran identities or automatic predictions."""
import unittest

import ocr_corpus_map as cm
from ocr_benchmark import reading_order as legacy
from ocr_reading_order import reading_order, row_groups
from ocr_row_map import ordered_map


def region(i, box, text="اب"):
    return dict(source_region=i, bbox=box, text=text, confidence=.9, bbox_valid=True)


class RowOrderTests(unittest.TestCase):
    def test_short_annotation_does_not_split_sloped_row(self):
        rows = [region(0, [200, 707, 290, 785]), region(1, [100, 703, 190, 781]),
                region(2, [0, 696, 90, 774]), region(3, [140, 679, 180, 720])]
        self.assertNotEqual([r["source_region"] for r in legacy(rows)], [0, 1, 3, 2])
        found = row_groups(rows)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["satellites"], [3])
        self.assertEqual([r["source_region"] for r in reading_order(rows)], [0, 1, 3, 2])

    def test_rows_remain_separate_and_every_region_occurs_once(self):
        rows = [region(0, [0, 0, 80, 75]), region(1, [100, 2, 180, 77]),
                region(2, [0, 110, 80, 185]), region(3, [100, 112, 180, 187]),
                region(4, [200, 230, 230, 265])]
        self.assertEqual([r["source_region"] for r in reading_order(rows)], [1, 0, 3, 2, 4])
        self.assertEqual(len(row_groups(rows)), 3)
        self.assertEqual(reading_order([]), [])

    def test_translation_preserves_fixture_order(self):
        rows = [region(0, [0, 100, 80, 175]), region(1, [100, 102, 180, 177]),
                region(2, [0, 210, 80, 285]), region(3, [100, 212, 180, 287])]
        shifted = [dict(r, bbox=[r["bbox"][0]+50, r["bbox"][1]+17, r["bbox"][2]+50, r["bbox"][3]+17]) for r in rows]
        self.assertEqual([r["source_region"] for r in reading_order(rows)],
                         [r["source_region"] for r in reading_order(shifted)])

    def test_ordered_mapping_agrees_with_legacy_when_order_unchanged(self):
        tokens, starts, reference = cm.virtual_corpus([(2, 2, ["اب", "جد", "هوز", "حطي", "كلمن"])])
        spec = cm.Spec(anchor_length=3, minimum_anchor_coverage=5, minimum_anchor_advantage=2)
        index = cm.unique_index(reference, spec.anchor_length)
        rows = [region(i, [500-i*90, 100, 570-i*90, 175], t["form"]) for i, t in enumerate(tokens)]
        page = dict(page=1, image_sha256="fixture", regions=rows)
        self.assertEqual(ordered_map(page, reading_order(rows), tokens, starts, reference, index, spec),
                         cm.map_page(page, tokens, starts, reference, index, spec))


if __name__ == "__main__":
    unittest.main()
