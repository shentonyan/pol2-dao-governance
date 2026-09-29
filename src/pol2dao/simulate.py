"""Agent-based comparison: the DAO experiment's four conditions vs a PoL2 DAO.

This is a *model*, not evidence about people. Every behavioural assumption is
a parameter of :class:`Scenario` and is listed in docs/experiment-design.md.
Results are for exploring how the mechanisms interact and for designing a real
experiment, not for claims about what a real group would do.

Model in one paragraph
----------------------
A pod of ``n`` people has a majority and a minority group with different
utilities over the four options used by Sharma et al. (2026). People
deliberate for ``rounds`` rounds: under ``free`` moderation the next speaker
is drawn in proportion to sqrt(token budget) (power buys voice) and, after an
unflagged hostile message, minority members speak less (``intimidation``);
under ``round_robin`` everyone speaks once per round. Some majority messages
are hostile and some minority messages are critical; texts come from a small
labelled bank and are screened by the real :class:`~pol2dao.eap.LexiconJudge`,
so its misses and false alarms feed through. Flagged messages carry no
persuasive weight. After deliberation each person moves a fraction
``persuasion`` of the way toward the average utility of the messages heard,
then allocates tokens and the rule aggregates them.
"""

from __future__ import annotations

import csv
import math
import random
import zlib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from statistics import mean
from typing import Literal, Sequence

from .eap import Judge, LexiconJudge, Route, ScreeningPolicy
from .metrics import gini, nakamoto, normalized_regret
from .voting import Ballot, PowerScheme, Rule, allocate, budgets, tally

Behavior = Literal["sincere", "strategic"]

OPTIONS = (
    "Use the current model",
    "Use additional user information",
    "Track and apply user preferences",
    "Add specific flags/tags",
)

# (text, is_hostile). Ground truth is ours; the judge does not see it.
HOSTILE_BANK: tuple[tuple[str, bool], ...] = (
    ("那些少数派没资格说话，闭嘴吧。", True),
    ("Anyone who backs option 3 is an idiot.", True),
    ("They shouldn't be allowed to vote on this.", True),
    ("你们要是再反对，否则后果自负。", True),
    ("Honestly, people like them should go back where they came from.", True),  # no marker: a miss
)
CRITICAL_BANK: tuple[tuple[str, bool], ...] = (
    ("我反对选项2，它会忽略少数用户的需求。", False),
    ("I disagree: option 2 treats our edge cases as noise.", False),
    ("我很生气，这个方案有问题。", False),
    ("This stupid default hurts people like me; I oppose option 2.", False),  # marker on a thing: false alarm
)
NEUTRAL_BANK: tuple[tuple[str, bool], ...] = (
    ("谢谢大家，我们一起看看每个选项的代价。", False),
    ("What do you think about option 4's tags?", False),
    ("I understand the concern about privacy.", False),
    ("选项3需要更多数据，我担心隐私。", False),
    ("Option 1 is cheapest to run.", False),
)


@dataclass(frozen=True)
class Scenario:
    name: str = "baseline"
    n: int = 25
    minority_frac: float = 0.2
    majority_u: tuple[float, ...] = (0.2, 0.55, 0.45, 0.3)
    minority_u: tuple[float, ...] = (0.0, 0.0, 1.0, 0.2)
    noise: float = 0.1
    rounds: int = 3
    hate_rate: float = 0.0        # share of majority messages that are hostile
    criticism_rate: float = 0.5   # share of minority messages that are critical
    intimidation: float = 0.5     # minority speaking propensity lost after unflagged hostility (free talk)
    persuasion: float = 0.3
    temperature: float = 0.15     # sincere allocation: tokens ~ softmax(u / T)
    power_holders: Literal["random", "majority", "minority"] = "random"


@dataclass(frozen=True)
class Condition:
    name: str
    rule: Rule
    power: PowerScheme
    moderation: Literal["free", "round_robin"] = "free"
    screening: bool = False


CONDITIONS: tuple[Condition, ...] = (
    Condition("quadratic-equal", "quadratic", "equal"),
    Condition("quadratic-20/80", "quadratic", "20/80"),
    Condition("ranked-equal", "linear", "equal"),
    Condition("ranked-20/80", "linear", "20/80"),
    Condition("pol2", "quadratic", "equal", "round_robin", True),
    Condition("pol2-no-screening", "quadratic", "equal", "round_robin", False),
    Condition("pol2-free-talk", "quadratic", "equal", "free", True),
)


def _softmax(u: Sequence[float], t: float) -> list[float]:
    m = max(u)
    e = [math.exp((x - m) / t) for x in u]
    z = sum(e)
    return [x / z for x in e]


def _allocation(u: Sequence[float], budget: float, rule: Rule, behavior: Behavior, t: float):
    if behavior == "sincere":
        return allocate(_softmax(u, t), budget)
    if rule == "quadratic":
        # With utility linear in votes and cost v^2, optimal votes are proportional
        # to (relative) utility, so tokens ~ utility^2.
        mu = mean(u)
        return allocate([max(x - mu, 0.0) ** 2 for x in u], budget)
    best = max(range(len(u)), key=lambda j: u[j])
    return tuple(int(budget) if j == best else 0 for j in range(len(u)))


def _message(rng: random.Random, minority: bool, sc: Scenario) -> tuple[str, bool]:
    if not minority and rng.random() < sc.hate_rate:
        return rng.choice(HOSTILE_BANK)
    if minority and rng.random() < sc.criticism_rate:
        return rng.choice(CRITICAL_BANK)
    return rng.choice(NEUTRAL_BANK)


def run_once(sc: Scenario, cond: Condition, behavior: Behavior, rng: random.Random,
             judge: Judge | None = None, policy: ScreeningPolicy | None = None) -> dict:
    judge = judge or LexiconJudge()
    policy = policy or ScreeningPolicy()
    n, k = sc.n, len(sc.majority_u)
    n_min = max(1, round(sc.minority_frac * n))
    is_min = [i < n_min for i in range(n)]
    base = [sc.minority_u if m else sc.majority_u for m in is_min]
    u0 = [[min(max(x + rng.gauss(0, sc.noise), 0.0), 1.0) for x in b] for b in base]

    holders = None
    n_hold = max(1, round(0.2 * n))
    if sc.power_holders == "majority":
        holders = rng.sample([i for i in range(n) if not is_min[i]], n_hold)
    elif sc.power_holders == "minority":
        holders = rng.sample(range(n_min), min(n_hold, n_min))
    bud = budgets(n, cond.power, rng, holders)

    # --- deliberation ------------------------------------------------------
    total_msgs = sc.rounds * n
    heard = [0.0] * n            # persuasive weight per speaker
    spoke = [0] * n
    intimidated = False
    hostile = hostile_flagged = benign = benign_flagged = 0
    for m in range(total_msgs):
        if cond.moderation == "round_robin":
            s = m % n
        else:
            w = [math.sqrt(bud[i]) * ((1 - sc.intimidation) if (is_min[i] and intimidated) else 1.0)
                 for i in range(n)]
            s = rng.choices(range(n), weights=w)[0]
        text, is_hostile = _message(rng, is_min[s], sc)
        flagged = cond.screening and policy.route(judge.judge(text)) is Route.FLAG
        if is_hostile:
            hostile += 1
            hostile_flagged += flagged
            if not flagged:
                intimidated = True
        else:
            benign += 1
            benign_flagged += flagged
        spoke[s] += 1
        if not flagged:
            heard[s] += 1.0

    z = sum(heard)
    if z > 0:
        avg = [sum(heard[i] * u0[i][j] for i in range(n)) / z for j in range(k)]
        u1 = [[(1 - sc.persuasion) * u0[i][j] + sc.persuasion * avg[j] for j in range(k)]
              for i in range(n)]
    else:
        u1 = u0

    # --- vote ----------------------------------------------------------------
    ballots = [Ballot(f"p{i}", _allocation(u1[i], bud[i], cond.rule, behavior, sc.temperature), bud[i])
               for i in range(n)]
    t = tally(ballots, cond.rule)
    min_fav = max(range(k), key=lambda j: sc.minority_u[j])
    maj_fav = max(range(k), key=lambda j: sc.majority_u[j])
    totals = [sum(u[j] for u in u0) for j in range(k)]
    optimum = max(range(k), key=lambda j: totals[j])
    return {
        "winner": t.winner,
        "minority_win": int(t.winner == min_fav),
        "majority_win": int(t.winner == maj_fav),
        "optimum_hit": int(t.winner == optimum),
        "regret": normalized_regret(u0, t.winner),
        "influence_gini": gini(t.per_voter.values()),
        "nakamoto": nakamoto(t.per_voter),
        "minority_voice_share": sum(spoke[i] for i in range(n) if is_min[i]) / total_msgs,
        "hostile_msgs": hostile,
        "hostile_missed": hostile - hostile_flagged,
        "benign_msgs": benign,
        "benign_flagged": benign_flagged,
    }


def _seed(*parts: object) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("baseline"),
    Scenario("hostile", hate_rate=0.3),
)


def run_grid(reps: int = 400, scenarios: Sequence[Scenario] = SCENARIOS,
             conditions: Sequence[Condition] = CONDITIONS,
             behaviors: Sequence[Behavior] = ("sincere", "strategic"),
             holders: Sequence[str] = ("random", "majority"), seed: int = 20260929) -> list[dict]:
    judge = LexiconJudge()
    rows = []
    for sc0 in scenarios:
        for h in holders:
            sc = replace(sc0, power_holders=h)
            for beh in behaviors:
                for cond in conditions:
                    # Same seed across conditions: common random numbers.
                    rng = random.Random(_seed(seed, sc.name, h, beh))
                    runs = [run_once(sc, cond, beh, rng, judge) for _ in range(reps)]
                    hostile = sum(r["hostile_msgs"] for r in runs)
                    benign = sum(r["benign_msgs"] for r in runs)
                    rows.append({
                        "scenario": sc.name, "power_holders": h, "behavior": beh,
                        "condition": cond.name, "rule": cond.rule, "power": cond.power,
                        "moderation": cond.moderation, "screening": cond.screening, "reps": reps,
                        "minority_win": mean(r["minority_win"] for r in runs),
                        "majority_win": mean(r["majority_win"] for r in runs),
                        "optimum_hit": mean(r["optimum_hit"] for r in runs),
                        "regret": mean(r["regret"] for r in runs),
                        "influence_gini": mean(r["influence_gini"] for r in runs),
                        "nakamoto": mean(r["nakamoto"] for r in runs),
                        "minority_voice_share": mean(r["minority_voice_share"] for r in runs),
                        "hostile_miss_rate": (sum(r["hostile_missed"] for r in runs) / hostile
                                              if hostile else float("nan")),
                        "benign_flag_rate": (sum(r["benign_flagged"] for r in runs) / benign
                                             if benign else float("nan")),
                    })
    return rows


def write_csv(rows: list[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    return path


def scenario_table() -> list[dict]:
    return [asdict(s) for s in SCENARIOS]
