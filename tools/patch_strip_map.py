"""Strip-aware token_map2 rebuild (S10 followup).

Re-runs page_dp per page with mt.load_page(n, keep_strips=True), diffs new
token records against token_map2.json, and patches records whose boxes
changed. Kinds: skip2box (old skip -> boxed), box2skip (old boxed -> skip,
never patched, reported), geom (geometry changed; split by strip flag).
--apply writes token_map2.json in place; default is a dry run.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt

DATA = Path(__file__).resolve().parent / "data"
ANCHORS = (206, 207, 422, 23, 154, 155)


def page_offsets(spans, verses):
    off = {}
    first_sp = next((sp for sp in spans if sp), None)
    idx = sum(len(verses[i][2]) for i in range(first_sp[0]))
    for p in range(604):
        sp = spans[p]
        if sp is None:
            continue
        off[p + 1] = (idx, sum(len(verses[i][2]) for i in range(sp[0], sp[1] + 1)))
        idx += off[p + 1][1]
    return off


def main():
    apply = "--apply" in sys.argv
    verses = mt.load_tokens()
    tm = json.loads((DATA / "token_map2.json").read_text())
    spans = [tuple(tm["spans"][str(p + 1)]) if str(p + 1) in tm["spans"]
             else None for p in range(604)]
    old_map = {r["t"]: r for r in tm["map"]}
    off = page_offsets(spans, verses)
    tok_idx = off[1][0] if 1 in off else next(iter(off.values()))[0]
    stats = dict(pages=0, dpfail=0, unchanged=0, skip2box=0, box2skip=0,
                 geom=0, geom_strip=0)
    per_page = {}
    other_samples = []
    new_recs = {}
    for p in range(604):
        sp = spans[p]
        if sp is None:
            continue
        page = p + 1
        s0, s1 = sp
        toks = [t for i in range(s0, s1 + 1) for t in verses[i][2]]
        stats["pages"] += 1
        lp = mt.load_page(page, keep_strips=True)
        if lp is None:
            tok_idx += len(toks)
            continue
        d, stream = lp
        cost, mapping = mt.page_dp(stream, toks)
        if mapping is None:
            stats["dpfail"] += 1
            print(f"p{page}: STRIP DP FAILED ({len(stream)} boxes vs {len(toks)} toks)")
            tok_idx += len(toks)
            continue
        pd = dict(diff=0, strip=0, skip2box=0, box2skip=0, other=0)
        for gi, g in enumerate(mapping):
            t = tok_idx
            tok_idx += 1
            old = old_map.get(t)
            if g is None or len(g) == 0:
                new = dict(t=t, page=page, boxes=[], skip=True)
                kind = None if (old is None or old.get("skip")) else "box2skip"
            else:
                bs = [stream[j] for j in g]
                new = dict(t=t, page=page,
                           boxes=[b["cx"] for b in bs],
                           x=[min(b["x0"] for b in bs), max(b["x1"] for b in bs)],
                           y=[int(min(b["y0"] for b in bs)),
                              int(max(b["y1"] for b in bs))],
                           line=bs[0]["line"],
                           n=len(bs),
                           npx=sum(b["npx"] for b in bs),
                           span=bs[0]["x1"] - bs[-1]["x0"] + 1)
                if any(b.get("strip") for b in bs):
                    new["strip"] = 1
                if old is None or old.get("skip"):
                    kind = "skip2box"
                elif (old.get("x") == new["x"] and old.get("y") == new["y"]
                      and old.get("boxes") == new["boxes"]):
                    kind = None
                else:
                    kind = "geom"
            if kind is None:
                stats["unchanged"] += 1
                continue
            strip_rec = bool(new.get("strip"))
            stats[kind] += 1
            if kind == "geom" and strip_rec:
                stats["geom_strip"] += 1
                pd["strip"] += 1
            elif kind == "geom":
                pd["other"] += 1
                if len(other_samples) < 40:
                    other_samples.append((page, t, old.get("x"), new["x"],
                                          old.get("y"), new["y"]))
            new_recs[t] = new
        if pd["diff"]:
            per_page[page] = pd
            print(f"p{page}: diff={pd['diff']} strip={pd['strip']} "
                  f"skip2box={pd['skip2box']} box2skip={pd['box2skip']} "
                  f"other={pd['other']}")
    print("== summary ==")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("== non-strip geom diffs (sample) ==")
    for s in other_samples:
        print(f"  p{s[0]} t{s[1]}: x {s[2]} -> {s[3]}, y {s[4]} -> {s[5]}")
    print("== anchors ==")
    for a in ANCHORS:
        if a not in off:
            print(f"anchor p{a}: no span")
            continue
        t0, nt = off[a]
        na = sum(1 for t in range(t0, t0 + nt) if t in new_recs)
        print(f"anchor p{a}: {na}/{nt} changed records")
    if not apply:
        print("(dry run; no file written)")
        return
    for t, r in new_recs.items():
        old_map[t] = r
    tm["map"] = [old_map[r["t"]] for r in tm["map"]]
    (DATA / "token_map2.json").write_text(json.dumps(tm))
    print("patched token_map2.json:", len(new_recs), "records")


if __name__ == "__main__":
    main()
