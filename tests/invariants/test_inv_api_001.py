"""INV-API-001 — ett svar tolkas aldrig som JSON utan att kroppen kontrolleras,
och en route som väntar på en modell deklarerar alltid `maxDuration`.

Bakgrunden är två fel som SER ut som ett, och det är därför de hör ihop i en
invariant:

1. `app/api/email-studio/route.ts` saknade `maxDuration`. Den väntar på ett
   LLM-anrop, och Vercels standardtak är kortare än en omskrivning tar. Vercel
   dödade funktionen mitt i — och ett dödat anrop svarar UTAN kropp.
2. `EmailStudioEditor` anropade `res.json()` FÖRE `res.ok`. Mot den tomma
   kroppen kastade den `Unexpected end of JSON input`, och eftersom catch-grenen
   visade `e.message` rakt av fick kunden se webbläsarens interna felsträng.

Felet pekade alltså på frontend medan orsaken satt i routens konfiguration.
Samma par kan uppstå i proxyn mot Render, som somnar efter 15 minuter och
svarar med en HTML-sida medan den vaknar — också det "inte JSON".

Formen är statisk med flit, av samma skäl som INV-SEC-010: den fäller en NY
route eller en ny fetch som någon lägger till utan att ta ställning. Det är den
fällan som gäller — hålet uppstod inte genom att någon tog bort en kontroll
utan genom att ingen la till en.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "app" / "api"
UI_DIRS = (ROOT / "app", ROOT / "lib", ROOT / "components")

#: Den gemensamma läsvägen. Båda kontrollerar status, tom kropp och icke-JSON;
#: `readJsonBody` behåller dessutom felkroppen åt anropare som har egen
#: felsemantik i den (proxyns `{ offline: true }` kommer med 503).
SAFE_READERS = ("readJson", "readJsonBody")

#: Routes som väntar på en modell eller på Render-backenden. Utan maxDuration
#: dödas de mitt i och svarar utan kropp.
SLOW_MARKERS = ("generateText", "proxyWithApiKey", "proxyToBackend", "proxyAsTenant")

#: `request.json()` är INKOMMANDE kropp i en route — Next kastar där ett
#: hanterbart fel, och routen har ingen Response att kontrollera status på.
#: Det är inte det mönster den här invarianten handlar om.
INCOMING_BODY = re.compile(r"\brequest\.json\(\)")

#: `await <namn>.json()` — alltså ett fetch-svar som tolkas direkt.
RESPONSE_JSON = re.compile(r"await\s+([A-Za-z_$][\w$]*)\.json\(\)")

#: Filer som får läsa ett svar rått, med skäl. Skälet måste också stå i filen.
RAW_JSON_ALLOWLIST: dict[str, str] = {
    "lib/http/json.ts": (
        "Själva helpern. Den läser kroppen som text och tolkar den — det är "
        "implementationen av regeln, inte ett undantag från den."
    ),
}


#: Kommentarer och strängar måste bort före sökningen. INV-SEC-010 lärde sig
#: detta på det hårda sättet: testet fällde på en KOMMENTAR som förklarade
#: varför regeln gällde, och anklagade alltså filen för det den beskrev. Här är
#: risken större, eftersom fixen ovan uttryckligen NÄMNER `await
#: response.json()` i sin egen förklaring av vad som togs bort.
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")


def _utan_kommentarer(source: str) -> str:
    """Behåller radnumreringen — nyradstecken lämnas kvar."""

    def _behall_nyrader(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    utan_block = _BLOCK_COMMENT.sub(_behall_nyrader, source)
    return _LINE_COMMENT.sub("", utan_block)


def _source_files() -> list[Path]:
    files: list[Path] = []
    for directory in UI_DIRS:
        if not directory.exists():
            continue
        for pattern in ("*.ts", "*.tsx"):
            files.extend(directory.rglob(pattern))
    return sorted(f for f in files if "node_modules" not in f.parts)


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _route_files() -> list[Path]:
    return sorted(API_DIR.rglob("route.ts"))


def _route_rel(path: Path) -> str:
    return path.relative_to(API_DIR).as_posix()


def test_det_finns_filer_att_kontrollera():
    """Slutar globben hitta filer blir allt nedan grönt av fel skäl."""
    assert _source_files(), f"Inga käll-filer hittades under {UI_DIRS} — testet mäter ingenting."
    assert _route_files(), f"Inga route.ts hittades under {API_DIR} — testet mäter ingenting."


@pytest.mark.parametrize("route", _route_files(), ids=_route_rel)
def test_langsam_route_deklarerar_maxduration(route: Path):
    source = _utan_kommentarer(route.read_text(encoding="utf-8"))

    triggers = [marker for marker in SLOW_MARKERS if marker in source]
    if not triggers:
        pytest.skip("routen väntar varken på en modell eller på backenden")

    assert re.search(r"export\s+const\s+maxDuration\s*=\s*\d+", source), (
        f"{_route_rel(route)} anropar {triggers} men deklarerar ingen maxDuration.\n"
        f"Vercels standardtak är kortare än ett modellanrop tar. Funktionen dödas "
        f"då mitt i och svarar UTAN kropp — klientens .json() kastar "
        f"'Unexpected end of JSON input', och felet ser ut att sitta i frontend.\n"
        f"Lägg till: export const maxDuration = 60;"
    )


@pytest.mark.parametrize("path", _source_files(), ids=_rel)
def test_svar_tolkas_aldrig_som_json_utan_kontroll(path: Path):
    rel = _rel(path)
    if rel in RAW_JSON_ALLOWLIST:
        pytest.skip(f"rå läsning med flit: {RAW_JSON_ALLOWLIST[rel]}")

    source = _utan_kommentarer(path.read_text(encoding="utf-8"))

    offending: list[str] = []
    for match in RESPONSE_JSON.finditer(source):
        # Inkommande request-kropp är ett annat mönster, se INCOMING_BODY.
        if INCOMING_BODY.search(match.group(0)):
            continue
        rad = source[: match.start()].count("\n") + 1
        # `.json().catch(...)` hanterar redan en otolkbar kropp.
        efter = source[match.end() : match.end() + 40]
        if efter.lstrip().startswith(".catch"):
            continue
        offending.append(f"rad {rad}: {match.group(0)}")

    assert not offending, (
        f"{rel} tolkar ett fetch-svar som JSON utan att kontrollera kroppen:\n"
        + "\n".join(f"  {o}" for o in offending)
        + f"\n\nEtt svar kan vara tomt (funktionen dödades vid maxDuration), vara "
        f"HTML (Render vaknar ur viloläge) eller vara 204. I alla tre fallen "
        f"kastar .json() 'Unexpected end of JSON input', och meddelandet visas "
        f"för kunden.\n"
        f"Använd någon av {SAFE_READERS} från lib/http/json.ts, eller lägg "
        f"`.catch()` direkt efter .json() om kroppen får saknas."
    )


@pytest.mark.parametrize("rel", sorted(RAW_JSON_ALLOWLIST), ids=lambda r: r)
def test_allowlistad_fil_finns_och_motiverar_sig(rel: str):
    path = ROOT / rel
    assert path.exists(), (
        f"{rel} står i RAW_JSON_ALLOWLIST men filen finns inte. En stale "
        f"allowlist är hur en NY fil med samma namn ärver ett undantag ingen läst."
    )
    source = path.read_text(encoding="utf-8").lower()
    assert "unexpected end of json input" in source, (
        f"{rel} är allowlistad men förklarar inte i filen vilket fel den finns "
        f"för att hantera. Skälet ska stå där någon läser det."
    )


def test_helpern_finns_och_hanterar_de_tre_fallen():
    """Utan den här filen är allt ovan bara en regel utan väg att följa den."""
    helper = ROOT / "lib" / "http" / "json.ts"
    assert helper.exists(), "lib/http/json.ts saknas — det finns ingen säker väg att hänvisa till."

    source = helper.read_text(encoding="utf-8")
    for reader in SAFE_READERS:
        assert f"export async function {reader}" in source, (
            f"{reader} exporteras inte längre från lib/http/json.ts, men "
            f"invarianten hänvisar anropare dit."
        )
    # Texten läses före tolkningen — annars kastar felgrenen
    # 'body stream already read' och döljer det ursprungliga felet.
    assert "response.text()" in source, (
        "Helpern läser inte kroppen som text först. Kroppen kan bara läsas en "
        "gång: .json() följt av .text() i felgrenen döljer det riktiga felet."
    )
