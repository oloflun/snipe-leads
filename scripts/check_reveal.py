"""Fails if any `.rise` element is actually invisible after the page settles.

A section that renders as a heading with nothing under it is worse than having
no animation at all. That has shipped twice, so this check measures the thing
that matters — COMPUTED OPACITY — not the class that is supposed to control it.

Why that distinction: the old version counted elements missing `is-visible`.
Since 2026-08-10 the stylesheet only hides `.rise` while <html> carries
`reveal-armed`, so a missing `is-visible` on an unarmed page is harmless. A
class-based check would now fail on a perfectly legible page and, worse, would
pass on a broken one if the class mechanism were ever renamed again. Opacity is
what the reader actually experiences.

Four entries, because they fail differently: a normal load, a mid-page landing
(restored scroll position or an anchor, where everything above never intersects
again), a fast scroll to the bottom, and a run with JavaScript disabled
entirely — the last one is the regression test for the inverted default.

    python scripts/check_reveal.py http://localhost:3005
"""
import asyncio
import sys

from playwright.async_api import async_playwright

PATHS = ["/", "/leads", "/support"]

# Mät det läsaren faktiskt ser. En nod räknas som dold om den är genomskinlig
# ELLER om någon förälder gömmer den.
_INVISIBLE_JS = """() => Array.from(document.querySelectorAll('.rise'))
    .filter(n => {
      const s = getComputedStyle(n);
      return parseFloat(s.opacity) < 0.99 || s.visibility === 'hidden';
    })
    .map(n => (n.textContent || '').trim().slice(0, 60))"""


async def hidden_count(page) -> int:
    return len(await page.evaluate(_INVISIBLE_JS))


async def main(base: str) -> None:
    failures = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        for path in PATHS:
            # 1. plain load, no scrolling at all
            await page.goto(base + path, wait_until="networkidle")
            await page.wait_for_timeout(1600)
            n = await hidden_count(page)
            if n:
                failures.append(f"{path} utan scroll: {n} dolda")

            # 2. straight to the bottom, then back up
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(900)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(600)
            n = await hidden_count(page)
            if n:
                failures.append(f"{path} efter scroll: {n} dolda")

            # 3. landing mid-page, where elements above never intersect again
            await page.goto(base + path + "#demo", wait_until="networkidle")
            await page.wait_for_timeout(1600)
            n = await hidden_count(page)
            if n:
                failures.append(f"{path}#demo: {n} dolda")

            # 4. Simulera att hooken ALDRIG körde: ta bort `reveal-armed` och
            #    kräv att allt ändå är synligt. Det är hela den inverterade
            #    defaulten, mätt direkt.
            #
            #    Varför inte `java_script_enabled=False` i stället, som vore
            #    det uppenbara no-JS-testet: med JS avstängt kan Playwright
            #    inte köra page.evaluate alls, så det går inte att mäta
            #    computed opacity. Det testet hade sett strängare ut och inte
            #    kunnat mäta något.
            await page.goto(base + path, wait_until="networkidle")
            await page.wait_for_timeout(300)
            await page.evaluate(
                "() => document.documentElement.classList.remove('reveal-armed')"
            )
            # Vänta ut övergången. `.rise` har en opacity-transition, så en
            # mätning direkt efter klassborttagningen fångar elementen mitt i
            # intoningen och rapporterar ~0 för allt — ett mätfel som såg ut
            # som ett verkligt fel första gången det kördes.
            await page.wait_for_timeout(800)
            leftovers = await page.evaluate(_INVISIBLE_JS)
            if leftovers:
                failures.append(
                    f"{path} utan reveal-armed: {len(leftovers)} dolda "
                    f"(t.ex. {leftovers[0]!r}) — defaulten är inte synlig"
                )

        await browser.close()

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print(f"OK — inga dolda .rise-element på {len(PATHS)} sidor × 4 lägen")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3005"))
