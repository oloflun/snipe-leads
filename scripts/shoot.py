"""Local screenshot capture for visual verification.

Playwright drives a local browser and writes PNGs; the images are then read with
native vision. No external API calls.

    python scripts/shoot.py <out-dir> <url> [<url> ...]
"""
import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

WIDTH = 1440
HEIGHT = 900


def slug(url: str) -> str:
    s = re.sub(r"^https?://", "", url)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")
    return s or "page"


async def main(out_dir: str, urls: list[str]) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=1,
            # The verification browser had reduced-motion on, which hid every
            # reveal. Capture what a normal visitor sees.
            reduced_motion="no-preference",
        )
        for url in urls:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(1200)

            fold = out / f"{slug(url)}--fold.png"
            await page.screenshot(path=str(fold))

            full = out / f"{slug(url)}--full.png"
            await page.screenshot(path=str(full), full_page=True)

            height = await page.evaluate("document.documentElement.scrollHeight")
            print(f"{url} -> {fold.name} (fold), {full.name} (full, {height}px)")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2:]))
