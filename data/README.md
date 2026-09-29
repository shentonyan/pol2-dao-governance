# Data / 数据

Only **aggregate numbers published with the article** are stored here. The raw OSF
files are not redistributed; download them from <https://osf.io/q6snh/> to use
`pol2dao replay`.

这里只存放论文公布的汇总数字。OSF 原始数据不在本仓库中，需要逐张选票重放时请从 <https://osf.io/q6snh/> 下载。

| File | Content | Source |
|---|---|---|
| `sharma2026_table1_means.csv` | Mean budget share `r_i = choice_i / votes_given` per round × condition, and n | Sharma et al. (2026) Table 1, as reproduced from the OSF data by [dao-governance-replication](https://github.com/shentonyan/dao-governance-replication) (`results/tables/table1.csv`), rounded to 4 decimals |
| `sharma2026_token_totals.csv` | Tokens placed on each option per round × condition | Computed from the OSF vote files by dao-governance-replication (`results/tables/outcomes_by_condition.csv`) |

Conventions (from dao-governance-replication): `early` = the article's 20/80 power
condition; the OSF file named `anonymous_round3_vote.csv` is the article's round 2;
`ranked` conditions add tokens linearly, `quadratic` conditions count √tokens.
Options: 1 use the current model · 2 use additional user information · 3 track and
apply user preferences · 4 add specific flags/tags.

Citation: Sharma, T. et al. Democratic governance through DAO-based deliberation and
voting for inclusive decision making in AI models. *Sci. Rep.* **16**, 11792 (2026).
https://doi.org/10.1038/s41598-026-40180-8
