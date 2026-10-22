import json
import argparse
import hashlib
from pathlib import Path
import numpy as np

DATA = Path(__file__).resolve().parent / "data"
K = 34
CMAP = {
    1: [0, 2, 6, 8, 10, 29, 31, 33],
    2: [4, 17, 18, 19, 20, 22, 25, 27, 30],
    3: [],
    4: [5, 13, 23],
    5: [1, 12, 24],
    6: [3, 11, 16],
    7: [28],
    8: [7],
    9: [9, 14],
    0: [15, 26],
    None: [21, 32],
}
C2D = {}
for dig, ks in CMAP.items():
    for k in ks:
        C2D[k] = dig

def kmeans(F, K=K, iters=30, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(F), K, replace=False)
    C = F[idx].copy()
    lab = None
    for _ in range(iters):
        S = F @ C.T
        lab = S.argmax(1)
        for k in range(K):
            m = lab == k
            if m.sum() > 0:
                C[k] = F[m].mean(0)
                C[k] /= max(np.linalg.norm(C[k]), 1e-6)
    return lab

def load(path=DATA / "rosette_digits.npz"):
    d = np.load(path, allow_pickle=False)
    X = d["digits"].astype(np.float32)
    meta = d["meta"]
    F = X.reshape(len(X), -1)
    F = F / np.maximum(F.sum(1, keepdims=True), 1)
    return X, meta, F

def build_rosettes(X, meta, dig):
    # group consecutive crops into rosettes via ndig counter
    by_page = {}
    i = 0
    N = len(meta)
    while i < N:
        page, cx, cy, w, h, ndig = meta[i]
        if int(ndig) not in (1, 2, 3) or int(ndig) != ndig or i + int(ndig) > N:
            raise ValueError(f"invalid digit grouping at row {i}")
        if not np.all(meta[i:i + int(ndig), :3] == meta[i, :3]):
            raise ValueError(f"inconsistent rosette group at row {i}")
        page = int(page)
        digs = []
        for j in range(i, min(i + int(ndig), N)):
            digs.append(int(dig[j]))
        by_page.setdefault(page, []).append(
            dict(cx=float(cx), cy=float(cy), ndig=int(ndig),
                 digits=digs, row0=i))
        i += int(ndig)
    return by_page

def rosette_number(digits):
    if any(d < 0 for d in digits) or not digits:
        return None
    val = 0
    for d in digits:
        val = val * 10 + d
    return val

def tight16(x):
    ys, xs = np.nonzero(x)
    if len(ys) == 0:
        return np.zeros(400, dtype=np.float32)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = x[y0:y1, x0:x1].astype(np.float32)
    h, w = sub.shape
    s = 20.0 / max(h, w)
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    from PIL import Image
    im = Image.fromarray((sub * 255).astype(np.uint8)).resize((nw, nh), Image.BILINEAR)
    canvas = np.zeros((20, 20), dtype=np.float32)
    oy, ox = (20 - nh) // 2, (20 - nw) // 2
    canvas[oy:oy + nh, ox:ox + nw] = np.asarray(im, dtype=np.float32) / 255.0
    return (canvas / max(np.linalg.norm(canvas), 1e-6)).reshape(-1)


def reading_order(rows, tolerance=40):
    """Group slight y-jitter within a text row, then read right-to-left.

    This is still a geometric heuristic; independently labeled rows should
    validate it. Sorting raw (cy,-cx) can reverse same-line verse numbers.
    """
    groups = []
    for r in sorted(rows, key=lambda r: r["cy"]):
        if groups and r["cy"] - min(q["cy"] for q in groups[-1]) <= tolerance:
            groups[-1].append(r)
        else:
            groups.append([r])
    return [r for group in groups for r in sorted(group, key=lambda r: -r["cx"])]

def build_refs(X, meta, by_page):
    # known rosette numbers on anchor pages: page -> (surah, first_verse)
    # p567 and p604 cross surah boundaries and restart verse numbers; a
    # single consecutive-number anchor gives incorrect training labels.
    # p567 is independently transcribed in audit_manual_rosettes.json.
    anchors = {1: (2, 1), 206: (9, 123), 207: (10, 1), 422: (33, 36),
               49: (3, 1), 186: (9, 1)}
    refs = {}
    for page, (s, a0) in anchors.items():
        rs = reading_order(by_page.get(page, []))
        for k, r in enumerate(rs):
            n = a0 + k
            digs = [int(c) for c in str(n)]
            if len(digs) != r["ndig"]:
                continue
            for j, dv in enumerate(digs):
                row = r["row0"] + j
                refs.setdefault(dv, []).append(tight16(X[row]))
    R = []
    RL = []
    for dv, xs in refs.items():
        for v in xs:
            R.append(v)
            RL.append(dv)
    return np.array(R), np.array(RL)

def classify(X, meta, lab, by_page, extra=None):
    R, RL = build_refs(X, meta, by_page)
    if extra is not None:
        R = np.vstack([R, extra[0]])
        RL = np.concatenate([RL, extra[1]])
    F = np.array([tight16(x) for x in X])
    S = F @ R.T
    best = S.argmax(1)
    score = S[np.arange(len(F)), best]
    dig = RL[best].astype(np.int64)
    dig[score < 0.60] = -1
    return dig, score, F

def build_extra(F, dig, score, lab, K=K):
    groups = {}
    for i in range(len(F)):
        if dig[i] >= 0 and score[i] > 0.90:
            groups.setdefault((int(dig[i]), int(lab[i])), []).append(F[i])
    R, L = [], []
    for (dv, k), xs in sorted(groups.items()):
        if len(xs) < 8:
            continue
        m = np.mean(xs, axis=0)
        m /= max(np.linalg.norm(m), 1e-6)
        R.append(m)
        L.append(dv)
    if not R:
        return None
    return np.array(R), np.array(L, dtype=np.int64)

def expected_seq(cs):
    E, ES = [], []
    for s in range(2, 115):
        for a in range(1, cs[s] + 1):
            E.append(a)
            ES.append(s)
    return np.array(E), np.array(ES)

def align_global(seq, E, ES, band=240, skip_pen=2.2, junk_pen=2.2):
    """Banded global alignment, consuming BOTH complete sequences.

    Expected verses may be missed at page boundaries or sequence ends.
    The legacy terminal minimum over any verse index gave a free unmatched
    suffix; this implementation charges every deletion, including the tail.
    """
    n, m = len(seq), len(E)
    INF = 1e12
    D = np.full((2, 2 * band + 1), INF, dtype=np.float64)
    BK = np.full((n + 1, 2 * band + 1), -2, dtype=np.int8)
    # j - i + band indexing
    def J(i, jj):
        return jj - i + band
    D[0, J(0, 0)] = 0.0
    for i in range(n + 1):
        nxt = (i + 1) % 2
        cur = i % 2
        if i < n:
            D[nxt] = INF
        lo = max(0, i - band)
        hi = min(m, i + band)
        for jj in range(lo, hi + 1):
            k = J(i, jj)
            c = D[cur, k]
            if c >= INF / 2:
                continue
            # Process horizontal skips left-to-right, including at the end.
            if jj < m and jj + 1 <= min(m, i + band):
                if i == 0 or i == n or seq[i]["page"] != seq[i - 1]["page"]:
                    k2 = J(i, jj + 1)
                    if c + skip_pen < D[cur, k2]:
                        D[cur, k2] = c + skip_pen
                        BK[i, k2] = 1
            if i == n:
                continue
            k_junk = k - 1  # junk: (i,jj) -> (i+1,jj) => index jj-(i+1)+band
            if 0 <= k_junk <= 2 * band:
                if c + junk_pen < D[nxt, k_junk]:
                    D[nxt, k_junk] = c + junk_pen
                    BK[i + 1, k_junk] = 0
            if jj < m:
                r = seq[i]
                num = r["num"]
                if num is None:
                    pc = 1.2
                elif num == E[jj]:
                    pc = 0.0
                else:
                    pc = (1.0 + 0.35 * abs(len(str(num)) - len(str(E[jj])))
                          + 0.004 * abs(num - E[jj]))
                k2 = J(i + 1, jj + 1)
                if k2 < 0 or k2 > 2 * band:
                    continue
                if c + pc < D[nxt, k2]:
                    D[nxt, k2] = c + pc
                    BK[i + 1, k2] = 2
    if abs(m - n) > band or D[n % 2, J(n, m)] >= INF / 2:
        return None
    # trace
    i, jj = n, m
    ra = [None] * n
    while i > 0 or jj > 0:
        k = J(i, jj)
        b = BK[i, k]
        if b == 0:
            ra[i - 1] = None
            i -= 1
        elif b == 1:
            jj -= 1
        elif b == 2:
            ra[i - 1] = jj - 1
            i -= 1
            jj -= 1
        else:
            return None
    return ra

def harvest(seq):
    """Find runs of consecutive reads (+1) of length>=4; label crops."""
    labels = {}
    run = []
    for i, r in enumerate(seq):
        nm = r["num"]
        ok = False
        if run:
            pv = seq[run[-1]]["num"]
            if nm is not None and pv is not None and nm == pv + 1:
                ok = True
        if nm is not None:
            if ok or not run:
                run.append(i)
                continue
        # flush
        if len(run) >= 4:
            for k in run:
                rr = seq[k]
                digs = [int(c) for c in str(rr["num"])]
                if len(digs) == rr["ndig"]:
                    for j in range(rr["ndig"]):
                        labels.setdefault(rr["row0"] + j, digs[j])
        run = [i] if nm is not None else []
    if len(run) >= 4:
        for k in run:
            rr = seq[k]
            digs = [int(c) for c in str(rr["num"])]
            if len(digs) == rr["ndig"]:
                for j in range(rr["ndig"]):
                    labels.setdefault(rr["row0"] + j, digs[j])
    return labels

def consec_rate(seq):
    ok = pairs = 0
    for p in set(r["page"] for r in seq):
        rs = reading_order([r for r in seq if r["page"] == p])
        for a, b in zip(rs, rs[1:]):
            if a["num"] is None or b["num"] is None:
                continue
            pairs += 1
            if b["num"] == a["num"] + 1:
                ok += 1
    return ok, pairs

def main():
    parser = argparse.ArgumentParser(description="Inferred rosette-to-verse map; not independently certified ground truth.")
    parser.add_argument("--digits", type=Path, default=DATA / "rosette_digits.npz")
    parser.add_argument("--boxes", type=Path, default=DATA / "real_boxes")
    parser.add_argument("--output-directory", type=Path, default=DATA)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    X, meta, F = load(args.digits)
    lab = kmeans(F)
    by_page0 = build_rosettes(X, meta, np.zeros(len(X), dtype=np.int64) - 2)
    dig, score, F16 = classify(X, meta, lab, by_page0)
    extra = build_extra(F16, dig, score, lab)
    if extra is not None:
        dig, score, F16 = classify(X, meta, lab, by_page0, extra=extra)
    for it in range(8):
        seq = build_seq_fn(X, meta, dig)
        ok, pairs = consec_rate(seq)
        labels = harvest(seq)
        print(f"iter {it}: consec {ok}/{pairs} ({100.0*ok/max(pairs,1):.1f}%) "
              f"harvested {len(labels)} crops", flush=True)
        if len(labels) < 500:
            break
        rows = np.array(sorted(labels.keys()))
        y = np.array([labels[r] for r in rows], dtype=np.int64)
        V = F16[rows]
        R, L = V, y
        dig, score, F16 = classify(X, meta, lab, by_page0, extra=(R, L))
    # final EM state -> global alignment
    verses = json.load(open(DATA / "quran-uthmani.json"))["verses"]
    from collections import Counter
    cs = Counter(int(v["verse_key"].split(":")[0]) for v in verses)
    E, ES = expected_seq(cs)
    grids = {}
    for p in range(1, 605):
        f = args.boxes / f"page_{p:03d}.json"
        if f.exists():
            d = json.loads(f.read_text())
            if d.get("grid"):
                grids[p] = d["grid"]["centers"]
    seq = build_seq_fn(X, meta, dig)
    ra = align_global(seq, E, ES)
    for i, r in enumerate(seq):
        if ra[i] is not None:
            r["surah"] = int(ES[ra[i]])
            r["verse"] = int(E[ra[i]])
        else:
            r["surah"] = None
            r["verse"] = None
    aligned_v = sum(1 for i in range(len(seq)) if ra[i] is not None)
    exact = sum(1 for i in range(len(seq))
                if ra[i] is not None and seq[i]["num"] == E[ra[i]])
    print(f"final: rosettes={len(seq)} aligned={aligned_v} exact={exact} "
          f"missed={len(E) - aligned_v}")
    # post-process: assign missed verses to junked rosettes sandwiched
    # between aligned neighbors
    junk_runs = []
    i = 0
    while i < len(seq):
        if ra[i] is None:
            j = i
            while j < len(seq) and ra[j] is None:
                j += 1
            junk_runs.append((i, j))
            i = j
        else:
            i += 1
    for (a, b) in junk_runs:
        pa = max((ra[k] for k in range(a - 1, -1, -1) if ra[k] is not None),
                 default=None)
        pb = min((ra[k] for k in range(b, len(seq)) if ra[k] is not None),
                 default=None)
        if pa is None or pb is None:
            continue
        gap = list(range(pa + 1, pb))
        if not gap:
            continue
        n = b - a
        if n <= len(gap):
            # assign first n missed verses to the junked rosettes
            for off, k in enumerate(range(a, b)):
                vpos = gap[off]
                seq[k]["surah"] = int(ES[vpos])
                seq[k]["verse"] = int(E[vpos])
                seq[k]["recovered"] = True
    for i, r in enumerate(seq):
        if ra[i] is not None and r.get("verse") is None:
            r["surah"] = int(ES[ra[i]])
            r["verse"] = int(E[ra[i]])
    covered = set()
    for i, r in enumerate(seq):
        if r.get("verse") is not None:
            covered.add((r["surah"], r["verse"]))
    miss = [j for j in range(len(E)) if (int(ES[j]), int(E[j])) not in covered]
    ghosts = []
    for j in miss:
        prev_i = max((i for i in range(len(seq))
                      if ra[i] is not None and ra[i] < j), default=None)
        next_i = min((i for i in range(len(seq))
                      if ra[i] is not None and ra[i] > j), default=None)
        if prev_i is None:
            gpage = seq[next_i]["page"]
        elif next_i is None:
            gpage = seq[prev_i]["page"]
        elif seq[prev_i]["page"] == seq[next_i]["page"]:
            gpage = seq[prev_i]["page"]
        else:
            A = seq[prev_i]["page"]
            ctr = grids.get(A)
            on_last = ctr is not None and seq[prev_i]["cy"] >= ctr[-1] - 45
            gpage = seq[next_i]["page"] if on_last else A
        ghosts.append(dict(page=gpage, surah=int(ES[j]), verse=int(E[j])))
    allv = [r for r in seq if r["verse"] is not None] + \
           [dict(page=g["page"], cy=-1, cx=-1, surah=g["surah"],
                 verse=g["verse"]) for g in ghosts]
    pages_out = {}
    for p in range(1, 605):
        rs = [r for r in allv if r["page"] == p]
        if not rs:
            pages_out[str(p)] = None
            continue
        # Ghosts have cy=-1. They must not become the first verse merely
        # because of that sentinel; spans use canonical verse order.
        rs.sort(key=lambda r: (r["surah"], r["verse"]))
        a, b = rs[0], rs[-1]
        pages_out[str(p)] = dict(first=f"{a['surah']}:{a['verse']}",
                                 last=f"{b['surah']}:{b['verse']}",
                                 n=len(rs))
    (args.output_directory / "page_verse_map.json").write_text(json.dumps(pages_out, indent=0))
    np.savez_compressed(args.output_directory / "rosette_seq.npz",
                        meta=np.array([[r["page"], r.get("cx", -1), r.get("cy", -1),
                                        r.get("surah") if r.get("surah") else -1,
                                        r.get("verse") if r.get("verse") else -1,
                                        r["num"] if r.get("num") is not None else -1,
                                        r.get("row0", -1)]
                                        for r in seq], dtype=np.float64))
    (args.output_directory / "_rosette_map_report.json").write_text(json.dumps(dict(
        version="global-terminal-rtl-v2", status="inferred, not independent ground truth",
        digits_sha256=hashlib.sha256(args.digits.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        mapped_rosettes=aligned_v, raw_reads_equal_assigned=exact,
        inferred_ghost_verses=len(ghosts),
        caveat="Self-trained digit templates, manual anchors, sequence alignment and ghost assignment; "
               "no held-out accuracy is measured by this script."), indent=2) + "\n")
    print("saved page_verse_map.json")
    for p in (1, 2, 23, 206, 207, 300, 422, 599, 604):
        print(f"p{p}:", pages_out.get(str(p)))

def build_seq_fn(X, meta, dig):
    by_page = build_rosettes(X, meta, dig)
    seq = []
    for p in sorted(by_page):
        rs = reading_order(by_page[p])
        for r in rs:
            r["page"] = p
            r["num"] = rosette_number(r["digits"])
            seq.append(r)
    return seq

if __name__ == "__main__":
    main()
