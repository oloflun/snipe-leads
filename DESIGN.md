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
| App | `/dashboard/*`, `/settings/*` | Workbench: dense rows, fixed type scale, no hero, no reveals, no imagery |
| Content | `/login`, `/onboarding`, `/not-found` | Single column, typography only |

## Theme

```css
--ink      0.20  0.018 252   /* primary text, primary fill */
--ink2     0.28  0.018 252   /* secondary text on paper */
--paper    0.965 0.008 88    /* page ground — warm, never #fff */
--paper2   0.93  0.012 88    /* raised plane, always WITH a hairline */
--mineral  0.55  0.015 252   /* muted text */
--seal     0.42  0.022 252   /* deep plane on dark sections */
--ochre    0.74  0.16  64    /* the only accent */
--moss     0.42  0.071 142   /* success */
--danger   0.57  0.18  27    /* error, escalation */
--focus    = ochre
```

**Accent discipline.** Ochre on: the primary CTA, the current selection, the focus ring, state
indicators, oversized numerals, and one marked word per heading. Roughly 3 to 5% of a viewport.
Driving it to zero is as wrong as flooding it.

**Contrast is measured, not estimated.** Paper text needs a background at or below ~0.28 relative
luminance for 3:1. An ochre form at `oklch(0.80)` is nowhere near it, and no scrim rescues text laid
over it. This was found the hard way: measure by hiding the text and sampling the background, never
by sampling a screenshot that still has glyphs in it.

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

**`.rise` starts at `opacity: 0`.** Without JavaScript the page would be blank, so a `<noscript>`
block must force it visible. Reduced motion is handled globally and needs no per-component fallback.

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

Every interactive element ships all 8 states. Focus ring is ochre, 2px, 2px offset, no exceptions.
Tap targets 44px. `<html lang>` follows the locale switch, or a screen reader reads English copy
with Swedish pronunciation. Verified at 320/375/390/414/768/1024/1440/1920 in both motion modes,
using **element bounds**, not `scrollWidth`: `overflow-x: clip` hides real overflow from that check.

## Verification

A screenshot you did not read does not count. Computed-style assertions are not a substitute for
looking: it is possible to pass every mechanical rule and ship an empty page, and that has already
happened once in this project.

Measure, in this order: look at it, sweep the breakpoints by element bounds, tab through it, measure
contrast with the text hidden, then measure production LCP and CLS against a real production build.
Dev-mode bundle size is meaningless (3.8 MB dev against 650 KB production here).
