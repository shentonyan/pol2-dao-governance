"""E0-E3, E6: which mechanism does what, and when.

E0  decomposition   ranked-20/80 -> pol2, one mechanism at a time
E1  sensitivity     intimidation x hate rate, persuasion x hate rate (heatmaps)
E2  intensity       how strong must the minority's preference be for each rule?
E3  scale           pod size and minority share
E6  sybil           fake identities under linear vs quadratic voting
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ..simulate import CONDITIONS, Condition, Scenario
from ._common import (BASELINE, COND, COND_COLOR, HOSTILE, INK, MUTED, PALETTE, cell, div_cmap,
                      frange, heat_labels, note, plt, save, seq_cmap, style, write_csv)

STRAT = "strategic"


# ---------------------------------------------------------------------------
# E0 decomposition
# ---------------------------------------------------------------------------

STEPS = [
    ("ranked · 20/80\nfree talk", Condition("s0", "linear", "20/80")),
    ("+ equal power", Condition("s1", "linear", "equal")),
    ("+ quadratic", Condition("s2", "quadratic", "equal")),
    ("+ turn-taking", Condition("s3", "quadratic", "equal", "round_robin")),
    ("+ EAP screening\n(= pol2)", Condition("s4", "quadratic", "equal", "round_robin", True)),
]


def e0_decomposition(out: Path, reps: int, log) -> list[Path]:
    rows = []
    for sc_name, sc in (("baseline", replace(BASELINE, power_holders="majority")),
                        ("hostile", replace(HOSTILE, power_holders="majority"))):
        for label, cond in STEPS:
            c = cell(sc, cond, reps, STRAT, key=("E0", sc_name))
            rows.append({"scenario": sc_name, "step": label.replace("\n", " "),
                         "minority_win": c["minority_win"], "regret": c["regret"],
                         "minority_voice_share": c["minority_voice_share"]})
    write_csv(rows, out, "e0_decomposition.csv")
    log("E0 done")
    p = plt()
    fig, axes = p.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, sc_name in zip(axes, ("baseline", "hostile")):
        vals = [r["minority_win"] for r in rows if r["scenario"] == sc_name]
        xs = range(len(vals))
        prev = 0.0
        for i, v in enumerate(vals):
            if i == 0:
                ax.bar(i, v, 0.6, color=PALETTE[3], zorder=2)
            else:
                d = v - prev
                ax.bar(i, d, 0.6, bottom=prev, color=PALETTE[0] if d >= 0 else PALETTE[1], zorder=2)
                ax.plot([i - 1 + 0.3, i - 0.3], [prev, prev], color=MUTED, lw=0.8)
                ax.text(i, max(v, prev) + 0.02, f"{d:+.2f}", ha="center", fontsize=7.5, color=INK)
            prev = v
        ax.plot(len(vals) - 1, prev, marker="o", color=PALETTE[6], ms=7, zorder=3)
        ax.set_xticks(list(xs), [s[0] for s in STEPS], fontsize=7.5)
        style(ax, f"{sc_name} scenario · power held by majority · strategic voters",
              "P(minority's option wins)" if sc_name == "baseline" else None)
        ax.set_ylim(0, 1)
    note(fig, "each step adds one PoL2 mechanism on top of the previous; blue = gain, orange = loss")
    fig.tight_layout()
    return [save(fig, out, "e0_mechanism_decomposition.png")]


# ---------------------------------------------------------------------------
# E1 sensitivity heatmaps
# ---------------------------------------------------------------------------

def e1_sensitivity(out: Path, reps: int, log) -> list[Path]:
    hate = frange(0, 0.6, 7)
    intim = frange(0, 1, 6)
    pers = frange(0, 0.6, 6)
    rows = []
    grids = {}
    for name, param, values in (("intimidation", "intimidation", intim), ("persuasion", "persuasion", pers)):
        g = {c: [[0.0] * len(hate) for _ in values] for c in ("quadratic-equal", "pol2")}
        for i, v in enumerate(values):
            for j, h in enumerate(hate):
                sc = replace(BASELINE, hate_rate=h, **{param: v}, power_holders="majority")
                for cname in g:
                    r = cell(sc, COND[cname], reps, STRAT, key=("E1", name, i, j))
                    g[cname][i][j] = r["minority_win"]
                    rows.append({"param": param, "value": v, "hate_rate": h, "condition": cname,
                                 "minority_win": r["minority_win"], "regret": r["regret"]})
            log(f"E1 {name} row {i + 1}/{len(values)}")
        grids[name] = g
    write_csv(rows, out, "e1_sensitivity.csv")
    p = plt()
    fig, axes = p.subplots(2, 3, figsize=(11, 6.2))
    for r_, (name, values) in enumerate((("intimidation", intim), ("persuasion", pers))):
        g = grids[name]
        diff = [[g["pol2"][i][j] - g["quadratic-equal"][i][j] for j in range(len(hate))]
                for i in range(len(values))]
        for c_, (title, data, cmap, vmin, vmax) in enumerate((
                ("quadratic-equal (Sharma condition)", g["quadratic-equal"], seq_cmap(), 0, 1),
                ("pol2", g["pol2"], seq_cmap(), 0, 1),
                ("pol2 − quadratic-equal", diff, div_cmap(), -0.5, 0.5))):
            ax = axes[r_][c_]
            ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", origin="lower")
            heat_labels(ax, data, "{:+.2f}" if c_ == 2 else "{:.2f}", 0.75 if c_ < 2 else 1.1, vmin, vmax)
            if c_ == 2:
                for i, row in enumerate(data):
                    for j, v in enumerate(row):
                        ax.texts[i * len(hate) + j].set_color("white" if abs(v) > 0.3 else INK)
            ax.set_xticks(range(len(hate)), [f"{h:.1f}" for h in hate], fontsize=7.5)
            ax.set_yticks(range(len(values)), [f"{v:.1f}" for v in values], fontsize=7.5)
            style(ax, title, name if c_ == 0 else None, "hate rate (share of majority messages)" if r_ == 1 else None, grid="")
    note(fig, "P(minority's option wins), strategic voters, power held by majority; each cell = "
              f"{reps} pods")
    fig.tight_layout()
    return [save(fig, out, "e1_sensitivity_heatmaps.png")]


# ---------------------------------------------------------------------------
# E2 preference intensity
# ---------------------------------------------------------------------------

def e2_intensity(out: Path, reps: int, log) -> list[Path]:
    """Scale the minority's intensity: minority_u = (0, 0, s, 0.2 s), s in [0.3, 1]."""
    scales = frange(0.3, 1.0, 8)
    conds = ["ranked-equal", "quadratic-equal", "pol2"]
    rows = []
    for s in scales:
        sc = replace(HOSTILE, minority_u=(0.0, 0.0, s, 0.2 * s), power_holders="majority")
        for cname in conds:
            for beh in ("sincere", "strategic"):
                r = cell(sc, COND[cname], reps, beh, key=("E2", s, beh))
                rows.append({"intensity": s, "condition": cname, "behavior": beh,
                             "minority_win": r["minority_win"], "optimum_hit": r["optimum_hit"],
                             "optimum_is_minority_fav": r["optimum_is_minority_fav"],
                             "regret": r["regret"]})
        log(f"E2 intensity {s:.2f}")
    write_csv(rows, out, "e2_intensity.csv")
    p = plt()
    fig, axes = p.subplots(1, 3, figsize=(11, 3.4))
    for ax, (beh, metric, title) in zip(axes, (
            ("strategic", "minority_win", "strategic · P(minority's option wins)"),
            ("strategic", "regret", "strategic · equal-weight regret"),
            ("sincere", "minority_win", "sincere · P(minority's option wins)"))):
        for cname in conds:
            ys = [r[metric] for r in rows if r["condition"] == cname and r["behavior"] == beh]
            ax.plot(scales, ys, color=COND_COLOR[cname], lw=2, marker="o", ms=4, label=cname, zorder=2)
        opt = [r["optimum_is_minority_fav"] for r in rows if r["condition"] == conds[0] and r["behavior"] == beh]
        first = next((s for s, o in zip(scales, opt) if o > 0.5), None)
        if first is not None:
            ax.axvline(first, color=MUTED, lw=0.8, ls=":")
            ax.annotate(" from here on the minority's option\n is also the equal-weight optimum",
                        xy=(first, 0.02), xycoords=("data", "axes fraction"), fontsize=6.5, color=MUTED, va="bottom")
        style(ax, title, xlabel="minority preference intensity s")
    axes[0].legend(frameon=False, fontsize=7.5)
    note(fig, "minority_u = (0, 0, s, 0.2 s); hostile scenario (hate rate 0.3), power held by majority; " f"{reps} pods per point")
    fig.tight_layout()
    return [save(fig, out, "e2_preference_intensity.png")]


# ---------------------------------------------------------------------------
# E3 scale
# ---------------------------------------------------------------------------

def e3_scale(out: Path, reps: int, log) -> list[Path]:
    sizes = [10, 15, 25, 40, 60, 100]
    fracs = [0.1, 0.2, 0.3, 0.4]
    conds = ["ranked-20/80", "quadratic-equal", "pol2"]
    rows = []
    for n in sizes:
        for cname in conds:
            r = cell(replace(HOSTILE, n=n, power_holders="majority"), COND[cname], reps, STRAT, key=("E3n", n))
            rows.append({"sweep": "n", "value": n, "condition": cname, **{k: r[k] for k in
                         ("minority_win", "regret", "minority_voice_share", "nakamoto", "influence_gini")}})
        log(f"E3 n={n}")
    for f in fracs:
        for cname in conds:
            r = cell(replace(HOSTILE, minority_frac=f, power_holders="majority"), COND[cname], reps, STRAT, key=("E3f", f))
            rows.append({"sweep": "minority_frac", "value": f, "condition": cname, **{k: r[k] for k in
                         ("minority_win", "regret", "minority_voice_share", "nakamoto", "influence_gini")}})
    write_csv(rows, out, "e3_scale.csv")
    p = plt()
    fig, axes = p.subplots(1, 3, figsize=(11, 3.4))
    for cname in conds:
        ys = [r["minority_win"] for r in rows if r["sweep"] == "n" and r["condition"] == cname]
        axes[0].plot(sizes, ys, color=COND_COLOR[cname], lw=2, marker="o", ms=4, label=cname, zorder=2)
        ys = [r["nakamoto"] / n for r, n in zip([r for r in rows if r["sweep"] == "n" and r["condition"] == cname], sizes)]
        axes[1].plot(sizes, ys, color=COND_COLOR[cname], lw=2, marker="o", ms=4, zorder=2)
        ys = [r["minority_win"] for r in rows if r["sweep"] == "minority_frac" and r["condition"] == cname]
        axes[2].plot(fracs, ys, color=COND_COLOR[cname], lw=2, marker="o", ms=4, zorder=2)
    axes[0].set_xscale("log")
    axes[1].set_xscale("log")
    axes[0].set_xticks(sizes, sizes)
    axes[1].set_xticks(sizes, sizes)
    style(axes[0], "pod size", "P(minority's option wins)", "n (log scale)")
    style(axes[1], "how many people it takes to control >50 % of votes", "Nakamoto coefficient / n", "n (log scale)")
    style(axes[2], "minority share (n = 25)", "P(minority's option wins)", "minority share of the pod")
    axes[0].legend(frameon=False, fontsize=7.5)
    note(fig, "hostile scenario, power held by majority, strategic voters; " f"{reps} pods per point")
    fig.tight_layout()
    return [save(fig, out, "e3_scale.png")]


# ---------------------------------------------------------------------------
# E6 sybil attack
# ---------------------------------------------------------------------------

def e6_sybil(out: Path, reps: int, log) -> list[Path]:
    ids = [1, 2, 3, 5, 8]
    attackers = [1, 3, 5]
    rows = []
    for mode in ("split", "fresh"):
        for a in attackers:
            for s in ids:
                sc = replace(BASELINE, sybil_attackers=a, sybil_ids=s, sybil_mode=mode)
                for cname in ("ranked-equal", "quadratic-equal"):
                    r = cell(sc, COND[cname], reps, STRAT, key=("E6", mode, a, s))
                    rows.append({"mode": mode, "attackers": a, "ids_per_attacker": s, "condition": cname,
                                 "minority_win": r["minority_win"], "majority_win": r["majority_win"],
                                 "influence_gini": r["influence_gini"], "nakamoto": r["nakamoto"]})
            log(f"E6 {mode} attackers={a}")
    write_csv(rows, out, "e6_sybil.csv")
    p = plt()
    fig, axes = p.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, mode in zip(axes, ("split", "fresh")):
        for k, a in enumerate(attackers):
            for cname, ls in (("ranked-equal", "-"), ("quadratic-equal", "--")):
                ys = [r["minority_win"] for r in rows if r["mode"] == mode and r["attackers"] == a
                      and r["condition"] == cname]
                ax.plot(ids, ys, color=PALETTE[k], ls=ls, lw=2, marker="o", ms=4, zorder=2,
                        label=f"{cname}, {a} attacker{'s' if a > 1 else ''}")
        ax.set_xticks(ids, ids)
        style(ax, {"split": "split: one budget spread over s identities",
                   "fresh": "fresh: every identity gets a full budget"}[mode],
              "P(minority's option wins)" if mode == "split" else None, "identities per attacker (s)")
    axes[0].legend(frameon=False, fontsize=6.5, ncol=2)
    note(fig, "baseline scenario, equal power, strategic voters; attackers are majority members; "
              f"{reps} pods per point")
    fig.tight_layout()
    return [save(fig, out, "e6_sybil_attack.png")]
