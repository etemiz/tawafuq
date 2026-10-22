"""Selection must not admit exposed or ornamented pages or replace slots."""
import unittest

from word_boundary_fresh_plan import STRATA
from word_ink_trim_fresh_plan import select_pages


class InkTrimPlanTests(unittest.TestCase):
    def test_eligibility_frame_order_and_complete_schedule(self):
        bands = {n: [] for n in range(1, 605)}
        chosen = select_pages(set(), bands)
        excluded = {p["page"] for p in chosen[::2]}
        for p in chosen[1::2]:
            bands[p["page"]] = [[0, 100]]
        result = select_pages(excluded, bands)
        self.assertEqual(result, select_pages(excluded, dict(reversed(list(bands.items())))))
        for page, (lo, hi) in zip(result, STRATA):
            self.assertTrue(lo <= page["page"] <= hi)
            self.assertNotIn(page["page"], excluded)
            self.assertFalse(bands[page["page"]])
            self.assertEqual(page["eligible_pages"], hi-lo)
            self.assertEqual(page["positions"], [dict(physical_row=r, lexical_position_rtl=k)
                                                for r in (2, 7, 12) for k in (1, 4, 7)])


if __name__ == "__main__":
    unittest.main()
