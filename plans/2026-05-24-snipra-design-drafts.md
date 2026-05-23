# Plan: Snipra Design Drafts Polish

## Scope
Polish both design draft variants (`editorial-clean`, `modern-blend`) in `components/DesignDrafts.tsx` until they are presentation-ready. Landing page and portal for each variant.

## Completed
- [x] Set `/` as main landing page using `editorial-clean` variant
- [x] `EditorialLandingHeader`: frosted glass (`bg-paper/30 backdrop-blur-xl`), sticky, large logo/headline
- [x] Landing gradient: pure CSS radial-gradient on `<main>` (replacing blurred blob that was clipped by `body { overflow-x: hidden }`)
- [x] Gradient positioned at top-0 of main, fades out with mask around hero headline end
- [x] Gradient parameters: `circle at 18% 0%`, opacity 0.3, transparent 65%, h-860px, mask 78%→100%
- [x] Portal sidebar restored: `w-[324px]`, ink-fill active nav, Swedish characters fixed
- [x] Portal dashboard: reduced heading size, metric cards + table + "Nästa handling" visible in one viewport
- [x] Landing page APPROVED by user (2026-05-24)

## In Progress
- [ ] Dashboard portal further work (user flagged at session end — specifics TBD)

## Remaining
- [ ] Identify specific dashboard issues (ask user or review at `/design-drafts/editorial-clean/portal`)
- [ ] `modern-blend` variant review — may need same gradient/header treatment
- [ ] Any remaining portal sub-pages (leads, companies, contacts, campaigns, etc.)

## Deferred
- Connecting mockdata to Supabase (separate initiative)
- `modern-blend` variant until `editorial-clean` is fully approved

## Blockers
None currently.

## Next Steps
1. Open `/design-drafts/editorial-clean/portal` and ask user what specifically needs fixing on the dashboard
2. Address dashboard feedback
3. Review other portal pages if needed
4. Then assess `modern-blend` variant
