"""Demons siffror är handräknade. Det här testet räknar om dem.

## Varför de är handräknade från början

`/demo/bokforing` kör ingen backend och ingen modell: sidan är publik och
anonym, och en levande körning per besökare kostar pengar utan att visa mer.
Talen är därför konstanter i `lib/demo/bokforing.ts`.

En konstant kan bli fel utan att något säger ifrån. Alternativet — att räkna i
webbläsaren med en TypeScript-kopia av `bookkeeping/math.py` — hade varit en
andra uträkning som glider isär från den riktiga, och den enda som märker det
är en besökare som räknar efter.

Testet läser konstanterna ur TS-filen och räknar om dem med `Decimal`, samma
regler som `bookkeeping/math.py`. Går de isär fälls bygget, inte besökaren.

## Sedan 2026-09-15 är underlagen TRE

Demon fick en underlagsväljare (skuld 2440, fordran 1510, direktbetalning
1930), så testet itererar UNDERLAG-blocken i stället för att anta ett enda
kvitto. Varje underlag balanseras för sig, och periodrapporten måste vara
exakt summan av dem.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
DEMO = (ROT / "lib" / "demo" / "bokforing.ts").read_text(encoding="utf-8")


def _underlagsblock() -> list[str]:
    """Ett textblock per objekt i UNDERLAG, avgränsat på `id:`-raderna."""
    lista = DEMO.split("export const UNDERLAG")[1].split("export const PERIOD")[0]
    delar = re.split(r'\n\s*id:\s*"', lista)[1:]
    assert len(delar) >= 3, "UNDERLAG ska bära minst tre underlag."
    return delar


def _falt(block: str, namn: str) -> str:
    match = re.search(rf'{namn}:\s*"([^"]+)"', block)
    assert match, f"Hittar inte {namn} i underlagsblocket."
    return match.group(1)


def _summa(namn: str) -> Decimal:
    block = DEMO.split("summor:")[1]
    match = re.search(rf'{namn}:\s*"([^"]+)"', block)
    assert match, f"Hittar inte summan {namn}"
    return Decimal(match.group(1))


def test_momsen_stammer_med_bruttot_och_satsen_i_varje_underlag():
    """Netto och moms räknas ur brutto, precis som `moms_fran_brutto` gör —
    för VARJE underlag, inte bara det första."""
    for block in _underlagsblock():
        brutto = Decimal(_falt(block, "brutto"))
        sats = Decimal(_falt(block, "momssats"))

        netto = (brutto / (1 + sats)).quantize(Decimal("0.01"))
        moms = brutto - netto

        # Momsen ska stå som egen verifikatrad (2641 eller 2611) med exakt
        # det beloppet, och nettot på kostnads- eller intäktskontot.
        belopp = {Decimal(v) for v in re.findall(r'(?:debet|kredit):\s*"([^"]+)"', block)}
        assert netto in belopp, f"Nettot {netto} står inte i verifikatet."
        assert moms in belopp, f"Momsen {moms} står inte i verifikatet."


def test_varje_verifikat_balanserar():
    """Debet = kredit = brutto, i varje underlag för sig. Det är hela poängen
    med dubbel bokföring, och ett obalanserat exempel på hemsidan vore ett
    exempel på att vi inte kan det."""
    for block in _underlagsblock():
        debet = sum(Decimal(v) for v in re.findall(r'debet:\s*"([^"]+)"', block))
        kredit = sum(Decimal(v) for v in re.findall(r'kredit:\s*"([^"]+)"', block))

        assert debet == kredit, f"Debet {debet} != kredit {kredit} i {_falt(block, 'filnamn')}"
        assert debet == Decimal(_falt(block, "brutto")), (
            f"Verifikatet i {_falt(block, 'filnamn')} summerar inte till bruttot."
        )


def test_periodsummorna_ar_summan_av_underlagen():
    """Rapporten får inte påstå något underlagen inte bär. Intäkter, kostnader
    och moms räknas om ur varje undarlags brutto/sats/riktning."""
    intakter = Decimal("0")
    kostnader = Decimal("0")
    utgaende = Decimal("0")
    ingaende = Decimal("0")

    for block in _underlagsblock():
        brutto = Decimal(_falt(block, "brutto"))
        sats = Decimal(_falt(block, "momssats"))
        riktning = _falt(block, "riktning")

        netto = (brutto / (1 + sats)).quantize(Decimal("0.01"))
        moms = brutto - netto

        if riktning == "intakt":
            intakter += netto
            utgaende += moms
        else:
            kostnader += netto
            ingaende += moms

    assert _summa("intakter") == intakter
    assert _summa("kostnader") == kostnader
    assert _summa("utgaende_moms") == utgaende
    assert _summa("ingaende_moms") == ingaende

    # Resultat = intäkter - kostnader.
    assert _summa("resultat_fore_skatt") == _summa("intakter") - _summa("kostnader")
    # Moms att betala = utgående - ingående. Negativt = fordran.
    assert _summa("moms_att_betala") == _summa("utgaende_moms") - _summa("ingaende_moms")

    # Antalen ska följa listan, inte en gammal konstant.
    antal = len(_underlagsblock())
    match = re.search(r"antal_underlag:\s*(\d+)", DEMO)
    assert match and int(match.group(1)) == antal, "antal_underlag stämmer inte med listan."


def test_chattsvaren_bar_bara_belopp_som_star_pa_sidan():
    """Demons svar måste klara INV-BOOK-003, annars visar sidan något
    produkten vägrar göra.

    Grinden i produkten körs vid SVARSTILLFÄLLET. Här finns inget svarstillfälle
    — svaren är konstanter — så kontrollen flyttar till bygget. Ett påhittat tal
    fäller alltså testet i stället för besökaren.

    Tillåtna belopp är de som redan STÅR på sidan: periodrapportens summor och
    verifikatens rader (inklusive brutto). Hela FRAGOR-blocket läses som text,
    både frågor och svar — ett belopp i en FRÅGA måste ändå finnas på sidan.
    """
    samtal = DEMO.split("export const FRAGOR")[1]
    assistentsvar = " ".join(re.findall(r'"([^"]*)"', samtal))

    tillatna = {
        _summa(namn)
        for namn in (
            "intakter",
            "kostnader",
            "utgaende_moms",
            "ingaende_moms",
            "resultat_fore_skatt",
            "moms_att_betala",
        )
    }
    for block in _underlagsblock():
        tillatna.add(Decimal(_falt(block, "brutto")))
        tillatna |= {Decimal(v) for v in re.findall(r'(?:debet|kredit):\s*"([^"]+)"', block)}
    # Absolutbelopp: "-250.00" skrivs som "250,00 kr" i text.
    tillatna |= {abs(t) for t in tillatna}

    for rat in re.findall(r"(\d[\d\s ]*,\d{2})\s*kr", assistentsvar):
        varde = Decimal(rat.replace(" ", "").replace(" ", "").replace(",", "."))
        assert varde in tillatna, (
            f"Beloppet {rat!r} i demochatten står inte i rapporten eller något "
            "verifikat. Det riktiga svaret hade fällts av INV-BOOK-003."
        )


def test_demon_ar_markt_som_exempel():
    """Samma regel som leads-agentens exempelbolag: en siffra som ser ut att
    komma ur en körning måste säga att den inte gör det."""
    komponent = (ROT / "components" / "bookkeeping" / "BokforingDemo.tsx").read_text(
        encoding="utf-8"
    )
    assert "Exempel." in komponent, "Demon är inte märkt som exempel."
    assert "påhittade" in komponent, "Demon säger inte att datan är påhittad."


def test_demoroutens_lank_pekar_pa_demon_och_inte_pa_dashboarden():
    """Annars studsar besökaren till /login mitt i det de skulle prova.

    Exakt buggen som fixades i a6a9ea2 för de andra demoytorna.
    """
    appshell = (ROT / "components" / "AppShell.tsx").read_text(encoding="utf-8")
    karta = appshell.split("const DEMO_VAGAR")[1].split("};")[0]
    assert '"/dashboard/bokforing": "/demo/bokforing"' in karta, (
        "Bokföringsfliken saknas i DEMO_VAGAR — den pekar då på /dashboard och "
        "kastar ut besökaren till inloggningen."
    )


def test_besiktningen_kanner_till_bokforingsytorna():
    """Annars upprepas luckan 9ee12fd hittade: en yta som aldrig besiktigas."""
    qa = (ROT / "scripts" / "qa_vyer.mjs").read_text(encoding="utf-8")
    for vag in ("/demo/bokforing", "/dashboard/bokforing", "/admin/bokforing"):
        assert f'"{vag}"' in qa, f"{vag} besiktigas inte av qa_vyer.mjs."
