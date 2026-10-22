"""Boundary and portable-replay ground truths for the second historical copy."""

import json
import unittest

from historical_extension import page_inventory, phrase_windows, analyze, FIRST_REVIEW


class HistoricalExtensionTests(unittest.TestCase):
    def corpus(self):
        return {i:dict(t=i,verse="2:1" if i<3 else "2:2",word=w)
                for i,w in enumerate(("a","name","b","c","name","d"))}

    def test_partial_boundary_verses_not_silently_completed(self):
        selected=page_inventory(self.corpus(),dict(first_verse="2:1",first_word=3,
                                last_verse="2:2",last_word=1))
        self.assertEqual(set(selected),{2,3})
        self.assertNotIn("name",[r["word"] for r in selected.values()])

    def test_boundary_ordinals_are_one_based_and_must_be_valid(self):
        for start,stop in ((0,1),(4,1),(1,0),(1,4)):
            with self.subTest(start=start,stop=stop),self.assertRaises(ValueError):
                page_inventory(self.corpus(),dict(first_verse="2:1",first_word=start,
                               last_verse="2:2",last_word=stop))

    def test_reversed_span_rejected(self):
        with self.assertRaises(ValueError):
            page_inventory(self.corpus(),dict(first_verse="2:2",first_word=1,
                           last_verse="2:1",last_word=None))

    def test_repeated_phrase_identity_is_contiguous_and_within_verse(self):
        corpus={i:dict(t=i,verse="2:1" if i<5 else "2:2",word=w)
                for i,w in enumerate(("a","b","x","a","b","a","b"))}
        self.assertEqual([[r["t"] for r in w] for w in phrase_windows(corpus,"2:1",["a","b"])],[[0,1],[3,4]])
        self.assertEqual(phrase_windows(corpus,"2:1",["b","a"]),[])

    def test_portable_reconstruction_preserves_first_measured_outcomes(self):
        report=analyze()
        first=json.loads(FIRST_REVIEW.read_text())
        for key in set(first)-{"inputs"}:
            self.assertEqual(report[key],first[key],key)
        self.assertEqual(sum(p["canonical_name_count"] for p in report["pages"]),66)
        self.assertEqual(report["modern_unresolved"],[])


if __name__ == "__main__":
    unittest.main()
