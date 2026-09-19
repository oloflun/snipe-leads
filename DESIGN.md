# Design — Snajp

A locked design system. Every page reads this file before emitting code. Do not regenerate per
page; extend or amend this file when the system needs to grow.

Stamp: `/* Snajp · genre: nordic-editorial · design-system: DESIGN.md · designed-as-app */`

---

## Read this first: why the previous version of this file failed

The 2026-07-28 revision of this document was written entirely as prohibitions. No shadows, no
borders, accent under 5%, no mono, no sub-captions, italic hero only. Not one rule described what
*creates* visual interest. A fully compliant page was therefore guaranteed to be empty, and that is
exactly what shipped: measured against the editorial page it replaced, it had 2 hairline rules
against 106, zero ochre at display scale against 30, and one display type step against six.

The lesson is recorded here because it will otherwise be repeated: **a design system that only
subtracts produces subtraction.** Every rule below that removes something is paired with what takes
its place. If you find yourself deleting a texture layer, name the layer that replaces it before
you do.

## Provenance

Tier 1 · derive. The palette and the display face are retained brand evidence; nothing here is
invented. Genre moved editorial → nordic-saas → **nordic-editorial**, which is where it settled:
the warm editorial character of the original, with the honesty and responsiveness it lacked.

| What | Source |
|---|---|
| OKLCH palette | `app/globals.css` `:root`, unchanged since the first build |
| Display face | Fraunces, variable `opsz`/`SOFT` |
| Accent placement | the approved `editorial-clean` landing |
| Photography method | anti-slop-design's horai/calyx demos |

## Genre

**Nordic editorial.** Warm ground, cool ink, one amber accent. The page is structured like a
printed object: ruled, typographic, unhurried. Photography carries atmosphere where it earns its
place; drawn form carries it where photography would be a lie.

The palette is what keeps this out of generic SaaS territory, and every generic pull is toward pure
white and toward blue. **Holding the warm paper is most of the work.**

## What creates the design

This section is the counterweight to the bans. A page that has none of these is not minimal, it is
unfinished.

1. **Display type at real scale, with steps.** At least four distinct display sizes on a marketing
   page, topping out near 90px on desktop. A single hero size with a cliff down to body text reads
   as a document, not a design.
2. **Ochre at display scale.** The accent must appear large at least a few times per page: a marked
   word inside a heading, oversized numerals, a tracked micro-head. Accent used only on buttons is
   accent that is not there.
3. **The hairline rule system.** Rules separate rows, head sections and carry ruled lists. They are
   the structural language and they are cheap. Tonal planes alone do not separate: `paper2` sits
   0.035 OKLCH lightness from `paper` and is close to invisible.
4. **One tonal inversion per page.** A full-width ink band, or a light band on a dark page.
5. **A moment that is not information.** One statement line, large, with nothing competing.
6. **Imagery, or a reason there is none.** Either real photographs, or one drawn form used no more
   than twice. A pure-text marketing page is incomplete work.
7. **Reveal on scroll.** Opacity plus a short rise, 300ms. A page that never settles reads as a
   screenshot.

## Macrostructure families

| Family | Routes | Shape |
|---|---|---|
| Marketing | `/`, `/leads`, `/support` | Hero → problem → statement → live demo → place → steps → objections → limits → close |
| App | `/dashboard/*`, `/settings/*`, `/demo/*` | Workbench: fast ink-vänsterrail (ikonrail <lg, ochre-markör på aktiv flik — sidans EN tonala inversion), dense rows, fasta tabeller (`Tabell`/`Radlista` i components/ui.tsx: deklarerade kolumnbredder, kicker-huvuden, tnum), fixed type scale, no hero, no reveals, no imagery. Samma railmönster som bokforing-webb/components/Sidebar.tsx |
| Content | `/login`, `/onboarding`, `/not-found` | Single column, typography only |

## Theme

```css
--ink         0.20  0.018 252   /* primary text, primary fill */
--ink2        0.28  0.018 252   /* secondary text on paper */
--paper       0.965 0.008 88    /* page ground — warm, never #fff */
--paper2      0.93  0.012 88    /* raised plane, always WITH a hairline */
--mineral     0.50  0.015 252   /* muted text (kicker colour) — 0.55 until 2026-09-19 */
--ink-muted   0.42  0.018 252   /* secondary text on paper, muted role */
--ink-subtle  0.48  0.018 252   /* tertiary/meta text on paper, muted role */
--paper-muted 0.72  0.008 88    /* secondary text on the dark ink rail */
--paper-subtle 0.62 0.008 88    /* tertiary/meta text on the dark ink rail */
--seal        0.42  0.022 252   /* deep plane on dark sections */
--ochre       0.74  0.16  64    /* the only accent */
--moss        0.42  0.071 142   /* success */
--danger      0.57  0.18  27    /* error, escalation */
--focus       = ochre
```

**Accent discipline.** Ochre on: the primary CTA, the current selection, the focus ring, state
indicators, oversized numerals, and one marked word per heading. Roughly 3 to 5% of a viewport.
Driving it to zero is as wrong as flooding it.

**Contrast is measured, not estimated.** Paper text needs a background at or below ~0.28 relative
luminance for 3:1. An ochre form at `oklch(0.80)` is nowhere near it, and no scrim rescues text laid
over it. This was found the hard way: measure by hiding the text and sampling the background, never
by sampling a screenshot that still has glyphs in it.

**Muted text uses tokens, never `ink/xx` or `paper/xx` opacity.** An axe scan of the production demo
(2026-09-19) found 181 `color-contrast` nodes failing WCAG 2.2 AA across 8 routes, all traced to two
things: the ad-hoc opacity trail on `--ink`/`--paper` (20 distinct steps in use, `text-ink/20`
through `text-ink/88`, computed contrast ranging 1.7:1 to 12.6:1 with no relationship to role) and
`--mineral` at `L 0.55`, which measured 4.38:1 on `--paper` — under the 4.5:1 floor. Opacity steps
don't carry contrast guarantees: `oklch(var(--ink) / 0.45)` blends toward the background it sits on,
so the same class passes on `--ink` and fails on `--paper2`, and nobody can tell which without
measuring. The fix is four named, solid (non-alpha) tokens plus one adjusted existing token, each
picked to clear AA on every ground it is used on, with margin for the second-worst ground measured
(`--paper2` for the light tokens):

| Token | Value | On `--paper` | On `--paper2` | On `--ink` (rail) | Replaced |
|---|---|---|---|---|---|
| `--mineral` | `0.50 0.015 252` | 5.41:1 | 4.88:1 | — | itself (was `0.55`, 4.38:1 — failed) |
| `--ink-muted` | `0.42 0.018 252` | 7.63:1 | 6.87:1 | — | `text-ink/55`, `/60` |
| `--ink-subtle` | `0.48 0.018 252` | 5.90:1 | 5.31:1 | — | `text-ink/20`…`/50` |
| `--paper-muted` | `0.72 0.008 88` | — | — | 7.29:1 | `text-paper/55`…`/85` |
| `--paper-subtle` | `0.62 0.008 88` | — | — | 4.97:1 | `text-paper/25`…`/50` |

Everything above `ink/55` and `paper/50` (`ink/60` through `/88`, `paper/55` through `/85`) already
cleared 4.5:1 on both grounds it is measured against, so those steps were folded into
`ink-muted`/`paper-muted` too, for consistency — one vocabulary, not two — not because they were
failing. Two steps per ground hold the hierarchy DESIGN.md requires (2-3 distinguishable muted
levels); twenty did not add a third visible level, they added noise. `--ink` (full), `--ink2` and
`--ochre`/`--warning`/`--danger`/`--moss` are unchanged — they already passed or are governed
separately (`--warning` for text-on-accent, see above). Dark mode carries matching pairs with the
ink/paper roles swapped, same method, same margins (see `app/globals.css` `:root[data-theme="dark"]`).

Tailwind exposes all four as color utilities the normal way: `text-ink-muted`, `text-ink-subtle`,
`text-paper-muted`, `text-paper-subtle` (`tailwind.config.ts`). Write muted or meta text with one of
these, or with `text-mineral` for kickers — never with `text-ink/NN` or `text-paper/NN` again. The
`placeholder:` opacity variants are unaffected: placeholder text is out of AA's normal-text scope
and keeps the old opacity trail.

The same scan also caught bare `text-ochre` used as running text (badges, kickers, marked words,
inline links): `--ochre` measures 2.16:1 on paper, nowhere near 3:1 let alone 4.5:1. `--warning`
already existed as the text-safe ochre variant (see above) and is now used everywhere `text-ochre`
was doing double duty as body text, moved from `L 0.54` to `L 0.50` so it also clears the
ochre-tinted demo banner background (`bg-ochre/10`/`/12`), which measured 4.33:1 at the old value.
`text-ochre` itself is untouched and stays correct for two cases this scan doesn't reach: an accent
on a non-text element (background, border, icon fill), and text sitting on the dark `--ink` rail,
where `--ochre` gives 7.56:1 and `--warning` would only give 3.44:1 — the text-safe variant is
calibrated for light grounds, not the rail.

## Typography

| Role | Face | Use |
|---|---|---|
| Hero display | Fraunces, italic | The marked word only. Once or twice per page. |
| Headings | Fraunces, roman | Section heads, card titles |
| Body | Geist, 400/450 | All running text |
| Data | Geist, `tnum` | Numerals in tables and tiles |
| Numerals | Fraunces, ochre | Oversized step and list numbers |

Marketing type is fluid (`clamp`); product type is a fixed rem scale. A clamp-sized heading inside a
dashboard sidebar looks worse, not better.

**Micro-labels.** The original page carried 78 tracked mono eyebrows. That was too many. What
survives is only what a first-time reader needs for context, set in the body face at 0.8125rem, not
tracked-out mono. Mono is reserved for product surfaces where it reads as data.

**Inputs never below 16px.** iOS Safari force-zooms a focused field under 16px and breaks the layout.

## Imagery

Two sanctioned methods, both proven in the anti-slop-design demos:

**Photography.** Real photographs, vendored into `public/photos`, never hotlinked: the hero image is
the largest contentful paint and must not depend on another company's CDN. Source them, verify each
one loads, **look at each one**, then downsize and re-encode to WebP. Credit the photographer in
`public/photos/ATTRIBUTION.md` even when the licence does not require it.

**Drawn form.** Inline SVG with radial gradients. Used at most twice per page, opening and closing.
A third instance reads as a smudge rather than a motif.

Never: fake browser chrome, phone frames, mock IDE windows, gradient mesh, floating blobs.

## Motion

```css
--ease-out:  cubic-bezier(0.16, 1, 0.3, 1);
--dur-short: 180ms;
--dur-mid:   300ms;
```

Reveal on scroll via one IntersectionObserver, `.rise` → `is-visible`, unobserved after first
reveal. Parallax only on `hover: hover and pointer: fine`; touch browsers ignore or jitter on
`background-attachment: fixed`.

**`.rise` starts at `opacity: 0`, so the reveal system is load-bearing and must fail toward
visible.** Anything it misses is not an animation that did not play, it is a heading with nothing
under it. That shipped once: twelve elements stayed invisible on every route of a live deploy.
Four guards, all required, all in `components/marketing/useReveal.ts`:

- `threshold: 0`. An element taller than the viewport can never reach a non-zero ratio, because the
  ratio is capped at viewport height over element height. A threshold of 0.08 silently excluded
  every tall section.
- Reveal whatever is already on or above the screen at mount. Land mid-page from a restored scroll
  position or an anchor and the elements above never intersect again.
- A timed failsafe reveals the rest after 1200ms.
- A `<noscript>` block in `app/layout.tsx` forces `.rise` visible. Neither it nor the CSS rule
  survives alone.

`scripts/check_reveal.py` counts un-revealed elements across three routes × three entry modes. It
was confirmed to **fail** against the broken version, 12 per page, before it was trusted.

Reduced motion is handled globally and needs no per-component fallback.

## Honest-proof rule

Binding, and the reason several usual modules are unavailable.

- No invented metrics, customer counts, testimonials or logo walls anywhere in marketing copy.
- Mock and seed data are **required** inside the demos and the dashboard. They may not be cited in
  copy as evidence of results.
- Any illustrative example carries a plain line saying so.
- Two sources of truth on one surface is one too many: if a component reports its own live status,
  do not add a second status claim next to it.
- Because fabricated proof is unavailable, **the live product surface is the proof.**

## Copy

Written with `copywriting`, reworked with `copy-editing`'s seven sweeps, finished with `humanizer`
on English and `humanizer-svenska` on Swedish. Always finish with the humanizers.

The humanizers remove AI tells. They do **not** license rewriting content: changing "took new
premises" to "signed a new lease" is a different factual claim, not a humanisation. If a pass wants
to change what a sentence asserts, that pass has overreached.

No em-dashes in any visible string, in either language.

## Accessibility floor

A `.kicker` label is a caption, not a heading — mark it up as `<p>`/`<span>`, even sitting right under
a page `<h1>`. Rendering it as `<h3>` reads as a level skip to axe (`heading-order`) the moment
there is no `<h2>` between them, which is the common case for a kicker that opens a section. Found
on `/demo/iris` and `/demo/iris/installningar` 2026-09-19, fixed in `components/leads/IrisBolag.tsx`
and `components/leads/IrisInstallningar.tsx`.

Every interactive element ships all 8 states. Focus ring is ochre, 2px, 2px offset, no exceptions.
Tap targets 44px. `<html lang>` follows the locale switch, or a screen reader reads English copy
with Swedish pronunciation. Verified at 320/375/390/414/768/1024/1440/1920 in both motion modes,
using **element bounds**, not `scrollWidth`: `overflow-x: clip` hides real overflow from that check.

## Verification

A screenshot you did not read does not count. Computed-style assertions are not a substitute for
looking: it is possible to pass every mechanical rule and ship an empty page, and that has already
happened once in this project.

The procedure is CARL DESIGN rules 5 to 10, and the pass list is in the design skill's Step 5.
In short: capture and **read** fold, full page and mobile; squint test at 5px; sweep the breakpoints
by **element bounds**, not `scrollWidth`; tab through; measure contrast with the text hidden,
sampling pure background; test any JS-driven reveal with JavaScript off; then production LCP and
CLS from a real production build. Dev-mode bundle size is meaningless (3.8 MB dev against 650 KB
production here). Finish with `detect.mjs` over the changed files.

If the browser preview cannot produce a screenshot, fall back to Playwright and `Read` the PNGs.
If nothing works, stop and fix the capture. Never guess from the code.

**Iterate until a full pass finds nothing**, not until the output is acceptable, and say plainly
when a pass comes back clean.

### Measured floors — the numbers the next change has to hold

These are the current page, measured. They exist because "empty but rule-compliant" is not
detectable without numbers.

| | Editorial original | The flat redesign | Current |
|---|---|---|---|
| Hairline rules | 106 | 2 | 13 |
| Ochre at display scale (≥28px) | 30 | 0 | 11 |
| Display type steps | 6 | 1 | 6 |
| Distinct font sizes | 20 | 9 | 15 |
| Images | 1 | 1 | 7 |
| Production LCP | — | — | 440 ms |
| CLS | — | — | 0 |

`scripts/measure.py` produces this table. Run it against the previous version as well as the new
one: the ratio is the diagnosis, not the absolute number.
