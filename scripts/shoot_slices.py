"""Capture a long page in viewport-sized slices so detail survives.

    python scripts/shoot_slices.py <out-dir> <url> <slug> [max_slices]
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

WIDTH = 1440
HEIGHT = 900


async def main(out_dir: str, url: str, slug: str, max_slices: int) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=1,
            reduced_motion="no-preference",
        )
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)

        total = await page.evaluate("document.documentElement.scrollHeight")
        n = min(max_slices, -(-total // HEIGHT))
        for i in range(n):
            y = i * HEIGHT
            await page.evaluate(f"window.scrollTo(0, {y})")
            await page.wait_for_timeout(600)
            path = out / f"{slug}--s{i:02d}.png"
            await page.screenshot(path=str(path))
            print(f"slice {i} @ y={y} -> {path.name}")
        await browser.close()
        print(f"total height {total}px, {n} slices")


if __name__ == "__main__":
    asyncio.run(
        main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 12)
    )
