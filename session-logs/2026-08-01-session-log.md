# Session Log — 2026-08-01

## Session Summary
Rebuilt the design system (`~/.agents/skills/design/`) after archaeology across three prior sessions showed the previous rework fixed mechanical failures (hooks not firing, brand contamination) but never asked why the original system's output had been good. Replaced the single house style with a register table picked from the business, made the exit bar mechanical (a Stop hook that blocks on unseen renders), and verified with three blind one-shot builds from fresh subagents — all cleared the reference bar on the first attempt. Applied the hardened system to Klova (audit, 8 fixes) and Alunix (a scroll-driven dolly set-piece borrowing a principle from 21st.dev, plus a reduced-motion regression found by the user and fixed). Then rebuilt `/conclude` itself: its mechanical half now runs concurrently in one script, cutting 8–9 minutes of serial waiting to near zero. Closed by completing the installer wiring, pushing `super-intelligence` and `anti-slop-design`, and making `alunix` canonical.

## What Changed

### Files Created
- `C:\Users\Anton L\anti-slop-design\plans\2026-07-31-what-actually-made-the-difference.md` — the archaeology distillate: ten load-bearing factors from six parallel readers over three prior sessions, the original system, the demo-site source, and the hook chain.
- `C:\Users\Anton L\.agents\scripts\conclude-finalize.py` — runs the seven mechanical `/conclude` tasks concurrently. Every value is an argument; nothing decides anything. `--dry-run` copies `sessions.db` to a temp file and prints external commands instead of running them.
- `C:\Users\Anton L\.claude\hooks\design-session-start.py` — `SessionStart`, clears `.once-*`/`.design-verb`/`.stop-signature`. These never cleared, so "once per session" silently meant "once per project, forever."
- `C:\Users\Anton L\.claude\hooks\design-vision-track.py` — `PostToolUse` on `Read`, logs when a rendered image enters context. Feeds the Stop-hook block.
- `C:\Users\Anton L\.claude\skills\design\references\house-physics.md` — structural invariants true in every register, then a per-register inventory with exact values from real page source.
- `C:\Users\Anton L\.claude\skills\design\scripts\contrast.py`, `contrast_over_media.py` — both were wrong on their first real run in ways that would have passed a broken page.
- Six demo pages in `anti-slop-design\sites\`: `tidvatten.html`, `vintergatan.html`, `vinterspelen.html` (built blind by subagents, one attempt each) plus `klova/` (vendored source + README on why it correctly breaks the editorial invariants).
- `C:\Users\Anton L\alunix` — standalone repo, cloned from `alunix-site` with full history, origin removed. **Canonical as of today.**
- `C:\Users\Anton L\alunix-site\SUPERSEDED.md` — marks the old directory, left in place rather than deleted.
- `C:\Users\Anton L\klova-hamnkrog\AUDIT-2026-07-31.md` — audit findings and fixes.

### Files Modified
- `C:\Users\Anton L\.claude\skills\design\SKILL.md` — resident "craft floor": lane naming before code, the register table, house physics, composition contract, apparatus budget, "a muted tone needs a value per ground", "reduced motion removes motion, not content".
- `C:\Users\Anton L\.agents\skills\conclude\SKILL.md` — steps 2c/2e/2f collapse into one backgrounded script call; steps 8/8b become "collect the report you already started"; the `python3 - <<'PYEOF'` heredoc removed and warned against; step 1 gains a parallel evidence batch; step 3c gains robocopy verification and a "stage what you touched" warning.
- `C:\Users\Anton L\.claude\hooks\design-stop.py` — Stop now **blocks** when UI edits exist that no rendered image was Read afterward (capped at 2, then advisory). Dedup no longer hashes the per-minute timestamp (was spamming — 48 duplicate reports found).
- `C:\Users\Anton L\.claude\hooks\design-verify-gate.py` — inverted from "prefer read_page, two rounds max" to "judge from pixels, iterate until a full pass finds nothing". Now also fires on `mcp__claude-in-chrome__*`.
- `C:\Users\Anton L\.claude\hooks\design-route.py` — registers cross-project roots so a build spanning repos stays visible to the Stop report.
- `C:\Users\Anton L\anti-slop-design\sites\index.html` — content rewritten for registers; fixed three gates the page broke against itself (re-drawn browser chrome, gate 47; a bare `1fr` computing to 1522px at 320px and dragging 1200px of horizontal scroll, gates 50/51; 21 visible em-dashes, gate 75); split the brand ochre into three measured tokens after the bright one tested 2.17:1.
- `C:\Users\Anton L\anti-slop-design\anti-slop-design.md` — hub doc, dated rework section, prior status marked superseded.
- `C:\Users\Anton L\alunix-site\components\GraphIgnition.tsx` — static reveal (1.045→1.0) became a dolly (2.05→1.0) with a title crossing the media; then the reduced-motion fix separating what moves from what the section says.
- `C:\Users\Anton L\klova-hamnkrog\` — menu moved to the home page, columns widened, 8 audit fixes.
- `C:\Users\Anton L\super-intelligence\install.mjs` / `upgrade.mjs` / `CHANGELOG.md` / `VERSION` — 0.4.4→0.4.5, design skill and hooks synced, registration table 6→8 entries plus matcher reconciliation.

### Files Moved/Deleted
- Nothing deleted. `alunix-site` remains on disk marked superseded; `alunix` is the canonical clone.

## Decisions Made
- **Registers replace the single house style.** The three original demos are all editorial print; treating their shared traits as universal produced roman numerals on a harbour restaurant. Structure (hierarchy through scale, one display-scale accent, hairlines, weighted columns) is now separated from register-specific choices (apparatus, grain, buttons, imagery). Confirmed by building Klova, which breaks nearly every "invariant" and is right to.
- **The exit bar is mechanical, not advisory.** The instruction that made the difference — "iterate until you beat the references, verified on pixels" — is now a Stop hook rather than something the user retypes each session.
- **Reduced motion removes motion, not content.** Cutting a whole scroll progression pins it on its last frame at every position, which reads as broken. Separate decorative travel from informational progression; switch off only the former.
- **`/conclude`'s mechanical half runs concurrently, started early.** Ordering was the dominant cost: run serially at the end, the latency is fully additive; run underneath the writing steps, it is close to free.
- **`alunix` is canonical; `alunix-site` is marked, not deleted.** Two live copies is how the wrong one gets edited, but deletion is the user's call, not an automatic cleanup step.
- **`super-intelligence` pushed to `design-system-v2`, not `main`.** CARL rule 5 reserves `main` for an explicit instruction; GitHub offers a PR link.

## Context & Discussion
- The user's critique comparing Tidvatten (liked — modern clean, intentional) against Vintergatan (fell into "the same mold as the first Snipra") produced the apparatus budget and the "at least three distinct section anatomies" rule.
- The user caught the Alunix regression live with three screenshots at different scroll positions, all identical. Traced to their OS-level reduced-motion setting meeting a design decision never tested in that mode.
- The user asked to try a 21st.dev scroll component; two were studied and only the *principle* was taken — the container-scroll example's drawn device frame was rejected on sight as a gate-47 violation.
- The user asked how to make `/conclude` faster without dropping steps ("they were all added for a reason"). That framing shaped the fix: nothing was removed, the mechanical half was parallelised and the rationale for each task kept in the protocol text.
- Two agent runs hit the monthly spend limit mid-task and were recovered from partial disk output rather than restarted.

## Open Threads
- **`gbrain` is unconfigured on this machine** — `Source "default" has no local_path`. Previously silent, now visible in the finalize report. Fix is `gbrain sources add default --path <path>`; the path is the user's call.
- **`super-intelligence` is on `design-system-v2`**, pushed but not merged to `main`. PR link available.
- **`alunix-site` can be deleted** once the user has confirmed `alunix` runs and carries everything.
- **Alunix landing page still needs work** per the user's own assessment — only the hero set-piece was reworked under the new register system.
- **`klova-hamnkrog` tracks `.next/`** — 103 build artifacts show as changes on every run. Worth gitignoring.
- **`.impeccable/` report files accumulating in `snipe-leads`** — hook telemetry, harmless, never auto-deleted per the destructive-action guard.

## Cross-Project Handoffs
- **To `super-intelligence`:** design system 0.4.5 with installer wiring, pushed to `design-system-v2`. Merge to `main` is the user's decision.
- **To `alunix`:** inherits the hardened system directly; commit history carries the reasoning.

## Current State After This Session
The design system rebuild is complete, verified and distributed: `anti-slop-design` is pushed with six live demo registers and a corrected showcase page, `verify-design-system.py` passes 80/80, and `super-intelligence` 0.4.5 carries the whole system plus installer wiring proven against a simulated 0.4.4 install. `/conclude` itself is faster by construction rather than by cutting steps. `alunix` is canonical and clean. Next session: decide the `super-intelligence` merge to `main`, configure or drop `gbrain`, and continue hardening the rest of the Alunix page under the register system.

<!-- session-state
date: 2026-08-01
type: design-system-rebuild
files_created:
  - C:\Users\Anton L\anti-slop-design\plans\2026-07-31-what-actually-made-the-difference.md
  - C:\Users\Anton L\.agents\scripts\conclude-finalize.py
  - C:\Users\Anton L\.claude\hooks\design-session-start.py
  - C:\Users\Anton L\.claude\hooks\design-vision-track.py
  - C:\Users\Anton L\.claude\skills\design\references\house-physics.md
  - C:\Users\Anton L\.claude\skills\design\scripts\contrast.py
  - C:\Users\Anton L\.claude\skills\design\scripts\contrast_over_media.py
  - C:\Users\Anton L\anti-slop-design\sites\tidvatten.html
  - C:\Users\Anton L\anti-slop-design\sites\vintergatan.html
  - C:\Users\Anton L\anti-slop-design\sites\vinterspelen.html
  - C:\Users\Anton L\alunix
  - C:\Users\Anton L\alunix-site\SUPERSEDED.md
  - C:\Users\Anton L\klova-hamnkrog\AUDIT-2026-07-31.md
files_modified:
  - C:\Users\Anton L\.claude\skills\design\SKILL.md
  - C:\Users\Anton L\.agents\skills\conclude\SKILL.md
  - C:\Users\Anton L\.claude\hooks\design-stop.py
  - C:\Users\Anton L\.claude\hooks\design-verify-gate.py
  - C:\Users\Anton L\.claude\hooks\design-route.py
  - C:\Users\Anton L\anti-slop-design\sites\index.html
  - C:\Users\Anton L\anti-slop-design\anti-slop-design.md
  - C:\Users\Anton L\alunix-site\components\GraphIgnition.tsx
  - C:\Users\Anton L\klova-hamnkrog\src\components\Menu.tsx
  - C:\Users\Anton L\super-intelligence\install.mjs
  - C:\Users\Anton L\super-intelligence\upgrade.mjs
decisions_made: 6
open_threads: 6
handoffs_pending:
  - target: super-intelligence
    topic: "0.4.5 pushed to design-system-v2, merge to main is the user's call"
priority_changes: true
status_updated: true
next_session_focus: "Merge super-intelligence to main or not, configure gbrain, continue hardening the Alunix page under the register system"
session-state -->
