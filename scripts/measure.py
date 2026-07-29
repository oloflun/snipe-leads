"""Quantify the visual richness of a page so old/new can be compared with numbers.

    python scripts/measure.py <url> [<url> ...]
"""
import asyncio
import json
import sys

from playwright.async_api import async_playwright

PROBE = r"""
() => {
  const main = document.querySelector('main') || document.body;
  const els = [...main.querySelectorAll('*')];
  const vis = els.filter(el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  });
  const textEls = vis.filter(el =>
    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())
  );

  const sizes = {}, colors = {}, families = {}, weights = {};
  let serifCount = 0, accentCount = 0, accentDisplayCount = 0;
  let minLeft = 1e9, maxRight = 0;

  for (const el of textEls) {
    const s = getComputedStyle(el);
    const px = Math.round(parseFloat(s.fontSize));
    sizes[px] = (sizes[px] || 0) + 1;
    colors[s.color] = (colors[s.color] || 0) + 1;
    const fam = s.fontFamily.split(',')[0].replace(/["']/g, '');
    families[fam] = (families[fam] || 0) + 1;
    weights[s.fontWeight] = (weights[s.fontWeight] || 0) + 1;
    if (/Fraunces|serif/i.test(s.fontFamily)) serifCount++;
    const isAccent = s.color.includes('0.74 0.16 64') || /rgb\(2[0-9]{2},\s*1[0-9]{2}/.test(s.color);
    if (isAccent) { accentCount++; if (px >= 28) accentDisplayCount++; }
    const r = el.getBoundingClientRect();
    if (r.width > 30) { minLeft = Math.min(minLeft, r.left); maxRight = Math.max(maxRight, r.right); }
  }

  // structural lines: any element acting as a hairline rule
  const rules = vis.filter(el => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const hasBorder = ['borderTopWidth','borderBottomWidth'].some(p => parseFloat(s[p]) > 0 && parseFloat(s[p]) <= 2);
    const isBar = r.height <= 2 && r.width > 40;
    return hasBorder || isBar;
  }).length;

  const bgs = {};
  for (const el of vis) {
    const s = getComputedStyle(el);
    if (s.backgroundColor !== 'rgba(0, 0, 0, 0)') bgs[s.backgroundColor] = (bgs[s.backgroundColor] || 0) + 1;
    if (s.backgroundImage && s.backgroundImage !== 'none') bgs['[gradient/image]'] = (bgs['[gradient/image]'] || 0) + 1;
  }

  const sizeList = Object.keys(sizes).map(Number).sort((a, b) => b - a);
  return {
    height: document.documentElement.scrollHeight,
    textElements: textEls.length,
    distinctFontSizes: sizeList.length,
    fontSizeRange: [sizeList[sizeList.length - 1], sizeList[0]],
    topSizes: sizeList.slice(0, 8),
    distinctTextColors: Object.keys(colors).length,
    distinctWeights: Object.keys(weights).length,
    families,
    serifTextElements: serifCount,
    accentTextElements: accentCount,
    accentAtDisplayScale: accentDisplayCount,
    hairlineRules: rules,
    distinctBackgrounds: Object.keys(bgs).length,
    contentLeft: Math.round(minLeft),
    contentRight: Math.round(maxRight),
    contentWidthUsed: Math.round(maxRight - minLeft),
    images: main.querySelectorAll('img,svg,canvas,video').length
  };
}
"""


async def main(urls):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1440, "height": 900},
            reduced_motion="no-preference",
        )
        out = {}
        for url in urls:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(1500)
            out[url] = await page.evaluate(PROBE)
        await browser.close()
        print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
