"""E7: PAI-autonomous decision (PoLEn ch. 7 Art. 2) vs human voting."""

from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path
from statistics import mean

from ..autonomy import pai_decide, report
from ..metrics import normalized_regret
from ..simulate import Scenario, _allocation
from ..voting import Ballot, tally
from ._common import BASELINE, COND_COLOR, PALETTE, frange, note, plt, save, seed, style, write_csv


def _pod(sc: Scenario, rng: random.Random):
    n, k = sc.n, len(sc.majority_u)
    n_min = max(1, round(sc.minority_frac * n))
    base = [sc.minority_u if i < n_min else sc.majority_u for i in range(n)]
    return [[min(max(x + rng.gauss(0, sc.noise), 0.0), 1.0) for x in b] for b in base]


def e7_autonomy(out: Path, reps: int, log) -> list[Path]:
    strategic_share = frange(0, 1, 6)
    noise = 0.1
    sc = BASELINE
    k = len(sc.majority_u)
    min_fav = max(range(k), key=lambda j: sc.minority_u[j])
    rows = []
    methods = ["PAI raw sum", "PAI utilitarian", "PAI borda", "vote quadratic-equal", "vote ranked-equal"]
    for s in strategic_share:
        rng = random.Random(seed("E7", s))
        acc = {m: {"minority_win": 0.0, "regret": 0.0} for m in methods}
        for _ in range(reps):
            u = _pod(sc, rng)
            n = len(u)
            strat = [rng.random() < s for _ in range(n)]
            reps_ = [report(u[i], noise, rng, strat[i]) for i in range(n)]
            winners = {
                "PAI raw sum": pai_decide(reps_, "raw"),
                "PAI utilitarian": pai_decide(reps_, "utilitarian"),
                "PAI borda": pai_decide(reps_, "borda"),
            }
            for m, rule in (("vote quadratic-equal", "quadratic"), ("vote ranked-equal", "linear")):
                ballots = [Ballot(f"p{i}", _allocation(u[i], 100, rule, "strategic" if strat[i] else "sincere",
                                                       sc.temperature), 100) for i in range(n)]
                winners[m] = tally(ballots, rule).winner
            for m, w in winners.items():
                acc[m]["minority_win"] += w == min_fav
                acc[m]["regret"] += normalized_regret(u, w)
        for m in methods:
            rows.append({"strategic_share": s, "method": m,
                         "minority_win": acc[m]["minority_win"] / reps, "regret": acc[m]["regret"] / reps})
        log(f"E7 strategic share {s:.1f}")
    write_csv(rows, out, "e7_autonomy.csv")
    p = plt()
    fig, axes = p.subplots(1, 2, figsize=(9, 3.4))
    colors = {"PAI raw sum": PALETTE[7], "PAI utilitarian": PALETTE[6], "PAI borda": PALETTE[4],
              "vote quadratic-equal": COND_COLOR["quadratic-equal"], "vote ranked-equal": COND_COLOR["ranked-equal"]}
    for m in methods:
        rs = [r for r in rows if r["method"] == m]
        axes[0].plot(strategic_share, [r["minority_win"] for r in rs], color=colors[m], lw=2, marker="o", ms=4, label=m, zorder=2)
        axes[1].plot(strategic_share, [r["regret"] for r in rs], color=colors[m], lw=2, marker="o", ms=4, zorder=2)
    style(axes[0], "P(minority's option wins)", "probability", "share of people who exaggerate / vote strategically")
    axes[0].set_ylim(0, 1)
    style(axes[1], "equal-weight regret (true utilities)", "regret", "share of people who exaggerate / vote strategically")
    axes[0].legend(frameon=False, fontsize=7.5)
    note(fig, "PAI reads reported utilities (noise σ = 0.1) and decides without a vote; baseline scenario, equal power, "
              f"{reps} pods per point")
    fig.tight_layout()
    return [save(fig, out, "e7_pai_autonomy_vs_voting.png")]
