import json, re
from pathlib import Path
import numpy as np

DATA = Path(__file__).resolve().parent / "data"
DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u0653-\u0655\u0640]")

def norm(t):
    t = DIAC.sub("", t)
    return (t.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا")
             .replace("آ", "ا").replace("ى", "ي").replace("ة", "ه"))

def load_tokens():
    d = json.load(open(DATA / "quran-uthmani.json"))
    toks = []
    for v in d["verses"]:
        # Token maps omit annotation-only tokens whose normalized text is empty.
        toks.extend(t for t in v["text_uthmani"].split() if norm(t))
    return toks

def fit():
    tm = json.load(open(DATA / "token_map.json"))
    recs = tm["map"]
    raw = load_tokens()
    letters = sorted({norm(c) for t in raw for c in norm(t) if not DIAC.match(c)})
    li = {c: i for i, c in enumerate(letters)}
    print(f"{len(letters)} letters: {''.join(letters)}")

    rows, mass, width = [], [], []
    for r in recs:
        if r.get("skip") or r["n"] < 1 or r["n"] > 3:
            continue
        t = raw[r["t"]]
        nt = norm(t)
        if not nt:
            continue
        span = r["span"]
        if span <= 5:
            continue
        cur = 22.0 + 11.5 * len(nt)
        if abs(span - cur) / cur > 0.30:
            continue
        f = np.zeros(len(letters) + 2)
        for c in nt:
            f[li[c]] += 1
        f[len(letters)] = len(t) - len(nt)  # diacritic count
        f[len(letters) + 1] = 1.0  # intercept
        rows.append(f)
        mass.append(r["npx"])
        width.append(span)
    X = np.array(rows)
    print(f"training tokens: {len(X)} of {len(recs)}")
    mw = np.linalg.lstsq(X, np.array(mass), rcond=None)[0]
    ww = np.linalg.lstsq(X, np.array(width), rcond=None)[0]
    for nm, w, y in [("mass", mw, np.array(mass)), ("width", ww, np.array(width))]:
        pred = X @ w
        r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        mae = np.abs(y - pred).mean()
        print(f"{nm}: R2={r2:.3f} MAE={mae:.1f} (mean y={y.mean():.1f})")
    out = {"letters": letters,
           "mass": dict(zip(letters, mw[:len(letters)].round(2)),
                       diac=round(float(mw[len(letters)]), 2),
                       intercept=round(float(mw[len(letters) + 1]), 2)),
           "width": dict(zip(letters, ww[:len(letters)].round(2)),
                         diac=round(float(ww[len(letters)]), 2),
                         intercept=round(float(ww[len(letters) + 1]), 2))}
    (DATA / "letter_model.json").write_text(json.dumps(out, indent=1))
    print("mass letters:", {k: v for k, v in sorted(out["mass"].items(), key=lambda kv: -kv[1]) if k not in ("diac", "intercept")})
    print("width letters:", {k: v for k, v in sorted(out["width"].items(), key=lambda kv: -kv[1]) if k not in ("diac", "intercept")})

if __name__ == "__main__":
    fit()
