"""Genererar delningsbilden public/og/snajp.jpg (1200 x 630).

Bilden som visas när en länk till snajp.se delas i LinkedIn, Slack, Teams,
iMessage eller en AI-assistents svar. Den fanns inte före 2026-11-05: en delad
länk visade bara en grå ruta.

Byggd av hjältefotot och sajtens egna tokens (DESIGN.md), inte av en mall.
Inga priser i bilden: en statisk bild med ett pris blir fel samma dag som
lib/pricing.ts ändras, och priserna i länkarna ska följa hemsidan av sig
själva (lib/seo.ts, `prisrad`).

    python scripts/generera_og.py

Kräver Playwright för Python (`pip install playwright` och
`playwright install chromium`) och nätet för Google Fonts.
"""

from __future__ import annotations

import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

ROT = Path(__file__).resolve().parents[1]


def data_uri(fil: Path, typ: str) -> str:
    # Inbäddat och inte file://: en sida laddad med set_content har ursprunget
    # about:blank och får inte läsa filer från disken.
    return f"data:{typ};base64,{base64.b64encode(fil.read_bytes()).decode('ascii')}"


FOTO = data_uri(ROT / "public" / "photos" / "goteborg-golden.webp", "image/webp")
LOGGA = data_uri(ROT / "public" / "snajp-logo-v1-white.svg", "image/svg+xml")
UT = ROT / "public" / "og" / "snajp.jpg"

HTML = f"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@500&family=Source+Serif+4:ital,opsz,wght@0,8..60,600;1,8..60,600&display=block" rel="stylesheet">
<style>
  :root {{
    --ink: oklch(0.20 0.018 252);
    --paper: oklch(0.965 0.008 88);
    --paper-muted: oklch(0.72 0.008 88);
    --ochre: oklch(0.74 0.16 64);
    --display: "Source Serif 4", serif;
    --body: "Geist", sans-serif;
  }}
  * {{ margin: 0; box-sizing: border-box; }}
  body {{ width: 1200px; height: 630px; overflow: hidden; background: var(--ink); }}
  .plat {{ position: relative; width: 1200px; height: 630px; }}
  .plat img.foto {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 40%; }}
  .slöja {{ position: absolute; inset: 0; background: linear-gradient(to bottom, oklch(0.20 0.018 252 / 0.55) 0%, oklch(0.20 0.018 252 / 0.25) 35%, oklch(0.20 0.018 252 / 0.86) 100%); }}
  .innehåll {{ position: absolute; inset: 0; padding: 64px 72px; display: flex; flex-direction: column; justify-content: space-between; }}
  .logga {{ height: 44px; width: auto; align-self: flex-start; }}
  h1 {{ font-family: var(--display); font-weight: 600; font-size: 88px; line-height: 0.98; letter-spacing: -0.03em; color: var(--paper); max-width: 15ch; }}
  h1 em {{ font-style: italic; color: var(--ochre); }}
  p {{ margin-top: 26px; font-family: var(--body); font-weight: 500; font-size: 26px; color: var(--paper-muted); }}
</style></head>
<body><div class="plat">
  <img class="foto" src="{FOTO}" alt="">
  <div class="slöja"></div>
  <div class="innehåll">
    <img class="logga" src="{LOGGA}" alt="Snajp">
    <div>
      <h1>Leads och kundtjänst, på <em>svenska</em>.</h1>
      <p>Svensk AI-SDR och AI-kundtjänst för B2B · snajp.se</p>
    </div>
  </div>
</div></body></html>"""


def main() -> None:
    UT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        webblasare = p.chromium.launch()
        sida = webblasare.new_page(viewport={"width": 1200, "height": 630})
        sida.set_content(HTML, wait_until="networkidle")
        sida.evaluate("document.fonts.ready")
        sida.screenshot(path=str(UT), type="jpeg", quality=86)
        webblasare.close()
    print(f"Skrev {UT.relative_to(ROT)} ({UT.stat().st_size // 1024} kB)")


if __name__ == "__main__":
    main()
