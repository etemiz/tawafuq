"""Article figures (Phase C). Sources: frozen numbers from docs/RESULTS.md
+ committed JSON artifacts. Latin labels only (no Arabic reshaping needed).

Run: python tools/make_figs.py   -> docs/articles/figs/*.png
"""
from pathlib import Path

import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGS = Path(__file__).resolve().parent.parent / "docs" / "articles" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)
DATA = Path(__file__).resolve().parent / "data"

CRI = "#E4296B"   # crimson ink
MAG = "#D42C8C"   # magenta ink
NULL = "#7a7a7a"


def fig_global():
    # RESULTS.md 3.2: 72.65% vs 25.35%±0.76% (400 reps, real-geometry null)
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar([0, 1], [25.35, 72.65], width=0.55,
                  color=[NULL, CRI], zorder=3)
    ax.errorbar([0], [25.35], yerr=[0.76], fmt="none", ecolor="black",
                capsize=5, zorder=4)
    labels = ["chance (real-geometry null)\n25.35% ± 0.76%",
              "the actual mushaf\n72.65%"]
    for b, lab in zip(bars, labels):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5,
                lab, ha="center", fontsize=10)
    ax.set_xticks([])
    ax.set_ylabel("divine-name words aligned (%)")
    ax.set_ylim(0, 90)
    ax.set_title("Alignment of 4,621 crimson divine-name words\n"
                 "z = 62  ·  p ≈ 10$^{-985}$  ·  ≈ 3,269 bits",
                 fontsize=11)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_global.png", dpi=160)
    plt.close(fig)


def fig_columns():
    # RESULTS.md 3.2 column-size curve (575 usable pages)
    ks = [3, 4, 5, 6, 7, 8, 10]
    obs = [299, 138, 77, 20, 6, 3, 1]
    null = [40.1, 5.4, 0.43, 0.03, 0.001, 0, 0]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(ks, obs, "o-", color=CRI, lw=2, label="observed mushaf")
    ax.plot(ks, null, "s--", color=NULL, lw=2,
            label="null (2000 full reshuffles)")
    for k, o, n in zip(ks, obs, null):
        ax.annotate(f"{o}", (k, o), textcoords="offset points",
                    xytext=(4, 4), color=CRI, fontsize=9)
        if n > 0:
            ax.annotate(f"{n:g}", (k, n), textcoords="offset points",
                        xytext=(4, -10), color=NULL, fontsize=8)
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 1e3)
    ax.set_xlabel("largest same-column word count on a page (k)")
    ax.set_ylabel("pages whose best column ≥ k")
    ax.set_title("Column-size curve: the null produces essentially no\n"
                 "5+ columns; the mushaf has 77", fontsize=11)
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_columns.png", dpi=160)
    plt.close(fig)


def fig_types():
    # RESULTS.md 3.2 per-type table
    rows = [
        ("Allah (standalone)", 86.5, 16.4),
        ("Allah-prefixed", 76.6, 1.5),
        ("Rabb family", 66.5, 8.6),
        ("partner words", 70.2, 26.3),
        ("Huwa", 58.8, 0.7),
        ("pause marks", 27.2, 9.6),
    ]
    names = [r[0] for r in rows][::-1]
    obs = [r[1] for r in rows][::-1]
    nul = [r[2] for r in rows][::-1]
    y = range(len(rows))
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.barh([i + 0.2 for i in y], obs, height=0.38, color=CRI,
            label="observed", zorder=3)
    ax.barh([i - 0.2 for i in y], nul, height=0.38, color=NULL,
            label="null", zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel("aligned (%)")
    ax.set_title("Per-type alignment rates vs the real-geometry null",
                 fontsize=11)
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.3, zorder=0)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_types.png", dpi=160)
    plt.close(fig)


def fig_p422():
    # schematic of p.422 crimson words from committed ink boxes (no image)
    d = json.load(open(DATA / "real_boxes" / "page_422.json"))
    reds = d["reds"]
    fig, ax = plt.subplots(figsize=(6.4, 9))
    for r in reds:
        ax.add_patch(plt.Rectangle((r["x0"], 1680 - r["y1"]),
                                   r["x1"] - r["x0"], r["y1"] - r["y0"],
                                   fill=True, color=CRI, alpha=0.85))
    # the famous column: x ≈ 333-403 (RESULTS.md B6)
    ax.axvspan(333, 403, color="black", alpha=0.08, zorder=0)
    ax.text(368, 1640, "12-of-16 column", ha="center", fontsize=9,
            color="black")
    ax.set_xlim(0, 1024)
    ax.set_ylim(0, 1680)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("p.422 (33:36-43): 16 crimson الله + محمد + هو\n"
                 "schematic from measured ink boxes", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_p422.png", dpi=160)
    plt.close(fig)


def fig_tint():
    # RESULTS.md S15/S16: per-word tint marking rate lower bounds
    rows = [("hem (هم)", 87), ("lakin", 83), ("takdhiban (refrain)", 100),
            ("qala (قال)", 45), ("inna/an", 40), ("alladhina", 40),
            ("qalu (قالوا)", 22), ("huwa", 23), ("qiya (~آية)", 21),
            ("qul (قل)", 19), ("fi (في)", 17), ("illa", 10),
            ("min (من)", 7), ("ma (ما)", 3), ("wala", 2)]
    rows.sort(key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.barh([r[0] for r in rows], [r[1] for r in rows], color=MAG, zorder=3)
    ax.set_xlabel("marked occurrences (%, ink-verified lower bound)")
    ax.set_title("The magenta tint layer marks a SELECTED subset of ~92\n"
                 "frequent words — not a blanket rule", fontsize=11)
    ax.grid(axis="x", alpha=0.3, zorder=0)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_tint.png", dpi=160)
    plt.close(fig)


def fig_sensitivity():
    # RESULTS.md 3.1 tolerance sensitivity for the p.422 column
    tols = ["±15px", "±30px", "±45px"]
    p = [9.6e-11, 3.9e-7, 5.1e-5]
    fig, ax = plt.subplots(figsize=(6, 4))
    b = ax.bar(tols, p, color=CRI, width=0.5, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(1e-5, 1e-10)
    for bb, v in zip(b, p):
        ax.text(bb.get_x() + bb.get_width() / 2, v * 1.6, f"1 in {1/v:,.0f}",
                ha="center", fontsize=10)
    ax.set_ylabel("corrected p (any page in the mushaf, look-elsewhere incl.)")
    ax.set_title("The p.422 column stays astronomically rare at every\n"
                 "reading of 'column' (±15 → ±45 px)", fontsize=11)
    ax.invert_yaxis()
    ax.grid(axis="y", alpha=0.3, which="both", zorder=0)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_sensitivity.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_global()
    fig_columns()
    fig_types()
    fig_p422()
    fig_tint()
    fig_sensitivity()
    print("wrote", FIGS)


def fig_scale():
    # "1 in X" comparison on a log scale (log10 values passed directly;
    # 1e985 etc. overflow float, so never compute log10 of the float)
    rows = [
        ("typical 6/49 lottery jackpot", 7.1, NULL),
        ("royal flush (poker)", 5.8, NULL),
        ("5-sigma physics discovery", 6.5, NULL),
        ("p.422 column, corrected", 10.0, CRI),
        ("4 verified anchors combined", 30.8, CRI),
        ("full deck into one prespecified order", 66.9, NULL),
        ("picking one given atom in the universe", 80.0, NULL),
        ("this study: the whole mushaf test", 985.0, CRI),
        ("this study: all divine word types combined", 1896.0, CRI),
    ]
    rows = rows[::-1]
    names = [r[0] for r in rows]
    logs = [r[1] for r in rows]
    cols = [r[2] for r in rows]
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    bars = ax.barh(names, logs, color=cols, zorder=3, height=0.62)
    ax.set_xlabel("improbability: 1 in 10$^{x}$  (log scale)")
    ax.set_xlim(0, 1960)
    for b, lg in zip(bars, logs):
        lab = f"1 in 10$^{{{lg:.0f}}}$" if lg > 5 else f"1 in {10**lg:,.0f}"
        ax.text(lg + 25, b.get_y() + b.get_height() / 2, lab,
                va="center", fontsize=9)
    ax.set_title("How improbable is 'improbable'?", fontsize=11)
    ax.grid(axis="x", alpha=0.3, zorder=0)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_scale.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_scale()


# ---------- v3 redesigns: takeaway titles, ink palette, annotation-first ----
PAL = {"ink": "#1b1b1b", "cri": "#E4296B", "mag": "#C22C86",
       "null": "#8a857e", "paper": "#fffdf9", "soft": "#e8e2d6"}


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0)
    ax.set_facecolor(PAL["paper"])


def fig_global_v3():
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    fig.patch.set_facecolor(PAL["paper"])
    bars = ax.bar([0, 1], [25.35, 72.65], width=0.5,
                  color=[PAL["null"], PAL["cri"]], zorder=3)
    ax.errorbar([0], [25.35], yerr=[0.76], fmt="none", ecolor="black",
                capsize=5, lw=1.2)
    ax.text(0, 27.5, "chance\n(shuffled mushaf)\n25.35% ± 0.76%",
            ha="center", fontsize=10, color="#4a463f")
    ax.text(1, 74.5, "the real mushaf\n72.65%", ha="center", fontsize=11,
            color=PAL["cri"], fontweight="bold")
    ax.text(0.5, 45, "z = 62\n1 in 10$^{985}$", ha="center", fontsize=12,
            color=PAL["ink"])
    ax.set_xticks([])
    ax.set_ylabel(None)
    ax.set_yticks([])
    ax.set_ylim(0, 95)
    ax.set_title("Chance aligns 1 in 4.  The real book aligns 3 in 4.",
                 fontsize=13, fontweight="bold", color=PAL["ink"], pad=12)
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_global.png", dpi=170)
    plt.close(fig)


def fig_columns_v3():
    ks = [3, 4, 5, 6, 7, 8, 10]
    obs = [299, 138, 77, 20, 6, 3, 1]
    null = [40.1, 5.4, 0.43, 0.03, 0.001, 0, 0]
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    fig.patch.set_facecolor(PAL["paper"])
    ax.plot(ks, obs, "o-", color=PAL["cri"], lw=2.4, ms=5)
    ax.plot(ks, null, "s--", color=PAL["null"], lw=1.8, ms=4)
    ax.annotate("the real mushaf", (4, 138), textcoords="offset points",
                xytext=(10, 12), color=PAL["cri"], fontsize=11,
                fontweight="bold")
    ax.annotate("chance (2,000 shuffles)", (6, 0.03),
                textcoords="offset points", xytext=(-8, -26),
                color=PAL["null"], fontsize=10)
    ax.axvline(5, color=PAL["soft"], lw=8, zorder=0)
    ax.text(5.25, 0.6, "5-deep columns:\nchance expects 0.43 pages,\nthe book has 77",
            fontsize=10, color=PAL["ink"], va="center")
    ax.set_yscale("log")
    ax.set_ylim(7e-4, 2e3)
    ax.set_xlabel("deepest same-column stack on a page (words)", fontsize=10)
    ax.set_ylabel("pages whose deepest stack ≥ k", fontsize=10)
    ax.set_title("Long columns: where chance runs out completely",
                 fontsize=13, fontweight="bold", color=PAL["ink"], pad=12)
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_columns.png", dpi=170)
    plt.close(fig)


def fig_scale_v3():
    rows = [
        ("royal flush (poker)", 5.8, PAL["null"]),
        ("5-sigma physics discovery", 6.5, PAL["null"]),
        ("jackpot in a typical 6/49 lottery", 7.1, PAL["null"]),
        ("100 coin flips, all heads", 30.1, PAL["null"]),
        ("a full deck into one prespecified order", 66.9, PAL["null"]),
        ("picking one given atom in the universe", 80.0, PAL["null"]),
        ("this study: the whole-mushaf test", 985.0, PAL["cri"]),
        ("this study: all divine word types combined", 1896.0, PAL["cri"]),
    ]
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    fig.patch.set_facecolor(PAL["paper"])
    names = [r[0] for r in rows]
    logs = [r[1] for r in rows]
    cols = [r[2] for r in rows]
    bars = ax.barh(names, logs, color=cols, height=0.62, zorder=3)
    ax.set_xlabel("improbability:  1 in 10$^{x}$   (log scale)", fontsize=10)
    ax.set_xlim(0, 1950)
    for b, lg, col in zip(bars, logs, cols):
        ax.text(lg + 28, b.get_y() + b.get_height() / 2,
                f"1 in 10$^{{{lg:.0f}}}$" if lg > 5 else f"1 in {10**lg:,.0f}",
                va="center", fontsize=9.5,
                color=PAL["cri"] if col == PAL["cri"] else "#555")
    ax.set_title("This result sits off every everyday scale",
                 fontsize=12.5, fontweight="bold", color=PAL["ink"], pad=12)
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_scale.png", dpi=170)
    plt.close(fig)


def fig_scale2():
    """Variant: the everyday events live in a sliver; blow it up."""
    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(7.6, 3.6), width_ratios=[1, 1.9])
    fig.patch.set_facecolor(PAL["paper"])
    everyday = [
        ("royal flush", 5.8), ("5-sigma physics", 6.5),
        ("6/49 lottery jackpot", 7.1), ("100 coins, all heads", 30.1),
        ("deck in one order", 66.9), ("one given atom", 80.0),
    ]
    # LEFT: zoom on 0..100
    axL.barh([e[0] for e in everyday], [e[1] for e in everyday],
             color=PAL["null"], height=0.55, zorder=3)
    for i, (n, v) in enumerate(everyday):
        axL.text(v + 1.5, i, f"10$^{{{v:.0f}}}$", va="center", fontsize=8.5,
                 color="#555")
    axL.set_xlim(0, 112)
    axL.set_title("everything humans call\n\"astronomically unlikely\"",
                  fontsize=10, fontweight="bold", color=PAL["ink"])
    axL.set_xlabel("exponent x  (1 in 10$^x$)", fontsize=8.5)
    axL.tick_params(labelsize=8.5)
    _style(axL)
    # RIGHT: the full range
    events = [(e[0], e[1]) for e in everyday] + [
        ("the whole-mushaf test", 985.0),
        ("all divine word types combined", 1896.0)]
    ys = list(range(len(events)))
    axR.barh(ys, [e[1] for e in events],
             color=[PAL["null"]] * 6 + [PAL["cri"]] * 2, height=0.55, zorder=3)
    axR.set_yticks(ys)
    axR.set_yticklabels([])
    for i, (n, v) in enumerate(events):
        axR.text(v + 28, i, f"10$^{{{v:.0f}}}$", va="center", fontsize=8.5,
                 color=PAL["cri"] if v > 100 else "#555")
    axR.axvspan(0, 100, color=PAL["soft"], zorder=0)
    axR.text(50, 7.35, "the left panel\nis this sliver",
             ha="center", fontsize=8.5, color="#555")
    axR.set_xlim(0, 2100)
    axR.set_ylim(-0.7, 8.2)
    axR.set_title("the same events on the full ruler",
                  fontsize=10, fontweight="bold", color=PAL["ink"])
    axR.set_xlabel("exponent x  (1 in 10$^x$)", fontsize=8.5)
    axR.tick_params(labelsize=8.5)
    _style(axR)
    fig.tight_layout()
    fig.savefig(FIGS / "fig_scale2.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    fig_global_v3()
    fig_columns_v3()
    fig_scale_v3()
    fig_scale2()
