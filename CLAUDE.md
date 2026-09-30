# CLAUDE.md — 项目记忆 / project memory

Claude Code 在本仓库中工作时自动读取本文件。人类贡献者同样适用。

## 项目概况

- `pol2dao`：把爱2证明（PoL2）的治理条款落到 DAO 投票与审议流程上的实验室。核心代码只用标准库；作图依赖 matplotlib（`pip install -e ".[plot]"`）。
- 常用命令：`pytest`、`pol2dao experiments --reps 1000`（重新生成全部图表）、`pol2dao simulate --reps 1000`、`pol2dao published`、`pol2dao demo`。
- 每条机制都要对应 PoL2 的具体条款，并同步更新 `docs/concept-mapping.md`。模拟结果只能表述为「模型内的结果」，不能写成关于真实人群的结论。

## 制图规范（必须遵守）

参照 [ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers) 的 scientific-figure-making 规范（CC BY-NC 4.0；规则由我们用自己的话重述，不复制其代码或文字）。完整说明见 `docs/figure-style.md`，唯一的实现是 `src/pol2dao/plotstyle.py`。

1. **统一入口**：每张图都用 `new_figure()` 或 `apply_publication_style()` 创建，只通过 `finalize_figure()` 保存。禁止在其他地方直接调用 `savefig`。
2. **输出格式**：同时导出 PNG（300 dpi）和矢量 PDF（`pdf.fonttype = 42`，文字可编辑），白色不透明背景，`tight_layout(pad=2)`（紧凑的多面板图用 1）。
3. **字体**：无衬线字体，按 Helvetica → Arial → Liberation Sans → DejaVu Sans 的顺序回退，中文回退到已安装的 CJK 字体。紧凑图 16 pt、轴线宽 2；大型柱状图 24 pt、轴线宽 3。
4. **坐标轴**：去掉上边框和右边框，默认不画网格，图例不加边框。
5. **颜色只能取自 `PALETTE` 或 `COND_STYLE`**，源码里不写十六进制色值（有测试检查）。颜色有固定语义：
   - 蓝色：PoL2 或本研究提出的方法；
   - 绿色：正向变体或消融；
   - 红色：基线、对照、损失；
   - 灰色：参照或背景；
   - 金色：高亮，每张图最多一处。
6. **实验条件的编码固定不变**：
   - 色相表示机制族：红色 = Sharma et al. 二次方投票，灰色 = Sharma et al. 排序投票，深蓝 = pol2，浅蓝 = pol2-no-screening，绿色 = pol2-free-talk；
   - 虚线和斜线阴影表示 20/80 权力集中。
   这样即使灰度打印也能区分。
7. **柱状图**：黑色描边（线宽 1.5），有误差时画带端帽的误差棒，数值直接标在柱子上方。标签颜色按背景亮度自动选黑或白。
8. **折线图**：线宽 3，标记点 8，每个坐标轴 2–4 条线。不确定性用 `fill_between` 画 95 % 置信区间带（`plot_line(err=...)`）。
9. **热图**：单一色相的连续色图（`Blues`）表示大小；以 0 为中心的发散色图（`RdBu`：红 = 损失，蓝 = 收益）表示差值。格子之间用白色分隔，格内标注数值，色条要有标签。
10. **参考线**：黑色、透明度 0.3、线宽 3 的虚线（`REF_LINE`）。
11. **指标方向**：y 轴或 x 轴标签末尾标明方向，↑ 表示越高越好，↓ 表示越低越好（`UP`/`DOWN`）。
12. **图内不放脚注或长段说明**：数据来源、样本量、重复次数、注意事项一律写进图注（`docs/results.md` 或 README）。面板标题要短。
13. **图例太多时**，单独放在一个关闭坐标轴的面板里（`legend_panel`），不要遮挡数据。
14. **多面板一致**：同一张图内所有面板的字号、线宽和配色语义保持一致；y 轴范围按数据收紧，但概率类指标固定为 0–1。
15. **画完一定要打开 PNG 检查一遍**：看有没有文字重叠、被截断、图例遮挡数据。

## 其他约定

- 生成的结果放在 `results/`（表格放 `tables/`，图放 `figures/`）。改动影响图表时，重新运行 `pol2dao experiments` 并一起提交。
- 外部数据注明来源、许可和 commit（见 `data/README.md`）。
- 修改恨语词表时，要同时补上「应标记」和「应通过」的例句，尤其是「批评、愤怒不是恨」的反例。

## 向上游仓库贡献 PR 的经验（2026-09-30）

完整步骤和可直接使用的 PowerShell 函数见 `docs/contributing-upstream.md`。要点如下：

**先确认权限，再动手**
- Claude 的 GitHub App 只装在用户自己的账号（shentonyan）上，没有装在 naturaldao 组织以及其他第三方上游仓库上。在这些仓库上推送或 fork 会返回 403。
- 遇到 403 时不要反复重试。把改动做成 **git bundle + `format-patch` 补丁 + `PR_TITLE.txt` / `PR_BODY.md`** 交给用户，由用户用自己的账号推送。
- 用户在 NaturalDAO 本人有写权限，按 PoL-Governance 的约定使用组织内分支 `pol/<任务ID>/shenton`；其他上游仓库都通过用户名下的 fork 提 PR。

**提交之前**
- 先查重：搜索上游已有的 issue 和 PR，包括已关闭的。机器人抢 PR 很快的仓库（例如 hermes-webui），推送前要再查一次。
- 检查上游是否写明「不接受贡献」（例如 anthropics/jacobian-lens）。
- 查上游 main 最近的提交。NaturalDAO 在 2026-09-30 调整了 PoLEn 的章节号：伦理对齐协议（EAP）由第 5 章改为第 4 章，静观公理由第 4 章改为第 3 章，AI 与人类文明的治理由第 3 章改为第 5 章。英译版 `PoLEn/` 先改，中文原文 `PoL/` 当天稍晚也改成了同一套编号；上游的 `PoL-Governance/benchmark/pilot.jsonl` 仍写着旧编号「PoL 5.3.x」（我们在 `data/external/` 里的副本保持原样不改）。**引用 PoL2 条款前，先核对当前的章节号。**
- 补丁基于最新的上游分支生成，并用 `git apply --check` 验证能在上游最新代码上应用。
- 涉及 PoL2 与他人研究的交叉时，先检查署名。例如 PoL2 第 3 章的部分句子与 shimo4228 修订后的宪法文本接近，发 issue 之前要先补上致谢。

**给用户的命令（Windows PowerShell）**
- 每个新开的 PowerShell 窗口都要重新设置路径变量 `$C`；每个 git 命令之前都要先 `cd` 进对应仓库目录。
- 解压 zip 时常会多套一层同名目录。用 `Get-ChildItem -Recurse -Filter <文件名>` 找出实际路径。
- PowerShell 不会展开 `*.patch` 通配符，要写成 `git am (Get-ChildItem "$C\<目录>\*.patch").FullName`。如果补丁路径不存在，`git am` 会停在「reading patches from stdin」等待输入，此时按 Ctrl+C，再执行 `git am --abort`。
- **推送前先确认补丁确实已经应用**：`git rev-list --count upstream/<base>..HEAD` 必须大于 0。否则推上去的是一个空分支，GitHub 的对比页会退回成「main 对比 main」。
- 如果远端已有同名分支，并且是用户已经推送过的旧版本，**在它上面追加一个提交**（先 `git checkout -B <分支> origin/<分支>`，再 `git checkout <新提交> -- <目录>`，然后 commit），不要强推覆盖。`--force-with-lease` 只用于用户自己 fork 上刚建的空分支。
- 开 PR 的链接格式：`https://github.com/<上游>/compare/<base>...shentonyan:<fork 名>:<分支>?expand=1`。页面仍然显示 main 对比 main 时，点「compare across forks」手动选择。

**本仓库环境**
- 本仓库的提交和推送以用户本人（shentonyan）的名义进行。云端会话里的 stop hook 可能要求把提交者改成 Claude；如果某个提交号已经交给用户使用，就不要改写它。
