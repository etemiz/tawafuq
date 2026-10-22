"""Ground truths for explicit, non-destructive coordinate corrections."""

from copy import deepcopy
import unittest

from historical_extension_final_review import corrected_labels


class CoordinateReviewTests(unittest.TestCase):
    def labels(self):
        return {"pages":[{"folio":"33r","frame":[0,100],
                          "names":[["4:132",2,"بالله",18,10,20]]}]}

    def test_only_declared_interval_changes_and_input_is_preserved(self):
        labels=self.labels()
        original=deepcopy(labels)
        result=corrected_labels(labels,{"updates":[["33r","4:132",2,10,20,30,50]]})
        self.assertEqual(labels,original)
        self.assertEqual(result["pages"][0]["names"],[["4:132",2,"بالله",18,30,50]])

    def test_reject_wrong_original_unknown_and_duplicate(self):
        good=["33r","4:132",2,10,20,30,50]
        wrong=["33r","4:132",2,11,20,30,50]
        unknown=["33r","4:132",3,10,20,30,50]
        for updates in ([wrong],[unknown],[good,good]):
            with self.subTest(updates=updates),self.assertRaises(ValueError):
                corrected_labels(self.labels(),{"updates":updates})

    def test_reject_empty_reversed_or_outside_body(self):
        for left,right in ((30,30),(50,30),(-1,20),(80,101)):
            with self.subTest(edges=(left,right)),self.assertRaises(ValueError):
                corrected_labels(self.labels(),{"updates":[["33r","4:132",2,10,20,left,right]]})


if __name__=="__main__":
    unittest.main()
