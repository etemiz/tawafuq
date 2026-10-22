"""Fresh evaluation contracts: unchanged denominators and recomputed centers."""
import unittest

from word_ink_trim_fresh_sample import scheduled_samples
from word_ink_trim_fresh_validation import assess_label, summarize, paired


class FreshInkTrimTests(unittest.TestCase):
    def label(self, **updates):
        label = dict(page=10, physical_row=2, lexical_position_rtl=1, verse="1:1", form="x",
                     rect=[4, 0, 6, 5], x_edges=[0, 10], x_edge_tolerance=12,
                     boundary_eligible=True, ownership_evaluable=True, edge_support=[[0], [10]])
        label.update(updates)
        return label

    def row(self, box, label=None):
        label = label or self.label()
        return dict(label, **assess_label(box, label))

    def test_complete_schedule_rejects_omission_duplicate_and_reordering(self):
        positions = [dict(physical_row=2, lexical_position_rtl=k) for k in (1, 4, 7)]
        schedule = dict(positions=positions)
        def page(ks):
            return dict(rows=[dict(physical_row=2, samples=[dict(lexical_position_rtl=k) for k in ks])])
        scheduled_samples(schedule, page((1, 4, 7)))
        for ks in ((1, 4), (1, 4, 4), (7, 4, 1)):
            with self.assertRaises(AssertionError):
                scheduled_samples(schedule, page(ks))

    def test_abstentions_stay_in_boundary_denominators_unavailable_never_does(self):
        rows = [self.row([0, 0, 10, 5]), self.row(None), dict(status="unavailable")]
        report = summarize(rows)
        self.assertEqual((report["scheduled"], report["labelled"], report["unavailable"]), (3, 2, 1))
        self.assertEqual((report["boundary_evaluable"], report["ownership_evaluable"]), (2, 2))
        self.assertEqual((report["boundary_pass"], report["all_ownership_boundary_pass"]), (1, 1))

    def test_center_regression_is_detected_even_if_horizontal_tolerance_passes(self):
        old, new = self.row([0, 0, 10, 5]), self.row([9, 0, 10, 5])
        result = paired([old], [new])
        self.assertEqual(result["transitions"]["center"]["regressed"], 1)
        self.assertEqual(result["transitions"]["fixed_boundary"]["both_pass"], 1)
        self.assertEqual(result["regressions"][0]["regressions"], ["center"])

    def test_uncertain_edges_can_be_sensitive_but_unspecified_ownership_cannot_be_certified(self):
        label = self.label(boundary_eligible=False, edge_support=[[0, 2], [10]], x_edge_tolerance=0)
        row = self.row([0, 0, 10, 5], label)
        self.assertEqual(row["all_ownership_outcome"], "ownership_sensitive")
        self.assertFalse(row["all_ownership_boundary_pass"])
        row = self.row([0, 0, 10, 5], self.label(boundary_eligible=False, ownership_evaluable=False, edge_support=None))
        self.assertEqual(row["all_ownership_outcome"], "unscorable")
        self.assertIsNone(row["all_ownership_boundary_pass"])
        self.assertEqual(summarize([row])["ownership_evaluable"], 0)

    def test_pairing_rejects_inventory_or_acceptance_changes(self):
        old = self.row([0, 0, 10, 5])
        for after in ([], [self.row(None)], [self.row([0, 0, 10, 5], self.label(lexical_position_rtl=4))]):
            with self.assertRaises(AssertionError):
                paired([old], after)


if __name__ == "__main__":
    unittest.main()
