"""Shared helpers for the experiment modules: output, colours, plotting."""

from __future__ import annotations

import csv
import random
import zlib
from pathlib import Path
from statistics import mean
from typing import Callable, Iterable, Sequence

from .. import simulate
from ..simulate import Condition, Scenario

# Reference categorical palette (validated for adjacent-pair CVD separation).
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

# Fixed colour per condition so the same condition looks the same in every figure.
COND = {c.name: c for c in simulate.CONDITIONS}
COND_COLOR = {
    "quadratic-equal": PALETTE[0], "quadratic-20/80": PALETTE[1], "ranked-equal": PALETTE[2],
    "ranked-20/80": PALETTE[3], "pol2": PALETTE[6], "pol2-no-screening": PALETTE[4],
    "pol2-free-talk": PALETTE[5],
}
HOSTILE = Scenario("hostile", hate_rate=0.3)
BASELINE = Scenario("baseline")


def seed(*parts: object) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


def cell(sc: Scenario, cond: Condition, reps: int, behavior: str = "strategic",
         flagger=None, key: Sequence[object] = ()) -> dict:
    """Mean of every metric over ``reps`` pods (common random numbers via ``key``)."""
    rng = random.Random(seed(*key) if key else seed(sc, behavior))
    flagger = flagger or _LEX
    runs = [simulate.run_once(sc, cond, behavior, rng, flagger) for _ in range(reps)]
    out = {k: mean(r[k] for r in runs) for k in runs[0]}
    for num, den, name in (("hostile_missed", "hostile_msgs", "hostile_miss_rate"),
                           ("benign_flagged", "benign_msgs", "benign_flag_rate"),
                           ("critical_flagged", "critical_msgs", "critical_flag_rate")):
        d = sum(r[den] for r in runs)
        out[name] = sum(r[num] for r in runs) / d if d else float("nan")
    return out


_LEX = simulate.lexicon_flagger()


def write_csv(rows: list[dict], out: Path, name: str) -> Path:
    path = out / "tables" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
    return path


def have_mpl() -> bool:
    import importlib.util

    return importlib.util.find_spec("matplotlib") is not None


def plt():
    from ..figures import _plt

    return _plt()


def save(fig, out: Path, name: str) -> Path:
    path = out / "figures" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    import matplotlib.pyplot as _p

    _p.close(fig)
    return path


def style(ax, title: str | None = None, ylabel: str | None = None, xlabel: str | None = None,
          grid: str = "y") -> None:
    if title:
        ax.set_title(title, loc="left", fontsize=9.5, color=INK)
    if ylabel:
        ax.set_ylabel(ylabel)
    if xlabel:
        ax.set_xlabel(xlabel)
    if grid:
        ax.grid(axis=grid, color=GRID, zorder=0, lw=0.8)
    ax.set_facecolor(SURFACE)


def note(fig, text: str) -> None:
    fig.text(0.995, 0.005, text, ha="right", va="bottom", fontsize=7, color=MUTED)


def seq_cmap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list("seq_blue", ["#f4f7fc", "#9cc0ec", "#2a78d6", "#0d3a73"])


def div_cmap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list("div", ["#a8431b", "#eb6834", "#f2f1ee", "#2a78d6", "#0d3a73"])


def heat_labels(ax, data, fmt="{:.2f}", threshold=0.6, vmin=0.0, vmax=1.0) -> None:
    for i, row in enumerate(data):
        for j, v in enumerate(row):
            frac = (v - vmin) / (vmax - vmin) if vmax > vmin else 0
            ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=6.5,
                    color="white" if frac > threshold else INK)


def frange(a: float, b: float, n: int) -> list[float]:
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def progress(name: str) -> Callable[[str], None]:
    def log(msg: str) -> None:
        print(f"[{name}] {msg}", flush=True)

    return log


__all__ = ["PALETTE", "INK", "MUTED", "GRID", "COND", "COND_COLOR", "HOSTILE", "BASELINE", "cell",
           "write_csv", "have_mpl", "plt", "save", "style", "note", "seq_cmap", "div_cmap",
           "heat_labels", "frange", "seed", "progress", "Iterable"]
