# What made E2 work

Distilled from the run between "Du kan skrota och börja om på E direkt" and the finished
photograph-led page. Written before any context compaction so it survives.

The two things that mattered are at the top. Everything after is how they played out.

---

## 1. Own eyes on every reference and every output

Not "read the code and reason about it". Not "assert the computed styles are correct". **Render it,
capture it, open the image, look.**

The session's original failure was precisely the absence of this. Screenshots failed early, and
instead of fixing that I substituted computed-style checks. Every claim I made was true and
irrelevant: no shadows, no blue, no em-dashes, correct tokens — while the page was empty. It is
possible to pass every mechanical rule and ship nothing, and that is what happened.

What this looks like in practice:

- **References first, captured, never recalled.** Legora, Sinch, horai, calyx, hyperborea were all
  screenshotted and read before a single line was written. Reading them produced facts I would have
  got wrong from memory: both Legora and Sinch *centre* their heroes; Sinch colours words inside the
  headline rather than using a second typeface; calyx mixes roman and italic inside one line.
- **Own output at every stage.** Fold, full page, and mobile, read as images. The full-page read is
  what caught the three flat text sections, the empty grid cell, the smudge behind step 01, and the
  wordmark outweighing the value proposition.
- **The squint test.** Blur the page 5px and screenshot. It shows hierarchy without content, which is
  how the empty cell in the 2-column-3-item grid became obvious.

The corollary: **when a measurement disagrees with your eyes, suspect the measurement.** Two of mine
were wrong and had to be separated from the real ones:

| Reported | Reality |
|---|---|
| "overflow at every width" | `scrollWidth === innerWidth`; the forms are deliberately outside and clipped. The probe measured geometry, not scroll. |
| "contrast 1.77:1" | I was sampling the ochre glyph and comparing text colour to text colour. Hiding the text and sampling pure background gave 8.77:1. |
| "broken images: 0" | The check was `complete && naturalWidth === 0`; a lazy image that never loads is not `complete`, so it slipped through. |

But one measurement that *looked* like an artifact was real: the sun core at `oklch(0.80)` genuinely
gave 2.12:1 against paper text. Both directions of error are possible. Verify the verifier.

## 2. Do not stop at the first acceptable output

Every round after "good enough" found a real defect. That is the whole argument.

| Round | What it found |
|---|---|
| After first E2 build | Headline broke one-word-per-line: `19ch` is narrower than one long Swedish word at 104px |
| After statement band | Divider photo read cool blue against a warm palette |
| After grid-break | My own arbitrary class `xl:-ml-[max(0px,calc((100vw-1480px)/2))]` evaluated to 0 at exactly 1440px, silently killing the break at the commonest desktop width |
| After reveals | `.rise` starts at `opacity: 0`, so the page was blank without JS |
| After "done" | `<html lang>` stayed `sv` after switching to English; a screen reader would read English with Swedish phonetics |
| After "done" again | The drawn form was used three times and read as a smudge; hyperborea uses its own once |
| After production build | One image was 624 KB of the 1063 KB initial payload |

The round that found nothing is the signal to stop, not the round that ships something acceptable.
Stopping earlier would have shipped six of those defects.

**The distinction that matters:** continuing until nothing is left to improve is different from
continuing for its own sake. The former is bounded by evidence; the latter is churn. The test is
whether the round produced a defect. When a full pass finds none, stop and say so.

---

## How the flow got there

### Diagnose with numbers, not adjectives

"It looks generic" is unactionable. The same probe run over both pages turned it into a fix list:

| Metric | Editorial original | The flat version | Ratio |
|---|---|---|---|
| Hairline rules | 106 | 2 | 0.02× |
| Ochre at display scale (≥28px) | 30 | 0 | 0× |
| Mono elements | 134 | 0 | 0× |
| Display type steps | 6 | 1 | — |
| Distinct font sizes | 20 | 9 | 0.45× |

The mechanism was then obvious and not a matter of taste: I had removed seven texture layers and
added one — `paper2` planes at 0.035 OKLCH lightness from `paper`, which is close to invisible.

### A system of only prohibitions produces subtraction

The DESIGN.md that produced the flat page was written entirely as bans. No shadows, no borders,
accent under 5%, no mono, no sub-captions. Not one rule said what *creates* interest, so a fully
compliant page was necessarily empty. **Every subtractive rule needs its replacement named.**

### Solve the blocked thing by finding how it was done before

"Use images" looked blocked: no `generate_image` tool exists in this session, and I confirmed that by
searching rather than assuming. The answer was in `anti-slop-design`'s own source: the demos hotlink
**real Unsplash photographs** and hand-author SVG. A comment in `horai.html` even says
`/* Verified-existing Unsplash photos */`, and another records swapping one out for being too bright
behind text. The capability was never missing; my assumption about what "generate" meant was wrong.

### Two sanctioned imagery methods, both proven

- **Photography** — source, verify each loads, *look at each*, then vendor into `public/`, downsize,
  re-encode to WebP, credit the photographer. Hotlinking puts the largest contentful paint behind
  someone else's CDN.
- **Drawn form** — inline SVG, used at most twice per page. A third instance is a smudge.

### Copy: three passes, always ending with the humanizers

`copywriting` for structure and offer → `copy-editing`'s seven sweeps → `humanizer` on English and
`humanizer-svenska` on Swedish.

**The humanizers remove AI tells. They do not license rewriting content.** The Swedish pass on
variant C changed "tagit nya lokaler" to "skrivit på ett nytt hyreskontrakt" — a different factual
claim, not a humanisation. Of its twelve changes only two were genuine humanizer work: one passive
construction and one piece of jargon. The disciplined edit (B) plus those two was better than either.

### Honest proof as a design constraint, not a limitation

No invented metrics, customers or testimonials. This removed the modules that were carrying the
original's hero right rail and its whole proof band — and forced a better answer: the honest-limits
list ("Vad det inte gör") took the same compositional slot with content that is true. The live
product surface became the proof.

### Section rhythm

Nine sections alternating ground and register: photo hero → problem → dark statement → light demo →
grid-break photo → steps → divider → objections → dark limits → photo close. Three flat text
sections in a row is where energy dies; that was visible only in the full-page read.

---

## The checks that earned their place

Run these, in this order, and look at the output of each:

1. Capture and **read** fold, full page, mobile.
2. Squint test at 5px blur.
3. Element-bounds overflow sweep across 8 widths × 2 motion modes. **Not `scrollWidth`** —
   `overflow-x: clip` hides real overflow from it.
4. Tab through the page: focus ring present on every stop, no trap, nothing focused offscreen.
5. Contrast with the text hidden, sampling pure background, against the actual text colours.
6. Reveal system with JS disabled.
7. Production build, then LCP and CLS. Dev bundle size is meaningless: 3.8 MB dev against 650 KB
   production here.
8. `detect.mjs` over changed files.

## Final numbers, all three candidates

| | D simplified | E1 graphic | E2 photo |
|---|---|---|---|
| LCP | 344 ms | 348 ms | 440 ms |
| CLS | 0 | 0 | 0 |
| First view | 1093 KB | 1112 KB | 1849 KB |

E2 was chosen. It is the only one with atmosphere and place, it carries the most selling copy, and
440 ms is far inside the 2500 ms threshold.
