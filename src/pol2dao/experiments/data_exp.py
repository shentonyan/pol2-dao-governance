"""E11-E13: the published DAO data, the decision chain, and the literature map.

E11  published overview   token shares in all 8 round x condition cells, the
                          equal-budget counterfactual, and budget concentration
E12  decision chain       verification cost and tamper localisation
E13  literature map       PoL2-Jev survey papers per governance axis, and which
                          module of this repository answers to each axis
"""

from __future__ import annotations

import csv
import json
import time
from collections import Counter
from pathlib import Path

from ..ledger import DecisionChain
from ..metrics import gini, nakamoto
from ..replay import from_published
from ..voting import budgets
from ._common import INK, MUTED, PALETTE, note, plt, save, style, write_csv

ROOT = Path(__file__).resolve().parents[3]
OPTION_COLORS = PALETTE[:4]
OPTION_SHORT = ["1 current model", "2 more user info", "3 track preferences", "4 flags/tags"]


def e11_published(out: Path, reps: int, log) -> list[Path]:
    tok = list(csv.DictReader((ROOT / "data" / "sharma2026_token_totals.csv").open(encoding="utf-8")))
    mea = {(r["round"], r["cond"]): r for r in csv.DictReader((ROOT / "data" / "sharma2026_table1_means.csv").open(encoding="utf-8"))}
    cf = {(str(r["round"]), r["cond"]): r for r in from_published()}
    rows = []
    for r in tok:
        key = (r["round"], r["cond"])
        t = [float(r[f"tokens_{i}"]) for i in range(1, 5)]
        m = [float(mea[key][f"mean_r{i}"]) for i in range(1, 5)]
        n = int(r["n"])
        rows.append({"round": key[0], "cond": key[1], "n": n,
                     **{f"actual_share_{i + 1}": t[i] / sum(t) for i in range(4)},
                     **{f"equal_share_{i + 1}": m[i] / sum(m) for i in range(4)},
                     "actual_winner_by_tokens": max(range(4), key=lambda j: t[j]) + 1,
                     "actual_winner_by_rule": int(r["winner_by_rule"]),
                     "equal_budget_winner_linear": cf[key]["equal_budget_winner"] or "",
                     "budget_gini": gini(budgets(n, "20/80" if "early" in key[1] else "equal", holders=range(round(0.2 * n)))),
                     "budget_nakamoto": nakamoto(budgets(n, "20/80" if "early" in key[1] else "equal", holders=range(round(0.2 * n))))})
    write_csv(rows, out, "e11_published_overview.csv")
    log("E11 done")
    p = plt()
    fig, axes = p.subplots(2, 4, figsize=(12, 5.6), sharey=True)
    order = ["quadratic-equal", "quadratic-early", "ranked-equal", "ranked-early"]
    label = {"quadratic-equal": "quadratic · equal", "quadratic-early": "quadratic · 20/80",
             "ranked-equal": "ranked · equal", "ranked-early": "ranked · 20/80"}
    for i, rnd in enumerate(("1", "2")):
        for j, cond in enumerate(order):
            ax = axes[i][j]
            r = next(x for x in rows if x["round"] == rnd and x["cond"] == cond)
            a = [r[f"actual_share_{k + 1}"] for k in range(4)]
            e = [r[f"equal_share_{k + 1}"] for k in range(4)]
            xs = range(4)
            ax.bar([x - 0.2 for x in xs], a, 0.38, color=PALETTE[1], zorder=2, label="actual token shares")
            wa = r["actual_winner_by_rule"] - 1          # quadratic cells are decided by sqrt(tokens)
            ax.text(wa - 0.2, a[wa] + 0.01, "win", ha="center", fontsize=7, color=INK)
            if "early" in cond:
                ax.bar([x + 0.2 for x in xs], e, 0.38, color=PALETTE[0], zorder=2, label="equal budgets, same split")
                we = max(range(4), key=lambda k: e[k])
                ax.text(we + 0.2, e[we] + 0.01, "win" if cond.startswith("ranked") else "win?", ha="center", fontsize=7, color=INK)
            ax.set_xticks(list(xs), ["1", "2", "3", "4"], fontsize=8)
            style(ax, f"round {rnd} · {label[cond]} · n={r['n']}", "share of tokens" if j == 0 else None,
                  "option" if i == 1 else None)
            ax.set_ylim(0, 0.55)
    h, l = axes[0][3].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=8, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0))
    note(fig, "Sharma et al. (2026) Table 1 and token totals; 'win' uses each condition's own rule (quadratic: sqrt of tokens per person); "
              "'win?' = linear proxy, not exact for quadratic.\nOptions: 1 current model · 2 more user info · 3 track preferences · 4 flags/tags")
    fig.tight_layout(rect=(0, 0.035, 1, 0.96))
    return [save(fig, out, "e11_published_overview.png")]


def e12_ledger(out: Path, reps: int, log) -> list[Path]:
    sizes = [10, 100, 1_000, 10_000]
    rows = []
    for n in sizes:
        chain = DecisionChain()
        t0 = time.perf_counter()
        for i in range(n):
            chain.append("ballot", {"voter": f"p{i}", "tokens": [i % 7, 3, 0, 1], "budget": 100})
        t_append = time.perf_counter() - t0
        t0 = time.perf_counter()
        ok, _ = chain.verify()
        t_verify = time.perf_counter() - t0
        path = chain.to_jsonl(out / "tables" / "_tmp_chain.jsonl")
        size = path.stat().st_size
        path.unlink()
        rows.append({"entries": n, "append_ms": t_append * 1e3, "verify_ms": t_verify * 1e3,
                     "bytes_per_entry": size / n, "intact": ok})
        log(f"E12 n={n} verify {t_verify * 1e3:.1f} ms")
    # tamper localisation: edit entry i of a 200-entry chain, see where verify stops
    chain = DecisionChain()
    for i in range(200):
        chain.append("message", {"speaker": f"p{i % 5}", "text": f"msg {i}"})
    detected = []
    for i in range(0, 200, 10):
        entries = [json.loads(json.dumps(e.to_dict())) for e in chain]
        entries[i]["payload"]["text"] = "edited"
        from ..ledger import Entry

        c2 = DecisionChain()
        c2._entries = [Entry(**e) for e in entries]
        ok, bad = c2.verify()
        detected.append({"edited_index": i, "detected_at": bad, "intact": ok})
    write_csv(rows, out, "e12_ledger_performance.csv")
    write_csv(detected, out, "e12_ledger_tamper.csv")
    p = plt()
    fig, axes = p.subplots(1, 2, figsize=(9, 3.4))
    axes[0].plot(sizes, [r["verify_ms"] for r in rows], color=PALETTE[0], lw=2, marker="o", ms=5, label="verify", zorder=2)
    axes[0].plot(sizes, [r["append_ms"] for r in rows], color=PALETTE[1], lw=2, marker="o", ms=5, label="append", zorder=2)
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].legend(frameon=False, fontsize=7.5)
    style(axes[0], f"cost of the decision chain (≈{rows[-1]['bytes_per_entry']:.0f} bytes per entry)", "milliseconds (log)", "entries (log)")
    axes[1].scatter([d["edited_index"] for d in detected], [d["detected_at"] for d in detected], color=PALETTE[0], s=18, zorder=2)
    axes[1].plot([0, 200], [0, 200], color=MUTED, lw=0.8, ls=":")
    style(axes[1], "editing entry i is detected exactly at entry i", "index reported by verify()", "index of the edited entry")
    note(fig, "SHA-256 hash chain, pure Python; times on this machine, single run")
    fig.tight_layout()
    return [save(fig, out, "e12_decision_chain.png")]


AXIS_TO_MODULE = {
    "G1": "eap.py (judge)", "G2": "eap.py + protocol (escalate)", "G3": "eap.py (criticism ≠ hate)",
    "G4": "eap.py (absence, fit_threshold)", "G5": "ledger.py + protocol (decision record)",
    "G6": "protocol.py (question / explain / escalate)", "G7": "simulate.py + autonomy.py",
}


def e13_literature(out: Path, reps: int, log) -> list[Path]:
    papers = list(csv.DictReader((ROOT / "data" / "external" / "pol2_survey_papers.csv").open(encoding="utf-8")))
    axes_def = json.loads((ROOT / "data" / "external" / "pol2_axes.json").open(encoding="utf-8").read())["axes"]
    tiers = ["核心", "相关", "背景"]
    counts = {a: Counter() for a in axes_def}
    for pr in papers:
        for a in pr["pol_axes"].split():
            if a in counts:
                counts[a][pr["tier"]] += 1
    rows = [{"axis": a, "name_zh": axes_def[a]["name_zh"], **{t: counts[a][t] for t in tiers},
             "total": sum(counts[a].values()), "module_here": AXIS_TO_MODULE[a],
             "pol2_refs": "; ".join(axes_def[a]["pol2_refs"])} for a in axes_def]
    write_csv(rows, out, "e13_literature_map.csv")
    log("E13 done")
    p = plt()
    fig, ax = p.subplots(figsize=(9, 3.8))
    ys = list(range(len(rows)))[::-1]
    left = [0] * len(rows)
    for t, col in zip(tiers, (PALETTE[0], PALETTE[2], PALETTE[3])):
        vals = [r[t] for r in rows]
        ax.barh(ys, vals, 0.6, left=left, color=col, label=t, zorder=2)
        left = [l + v for l, v in zip(left, vals)]
    for y, r, tot in zip(ys, rows, left):
        ax.text(-0.15, y, f"{r['axis']} {r['name_zh']}", ha="right", va="center", fontsize=8, color=INK)
        ax.text(tot + 0.15, y, f"→ {r['module_here']}", va="center", fontsize=7, color=MUTED)
    ax.set_yticks([])
    ax.set_xlim(0, 11)
    ax.legend(frameon=False, fontsize=7.5, title="tier", loc="lower right")
    style(ax, f"PoL2-Jev literature survey: {len(papers)} papers by governance axis, and the module here that answers to it",
          xlabel="papers (one paper can sit on several axes)", grid="x")
    note(fig, "source: NaturalDAO/PoL-Governance/research/PoL2-Jev-Typed-Literature-Survey (CC0)")
    fig.tight_layout()
    return [save(fig, out, "e13_literature_map.png")]
