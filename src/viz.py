"""Chart helpers.

Every chart displays inline in the notebook AND saves a PNG to output/charts
for the deck. One source of truth, so a chart in the slides can never drift
from the notebook that produced it.
"""

from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from . import config

PALETTE = {
    "fd": "#1f4e79",       # food delivery
    "qc": "#c55a11",       # quick commerce
    "control": "#7f7f7f",  # Swiggy
    "accent": "#2e7d32",
    "muted": "#bdbdbd",
    "positive": "#2e7d32",  # net contribution above zero
    "negative": "#b03a2e",  # net contribution below zero
}

# Diverging map for the sensitivity grid. White sits at zero, so the sign
# change is the first thing the eye finds.
SIGN_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "net_cm", [PALETTE["negative"], "#ffffff", PALETTE["positive"]]
)


def apply_style() -> None:
    plt.rcParams.update({
        "figure.figsize": (9, 5),
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "-",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "legend.frameon": False,
    })


def save(fig, name: str):
    """Save to output/charts and return the path. Call before plt.show()."""
    config.ensure_dirs()
    path = config.CHARTS / f"{name}.png"
    fig.savefig(path)
    return path


def pct_axis(ax, axis: str = "y") -> None:
    fmt = mtick.PercentFormatter(xmax=1.0, decimals=0)
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def mark_event(ax, quarter_label: str, quarters: list[str], text: str) -> None:
    """Drop a labelled vertical line at a quarter on a categorical x-axis.

    Use for the Bistro launch, the Quick shutdown, the CEO transition. A chart
    with the event timeline overlaid does more argumentative work than the
    same chart with the dates in a caption.
    """
    if quarter_label not in quarters:
        return
    x = quarters.index(quarter_label)
    ax.axvline(x, color=PALETTE["muted"], linestyle="--", linewidth=1.2, zorder=0)
    ax.annotate(
        text,
        xy=(x, ax.get_ylim()[1]),
        xytext=(4, -12),
        textcoords="offset points",
        fontsize=9,
        color="#555555",
        rotation=90,
        va="top",
    )


def sensitivity_grid(grid, ax=None, unit: str = "₹"):
    """Render the central exhibit: net CM per Bistro order across the grid.

    Rows are CM_bistro cases, columns are cannibalisation rates. The colour
    scale is symmetric about zero so the sign change reads before any number
    does. If the whole grid is one colour, that is the headline.
    """
    values = grid.to_numpy(dtype=float)
    lim = float(max(abs(values.min()), abs(values.max())) or 1.0)
    norm = mcolors.TwoSlopeNorm(vmin=-lim, vcenter=0.0, vmax=lim)

    if ax is None:
        _, ax = plt.subplots(figsize=(1.6 * grid.shape[1] + 2, 0.9 * grid.shape[0] + 2))
    ax.imshow(values, cmap=SIGN_CMAP, norm=norm, aspect="auto")

    ax.set_xticks(range(grid.shape[1]), grid.columns, rotation=0)
    ax.set_yticks(range(grid.shape[0]), grid.index)
    ax.set_xticks([x - 0.5 for x in range(1, grid.shape[1])], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, grid.shape[0])], minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)

    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = values[i, j]
            label = f"{'-' if v < 0 else ''}{unit}{abs(v):,.0f}"
            ax.text(
                j, i, label,
                ha="center", va="center", fontsize=10,
                fontweight="bold" if v < 0 else "normal",
                color="#111111",
            )
    return ax


def caption(fig, text: str) -> None:
    """Source and caveat line under the chart. Required on anything that
    reaches the deck: an uncaptioned chart invites the question you least
    want to be asked."""
    fig.text(0, -0.04, text, fontsize=8, color="#666666", va="top", wrap=True)
