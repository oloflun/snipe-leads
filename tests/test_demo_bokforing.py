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
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
DEMO = (ROT / "lib" / "demo" / "bokforing.ts").read_text(encoding="utf-8")


def _strang(namn: str) -> str:
    """Värdet för en nyckel skriven som `namn: "värde"`."""
    match = re.search(rf'{namn}:\s*"([^"]+)"', DEMO)
    assert match, f"Hittar inte {namn} i lib/demo/bokforing.ts"
    return match.group(1)


def _summa(namn: str) -> Decimal:
    block = DEMO.split("summor:")[1]
    match = re.search(rf'{namn}:\s*"([^"]+)"', block)
    assert match, f"Hittar inte summan {namn}"
    return Decimal(match.group(1))


def test_momsen_stammer_med_bruttot_och_satsen():
    """Netto och moms räknas ur brutto, precis som `moms_fran_brutto` gör.

    1250,00 med 25 % moms: netto = 1250 / 1,25 = 1000,00, moms = 250,00.
    """
    brutto = Decimal(_strang("brutto"))
    sats = Decimal(_strang("momssats"))

    netto = (brutto / (1 + sats)).quantize(Decimal("0.01"))
    moms = brutto - netto

    assert netto == Decimal("1000.00"), f"Nettot blev {netto}"
    assert moms == Decimal("250.00"), f"Momsen blev {moms}"


def test_verifikatet_balanserar():
    """Debet = kredit. Det är hela poängen med dubbel bokföring, och ett
    obalanserat exempel på hemsidan vore ett exempel på att vi inte kan det."""
    debet = sum(Decimal(v) for v in re.findall(r'debet:\s*"([^"]+)"', DEMO))
    kredit = sum(Decimal(v) for v in re.findall(r'kredit:\s*"([^"]+)"', DEMO))

    assert debet == kredit, f"Debet {debet} != kredit {kredit}"
    assert debet == Decimal(_strang("brutto")), "Verifikatet summerar inte till bruttot."


def test_periodsummorna_foljer_av_det_enda_underlaget():
    """Ett kostnadsunderlag, ingen försäljning. Allt annat följer av det."""
    assert _summa("intakter") == Decimal("0.00")
    assert _summa("utgaende_moms") == Decimal("0.00")
    assert _summa("kostnader") == Decimal("1000.00")
    assert _summa("ingaende_moms") == Decimal("250.00")

    # Resultat = intäkter - kostnader.
    assert _summa("resultat_fore_skatt") == _summa("intakter") - _summa("kostnader")
    # Moms att betala = utgående - ingående. Negativt = fordran.
    assert _summa("moms_att_betala") == _summa("utgaende_moms") - _summa("ingaende_moms")


def test_chattsvaret_bar_bara_belopp_som_star_i_periodrapporten():
    """Demons svar måste klara INV-BOOK-003, annars visar sidan något
    produkten vägrar göra.

    Talen i svaret jämförs mot summorna ovanför. Ett fjärde belopp i texten
    hade fällts av den riktiga grinden.
    """
    samtal = DEMO.split("export const SAMTAL")[1]
    assistentsvar = " ".join(
        block for block in re.findall(r'text:\s*\n?\s*"(.*?)"\s*\n?\s*\}', samtal, re.DOTALL)
    )

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
    # Absolutbelopp: "-250.00" skrivs som "250,00 kr" i text.
    tillatna |= {abs(t) for t in tillatna}

    for rat in re.findall(r"(\d[\d\s ]*,\d{2})\s*kr", assistentsvar):
        varde = Decimal(rat.replace(" ", "").replace(" ", "").replace(",", "."))
        assert varde in tillatna, (
            f"Beloppet {rat!r} i demochatten finns inte i periodrapporten. "
            "Det riktiga svaret hade fällts av INV-BOOK-003."
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
