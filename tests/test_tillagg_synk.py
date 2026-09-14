"""Tilläggskatalogen och databasens check-villkor får inte glida isär.

`lib/addons.ts` säger vad UI:t erbjuder. `workspaces_addons_check` säger vad
databasen tar emot. Glider de isär blir felet asymmetriskt och obehagligt:

  * ett värde som finns i UI:t men inte i villkoret ger ett check-brott vid
    sparning — alltså en växel som ser påslagbar ut och inte är det,
  * ett värde som finns i villkoret men inte i katalogen är ett tillägg som
    ingen kan sälja, och som filtreras bort tyst av `isAddonKey` i läsvägen.

Det är samma felklass som `agent_runs.agent_type` levde med i ett halvår:
två uppräkningar av samma sanning, utan något som jämför dem. Kommentaren i
lib/addons.ts säger redan "ändras i SAMMA ändring" — det här testet är den
meningen som kod.

Ligger i repo-rotens svit och inte i backendens: mätningen korsar Next-appen
och migrationskedjan, och ingendera äger den ensam.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS_TS = ROOT / "lib" / "addons.ts"
MIGRATIONS = ROOT / "supabase" / "migrations"

#: `addonKeys = [ "inbox", ... ] as const` — nycklarna UI:t känner till.
_ADDON_KEYS_RE = re.compile(r"export const addonKeys\s*=\s*\[(.*?)\]\s*as const", re.DOTALL)

#: Det senaste check-villkoret vinner: 022 skapade det, 060 utökade det med
#: `leadlists`, och nästa tillägg gör om samma sak. Testet ska mäta mot det
#: som FAKTISKT gäller, inte mot det första som skrevs.
_CHECK_RE = re.compile(
    r"add constraint workspaces_addons_check check\s*\(\s*addons\s*<@\s*array\[(.*?)\]::text\[\]",
    re.DOTALL,
)

_STRANG_RE = re.compile(r"'([a-z_]+)'|\"([a-z_]+)\"")


def _katalogens_nycklar() -> set[str]:
    text = ADDONS_TS.read_text(encoding="utf-8")
    match = _ADDON_KEYS_RE.search(text)
    assert match, "addonKeys hittades inte i lib/addons.ts — har listan döpts om?"
    nycklar = {a or b for a, b in _STRANG_RE.findall(match.group(1))}
    assert nycklar, "addonKeys parsades som tom — testet hade blivit grönt utan att mäta."
    return nycklar


def _villkorets_varden() -> tuple[set[str], Path]:
    """Värdemängden ur den SENAST numrerade migrationen som sätter villkoret."""
    traffar: list[tuple[str, Path, str]] = []
    for fil in sorted(MIGRATIONS.glob("*.sql")):
        text = fil.read_text(encoding="utf-8")
        match = _CHECK_RE.search(text)
        if match:
            traffar.append((fil.name, fil, match.group(1)))
    assert traffar, "workspaces_addons_check hittades inte i någon migration."

    _, fil, kropp = traffar[-1]
    varden = {a or b for a, b in _STRANG_RE.findall(kropp)}
    assert varden, f"check-villkoret i {fil.name} parsades som tomt."
    return varden, fil


def test_katalogen_och_check_villkoret_har_samma_varden():
    katalog = _katalogens_nycklar()
    villkor, fil = _villkorets_varden()

    bara_i_ui = sorted(katalog - villkor)
    bara_i_db = sorted(villkor - katalog)

    assert not bara_i_ui, (
        f"{bara_i_ui} finns i lib/addons.ts men inte i {fil.name}:s check-villkor. "
        "Växeln går att slå på och sparningen fälls av databasen."
    )
    assert not bara_i_db, (
        f"{bara_i_db} finns i {fil.name}:s check-villkor men inte i lib/addons.ts. "
        "Tillägget går inte att sälja, och läsvägens isAddonKey filtrerar bort det tyst."
    )


def test_varje_nyckel_har_en_katalogpost():
    """`addonKeys` är typen, `addonCatalog` är det människan läser. En nyckel
    utan post kastar i `addonSpec` — och gör det först när någon öppnar vyn."""
    text = ADDONS_TS.read_text(encoding="utf-8")
    katalogposter = set(re.findall(r"key:\s*\"([a-z_]+)\"", text))
    saknas = sorted(_katalogens_nycklar() - katalogposter)
    assert not saknas, f"{saknas} saknar post i addonCatalog (addonSpec kastar på dem)."


def test_skrivvagen_finns_och_grindas_pa_platform_admins():
    """Migrationen som ger tilläggen en skrivväg måste grinda den.

    Hela skälet att kolumnen saknade skrivväg i ett halvår var att ingen
    ville öppna `workspaces` för skrivning. En funktion som skriver den utan
    admin-kontroll hade varit sämre än ingen funktion alls.
    """
    filer = [f for f in MIGRATIONS.glob("*.sql") if "set_workspace_addons" in f.read_text(encoding="utf-8")]
    assert filer, "ingen migration definierar set_workspace_addons."

    text = "\n".join(f.read_text(encoding="utf-8") for f in filer)
    assert "security definer" in text, "funktionen måste vara security definer för att nå kolumnen."
    assert text.count("from public.platform_admins where user_id = anvandare") >= 2, (
        "både läs- och skrivfunktionen ska grinda på platform_admins."
    )
