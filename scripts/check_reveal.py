"""Fails if any `.rise` element is still hidden after the page settles.

`.rise` starts at opacity 0 and is revealed by an IntersectionObserver. When that
observer misses an element the section renders as a heading with nothing under
it, which is worse than having no animation at all. This is the smallest check
that fails when that happens.

Three entries, because they fail differently: a normal load, a mid-page landing
(restored scroll position or an anchor, where everything above never intersects
again), and a fast scroll to the bottom.

    python scripts/check_reveal.py http://localhost:3005
"""
import asyncio
import sys

from playwright.async_api import async_playwright

PATHS = ["/", "/leads", "/support"]


async def hidden_count(page) -> int:
    return await page.evaluate(
        """() => Array.from(document.querySelectorAll('.rise'))
                 .filter(n => !n.classList.contains('is-visible')).length"""
    )


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

        await browser.close()

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print(f"OK — inga dolda .rise-element på {len(PATHS)} sidor × 3 lägen")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3005"))
