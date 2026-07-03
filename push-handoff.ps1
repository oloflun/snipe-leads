# push-handoff.ps1
# Run this on a machine with git and gh installed (your local dev machine)
# This follows the project AGENT.md rules: feature branch + PR, no direct push to development

Write-Host "=== Snipra Automation Handoff Push Script ===" -ForegroundColor Cyan

# 1. Make sure we are on development and up to date
Write-Host "`n1. Switching to development and pulling latest..." -ForegroundColor Yellow
git checkout development
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to checkout development"; exit 1 }

git pull origin development
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to pull development"; exit 1 }

# 2. Create feature branch
$branch = "feature/snipra-automation-login-state"
Write-Host "`n2. Creating feature branch: $branch" -ForegroundColor Yellow
git checkout -b $branch
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create branch"; exit 1 }

# 3. Stage the changes (auth state is ignored)
Write-Host "`n3. Staging changes..." -ForegroundColor Yellow
git add snipra_automator.py
git add STATUS.md
git add session-logs/2026-06-30-session-log.md
git add handoffs/2026-06-30-snipra-automation-handoff.md
git add screenshots/
git add .gitignore

# Show what will be committed
Write-Host "`nStaged files:" -ForegroundColor Green
git status --short

# 4. Commit
Write-Host "`n4. Committing..." -ForegroundColor Yellow
git commit -m "feat(automation): reliable login + persistent state for Email Studio

- Rewrote login command to use fresh Playwright context (middleware redirect fix)
- Persist .snipra-auth-state.json after successful login
- Saved logged-in screenshots + cookies dump ('spara ner allt')
- Updated STATUS.md + added session log and handoff
- Added .snipra-auth-state.json to .gitignore

See handoff: handoffs/2026-06-30-snipra-automation-handoff.md
Session log: session-logs/2026-06-30-session-log.md"

if ($LASTEXITCODE -ne 0) { Write-Error "Commit failed"; exit 1 }

# 5. Push the branch
Write-Host "`n5. Pushing branch $branch to origin..." -ForegroundColor Yellow
git push origin $branch
if ($LASTEXITCODE -ne 0) { Write-Error "Push failed"; exit 1 }

# 6. Create PR
Write-Host "`n6. Creating Pull Request..." -ForegroundColor Yellow
gh pr create `
  --base development `
  --head $branch `
  --title "Feature: Snipra Automator - reliable login and persistent logged-in state" `
  --body "## Summary
- Fixed snipra_automator.py login flow (fresh context so middleware doesn't redirect /login)
- Persistent .snipra-auth-state.json so 'run' / 'demo' / '--interactive' start logged in
- Captured screenshots and cookies dump as requested

**Handoff:** handoffs/2026-06-30-snipra-automation-handoff.md  
**Session log:** session-logs/2026-06-30-session-log.md

## Verification
- login succeeds and saves state
- state + goto /emails → editor + refine buttons visible (no login redirect)
- Screenshots available in screenshots/

## What remains to do
- Test full refine flow with a real LLM key (DeepSeek etc.)
- Handle token expiration / refresh
- Improve dev server stability notes
- Decide on long-term storage of screenshots

See full details in the handoff file."

if ($LASTEXITCODE -ne 0) {
    Write-Warning "gh pr create failed. You may need to create the PR manually on GitHub."
    Write-Host "Branch pushed: $branch"
} else {
    Write-Host "`n✅ PR created successfully!" -ForegroundColor Green
}

Write-Host "`nDone. Check the PR on GitHub." -ForegroundColor Cyan