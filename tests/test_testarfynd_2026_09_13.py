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
DUO = ROOT / "components" / "dashboard" / "DuoSummary.tsx"
TILLAGG = ROOT / "lib" / "actions" / "tillagg.ts"
DASHBOARD = ROOT / "lib" / "data" / "dashboard.ts"
HALSA = ROOT / "lib" / "admin" / "halsa.ts"
PORTFOLJ = ROOT / "components" / "admin" / "Portfoljvy.tsx"
KUNDSIDA = ROOT / "app" / "admin" / "kunder" / "[id]" / "page.tsx"


def _las(fil: Path) -> str:
    return fil.read_text(encoding="utf-8")


# -- Fynd 1: Leadslistor ↔ Email studio ------------------------------------


def test_skriv_mejl_grindas_inte_langre_pa_adress():
    """Knappen syntes bara där `rad.contact_email` fanns. En lista utan
    adresser hade alltså ingen väg till Email studio alls."""
    text = _las(LISTVY)
    assert "Skriv mejl" in text
    # `(?<!!)`: mejlrutans "Ändra adressen" visas med flit bara när adressen
    # SAKNAS (`!rad.contact_email ? (<button`) — det är inte grinden som
    # testet vaktar mot.
    assert not re.search(r"(?<!!)rad\.contact_email\s*\?\s*\(\s*<button", text), (
        "Skriv mejl-knappen är åter villkorad på adressen."
    )
    assert not re.search(r"mejlbro\s*&&\s*rad\.contact_email", text), (
        "Mobilkortets Skriv mejl-knapp är åter villkorad på adressen."
    )


def test_rad_utan_adress_sparar_adressen_innan_utkastet():
    """Avregistreringsfoten byggs på mottagaradressen när utkastet köas —
    ett utkast utan adress hade legat i kön utan fot. Adressen ska därför
    sparas på prospektet (PATCH) innan kedjan skriver något."""
    text = _las(LISTVY)
    patch = text.find('method: "PATCH"')
    utkast = text.find('"/leads/outreach/draft"')
    assert patch != -1, "Listvyn sparar inte längre en angiven adress på prospektet."
    assert utkast != -1
    assert patch < utkast, "Adressen måste sparas FÖRE utkastjobbet."


def test_snabbmail_ar_tackat_och_stannar_pa_kapacitetsfel():
    text = _las(LISTVY)
    tak = re.search(r"const SVEP_TAK = (\d+);", text)
    assert tak and int(tak.group(1)) <= 25, "Svepet saknar tak eller taket har höjts över 25."
    assert "status === 429" in text and "status === 503" in text, (
        "Svepet stannar inte längre på budgettak (429) eller saknad LLM (503)."
    )
    assert "credits are depleted" in text, "Kreditslutstexten känns inte igen av svepet."


def test_mejlrutan_och_svepet_delar_en_kedja():
    """Två kopior av utkastkedjan glider isär — POST:en får bara finnas en gång."""
    text = _las(LISTVY)
    assert text.count('"/leads/outreach/draft"') == 1


# -- Fynd 2: titeln styr sökningen -----------------------------------------


def test_bestallningen_skickar_titeln_som_sokvillkor():
    text = _las(LISTVY)
    assert re.search(r"overrides:\s*\{\s*must_have:\s*\[titel\.trim\(\)\]\s*\}", text), (
        "Listbeställningen skickar inte titeln som must_have — titeln styr då inte sökningen."
    )


# -- Fynd 3: Duo-remsan efter Trio-bytet -----------------------------------


def test_duo_remsan_hardkodar_inget_paketnamn():
    text = _las(DUO)
    for namn in ("Snajp Duo", "Snajp Trio", "Snajp Leads", "Snajp Support"):
        assert namn not in text, (
            f"DuoSummary hårdkodar {namn!r}. Paketnamnet ska härledas ur products via lib/pricing.ts."
        )
    assert "paketForProdukter(products)" in text


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
