"""Enumerated ground truths for independent fixed-count site strata."""
import itertools
import unittest

import numpy as np

from alignment import ScoreSpec, reference_flags
from geometry_controls import Conditioning, expectation, sample_placements, stratify
from slot_expectation import expectation as unstratified_expectation


def page(slots, groups):
    slots = np.array(slots, dtype=float).reshape(-1, 2)
    groups = [(np.array(indices, dtype=int), k) for indices, k in groups]
    chosen = [i for indices, k in groups for i in indices[:k]]
    return dict(slots=slots, reds=slots[chosen], groups=groups)


def enumerate_draws(pages):
    choices = {}
    for n, d in pages.items():
        choices[n] = [d["slots"][list(itertools.chain.from_iterable(draw))]
                      for draw in itertools.product(*[
                          list(itertools.combinations(indices, k)) for indices, k in d["groups"]])]
    for drawn in itertools.product(*choices.values()):
        yield dict(zip(choices, drawn))


class GeometryTests(unittest.TestCase):
    def test_means_against_all_subsets_with_frozen_and_empty_strata(self):
        # Includes duplicate same-line sites, empty/full strata and a missing
        # page so mirror conditioning cannot silently bridge that gap.
        pages = {
            1: page([(0, 100), (1, 100), (0, 500), (0, 100), (2, 500)],
                    [([0, 1, 2], 2), ([3], 1), ([4], 0)]),
            2: page([(0, 924), (1, 924), (0, 524), (1, 524)],
                    [([0, 1], 1), ([2, 3], 1)]),
            4: page([(0, 100), (1, 100)], [([0, 1], 1)]),
        }
        for pairing in ("adjacent", "facing", "leaf", "none"):
            score = ScoreSpec(pairing=pairing)
            means = expectation(pages, score)
            counts = {k: [] for k in means}
            for placements in enumerate_draws(pages):
                sums = dict.fromkeys(means, 0)
                for c, m in reference_flags(placements, score).values():
                    sums["column"] += int(c.sum())
                    sums["mirror"] += int(m.sum())
                    sums["overlap"] += int((c & m).sum())
                    sums["aligned"] += int((c | m).sum())
                for key in sums:
                    counts[key].append(sums[key])
            for key in means:
                self.assertAlmostEqual(means[key], np.mean(counts[key]), places=12)

    def test_reduces_to_existing_page_and_line_formulas(self):
        slots = [(0, 100), (0, 500), (1, 100), (1, 500)]
        for null, groups in (("page", [([0, 1, 2, 3], 2)]),
                             ("line", [([0, 1], 1), ([2, 3], 1)])):
            pages = {1: page(slots, groups),
                     2: page([(li, 1024 - x) for li, x in slots], groups)}
            means = expectation(pages)
            existing, _ = unstratified_expectation(pages, null_model=null)
            for key in means:
                self.assertAlmostEqual(means[key], existing[key], places=12)

    def test_sampler_conserves_strata_and_handles_zero_selected_pages(self):
        pages = {1: page([(0, 100), (1, 100), (0, 500), (1, 500)],
                         [([0, 1, 2], 2), ([3], 1)]),
                 2: page([(0, 900)], [([0], 0)])}
        draws = sample_placements(pages, np.random.default_rng(17), 6000)
        allowed = list(enumerate_draws(pages))
        frequencies = {tuple(sorted(map(tuple, p[1]))): 0 for p in allowed}
        for positions in draws[1]:
            key = tuple(sorted(map(tuple, positions)))
            self.assertIn(key, frequencies)
            frequencies[key] += 1
        self.assertEqual(draws[2].shape, (6000, 0, 2))
        # Each of the three equally likely stratum subsets should appear.
        for count in frequencies.values():
            self.assertLess(abs(count - 2000), 180)

    def test_box_bins_edge_ties_and_line_conditioning(self):
        def box(x, width, line=0):
            return dict(x0=x, x1=x + width - 1, y0=0, y1=29,
                        line=line, color="red")
        sites = [box(0, 39), box(100, 39), box(200, 39), box(200, 39),
                 box(0, 40), box(0, 39, 1)]
        groups = stratify(sites, Conditioning(line=True, edge=True))
        actual = {frozenset(indices) for indices, _ in groups}
        self.assertEqual(actual, {frozenset([0]), frozenset([1]), frozenset([2, 3]),
                                  frozenset([4]), frozenset([5])})
        with self.assertRaises(ValueError):
            Conditioning(width_bin=0)

    def test_fully_conditioned_draw_is_deterministic(self):
        pages = {1: page([(0, 100), (1, 100), (0, 500)],
                         [([0, 1], 2), ([2], 0)]),
                 2: page([(0, 924), (1, 924)], [([0, 1], 2)])}
        means = expectation(pages)
        self.assertEqual(means, dict(column=4, mirror=4, overlap=4, aligned=4))
        draws = sample_placements(pages, np.random.default_rng(3), 5)
        for n in pages:
            np.testing.assert_array_equal(draws[n], np.tile(pages[n]["reds"], (5, 1, 1)))


if __name__ == "__main__":
    unittest.main()
