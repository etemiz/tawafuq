"""Independent exhaustive ground truths for the interval-layout pilot."""
from fractions import Fraction
from itertools import permutations
import unittest

import text_layout_comparator as lc


def row(widths, gaps, y=0, page=1, first_t=0, words=None):
    right = sum(widths)+sum(gaps)
    records = []
    edge = right
    for i, w in enumerate(widths):
        records.append(dict(t=first_t+i, word=(words or ["الله"]*len(widths))[i],
                            page=page, row=y, width=w, x2=2*edge-w, bbox=[edge-w, y, edge, y+1]))
        edge -= w+(gaps[i] if i < len(gaps) else 0)
    return dict(words=records, extent=[0, right], gaps_rtl=gaps)


class IntervalPilotTests(unittest.TestCase):
    def test_exhaustive_packing_and_freedom(self):
        r = row([3, 8, 2, 7, 5], [1, 1, 3, 6])
        positions = []
        for gaps in set(permutations(r["gaps_rtl"])):
            actual = lc.place(r, gaps)
            # Independent left-to-right reconstruction and interval edges.
            left = 0
            expected = []
            for i in range(len(r["words"])-1, -1, -1):
                width = r["words"][i]["width"]
                expected.append(2*left+width)
                left += width+(gaps[i-1] if i else 0)
            self.assertEqual(actual, expected[::-1])
            self.assertEqual(left, r["extent"][1])
            positions.append(actual)
        f = lc.freedom(r)
        self.assertEqual(f["distinct_gap_arrangements"], len(positions))
        for i, c in enumerate(f["centers"]):
            self.assertEqual(c["minimum_x2"], min(p[i] for p in positions))
            self.assertEqual(c["maximum_x2"], max(p[i] for p in positions))

    def test_rational_equal_gaps_and_identity(self):
        r = row([7, 8, 11, 4], [0, 1, 0])
        self.assertEqual(lc.place(r, r["gaps_rtl"]), [w["x2"] for w in r["words"]])
        positions = lc.place(r, [Fraction(1, 3)]*3)
        self.assertTrue(any(x.denominator == 3 for x in positions))
        self.assertEqual(positions[0], r["words"][0]["x2"])
        self.assertEqual(positions[-1], r["words"][-1]["x2"])
        with self.assertRaises(ValueError):
            lc.place(r, [-1, 1, 1])
        with self.assertRaises(ValueError):
            lc.place(r, [1, 1, 1])

    def test_exhaustive_score_scalar_reference(self):
        a = row([10]*4, [0, 10, 30], first_t=0, words=["الله", "والله", "x", "الله"])
        b = row([10]*4, [10, 20, 10], y=1, first_t=4, words=["والله", "x", "الله", "x"])
        words = a["words"]+b["words"]
        pairs = lc.candidate_pairs(words)
        for ga in set(permutations(a["gaps_rtl"])):
            for gb in set(permutations(b["gaps_rtl"])):
                centers = lc.place(a, ga)+lc.place(b, gb)
                exact, family = set(), set()
                for i, w in enumerate(words):
                    for j, v in enumerate(words):
                        if w["page"] == v["page"] and w["row"] != v["row"] and abs(centers[i]-centers[j]) <= 30:
                            if w["word"] == v["word"]:
                                exact.add(w["t"])
                            if w["word"] in ("الله", "والله") and v["word"] in ("الله", "والله"):
                                family.add(w["t"])
                actual = lc.score(centers, words, pairs)
                self.assertEqual(set(actual["endpoint_token_ids"]["all_identical_words"]), exact)
                self.assertEqual(set(actual["endpoint_token_ids"]["allah_name_family"]), family)
                self.assertEqual(actual["counts"]["standalone_allah"], sum(w["word"] == "الله" and w["t"] in exact for w in words))

    def test_boundary_tolerance_and_page_row_exclusion(self):
        words = [dict(t=i, word="الله", page=1 if i<3 else 2, row=i%2) for i in range(4)]
        pairs = lc.candidate_pairs(words)
        self.assertEqual(pairs[0], [(0, 1), (1, 2)])
        self.assertEqual(lc.score([0, 30, 100, 0], words, pairs)["counts"]["standalone_allah"], 2)
        self.assertEqual(lc.score([0, Fraction(301, 10), 100, 0], words, pairs)["counts"]["standalone_allah"], 0)


if __name__ == "__main__":
    unittest.main()
