# Session Log — 2026-08-01

## Session Summary
Rebuilt the design system (`~/.agents/skills/design/`) after archaeology across three prior sessions showed the previous rework fixed mechanical failures (hooks not firing, brand contamination) but never asked why the original v1 system's output was actually good. Replaced the single house style with a register table picked from the business, made the exit bar mechanical (Stop hook blocks on unseen renders), and verified the rebuild with three blind one-shot builds from fresh subagents, all of which cleared the reference bar on the first attempt. Applied the hardened system to Klova (audit, 8 fixes) and Alunix (a scroll-driven "dolly" ignition set-piece, borrowing a principle from 21st.dev, plus a reduced-motion regression found and fixed). Closed by syncing the design skill to `super-intelligence` 0.4.5, committing and pushing `anti-slop-design`, and cloning `alunix-site` into a standalone `alunix` repo with history preserved.

## What Changed

### Files Created
- `C:\Users\Anton L\anti-slop-design\plans\2026-07-31-what-actually-made-the-difference.md` — the archaeology distillate: ten load-bearing factors extracted from six parallel readers over the Snajp /goal session, the hardening session, the v2 rework session, the v1 system, the demo-site source, and the hook chain.
- `C:\Users\Anton L\.claude\hooks\design-session-start.py` (mirrored to `~/.agents/skills` chain and `super-intelligence`) — `SessionStart` hook, clears `.once-*`/`.design-verb`/`.stop-signature` on startup/clear. These never cleared before; "once per session" silently meant "once per project, forever."
- `C:\Users\Anton L\.claude\hooks\design-vision-track.py` — `PostToolUse` on `Read`, logs when a rendered image actually enters context. Feeds the Stop-hook block.
- `C:\Users\Anton L\.claude\skills\design\references\house-physics.md` — structural invariants that hold in every register, then a per-register inventory (editorial print / cinematic dark / illustrated dark / modern clean / warm photographic / historical art) with exact values extracted from real page source.
- `C:\Users\Anton L\.claude\skills\design\scripts\contrast.py`, `contrast_over_media.py` — contrast probes. Both were wrong on their first real run in ways that would have passed a broken page: one only parsed `rgb()` against Tailwind 4's `oklch()` output, the other measured text-over-photo against the page background instead of the rendered plate.
- Six demo pages in `C:\Users\Anton L\anti-slop-design\sites\`: `tidvatten.html`, `vintergatan.html`, `vinterspelen.html` (built blind by subagents, one attempt each) plus `klova/` (vendored source + README explaining why it correctly breaks the editorial invariants).
- `C:\Users\Anton L\alunix` — new standalone git repo, cloned from `alunix-site` with full commit history, origin remote removed.
- `C:\Users\Anton L\klova-hamnkrog\AUDIT-2026-07-31.md` — design audit findings and fixes (8 items).

### Files Modified
- `C:\Users\Anton L\.claude\skills\design\SKILL.md` — new resident "The craft floor" section: lane naming before code, the register table (picked from the business, not file order), house physics, composition contract, apparatus budget (≤4 mono micro-labels outside print registers), "a muted tone needs a value per ground," "reduced motion removes motion, not content."
- `C:\Users\Anton L\.claude\hooks\design-stop.py` — Stop now **blocks** when UI edits exist that no rendered image was Read afterward (capped at 2 blocks/session, then degrades to advisory). Dedup no longer hashes the per-minute timestamp line (was spamming duplicate reports — 48 found in one project).
- `C:\Users\Anton L\.claude\hooks\design-verify-gate.py` — inverted from "prefer read_page over screenshot, two rounds max" to "judge from pixels, iterate until a full pass finds nothing." Also fires on `mcp__claude-in-chrome__*`.
- `C:\Users\Anton L\.claude\hooks\design-route.py` — registers cross-project roots (`.linked-roots`) so a build spanning repos stays visible to the Stop-hook report.
- `C:\Users\Anton L\anti-slop-design\sites\index.html` — content rewritten to describe the system as it is now (registers, not one router); fixed three gates the page was breaking against itself (re-drawn browser chrome on demo frames — gate 47; a bare `1fr` grid track computing to 1522px at 320px and dragging 1200px of horizontal scroll — gates 50/51; 21 visible em-dashes — gate 75); split the brand ochre into three measured tokens after the bright one tested 2.17:1 against the page.
- `C:\Users\Anton L\alunix-site\components\GraphIgnition.tsx` — the graph set-piece changed from a static-scale reveal (1.045→1.0, "a settle, not a move") to a dolly (2.05→1.0, borrowed from 21st.dev's scroll-media-expansion pattern run in reverse) with a title layer crossing the media. Then: reduced motion was cutting the entire stage progression, not just the dolly travel — found via user report, reproduced exactly (frozen on the last frame at every scroll position), fixed by separating "what moves" (dolly, title translate, lerp) from "what the section says" (the six stages, which must still progress under reduced motion).
- `C:\Users\Anton L\klova-hamnkrog\src\app\page.tsx`, `src\components\Menu.tsx`, `src\app\globals.css`, `src\app\meny\page.tsx` — menu moved to the home page below the gallery, columns widened, 8 audit fixes (missing `--color-accent` token, IA duplication, empty grid cell on single-item sections, heading hierarchy, no display-scale accent, 4 real contrast failures including two in text the assistant itself introduced, targeted hero scrim instead of a flat one that killed the photo's warmth, `noscript` fallback for a reveal system invisible without JS).
- `C:\Users\Anton L\super-intelligence\` — VERSION 0.4.4→0.4.5, CHANGELOG.md entry, hooks and design skill synced from `.claude`/`.agents`. Committed locally only, not pushed (per Step 3c of `/conclude`).

### Files Moved/Deleted
- None deleted. `alunix-site` remains at its original path; `alunix` is a new clone alongside it (both currently exist — see Open Threads).

## Decisions Made
- **Registers replace the single house style:** The three original demo sites (Calyx, Hōrai, Hyperborea) are all editorial print. The prior "house physics" treated their shared traits as universal, which produced roman numerals on a harbour restaurant and a colophon on a one-person software firm. Fix: a register table keyed to the business, with structure (hierarchy through scale, one accent at display scale, hairlines, weighted columns) separated from register-specific choices (apparatus, grain, button style, imagery treatment). Confirmed correct by building and reading Klova, which breaks nearly every "invariant" and is right to.
- **Exit bar made mechanical, not advisory:** The Snajp session only reached reference quality after the user manually typed "iterate until you beat the references, verify with your own eyes" as an explicit goal. That is now enforced by `design-stop.py` blocking the Stop event when UI edits exist with no subsequent image Read — the same instruction, encoded as a hook rather than depended on being retyped each session.
- **Reduced motion removes motion, not content:** Cutting an entire scroll-driven stage progression under `prefers-reduced-motion` pins it on its last frame at every scroll position, which reads as broken. The fix generalizes: separate what's decorative motion (scale, translate, easing that keeps drifting) from what's informational progression (stages a section exists to show), and only switch off the former.
- **Two contrast probes needed to measure pixels, not computed style, in two different ways:** one for text against a token background (which required rasterizing every colour, since Tailwind 4's `oklch()` broke a naive `rgb()` parser), one for text over photo/video (which has no token background at all and must be judged against the rendered plate).
- **`alunix` cloned rather than moved:** Preserves full commit history in a fresh, remote-less local repo per the user's explicit request ("committa Alunix-sidan till en ny mapp: alunix"), rather than a plain directory copy that would have discarded history.

## Context & Discussion
- The user gave a detailed critique comparing Tidvatten (liked — modern clean, felt intentional) against Vintergatan (fell into "the same mold as the first Snipra" — too much classical serif/editorial default) and specifically flagged that the small editorial-style captions scattered across every section need to be load-bearing or removed, not decorative by default. This produced the apparatus-budget rule and the "at least three distinct section anatomies" rule.
- The user caught a real regression live: the Alunix graph animation was frozen on scroll for them specifically, screenshotted at three different scroll positions. This was traced to their OS-level "reduced motion" setting interacting with a design decision (cutting the whole scrub under that media query) that had never been tested in that mode.
- The user explicitly asked to try borrowing a scroll-effect component from 21st.dev; two were studied (scroll media expansion, container scroll rotation) and only the animation *principle* was taken — the container-scroll example's drawn device frame was rejected on sight as a gate-47 violation (re-drawn chrome).
- Two agent runs hit the monthly spend limit mid-task (Alunix rebuild, Vinterspelen one-shot) and were resumed/recovered from partial disk output rather than restarted from scratch.

## Open Threads
- **`alunix-site` and `alunix` both exist on disk now.** `alunix` is the new canonical clone with history; `alunix-site` was left untouched as the source. Confirm with the user whether `alunix-site` should be archived/removed, or whether `alunix` is meant to fully replace it going forward (dev server, deploy target, etc. all still point at `alunix-site`).
- **`install.mjs`/`upgrade.mjs` in `super-intelligence` do not yet wire the two new hooks** (`design-session-start.py`, `design-vision-track.py`) into `settings.json` for existing installs. `deployTemplate()`/`wf()` skip writes when the destination already exists, so this needs an explicit additive merge — flagged in the CHANGELOG rather than guessed at.
- **Alunix landing page still needs more work** per the user's own assessment ("sidan kräver fortfarande en del arbete") — this session only reworked the hero set-piece; the rest of the page was not revisited under the new register system.
- **`super-intelligence` commit (0.4.5) is local only, not pushed** — per protocol, pushing is a separate explicit action.
- **Demo `.impeccable/` report files accumulating in `snipe-leads`** — 16+ untracked `design-report-*.md` files from hook telemetry sit in the working tree; harmless but worth a cleanup pass at some point (not auto-deleted per the destructive-action guard).

## Cross-Project Handoffs
- **To `super-intelligence`:** design skill 0.4.5 committed locally with full rationale in `CHANGELOG.md`. Push is a separate, explicit action for the user.
- **To `alunix` (new repo):** inherits the hardened design system's output directly — no separate handoff doc needed, the commit history carries the reasoning.

## Current State After This Session
The design system rebuild is complete and verified: `anti-slop-design` is pushed to GitHub with six live demo registers and a corrected showcase page, `verify-design-system.py` passes 80/80. `super-intelligence` 0.4.5 has the same rebuild committed locally, pending push. `alunix` exists as a fresh standalone repo with full history; the Alunix landing page's hero set-piece is stronger but the user says the page overall still needs work. `klova-hamnkrog` has its audit fixes committed. Next session's most likely focus: decide the fate of `alunix-site` vs `alunix`, continue hardening the rest of the Alunix page under the new register system, and push `super-intelligence` when ready.

<!-- session-state
date: 2026-08-01
type: design-system-rebuild
files_created:
  - C:\Users\Anton L\anti-slop-design\plans\2026-07-31-what-actually-made-the-difference.md
  - C:\Users\Anton L\.claude\hooks\design-session-start.py
  - C:\Users\Anton L\.claude\hooks\design-vision-track.py
  - C:\Users\Anton L\.claude\skills\design\references\house-physics.md
  - C:\Users\Anton L\.claude\skills\design\scripts\contrast.py
  - C:\Users\Anton L\.claude\skills\design\scripts\contrast_over_media.py
  - C:\Users\Anton L\anti-slop-design\sites\tidvatten.html
  - C:\Users\Anton L\anti-slop-design\sites\vintergatan.html
  - C:\Users\Anton L\anti-slop-design\sites\vinterspelen.html
  - C:\Users\Anton L\anti-slop-design\sites\klova\README.md
  - C:\Users\Anton L\alunix
  - C:\Users\Anton L\klova-hamnkrog\AUDIT-2026-07-31.md
files_modified:
  - C:\Users\Anton L\.claude\skills\design\SKILL.md
  - C:\Users\Anton L\.claude\hooks\design-stop.py
  - C:\Users\Anton L\.claude\hooks\design-verify-gate.py
  - C:\Users\Anton L\.claude\hooks\design-route.py
  - C:\Users\Anton L\anti-slop-design\sites\index.html
  - C:\Users\Anton L\alunix-site\components\GraphIgnition.tsx
  - C:\Users\Anton L\klova-hamnkrog\src\app\page.tsx
  - C:\Users\Anton L\klova-hamnkrog\src\components\Menu.tsx
  - C:\Users\Anton L\super-intelligence\VERSION
  - C:\Users\Anton L\super-intelligence\CHANGELOG.md
decisions_made: 5
open_threads: 5
handoffs_pending:
  - target: super-intelligence
    topic: "design skill 0.4.5 committed locally, push pending"
priority_changes: true
status_updated: true
next_session_focus: "Resolve alunix vs alunix-site, continue hardening the rest of the Alunix landing page under the register system, push super-intelligence"
session-state -->
