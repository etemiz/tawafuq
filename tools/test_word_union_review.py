"""Sampling invariants for a diagnostic frame with deliberate special censuses."""
import unittest

from word_union_review import select


def row(i, kind="verse", name=False, regions=2, distance=1):
    return dict(page=i+1, v_id=i, kind=kind, is_allah_form=name,
                mandatory_regions=list(range(regions)), text_distance=distance)


class UnionSampleTests(unittest.TestCase):
    def test_reordering_frame_cannot_change_selection(self):
        frame = [row(i) for i in range(25)]
        frame += [row(25, kind="head_basmala"), row(26, name=True)]
        strata, samples = select(frame)
        self.assertEqual((strata, samples), select(list(reversed(frame))))
        self.assertEqual(sum(r["population"] for r in strata), len(frame))
        self.assertEqual(len(samples), 6)
        self.assertEqual({s["v_id"] for s in samples if s["stratum"] in {"head_basmala", "verse_name"}}, {25, 26})

    def test_small_strata_and_special_categories_are_censused(self):
        frame = [row(0), row(1, distance=2), row(2, regions=3), row(3, regions=4, distance=5)]
        frame += [row(i, name=True) for i in range(4, 10)]
        strata, samples = select(frame)
        self.assertEqual({s["v_id"] for s in samples}, set(range(10)))
        self.assertTrue(all(s["sampled"] == s["population"] for s in strata))

    def test_corrupt_frame_fails_instead_of_biasing_inventory(self):
        for frame in ([row(0), row(0)], [row(0, regions=1)], [row(0, distance=0)]):
            with self.assertRaises(AssertionError):
                select(frame)


if __name__ == "__main__":
    unittest.main()
