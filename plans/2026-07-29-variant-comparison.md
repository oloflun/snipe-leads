# Snajp landing page — three candidates

Written 2026-07-29. Nothing in this comparison is committed; all four pages run from worktrees on
disk. Screenshots referenced below are in `.shots/`.

---

## The candidates

| Port | Name | Worktree | What it is |
|---|---|---|---|
| 3008 | **Original** | `snajp-original` | The untouched Snipra editorial page, for reference |
| 3009 | **D · simplified original** | `snajp-copyedit` | The original's language, shortened, mockdata removed |
| 3010 | **E1 · graphic-led** | `snajp-humanized` | Dark ground, drawn SVG sun, no photographs at all |
| 3011 | **E2 · photograph-led** | `snajp-photo` | Four vendored photographs, parallax, statement band |

```bash
start http://localhost:3011/ && start http://localhost:3010/ && start http://localhost:3009/ && start http://localhost:3008/
```

## Measured, same method for all three

| | D (3009) | E1 graphic (3010) | E2 photo (3011) |
|---|---|---|---|
| LCP (production) | **344 ms** | 348 ms | 440 ms |
| CLS | 0 | 0 | 0 |
| First view weight | **1093 KB** | 1112 KB | 1849 KB |
| Images | 44 KB | 44 KB | 780 KB |
| Page height | 2930 px | 4820 px | 6628 px |
| Keyboard stops | 18, none without focus ring | verified | 19, none without focus ring |
| Responsive | clean, 8 widths × 2 motion modes | clean | clean |
| External dependencies in render path | none | none | none |

All three are far inside the thresholds (LCP good is under 2500 ms, CLS under 0.1). The differences
are character, not quality.

## What each one is for

**D · simplified original.** Keeps what the original actually had going for it: display serif at
real scale, the three-column hero, ochre numerals, hairline rules. Drops the invented metrics, the
invented customer marquee, and seven sections of mockdata workspace views. Of 78 mono micro-labels,
two survive, in the body face. Shortest of the three and the closest to what was already approved.

*Choose it if* the original's character is the point and the site should stay compact.

**E1 · graphic-led.** A full pivot: near-black ground, one drawn sun in inline SVG, display serif
with the accent word in ochre. Zero image files. Nothing to download, nothing to break if a CDN is
unreachable, and the lightest page of the three by a hair.

*Choose it if* the product should feel like a tool rather than a place, or if image licensing and
hosting are complications you would rather not have.

**E2 · photograph-led.** Stockholm at golden hour carrying the hero, Gamla stan behind a statement
band, a Scandinavian desk closing the page. Eight sections including problem, place and objections.
The only one that says "Swedish B2B" without writing the words.

*Choose it if* the page has to sell warmth and place. It costs 737 KB and 96 ms for that.

## Recommendation

**E2, the photograph-led one**, if the page's job is to persuade someone who has never heard of
Snajp. It is the only candidate with atmosphere, it carries the most selling copy, and its weight is
still well inside budget.

**D** if this is mainly for people who already know what Snajp is and the site should be quick to
read and quick to maintain.

E1 is the strongest fallback: it is nearly as light as D, more distinctive, and has no image supply
chain at all.

## What is true of all three

- Copy went through `copywriting` → `copy-editing` → `humanizer` (English) and `humanizer-svenska`
  (Swedish). The adopted variant is the seven-sweep edit plus the two changes from the Swedish
  humanizer that were genuinely humanizer work; the rest of that pass rewrote content and was
  discarded.
- No fabricated proof anywhere: no invented metrics, customer counts, testimonials or logo walls.
  Mock data lives only inside the demos, labelled as example data.
- `<html lang>` follows the locale switch. All tap targets 44px. No input under 16px. No em-dashes.
- The interactive Email Studio and support demos are the same live components in all three.

## Merging the winner back

The dashboard rework (auth split, entitlement, scope switch) lives only in the main tree, and every
variant was branched from it. So the winner merges *into* main rather than the other way round, and
the surface is small. Measured with `diff -rq`, excluding build output:

**D · simplified original — smallest merge.** Two files.
```
components/marketing/LandingSimplified.tsx   (new)
components/marketing/ProductPage.tsx         (one import, one tag)
```

**E1 · graphic-led.** Six files plus one new directory-free asset path.
```
components/marketing/LandingGraphic.tsx      (new)
components/marketing/useReveal.ts            (new)
components/marketing/copy-sections.ts        (new selling sections)
components/marketing/ProductSwitch.tsx       (tone="paper")
components/Logo.tsx                          (tone="paper")
app/globals.css                              (.rise, .parallax)
components/marketing/ProductPage.tsx         (wiring)
```

**E2 · photograph-led.** Same as E1, plus:
```
components/marketing/LandingPhoto.tsx        (new)
app/layout.tsx                               (noscript fallback for .rise)
public/photos/                               (4 webp + ATTRIBUTION.md, 863 KB)
```

`EmailStudioEditor.tsx`, `SupportChat.tsx` and `lib/i18n.tsx` are already identical across main and
all variants: the hardening pass and the `lang` fix were applied everywhere at once.

## Other open items

1. **Nothing is committed.** 134 changed paths in the main tree, plus four worktrees.
2. Migration `005_workspace_products.sql` is written but not applied.
3. The Vercel project rename and domain move were deliberately left out; deploy previews only.
4. `snajp-original` is a detached-HEAD worktree at the base commit. Delete it once the comparison
   is over: `git worktree remove ../snajp-original`.

## Screenshots

- `.shots/final3/` and `.shots/final5/` — photograph-led, desktop and mobile
- `.shots/graphic3/` — graphic-led, full page and mobile
- `.shots/final3/`, `.shots/versions2/` — simplified original
- `.shots/old/` — the original, sliced
- `.shots/antislop/` — the reference demos (horai, calyx, hyperborea)
- `.shots/ref/` — legora.com and sinch.com
