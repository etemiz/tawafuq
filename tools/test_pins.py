import unittest

from mark_identity import merge_split_runs
import mark_identity


class PinTests(unittest.TestCase):
    def test_run_deficit_cannot_be_a_full_match(self):
        run = dict(page=1, band=2, kind="cri", strip=False, x0=100, x1=130,
                   ymin=100, ymax=130, npx=50)
        self.assertIsNone(merge_split_runs([run], 2))
        # This must fail closed before consulting any global token stream.
        state, pins, black = mark_identity.match_class([0, 1], [run], 1)
        self.assertEqual((state, pins, black), ("amb", [], []))

    def test_prefixed_divine_names_are_candidates_not_false_friends(self):
        self.assertTrue({"والله", "بالله", "فلله", "ءالله"} <= mark_identity.NAMES)
        self.assertFalse({"اللهو", "اللهم", "يضلله"} & mark_identity.NAMES)

    def test_absent_detected_runs_do_not_certify_black_ink(self):
        self.assertEqual(mark_identity.match_class([0, 1], [], 1),
                         ("no_detected_run", [], [0, 1]))

    def test_rtl_run_merge_is_union_not_reversed_inner_edges(self):
        a = dict(page=1, band=2, kind="cri", strip=False, x0=100, x1=130,
                 ymin=100, ymax=130, npx=50)
        b = dict(page=1, band=2, kind="cri", strip=False, x0=60, x1=90,
                 ymin=95, ymax=140, npx=60)
        merged = merge_split_runs([a, b], 1)
        self.assertEqual(len(merged), 1)
        self.assertEqual((merged[0]["x0"], merged[0]["x1"]), (60, 130))
        self.assertEqual((merged[0]["ymin"], merged[0]["ymax"]), (95, 140))
        self.assertEqual(merged[0]["npx"], 110)


if __name__ == "__main__":
    unittest.main()
