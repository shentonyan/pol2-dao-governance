"""E9, E10: evaluate the EAP baseline judges on labelled text.

E9   NaturalDAO PoL-Governance pilot (20 public cases, CC0). Their status
     labels (violating / conforming / insufficient) are the proposers' own,
     unreviewed, and cover behaviours far wider than hate language (honesty,
     consent, tool actions). We ask: does a *lexical* hate-language judge flag
     the violating cases? v0 was written before reading the pilot (blind);
     v1 adds PoL2-anchored categories written after reading it (not blind).
E10  Bilingual stress corpus (96 sentences, 16 categories, this repository,
     written before v1): where the lexicon baselines fail and how the flag
     threshold trades off.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from ..eap import LexiconJudge, Route, ScreeningPolicy, fit_threshold
from ._common import INK, MUTED, PALETTE, note, plt, save, style, write_csv

ROOT = Path(__file__).resolve().parents[3]
STATUS_COLOR = {"violating": PALETTE[1], "conforming": PALETTE[0], "insufficient": PALETTE[3]}
JUDGES = {"v0 (blind)": LexiconJudge(), "v1 (after reading the pilot)": LexiconJudge.v1()}


def _recall_fp(rows, key):
    viol = [r for r in rows if r["status"] == "violating"]
    nonv = [r for r in rows if r["status"] != "violating"]
    return (sum(r[key] == "flag" for r in viol) / len(viol), sum(r[key] == "flag" for r in nonv) / len(nonv))


def e9_pilot(out: Path, reps: int, log) -> list[Path]:
    path = ROOT / "data" / "external" / "pol_governance_pilot.jsonl"
    rows_in = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    policy = ScreeningPolicy()
    rows = []
    for r in rows_in:
        text = r["input"]["target"]
        row = {"id": r["id"], "family": r["family_id"], "surface": r["input"]["surface"],
               "status": r["proposal"]["status"], "issues": " ".join(r["proposal"]["issues"])}
        for tag, judge in (("v0", JUDGES["v0 (blind)"]), ("v1", JUDGES["v1 (after reading the pilot)"])):
            d = judge.judge(text)
            row[f"p_hate_{tag}"] = d.p_hate
            row[f"route_{tag}"] = policy.route(d).value
            row[f"evidence_{tag}"] = " ".join(d.evidence)
        rows.append(row)
    write_csv(rows, out, "e9_pilot_benchmark.csv")
    stats = {tag: _recall_fp(rows, f"route_{tag}") for tag in ("v0", "v1")}
    log(f"E9 v0 recall {stats['v0'][0]:.2f} fp {stats['v0'][1]:.2f}; v1 recall {stats['v1'][0]:.2f} fp {stats['v1'][1]:.2f}")

    p = plt()
    fig, ax = p.subplots(figsize=(9.5, 5.6))
    ys = list(range(len(rows)))[::-1]
    for y, r in zip(ys, rows):
        c = STATUS_COLOR[r["status"]]
        ax.plot([r["p_hate_v0"], r["p_hate_v1"]], [y, y], color=c, lw=1.2, zorder=2)
        ax.scatter(r["p_hate_v0"], y, marker="o", s=28, facecolor="white", edgecolor=c, lw=1.5, zorder=3)
        ax.scatter(r["p_hate_v1"], y, marker="o", s=28, color=c, zorder=3)
        ax.text(-0.02, y, f"{r['id']} {r['family']} · {r['issues'] or '—'}", va="center", ha="right", fontsize=7, color=INK)
        ax.text(1.02, y, f"{r['route_v0']} → {r['route_v1']}", va="center", fontsize=7, color=MUTED)
    ax.axvline(policy.review_threshold, color=MUTED, lw=0.8, ls=":")
    ax.axvline(policy.flag_threshold, color=MUTED, lw=0.8, ls="--")
    ax.text(policy.flag_threshold, len(rows) - 0.4, " flag ≥ 0.6", fontsize=7, color=MUTED)
    ax.text(policy.review_threshold, len(rows) - 0.4, " review ≥ 0.3", fontsize=7, color=MUTED)
    ax.set_yticks([])
    ax.set_xlim(-0.02, 1.3)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    for s_, c in STATUS_COLOR.items():
        ax.scatter([], [], color=c, label=f"proposed status: {s_}")
    ax.scatter([], [], facecolor="white", edgecolor=INK, label="v0 (blind)")
    ax.scatter([], [], color=INK, label="v1 (after reading the pilot)")
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=7.5, loc="lower center", ncol=5, bbox_to_anchor=(0.5, 0.03))
    ax.set_title("NaturalDAO PoL-Governance pilot (20 cases)\nrecall on 'violating': "
                 f"v0 {stats['v0'][0]:.0%} → v1 {stats['v1'][0]:.0%} · false flags on the rest: "
                 f"v0 {stats['v0'][1]:.0%} → v1 {stats['v1'][1]:.0%}", loc="center", fontsize=9.5, color=INK)
    style(ax, None,
          xlabel="p(hate) from the lexicon baseline", grid="x")
    note(fig, "labels are the proposers' own and unreviewed (CC0); most 'violating' cases are dishonesty, consent or tool "
              "actions, which a hate-language lexicon cannot see")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return [save(fig, out, "e9_pilot_benchmark.png")]


def e10_stress(out: Path, reps: int, log) -> list[Path]:
    path = ROOT / "data" / "eap_stress_corpus.csv"
    corpus = list(csv.DictReader(path.open(encoding="utf-8")))
    policy = ScreeningPolicy()
    rows = []
    for r in corpus:
        row = dict(r)
        for tag, judge in (("v0", JUDGES["v0 (blind)"]), ("v1", JUDGES["v1 (after reading the pilot)"])):
            d = judge.judge(r["text"])
            route = policy.route(d)
            row[f"p_hate_{tag}"] = d.p_hate
            row[f"route_{tag}"] = route.value
            row[f"evidence_{tag}"] = " ".join(d.evidence)
            row[f"correct_{tag}"] = (route is Route.FLAG) == (r["expected"] == "flag")
        rows.append(row)
    write_csv(rows, out, "e10_stress_corpus.csv")
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[(r["category"], r["expected"], r["hard_case"])].append(r)
    summary = []
    for (cat, exp, hard), rs in by_cat.items():
        summary.append({"category": cat, "expected": exp, "hard_case": hard, "n": len(rs),
                        "accuracy_v0": sum(r["correct_v0"] for r in rs) / len(rs),
                        "accuracy_v1": sum(r["correct_v1"] for r in rs) / len(rs),
                        "accuracy_zh_v0": sum(r["correct_v0"] for r in rs if r["lang"] == "zh") / 3,
                        "accuracy_en_v0": sum(r["correct_v0"] for r in rs if r["lang"] == "en") / 3})
    write_csv(summary, out, "e10_stress_summary.csv")
    scores = [r["p_hate_v0"] for r in rows]
    labels = [r["expected"] == "flag" for r in rows]
    t_all, f1_all = fit_threshold(scores, labels)
    overall = {tag: sum(r[f"correct_{tag}"] for r in rows) / len(rows) for tag in ("v0", "v1")}
    log(f"E10 accuracy v0 {overall['v0']:.2f} v1 {overall['v1']:.2f}; fitted threshold {t_all:.2f} (F1 {f1_all:.2f})")

    p = plt()
    fig, axes = p.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    order = sorted(summary, key=lambda s: (s["hard_case"], s["expected"], -s["accuracy_v0"]))
    ys = list(range(len(order)))[::-1]
    for y, s_ in zip(ys, order):
        ax.barh(y + 0.18, s_["accuracy_zh_v0"], 0.34, color=PALETTE[0], zorder=2)
        ax.barh(y - 0.18, s_["accuracy_en_v0"], 0.34, color=PALETTE[1], zorder=2)
        if s_["accuracy_v1"] != s_["accuracy_v0"]:
            ax.scatter(s_["accuracy_v1"], y, marker="D", s=22, color=INK, zorder=3)
        lab = f"{s_['category']} ({'flag' if s_['expected'] == 'flag' else 'pass'})"
        ax.text(-0.02, y, lab + (" ★" if s_["hard_case"] == "1" else ""), ha="right", va="center", fontsize=7.5, color=INK)
    ax.barh(-5, 0, color=PALETTE[0], label="v0 · 中文")
    ax.barh(-5, 0, color=PALETTE[1], label="v0 · English")
    ax.scatter([], [], marker="D", s=22, color=INK, label="v1 (both languages), where it differs")
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.set_yticks([])
    ax.set_xlim(0, 1)
    n_easy = sum(s_["hard_case"] == "0" for s_ in order)
    ax.axhline(len(order) - n_easy - 0.5, color=MUTED, lw=0.8, ls=":")
    ax.text(0.5, len(order) - n_easy - 0.5, "★ hard cases below", fontsize=7, color=MUTED, va="bottom", ha="center")
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    style(ax, f"accuracy per category · overall v0 {overall['v0']:.0%}, v1 {overall['v1']:.0%} (96 sentences)",
          xlabel="accuracy (3 sentences per language per category)", grid="x")

    ax = axes[1]
    ts = sorted(set(scores))
    xs, prec, rec = [], [], []
    for t in ts:
        tp = sum(1 for s_, y in zip(scores, labels) if s_ >= t and y)
        fp = sum(1 for s_, y in zip(scores, labels) if s_ >= t and not y)
        fn = sum(1 for s_, y in zip(scores, labels) if s_ < t and y)
        xs.append(t)
        prec.append(tp / (tp + fp) if tp + fp else 1.0)
        rec.append(tp / (tp + fn))
    ax.step(xs, prec, where="post", color=PALETTE[0], lw=2, label="precision", zorder=2)
    ax.step(xs, rec, where="post", color=PALETTE[1], lw=2, label="recall", zorder=2)
    ax.axvline(policy.flag_threshold, color=MUTED, lw=0.8, ls="--")
    ax.text(policy.flag_threshold, 0.02, " default flag 0.6", fontsize=7, color=MUTED)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")
    style(ax, f"v0 flag threshold trade-off (best F1 {f1_all:.2f} at {t_all:.2f})", "score", "flag if p(hate) ≥ threshold")
    note(fig, "hard cases: subtle hostility, negation, quotation, obfuscation, insults aimed at things; the corpus was written before v1")
    fig.tight_layout()
    return [save(fig, out, "e10_stress_corpus.png")]
