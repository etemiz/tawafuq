"""Cross-page pair counts, including genuine opposite-cell mirror pairs."""
from collections import Counter


def word_cell_pairs(items, mirror_bins=None):
    """items = (word, page, row, column), unordered distinct-page pairs.

    With mirror_bins, require ca+cb=mirror_bins-1 instead of ca=cb.
    A global reversal of EVERY cell would not be a mirror-pair test.
    """
    counts = Counter((w, row, col) for w, pg, row, col in items)
    per_page = Counter((w, pg, row, col) for w, pg, row, col in items)
    if mirror_bins is None:
        return (sum(n * (n - 1) // 2 for n in counts.values())
                - sum(n * (n - 1) // 2 for n in per_page.values()))
    total = 0
    for (w, row, col), n in counts.items():
        other = mirror_bins - 1 - col
        if col < other:
            total += n * counts[(w, row, other)]
        elif col == other:
            total += n * (n - 1) // 2
    for (w, pg, row, col), n in per_page.items():
        other = mirror_bins - 1 - col
        if col < other:
            total -= n * per_page[(w, pg, row, other)]
        elif col == other:
            total -= n * (n - 1) // 2
    return total
