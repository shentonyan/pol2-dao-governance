"""Figures (optional: needs matplotlib, ``pip install -e .[plot]``)."""

from __future__ import annotations

from pathlib import Path

SERIES = {"sincere": "#2a78d6", "strategic": "#eb6834"}
EQUAL, ACTUAL = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _plt():
    import matplotlib
    import matplotlib.font_manager

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    installed = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
    cjk = [f for f in ("WenQuanYi Zen Hei", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei", "PingFang SC")
           if f in installed]
    plt.rcParams.update({
        "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
        "axes.spines.right": False,
        "font.family": ["DejaVu Sans", *cjk],
    })
    return plt


def simulation_figure(rows: list[dict], metric: str, path: str | Path, ylabel: str) -> Path:
    plt = _plt()
    panels = sorted({(r["scenario"], r["power_holders"]) for r in rows})
    conds = list(dict.fromkeys(r["condition"] for r in rows))
    fig, axes = plt.subplots(len(panels), 1, figsize=(8, 2.3 * len(panels)), sharex=True, sharey=True)
    axes = axes if len(panels) > 1 else [axes]
    width = 0.38
    for ax, (sc, h) in zip(axes, panels):
        for k, beh in enumerate(("sincere", "strategic")):
            vals = [next(r[metric] for r in rows if r["scenario"] == sc and r["power_holders"] == h
                         and r["behavior"] == beh and r["condition"] == c) for c in conds]
            xs = [i + (k - 0.5) * (width + 0.02) for i in range(len(conds))]
            ax.bar(xs, vals, width, color=SERIES[beh], label=beh, zorder=2)
        ax.set_title(f"scenario: {sc} · 20/80 power held by: {h}", loc="left", fontsize=9, color=INK)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color=GRID, zorder=0)
        ax.axvline(3.5, color=MUTED, lw=0.8, ls=":")
    axes[0].legend(title="voter behaviour", frameon=False, ncol=2, loc="upper left",
                   bbox_to_anchor=(0, 1.45))
    axes[-1].set_xticks(range(len(conds)), conds, rotation=20, ha="right")
    fig.text(0.99, 0.005, "left of dotted line: Sharma et al. conditions · right: PoL2 and ablations",
             ha="right", fontsize=7.5, color=MUTED)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def published_counterfactual_figure(tokens_csv: Path, means_csv: Path, path: str | Path) -> Path:
    """Ranked 20/80 conditions: actual token shares vs equal-budget shares."""
    import csv

    plt = _plt()
    tok = {(r["round"], r["cond"]): r for r in csv.DictReader(tokens_csv.open(encoding="utf-8"))}
    mea = {(r["round"], r["cond"]): r for r in csv.DictReader(means_csv.open(encoding="utf-8"))}
    keys = [("1", "ranked-early"), ("2", "ranked-early")]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
    for ax, key in zip(axes, keys):
        t = [float(tok[key][f"tokens_{i}"]) for i in range(1, 5)]
        a = [x / sum(t) for x in t]
        m = [float(mea[key][f"mean_r{i}"]) for i in range(1, 5)]
        e = [x / sum(m) for x in m]
        xs = range(4)
        ax.bar([x - 0.2 for x in xs], a, 0.38, color=ACTUAL, label="actual (20/80 budgets)", zorder=2)
        ax.bar([x + 0.2 for x in xs], e, 0.38, color=EQUAL, label="equal budgets, same split", zorder=2)
        for vals, off in ((a, -0.2), (e, 0.2)):
            j = max(range(4), key=lambda i: vals[i])
            ax.text(j + off, vals[j] + 0.01, "win", ha="center", fontsize=7.5, color=INK)
        ax.set_xticks(list(xs), ["opt 1", "opt 2", "opt 3", "opt 4"])
        ax.set_title(f"round {key[0]}, ranked voting, 20/80 power (n={tok[key]['n']})",
                     loc="left", fontsize=9, color=INK)
        ax.grid(axis="y", color=GRID, zorder=0)
    axes[0].set_ylabel("share of spent tokens")
    axes[1].legend(frameon=False, fontsize=8, loc="upper right")
    fig.text(0.99, 0.01, "Source: Sharma et al. (2026) Table 1 and token totals; see docs",
             ha="right", fontsize=7, color=MUTED)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
