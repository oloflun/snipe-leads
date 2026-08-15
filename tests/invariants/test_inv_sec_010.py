"""INV-SEC-010 — ingen route under app/api/ är anonymt nåbar utan att någon
skrivit ner varför.

Bakgrunden är mätt, inte befarad: före 2026-08-15 gjorde INGEN route under
app/api/ någon sessionskontroll, och proxy.ts-matchern täcker inte /api.
`GET /api/snajp-support/leads/soul` svarade 200 med innehåll mot produktion
utan cookie. Fixen var enkel; att den inte kan glida tillbaka är det som
kräver ett test.

Formen är statisk med flit. Ett test som startar Next och gör riktiga anrop
hade mätt en instans vid ett tillfälle; det här mäter KÄLLKODEN, kör i CI utan
nätverk, och — det avgörande — fäller en NY route som någon lägger till utan
att ta ställning. Det är den fällan som gäller, för hålet uppstod inte genom
att någon tog bort en kontroll utan genom att ingen la till en.

Den anonyma ytan är inte förbjuden. Den publika demon SKA vara anonym. Kravet
är att varje sådan route står i ANON_ALLOWLIST nedan med ett skäl som en
människa skrivit, och att skälet också står i filen.

Levande verifiering (den som faktiskt bevisar produktionen) körs separat:
  bash scripts/verify_inv_sec_010.sh https://<deploy>
Skriptet gör oautentiserade anrop och kräver 401. Det här testet är spärren
som gör att skriptet inte behöver köras för varje commit.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "app" / "api"

#: Routes som är anonyma MED FLIT. Nyckeln är sökvägen relativt app/api/,
#: värdet är skälet — och skälet måste också stå i filen (se testet nedan),
#: annars är den här listan bara en tyst avstängning av kontrollen.
ANON_ALLOWLIST: dict[str, str] = {
    "snajp-support/chat/route.ts": (
        "Den publika demon och kundernas egna chattlänkar. Kunden publicerar "
        "länken själv; att kräva inloggning här hade varit att kräva inloggning "
        "av kundens kunder. Skyddas av rate limit (migration 019), inte session."
    ),
    "snajp-support/jobs/[jobId]/route.ts": (
        "Pollning av ett jobb som chatten ovan startade. Jobb-id är UUID och "
        "backenden kontrollerar att jobbet tillhör den tenant nyckeln pekar på."
    ),
    "snajp-support/triage/route.ts": (
        "Triagering av ett inkommande meddelande innan avsändaren är känd — "
        "samma anonyma yta som chatten, samma tak."
    ),
}

#: Vad som räknas som en sessionsgrind. Alla härleder identiteten ur sessionen
#: på servern; ingen av dem litar på något klienten skickar.
#: `getPlatformAdmin` är den strängaste — den kräver dessutom en rad i
#: platform_admins — och används av /api/admin.
SESSION_GATES = (
    "proxyAsTenant",
    "requireSnajpTenant",
    "getWorkspaceContext",
    "getPlatformAdmin",
)

#: Anonyma routes får aldrig nå den administrativa ytan. `keys` är den farliga:
#: catch-allen kunde tidigare adressera POST /api/keys, och det enda som
#: räddade oss var att SNAJP_INTERNAL_API_KEY råkade vara demonyckeln.
FORBIDDEN_IN_ANON = ("/api/keys", "/api/tenants", "/api/admin")


def _route_files() -> list[Path]:
    return sorted(API_DIR.rglob("route.ts"))


def _rel(path: Path) -> str:
    return path.relative_to(API_DIR).as_posix()


def test_det_finns_routes_att_kontrollera():
    """Om globben slutar hitta filer blir alla test nedan grönt av fel skäl."""
    assert _route_files(), f"Inga route.ts hittades under {API_DIR} — testet mäter ingenting."


@pytest.mark.parametrize("route", _route_files(), ids=_rel)
def test_varje_route_ar_grindad_eller_medvetet_anonym(route: Path):
    rel = _rel(route)
    source = route.read_text(encoding="utf-8")

    if rel in ANON_ALLOWLIST:
        pytest.skip(f"anonym med flit: {ANON_ALLOWLIST[rel]}")

    assert any(gate in source for gate in SESSION_GATES), (
        f"{rel} har ingen sessionsgrind och står inte i ANON_ALLOWLIST.\n"
        f"Lägg till en av {SESSION_GATES}, eller lägg routen i allowlistan "
        f"med ett skrivet skäl — och skriv skälet i filen också.\n"
        f"Att bara lägga till den i listan är att stänga av kontrollen tyst."
    )


@pytest.mark.parametrize("rel", sorted(ANON_ALLOWLIST), ids=lambda r: r)
def test_allowlistad_route_finns_och_motiverar_sig_i_filen(rel: str):
    route = API_DIR / rel
    assert route.exists(), (
        f"{rel} står i ANON_ALLOWLIST men filen finns inte. En stale allowlist "
        f"är hur en NY route med samma namn ärver ett undantag ingen läst."
    )

    source = route.read_text(encoding="utf-8").lower()
    assert "anonym" in source, (
        f"{rel} är allowlistad men säger inte i filen att den är anonym med flit. "
        f"Skälet ska stå där någon läser det, inte bara i det här testet."
    )


@pytest.mark.parametrize("rel", sorted(ANON_ALLOWLIST), ids=lambda r: r)
def test_anonym_route_ror_aldrig_den_administrativa_ytan(rel: str):
    source = (API_DIR / rel).read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_IN_ANON:
        assert forbidden not in source, (
            f"{rel} är anonym och adresserar {forbidden}. Den ytan skapar "
            f"tenants och API-nycklar och får aldrig nås utan session."
        )


def test_proxy_matchern_utokas_inte_till_api():
    """Matchern svarar med en omdirigering till /login. För ett API-anrop är
    det fel form — den hade dolt 401:an bakom en 307 mot en HTML-sida, och
    grinden hade sett ut att finnas utan att göra sitt jobb.

    Grinden hör hemma i routen. Det här testet finns för att den slutsatsen
    är kontraintuitiv nog att någon kommer att vilja "fixa" matchern."""
    proxy = ROOT / "proxy.ts"
    if not proxy.exists():
        pytest.skip("proxy.ts finns inte i den här checkouten")

    source = proxy.read_text(encoding="utf-8")
    matcher = re.search(r"matcher\s*:\s*\[(.*?)\]", source, re.DOTALL)
    assert matcher, "Hittade ingen matcher i proxy.ts — testet mäter ingenting."

    # Bara de faktiska strängposterna. Att söka i råtexten fällde på en
    # KOMMENTAR som förklarade varför /api medvetet utelämnas — testet
    # anklagade alltså filen för det den uttryckligen inte gör.
    entries = re.findall(r'"([^"]+)"', matcher.group(1))
    assert entries, "Matchern innehåller inga poster — testet mäter ingenting."

    offending = [entry for entry in entries if entry.startswith("/api")]
    assert not offending, (
        f"proxy.ts-matchern täcker {offending}. Ta bort det: en omdirigering "
        f"till /login är fel svarsform för ett API-anrop och döljer 401:an. "
        f"Grinden hör hemma i routen."
    )
