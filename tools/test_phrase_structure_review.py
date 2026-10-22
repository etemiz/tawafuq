"""Independent exhaustive bounds for correlated phrase-center envelopes."""
from itertools import product
import unittest

from phrase_structure_review import pair_envelopes


class PhraseEnvelopeTests(unittest.TestCase):
    def test_every_tiny_independent_position_within_certificates(self):
        intervals = ((0, 0), (0, 30), (30, 31), (31, 60))
        for choice in product(intervals, repeat=4):
            reference = dict(enumerate(choice))
            guaranteed, upper = pair_envelopes(reference, [[0, 2]], 2)
            actual = []
            for coordinates in product(*(range(a, b+1) for a, b in choice)):
                actual.append(abs(coordinates[0]-coordinates[2]) <= 30 and abs(coordinates[1]-coordinates[3]) <= 30)
            self.assertEqual(bool(guaranteed), all(actual))
            self.assertEqual(bool(upper), any(actual))

    def test_outer_envelope_is_not_joint_feasibility(self):
        reference = {0: (100, 140), 1: (0, 40), 2: (100, 100), 3: (40, 40)}
        guaranteed, upper = pair_envelopes(reference, [[0, 2]], 2)
        self.assertFalse(guaranteed)
        self.assertEqual(upper, [[0, 2]])
        # Rigidly translate the first phrase. Its two required shifts conflict,
        # although each independent coordinate envelope overlaps the partner.
        self.assertFalse(any(abs(100+d-100) <= 30 and abs(d-40) <= 30 for d in (0, 40)))


if __name__ == "__main__":
    unittest.main()
