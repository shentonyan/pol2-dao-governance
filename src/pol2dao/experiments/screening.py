"""E4, E5, E8: the safety valve -- its operating point, its bias, and its timing.

E4  operating point   AUROC x false-flag rate of a synthetic judge -> who benefits
E5  judge bias        a judge that mistakes dissent for hostility
E8  dynamics          minority voice over the course of a deliberation
"""

from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path
from statistics import mean

from .. import simulate
from ..simulate import Scenario
from ._common import (BASELINE, COND, COND_COLOR, HOSTILE, INK, MUTED, PALETTE, cell, frange,
                      heat_labels, note, plt, save, seed, seq_cmap, style, write_csv)

STRAT = "strategic"


# ---------------------------------------------------------------------------
# E4 operating point of the judge
# ---------------------------------------------------------------------------

def e4_operating_point(out: Path, reps: int, log) -> list[Path]:
    aurocs = [0.70, 0.80, 0.886, 0.95, 0.99]   # 0.886 = median zero-shot AUROC in the survey
    ffr = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20]
    rows = []
    grids = {}
    for sc_name, sc in (("hostile", replace(HOSTILE, power_holders="majority")),
                        ("baseline", replace(BASELINE, power_holders="majority"))):
        ref = cell(sc, COND["pol2-no-screening"], reps, STRAT, key=("E4ref", sc_name))
        g = [[0.0] * len(ffr) for _ in aurocs]
        for i, a in enumerate(aurocs):
            for j, f in enumerate(ffr):
                fl = simulate.noisy_flagger(a, f, seed=seed("E4", a, f))
                r = cell(sc, COND["pol2"], reps, STRAT, fl, key=("E4", sc_name, a, f))
                g[i][j] = r["minority_win"] - ref["minority_win"]
                rows.append({"scenario": sc_name, "auroc": a, "false_flag_rate": f,
                             "minority_win": r["minority_win"], "no_screening": ref["minority_win"],
                             "gain": g[i][j], "hostile_miss_rate": r["hostile_miss_rate"],
                             "benign_flag_rate": r["benign_flag_rate"]})
            log(f"E4 {sc_name} auroc={a}")
        grids[sc_name] = g
    write_csv(rows, out, "e4_operating_point.csv")
    p = plt()
    from ._common import div_cmap

    fig, axes = p.subplots(1, 2, figsize=(9.5, 3.6))
    for ax, sc_name in zip(axes, ("hostile", "baseline")):
        g = grids[sc_name]
        ax.imshow(g, cmap=div_cmap(), vmin=-0.3, vmax=0.3, aspect="auto", origin="lower")
        heat_labels(ax, g, "{:+.2f}", 1.1, -0.3, 0.3)
        for t, row in zip(range(len(ax.texts)), [v for r_ in g for v in r_]):
            ax.texts[t].set_color("white" if abs(row) > 0.18 else INK)
        ax.set_xticks(range(len(ffr)), [f"{f:.0%}" for f in ffr], fontsize=7.5)
        ax.set_yticks(range(len(aurocs)), [f"{a:.3g}" for a in aurocs], fontsize=7.5)
        style(ax, f"{sc_name} scenario: gain from screening vs no screening",
              "judge AUROC" if sc_name == "hostile" else None, "false-flag rate on benign messages", grid="")
    note(fig, "Δ P(minority's option wins) = pol2 with a synthetic judge − pol2-no-screening; "
              f"strategic voters, power held by majority, {reps} pods per cell")
    fig.tight_layout()
    return [save(fig, out, "e4_judge_operating_point.png")]


# ---------------------------------------------------------------------------
# E5 judge bias against dissent
# ---------------------------------------------------------------------------

def e5_judge_bias(out: Path, reps: int, log) -> list[Path]:
    biases = frange(0, 2.5, 6)
    rows = []
    for sc_name, sc in (("hostile", replace(HOSTILE, power_holders="majority")),
                        ("baseline", replace(BASELINE, power_holders="majority"))):
        for b in biases:
            fl = simulate.noisy_flagger(0.886, 0.02, critic_bias=b, seed=seed("E5", b))
            r = cell(sc, COND["pol2"], reps, STRAT, fl, key=("E5", sc_name, b))
            rows.append({"scenario": sc_name, "critic_bias": b, "minority_win": r["minority_win"],
                         "regret": r["regret"], "critical_flag_rate": r["critical_flag_rate"],
                         "hostile_miss_rate": r["hostile_miss_rate"]})
        log(f"E5 {sc_name}")
    write_csv(rows, out, "e5_judge_bias.csv")
    p = plt()
    fig, axes = p.subplots(1, 2, figsize=(9, 3.4))
    for sc_name, col in (("hostile", PALETTE[1]), ("baseline", PALETTE[0])):
        rs = [r for r in rows if r["scenario"] == sc_name]
        axes[0].plot([r["critical_flag_rate"] for r in rs], [r["minority_win"] for r in rs],
                     color=col, lw=2, marker="o", ms=4, label=sc_name, zorder=2)
        for r in rs:
            axes[0].annotate(f"bias {r['critic_bias']:.1f}", (r["critical_flag_rate"], r["minority_win"]),
                             fontsize=6, color=MUTED, xytext=(3, 3), textcoords="offset points")
        axes[1].plot(biases, [r["regret"] for r in rs], color=col, lw=2, marker="o", ms=4, zorder=2)
    style(axes[0], "flagging dissent costs the minority the vote", "P(minority's option wins)",
          "share of the minority's critical messages that get flagged")
    style(axes[1], "equal-weight regret", "regret", "judge bias against critical messages (σ units)")
    axes[0].legend(frameon=False, fontsize=7.5)
    note(fig, "synthetic judge AUROC 0.886, 2 % false flags on neutral text; strategic voters, power held by majority")
    fig.tight_layout()
    return [save(fig, out, "e5_judge_bias.png")]


# ---------------------------------------------------------------------------
# E8 dynamics of voice
# ---------------------------------------------------------------------------

def e8_dynamics(out: Path, reps: int, log) -> list[Path]:
    sc = replace(HOSTILE, rounds=6, power_holders="majority")
    conds = ["ranked-20/80", "quadratic-equal", "pol2-free-talk", "pol2"]
    n = sc.n
    total = sc.rounds * n
    rows = []
    curves = {}
    fl = simulate.lexicon_flagger()
    for cname in conds:
        rng = random.Random(seed("E8", cname))
        acc = [0.0] * total
        for _ in range(reps):
            tr: list = []
            simulate.run_once(sc, COND[cname], STRAT, rng, fl, trace=tr)
            for i, m in enumerate(tr):
                acc[i] += m
        curves[cname] = [a / reps for a in acc]
        for rd in range(sc.rounds):
            seg = curves[cname][rd * n:(rd + 1) * n]
            rows.append({"condition": cname, "round": rd + 1, "minority_share": mean(seg)})
        log(f"E8 {cname}")
    write_csv(rows, out, "e8_dynamics.csv")
    p = plt()
    fig, ax = p.subplots(figsize=(9, 3.6))
    w = n  # one round
    for cname in conds:
        c = curves[cname]
        smooth = []
        for i in range(total):
            half = min(w // 2, i, total - 1 - i)   # symmetric window, so the edges are not biased
            smooth.append(mean(c[i - half:i + half + 1]))
        ax.plot(range(1, total + 1), smooth, color=COND_COLOR[cname], lw=2, label=cname, zorder=2)
    ax.axhline(sc.minority_frac, color=MUTED, lw=0.8, ls=":")
    ax.text(total, sc.minority_frac + 0.005, "fair share (20 %)", ha="right", fontsize=7, color=MUTED)
    for rd in range(1, sc.rounds):
        ax.axvline(rd * n + 0.5, color=MUTED, lw=0.5, ls="--")
    style(ax, "share of messages spoken by the minority, over the course of a deliberation",
          "minority share of messages (moving average, 1 round)", "message number (6 rounds × 25 people)")
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")
    note(fig, f"hostile scenario, power held by majority, strategic voters, {reps} pods per curve")
    fig.tight_layout()
    return [save(fig, out, "e8_voice_dynamics.png")]
