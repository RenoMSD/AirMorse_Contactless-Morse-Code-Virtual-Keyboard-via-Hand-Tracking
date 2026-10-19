# Helper for the multi-agent workflow described in AGENTS.md.
#
#   .\scripts\agents.ps1 setup                      Merge the coordination files into main (run once)
#   .\scripts\agents.ps1 start  <agent> <task-id>   Create agent/<agent>/<task-id> from origin/main
#   .\scripts\agents.ps1 finish <agent> <task-id>   Run pytest, commit, push the task branch
#   .\scripts\agents.ps1 status                     Show task board and pushed agent branches

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("setup", "start", "finish", "status")]
    [string]$Command,

    [Parameter(Position = 1)]
    [ValidateSet("cursor", "antigravity")]
    [string]$Agent,

    [Parameter(Position = 2)]
    [ValidatePattern("^T-\d{3}$")]
    [string]$Task
)

$ErrorActionPreference = "Stop"
$CoordinationBranch = "claude/peaceful-meitner-gldkkc"

function Invoke-Git {
    git @args
    if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') failed" }
}

function Require-TaskArgs {
    if (-not $Agent -or -not $Task) { throw "Usage: agents.ps1 $Command <cursor|antigravity> <T-001>" }
}

Set-Location (Split-Path $PSScriptRoot -Parent)

switch ($Command) {
    "setup" {
        Invoke-Git fetch origin
        Invoke-Git checkout main
        Invoke-Git pull origin main
        Invoke-Git merge --no-edit "origin/$CoordinationBranch"
        Invoke-Git push origin main
        Write-Host "Coordination files are on main."
    }
    "start" {
        Require-TaskArgs
        $branch = "agent/$Agent/$Task"
        Invoke-Git fetch origin main
        Invoke-Git checkout -B $branch origin/main
        Write-Host "On $branch. Spec: .agents/TASKS.md ($Task)."
    }
    "finish" {
        Require-TaskArgs
        $branch = "agent/$Agent/$Task"
        if ((git branch --show-current) -ne $branch) { throw "Not on $branch" }
        if (-not (Test-Path ".agents/handoffs/$Task.md")) { throw "Missing .agents/handoffs/$Task.md" }
        python -m pytest
        if ($LASTEXITCODE -ne 0) { throw "pytest failed; fix before handing off" }
        Invoke-Git add -A
        git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) { Invoke-Git commit -m "${Task}: work by $Agent" }
        Invoke-Git push -u origin $branch
        Write-Host "Pushed $branch. Ask Claude Code to review $Task."
    }
    "status" {
        Invoke-Git fetch origin --prune
        Select-String -Path ".agents/TASKS.md" -Pattern "^## T-|^- (owner|status):" | ForEach-Object { $_.Line }
        Write-Host "`nPushed agent branches:"
        git branch -r --list "origin/agent/*"
    }
}
