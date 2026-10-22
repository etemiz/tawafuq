"""Intro illustrations for the v5 article: dice-box thought experiment.

Run: .venv/bin/python tools/make_intro_dice_figs.py
Outputs:
  docs/articles/figs/intro_dice_3.png
  docs/articles/figs/intro_dice_4.png
  docs/articles/figs/intro_dice_mapping.png

The three figures answer the user's tracked-change requests in the article:
  (1) ten dice in a tall box, three ones in a vertical column;
  (2) the same, four ones in a vertical column;
  (3) a mapping of dice/box to words/page and the red one to God.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
from matplotlib.transforms import Affine2D

FIGS = Path(__file__).resolve().parent.parent / "docs" / "articles" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

PAPER = "#fffdf9"
INK = "#1b1b1b"
CRI = "#E4296B"
SOFT = "#e8e2d6"
NULL = "#8a857e"

PIPS = {
    1: [(0, 0)],
    2: [(-0.26, -0.26), (0.26, 0.26)],
    3: [(-0.26, -0.26), (0, 0), (0.26, 0.26)],
    4: [(-0.26, -0.26), (0.26, -0.26), (-0.26, 0.26), (0.26, 0.26)],
    5: [(-0.26, -0.26), (0.26, -0.26), (0, 0), (-0.26, 0.26), (0.26, 0.26)],
    6: [(-0.26, -0.27), (0.26, -0.27), (-0.26, 0), (0.26, 0),
        (-0.26, 0.27), (0.26, 0.27)],
}


def draw_die(ax, x, y, value, size=0.86, angle=0.0, one_color=CRI):
    tr = Affine2D().rotate_deg_around(x, y, angle) + ax.transData
    shadow = FancyBboxPatch(
        (x - size / 2, y - size / 2), size, size,
        boxstyle=f"round,pad=0,rounding_size={size * 0.16}",
        linewidth=0, facecolor=INK, alpha=0.10, zorder=2, transform=tr)
    ax.add_patch(shadow)
    face = FancyBboxPatch(
        (x - size / 2, y - size / 2), size, size,
        boxstyle=f"round,pad=0,rounding_size={size * 0.16}",
        linewidth=1.7, edgecolor=INK, facecolor=PAPER, zorder=3, transform=tr)
    ax.add_patch(face)
    pip_color = one_color if value == 1 else INK
    r = size * (0.105 if value == 1 else 0.082)
    for dx, dy in PIPS[value]:
        ax.add_patch(Circle((x + dx * size, y + dy * size), r,
                            facecolor=pip_color, edgecolor="none",
                            zorder=4, transform=tr))


def dice_box(ax, n_ones, seed_positions, box=(0.2, 0.2, 4.6, 9.6)):
    x0, y0, w, h = box
    ax.add_patch(FancyBboxPatch(
        (x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.18",
        linewidth=2.8, edgecolor=INK, facecolor=PAPER, zorder=1))
    ax.add_patch(FancyBboxPatch(
        (x0 + 0.12, y0 + 0.12), w - 0.24, h - 0.24,
        boxstyle="round,pad=0,rounding_size=0.14",
        linewidth=0.8, edgecolor=SOFT, facecolor="none", zorder=1))
    xs = 2.5
    ys = [2.1, 3.9, 5.7, 7.5][:n_ones]
    ax.plot([xs, xs], [ys[0] - 0.55, ys[-1] + 0.55], color=CRI,
            lw=1.1, ls=(0, (3, 4)), alpha=0.35, zorder=2)
    for y in ys:
        draw_die(ax, xs, y, 1)
    for (x, y, v, a) in seed_positions:
        draw_die(ax, x, y, v, angle=a)
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.axis("off")


def save(fig, name):
    fig.savefig(FIGS / name, dpi=220, facecolor=PAPER)
    plt.close(fig)
    print("wrote", FIGS / name)


def dice_three():
    fig, ax = plt.subplots(figsize=(3.7, 4.9))
    fig.patch.set_facecolor(PAPER)
    scatter = [
        (0.95, 8.9, 5, 12), (3.95, 9.0, 3, -8),
        (1.05, 7.3, 2, 17), (3.90, 7.1, 6, 9),
        (1.00, 5.0, 4, -14), (3.95, 3.1, 5, 7),
        (1.05, 1.3, 6, 11),
    ]
    dice_box(ax, 3, scatter)
    fig.subplots_adjust(0, 0, 1, 1)
    save(fig, "intro_dice_3.png")


def dice_four():
    fig, ax = plt.subplots(figsize=(3.7, 4.9))
    fig.patch.set_facecolor(PAPER)
    scatter = [
        (0.95, 9.0, 2, -10), (3.95, 8.8, 4, 13),
        (1.05, 7.4, 5, 8), (3.90, 4.1, 3, -15),
        (1.00, 2.3, 6, 10), (3.95, 1.2, 5, -7),
    ]
    dice_box(ax, 4, scatter)
    fig.subplots_adjust(0, 0, 1, 1)
    save(fig, "intro_dice_4.png")


def mapping():
    fig, ax = plt.subplots(figsize=(9.0, 4.9))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.4)
    ax.set_aspect("equal")
    ax.axis("off")

    # Left: the thought experiment.
    ax.add_patch(FancyBboxPatch(
        (0.35, 0.65), 3.2, 5.1, boxstyle="round,pad=0,rounding_size=0.16",
        linewidth=2.6, edgecolor=INK, facecolor=PAPER, zorder=1))
    aligned = [1.45, 2.85, 4.25]
    ax.plot([1.95, 1.95], [0.95, 4.75], color=CRI, lw=1.0,
            ls=(0, (3, 4)), alpha=0.35, zorder=2)
    for y in aligned:
        draw_die(ax, 1.95, y, 1, size=0.72)
    random_dice = [
        (0.95, 5.25, 4, 10), (2.95, 5.30, 2, -12),
        (0.95, 3.55, 3, -8), (2.95, 2.15, 5, 14),
        (0.95, 1.45, 6, 7), (0.95, 2.45, 2, -6),
        (2.95, 3.55, 6, 12),
    ]
    for x, y, v, a in random_dice:
        draw_die(ax, x, y, v, size=0.62, angle=a)
    ax.text(1.95, 0.18, "the experiment", ha="center", va="bottom",
            fontsize=11.5, color=INK, fontweight="bold")

    # Right: the mushaf page.
    px, py, pw, ph = 8.15, 0.45, 3.35, 5.55
    ax.add_patch(FancyBboxPatch(
        (px, py), pw, ph, boxstyle="round,pad=0,rounding_size=0.10",
        linewidth=2.2, edgecolor=INK, facecolor=PAPER, zorder=1))
    ax.add_patch(FancyBboxPatch(
        (px + 0.16, py + 0.16), pw - 0.32, ph - 0.32,
        boxstyle="round,pad=0,rounding_size=0.06",
        linewidth=0.8, edgecolor=SOFT, facecolor="none", zorder=1))
    line_y = [5.55 - 0.32 * i for i in range(15)]
    widths = [2.55, 2.80, 2.30, 2.85, 2.60, 2.90, 2.35, 2.80,
              2.55, 2.85, 2.40, 2.75, 2.65, 2.85, 2.10]
    for y, w in zip(line_y, widths):
        ax.add_patch(FancyBboxPatch(
            (px + 0.28, y - 0.035), w, 0.07,
            boxstyle="round,pad=0,rounding_size=0.03",
            linewidth=0, facecolor=SOFT, zorder=2))
    # crimson column: four Allah words on consecutive text lines
    col_y = [4.27, 3.63, 2.99, 2.35]
    for y in col_y:
        ax.add_patch(FancyBboxPatch(
            (px + 0.62, y - 0.085), 0.92, 0.17,
            boxstyle="round,pad=0,rounding_size=0.05",
            linewidth=0, facecolor=CRI, zorder=3))
        ax.text(px + 1.08, y, "Allah", ha="center", va="center",
                fontsize=7.2, color="white", zorder=4)
    ax.text(px + pw / 2, 0.18, "the page", ha="center", va="bottom",
            fontsize=11.5, color=INK, fontweight="bold")

    # Arrows and the three mappings.
    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4,
                                    shrinkA=0, shrinkB=0), zorder=5)

    def label(x, y, text, color=INK):
        ax.text(x, y, text, ha="center", va="center", fontsize=10.8,
                color=color, fontweight="bold", zorder=6,
                bbox=dict(boxstyle="round,pad=0.26", facecolor=PAPER,
                          edgecolor=SOFT, linewidth=0.8))

    arrow(3.60, 5.65, 8.10, 5.65)
    label(5.85, 5.98, "box = page")

    arrow(3.60, 2.15, 8.12, 2.15)
    label(5.85, 2.48, "dice = words", color=NULL)

    arrow(2.55, 4.25, 8.12, 4.27)
    label(5.35, 4.60, "red one = God", color=CRI)

    fig.subplots_adjust(0, 0, 1, 1)
    save(fig, "intro_dice_mapping.png")


if __name__ == "__main__":
    dice_three()
    dice_four()
    mapping()
