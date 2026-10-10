"""Testarfynden 2026-09-13 — Leadslistor, Duo-remsan, tilläggen och adminens testytor.

Varje fynd var ett fel som bara syntes i ett klick eller i en skärmdump, och
ingen av de befintliga sviterna hade fällt det. Filerna läses som text, samma
metod som test_leads_ui_endpoints.py: det här är korsningar mellan Next-appen
och backenden, inte logik som går att enhetstesta utan en TS-testlöpare.

Ligger i repo-rotens svit av samma skäl som test_tillagg_synk.py.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LISTVY = ROOT / "components" / "leads" / "LeadslistorView.tsx"
TILLAGG = ROOT / "lib" / "actions" / "tillagg.ts"
DASHBOARD = ROOT / "lib" / "data" / "dashboard.ts"
HALSA = ROOT / "lib" / "admin" / "halsa.ts"
PORTFOLJ = ROOT / "components" / "admin" / "Portfoljvy.tsx"
KUNDSIDA = ROOT / "app" / "admin" / "kunder" / "[id]" / "page.tsx"


def _las(fil: Path) -> str:
    return fil.read_text(encoding="utf-8")


# -- Fynd 1: Leadslistor ↔ Email studio ------------------------------------
# Mejlrutan per rad (Skriv mejl) och utkastsvepet togs bort 2026-10-10 (Antons
# beslut): raden öppnas i samma låda som ett Iris-lead, och Skapa utkast kör
# samma research och utkast som Iris. Det som vaktas nu är det nya flödet.


def test_listans_atgarder_skickar_uttryckliga_rader_och_foljs_i_listan():
    """Skapa utkast och Processa om skickar alltid de markerade eller synliga
    raderna (förut null utan kontaktfilter, så webbfiltren följde inte med),
    och förloppet läses ur listans `processering`. Flytta till Iris finns inte."""
    text = _las(LISTVY)
    assert "/till-iris" not in text, "Flytta till Iris är borttaget (2026-10-10)."
    assert "item_ids: kontaktfilter" not in text, "Åtgärderna får inte skicka null utan kontaktfilter."
    assert "JSON.stringify({ item_ids })" in text
    assert "lista.processering" in text, "Förloppet i listan läses inte längre."
    assert "/prospekt`" in text, "Raden öppnas inte längre i lådan via sitt prospekt."


# -- Fynd 2: titeln styr sökningen -----------------------------------------


def test_bestallningen_skickar_titeln_som_sokvillkor():
    text = _las(LISTVY)
    assert re.search(r"overrides:\s*\{\s*must_have:\s*\[titel\.trim\(\)\]\s*\}", text), (
        "Listbeställningen skickar inte titeln som must_have — titeln styr då inte sökningen."
    )


# -- Fynd 3: Duo-remsan efter Trio-bytet -----------------------------------
# Remsan (DuoSummary) togs bort med Snajp Suite 2026-10-03: översikten har
# inga länkkort längre, så det finns inget paketnamn att hårdkoda.


# -- Fynd 4: tilläggen -----------------------------------------------------


def test_saknad_migration_063_ger_ett_namngivet_besked():
    text = _las(TILLAGG)
    assert "42883" in text, "undefined_function (42883) känns inte igen."
    assert "063" in text and "railway_migrate.py" in text, (
        "Beskedet vid saknad RPC ska namnge migration 063 och skriptet som kör den."
    )


def test_kundbesok_visar_kundens_riktiga_tillagg():
    text = _las(DASHBOARD)
    start = text.find('if (lage.vy === "kund")')
    slut = text.find('if (lage.vy === "demo")')
    assert start != -1 and slut > start
    kundgren = text[start:slut]
    assert "addons: []" not in kundgren, "Kundbesöket nollställer tilläggen igen."
    assert "tillaggForKundbesok" in kundgren
    # Läsningen ska gå via den grindade RPC:n, inte en rak SELECT på kolumnen.
    assert "hamtaTillagg" in text
    assert not re.search(r"select[^\"]*addons[^\"]*from public\.workspaces", text)


def test_tillaggen_overlever_en_trasig_profilhamtning():
    text = _las(KUNDSIDA)
    fel = text.find("if (error || !profil)")
    assert fel != -1
    felgren = text[fel : text.find("return (", text.find("return (", fel) + 1)]
    assert "<Tillaggsvaljare" in felgren, (
        "Tilläggen försvinner med agentprofilen när backenden inte svarar."
    )


# -- Fynd 5: testarbetsytor i adminen --------------------------------------


def test_testarbetsytan_har_ett_eget_halsolage():
    text = _las(HALSA)
    assert re.search(r'export type Halsa = [^;]*"test"', text)
    assert "testkorningar" in text


def test_portfoljen_foredrar_lagrade_produkter():
    text = _las(PORTFOLJ)
    assert "rad.products" in text, "Paketet härleds fortfarande bara ur aktivitet."
    assert "arTestyta(rad.slug)" in text
