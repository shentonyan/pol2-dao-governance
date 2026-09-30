# 向上游仓库提交 PR：流程与脚本

记录 2026-09-30 一次向 6 个上游仓库提交贡献（naturaldao/NaturalDAO、ARCJ137442/jev-2048、MatrAIx-ai/MatrAIx-Persona-8B、nesquena/hermes-webui、anthropics/jacobian-lens、shimo4228/contemplative-agent）的经验。要点摘要写在仓库根目录的 `CLAUDE.md`。

## 1. 分工

| 谁 | 做什么 |
|---|---|
| Claude（云端会话） | 读上游代码和 issue、查重、写补丁与测试、在上游最新代码上验证、生成 `*.patch` / bundle / `PR_TITLE.txt` / `PR_BODY.md` / `NOTES_zh.md` |
| 用户（本地 Windows） | 用自己的账号推送到 fork 或组织分支，在网页上开 PR / issue |

原因：Claude 的 GitHub App 只装在用户自己的账号上。在第三方仓库和 naturaldao 组织上推送或 fork 都会返回 403。

## 2. 提交前检查清单

- [ ] 上游的 issue 和 PR（包括已关闭的）中没有重复。机器人抢 PR 很快的仓库，推送前再查一次。
- [ ] 上游 README 或 CONTRIBUTING 没有写「不接受贡献」。
- [ ] 补丁在上游**最新**的 base 分支上能应用：`git apply --check`。
- [ ] 上游仓库自带的测试、lint 通过，并且新增的测试在旧代码上会失败。
- [ ] 引用的 PoL2 章节号与当前 `PoLEn/` 一致（2026-09-30 起 EAP 为第 4 章）。
- [ ] 涉及他人研究时，署名和致谢已经处理。
- [ ] PR 正文如实说明验证方式和未验证的部分，并按上游的 PR 模板填写。

## 3. 本地提交用的 PowerShell 函数

每次新开 PowerShell 窗口都要先粘贴下面这一段。`$C` 是解压后补丁所在的目录，注意 zip 解压后常会多一层同名目录。

```powershell
$C = "D:\Downloads\upstream-contributions\upstream-contributions"

function Submit-Patch {
    param($Dir, $Fork, $Upstream, $Base, $Branch)
    $patches = @(Get-ChildItem "$C\$Dir\*.patch" -ErrorAction SilentlyContinue)
    if ($patches.Count -eq 0) { Write-Host "找不到补丁：$C\$Dir\*.patch" -ForegroundColor Red; return }

    Set-Location D:\work
    if (-not (Test-Path "D:\work\$Dir")) { git clone "https://github.com/$Fork.git" $Dir }
    Set-Location "D:\work\$Dir"

    if (-not (git remote | Select-String -Quiet '^upstream$')) { git remote add upstream "https://github.com/$Upstream.git" }
    git fetch upstream $Base
    git am --abort 2>$null
    git checkout -B $Branch "upstream/$Base"
    git am $patches.FullName
    if ($LASTEXITCODE -ne 0) { Write-Host "git am 失败" -ForegroundColor Red; return }

    $n = [int](git rev-list --count "upstream/$Base..HEAD")
    if ($n -lt 1) { Write-Host "补丁没有应用上，停止推送" -ForegroundColor Red; return }
    git log --oneline -1

    git push -u origin $Branch --force-with-lease
    if ($LASTEXITCODE -ne 0) { Write-Host "推送失败" -ForegroundColor Red; return }

    $forkName = $Fork.Split('/')[1]
    Start-Process "https://github.com/$Upstream/compare/$Base...shentonyan:${forkName}:$Branch?expand=1"
}
```

用法示例：

```powershell
Submit-Patch jev-2048 shentonyan/jev-2048 ARCJ137442/jev-2048 main fix/sample-coerced-flag
```

开 PR 时，用下面的命令把标题和正文复制到剪贴板：

```powershell
Get-Content "$C\<目录>\PR_TITLE.txt" -Raw | Set-Clipboard
Get-Content "$C\<目录>\PR_BODY.md" -Raw | Set-Clipboard
```

## 4. NaturalDAO（组织内分支）

用户在 NaturalDAO 有写权限。按 PoL-Governance 的 `AGENTS.md`：分支名为 `pol/<任务ID>/shenton`，同时新增任务页 `tasks/<ID>-shenton.md`，并在 `TASKS.md` 登记一行。提交前在 `PoL-Governance/` 目录运行 `python tools/check.py`。

用 bundle 交付：

```powershell
git fetch "$C\NaturalDAO-GOV-01\gov01.bundle" HEAD:pol/GOV-01/shenton
git push -u origin pol/GOV-01/shenton
```

如果远端已经有这个分支，而且是旧版本，就在它上面追加一个提交，不要强推：

```powershell
git fetch origin
git checkout -B pol/GOV-01/shenton origin/pol/GOV-01/shenton
git checkout <新版提交> -- PoL-Governance
git commit -m "..."
git push origin pol/GOV-01/shenton
```

## 5. 遇到过的问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `does not appear to be a git repository`（读取 bundle 时） | 解压后多了一层目录，路径不对 | 用 `Get-ChildItem D:\Downloads -Recurse -Filter gov01.bundle` 找到实际位置 |
| `src refspec ... does not match any` | 上一步的 fetch 失败，分支没有建出来 | 先修好上一步 |
| `rejected (non-fast-forward)` | 远端已经有同名的旧分支 | 在远端分支上追加一个提交（见第 4 节） |
| `Cannot find path` 之后停在 `reading patches from stdin` | 新窗口里 `$C` 是旧值 | 按 Ctrl+C，`git am --abort`，重新设置 `$C` |
| `not a git repository` | 当前不在仓库目录 | 先 `cd D:\work\<仓库>` |
| 对比页显示 main 对比 main | 推上去的是空分支（补丁没有应用） | `git reset --hard upstream/<base>`，重新 `git am`，再 `push --force-with-lease` |
