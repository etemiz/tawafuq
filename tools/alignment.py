"""CPU reference and batched scorers for an explicit, versioned statistic.

Columns: same clipped floor((x-26)/30) bin, at least two distinct lines.
Mirrors: same line and reflected 32px cell across a NUMERICALLY adjacent
pair, x for odd pages and 1024-x for even pages. Each endpoint is flagged.
The combined score is a Boolean union, never a sum of match incidences.
These are binned COMPONENT statistics, not a tolerance-window word census.
"""
from dataclasses import dataclass, asdict
import math

import numpy as np


@dataclass(frozen=True)
class ScoreSpec:
    column_width: float = 30.0
    column_origin: float = 26.0
    mirror_width: float = 32.0
    page_width: float = 1024.0
    bins: int = 32
    pairing: str = "adjacent"  # adjacent, facing (even/odd), leaf (odd/even), none
    version: str = "component-union-v1"

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.column_width, self.column_origin,
                                              self.mirror_width, self.page_width)):
            raise ValueError("finite score parameters required")
        if self.column_width <= 0 or self.mirror_width <= 0 or self.bins < 1:
            raise ValueError("bin widths and count must be positive")
        if self.page_width <= 0 or not isinstance(self.bins, int):
            raise ValueError("positive page width and integer bin count required")
        if self.pairing not in ("adjacent", "facing", "leaf", "none"):
            raise ValueError("unknown pairing")

    def to_dict(self):
        return asdict(self)


def eligible_pair(a, b, spec):
    return (b == a + 1 and spec.pairing != "none"
            and (spec.pairing == "adjacent"
                 or (spec.pairing == "facing" and a % 2 == 0)
                 or (spec.pairing == "leaf" and a % 2 == 1)))


def encode(page, positions, spec):
    """positions may have shape (k, 2) or (batch, k, 2)."""
    p = np.asarray(positions)
    lines = p[..., 0].astype(np.int64)
    cols = np.clip(np.floor((p[..., 1] - spec.column_origin)
                           / spec.column_width), 0, spec.bins - 1).astype(np.int64)
    reflected = p[..., 1] if page % 2 else spec.page_width - p[..., 1]
    mirrors = np.clip(np.floor(reflected / spec.mirror_width),
                      0, spec.bins - 1).astype(np.int64)
    return lines, cols, mirrors


def reference_flags(placements, spec=ScoreSpec()):
    """Deliberately slow pair enumeration, independent of occupancy scoring."""
    cols = {n: np.zeros(len(p), dtype=bool) for n, p in placements.items()}
    mirs = {n: np.zeros(len(p), dtype=bool) for n, p in placements.items()}
    # Scalar arithmetic intentionally does not call encode().
    import math
    cb = lambda x: min(spec.bins - 1, max(0, math.floor(
        (x - spec.column_origin) / spec.column_width)))
    mb = lambda n, x: min(spec.bins - 1, max(0, math.floor(
        (x if n % 2 else spec.page_width - x) / spec.mirror_width)))
    for n, p in placements.items():
        for i, (li, xi) in enumerate(p):
            for j in range(i):
                lj, xj = p[j]
                if li != lj and cb(xi) == cb(xj):
                    cols[n][i] = cols[n][j] = True
        if not eligible_pair(n, n + 1, spec) or n + 1 not in placements:
            continue
        for i, (li, xi) in enumerate(p):
            for j, (lj, xj) in enumerate(placements[n + 1]):
                if li == lj and mb(n, xi) == mb(n + 1, xj):
                    mirs[n][i] = mirs[n + 1][j] = True
    return {n: (cols[n], mirs[n]) for n in placements}


def _occupancy(keys, size):
    batch = keys.shape[0]
    offsets = np.arange(batch)[:, None] * size
    return np.bincount((keys + offsets).ravel(),
                       minlength=batch * size).reshape(batch, size)


def batch_flags(placements, spec=ScoreSpec()):
    """Return column/mirror flags, for shape (batch, k, 2) per page."""
    encoded = {n: encode(n, p, spec) for n, p in placements.items()}
    result = {}
    for n, (lines, cols, mirrors) in encoded.items():
        batch, k = lines.shape
        if k:
            nl = int(lines.max()) + 1
            cells = _occupancy(lines * spec.bins + cols, nl * spec.bins)
            totals = _occupancy(cols, spec.bins)
            rows = np.arange(batch)[:, None]
            col = totals[rows, cols] > cells[rows, lines * spec.bins + cols]
        else:
            col = np.zeros((batch, 0), dtype=bool)
        result[n] = (col, np.zeros((batch, k), dtype=bool))
    for n in placements:
        if n + 1 not in placements or not eligible_pair(n, n + 1, spec):
            continue
        la, _, ma = encoded[n]
        lb, _, mb = encoded[n + 1]
        if not la.size or not lb.size:
            continue
        size = (max(int(la.max()), int(lb.max())) + 1) * spec.bins
        ka, kb = la * spec.bins + ma, lb * spec.bins + mb
        ca, cb = _occupancy(ka, size), _occupancy(kb, size)
        rows = np.arange(la.shape[0])[:, None]
        result[n][1][:] |= cb[rows, ka] > 0
        result[n + 1][1][:] |= ca[rows, kb] > 0
    return result


def score_flags(flags):
    first = next(iter(flags.values()))[0]
    batch = first.shape[0]
    counts = {k: np.zeros(batch, dtype=np.int64)
              for k in ("column", "mirror", "overlap", "aligned")}
    for col, mir in flags.values():
        for name, mask in (("column", col), ("mirror", mir),
                           ("overlap", col & mir), ("aligned", col | mir)):
            counts[name] += mask.sum(axis=1)
    return counts


def sample_placements(pages, rng, batch, null_model="page"):
    """Uniform per-page subsets without replacement, via iid random ranks.

    Batch size is recorded because it changes consumption of the RNG stream.
    """
    placements = {}
    for n, d in pages.items():
        slots, k = d["slots"], len(d["reds"])
        if null_model == "line":
            drawn = np.empty((batch, k, 2), dtype=float)
            for line in np.unique(d["reds"][:, 0]):
                targets = np.flatnonzero(d["reds"][:, 0] == line)
                candidates = slots[slots[:, 0] == line]
                if len(targets) > len(candidates):
                    raise ValueError(f"page {n}, line {line}: insufficient slots")
                ranks = rng.random((batch, len(candidates)))
                # Full ranking is inexpensive for a single line and uniformly
                # assigns typed targets to sampled slots.
                pick = ranks.argsort(axis=1)[:, :len(targets)]
                drawn[:, targets] = candidates[pick]
            placements[n] = drawn
            continue
        if null_model != "page":
            raise ValueError("unknown null model")
        if k > len(slots):
            raise ValueError(f"page {n}: {k} components but only {len(slots)} slots")
        ranks = rng.random((batch, len(slots)))
        pick = np.argpartition(ranks, k - 1, axis=1)[:, :k] if k else np.empty(
            (batch, 0), dtype=np.int64)
        # A uniformly ordered subset is needed when positions receive fixed
        # type labels. argpartition alone only guarantees a uniform SET.
        selected_ranks = np.take_along_axis(ranks, pick, axis=1)
        pick = np.take_along_axis(pick, selected_ranks.argsort(axis=1), axis=1)
        placements[n] = slots[pick]
    return placements
