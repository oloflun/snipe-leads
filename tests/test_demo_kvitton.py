"""Kvittodemons siffror räknas OM här, mot exakt aritmetik.

Samma vaktpost som test_demo_bokforing.py var för den gamla demon, och av
samma skäl: `/demo/kvitton` kör ingen backend och ingen modell — talen är
konstanter i `lib/demo/kvitton.ts`, och den enda som annars märker när de
glider isär är en besökare som räknar efter.

Regler som prövas:
  1. SAMMANFATTNING (totalt, moms, antal, per kategori) stämmer med MEJL.
  2. Varje kronbelopp i FRAGOR-svaren går att härleda ur det som står på
     sidan — samma krav som INV-BOOK-003 ställer på det riktiga svaret,
     kontrollerat vid bygget i stället för vid körningen.
  3. Demon är nåbar: DEMO_VAGAR pekar dit och demosidan renderar den.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
KALLA = (ROT / "lib" / "demo" / "kvitton.ts").read_text(encoding="utf-8")


def _mejl() -> list[dict]:
    """MEJL-posterna, lästa med regex. Fältordningen i filen är fast."""
    block = KALLA.split("export const MEJL")[1].split("export const SAMMANFATTNING")[0]
    poster = []
    for obj in re.findall(r"\{(.*?)\n  \}", block, re.DOTALL):
        falt = dict(re.findall(r'(\w+):\s*"([^"]*)"', obj))
        belopp = re.search(r"belopp:\s*(?:\"([\d.]+)\"|null)", obj)
        falt["belopp"] = belopp.group(1) if belopp and belopp.group(1) else None
        poster.append(falt)
    return poster


def _moms(brutto: Decimal, sats: Decimal) -> Decimal:
    """Samma formel som bookkeeping/math.py: brutto × sats ÷ (1 + sats), öresavrundad."""
    return (brutto * sats / (1 + sats)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _sammanfattning() -> dict:
    block = KALLA.split("export const SAMMANFATTNING")[1].split("as const")[0]
    # Toppvärdena läses FÖRE perKategori — kategoriradernas `antal: 1` hade
    # annars skrivit över toppens `antal: 11` i dicten.
    topp = block.split("perKategori")[0]
    värden = dict(re.findall(r'(\w+):\s*"?([\d.]+)"?', topp))
    kategorier = re.findall(
        r'etikett:\s*"([^"]+)",\s*antal:\s*(\d+),\s*summa:\s*"([\d.]+)"', block
    )
    return {"värden": värden, "kategorier": kategorier}


MEJL = _mejl()
SAMMAN = _sammanfattning()
KLARA = [m for m in MEJL if m.get("utfall") == "kvitto"]
GRANSKA = [m for m in MEJL if m.get("utfall") == "kvitto_granska"]


def test_mejlen_ar_de_trettom_vi_tror():
    assert len(MEJL) == 13, f"MEJL har {len(MEJL)} poster, demon är skriven för 13."
    assert len(KLARA) == 8
    assert len(GRANSKA) == 3


def test_totalen_ar_summan_av_de_klara():
    totalt = sum(Decimal(m["belopp"]) for m in KLARA)
    assert str(totalt) == SAMMAN["värden"]["totalt"], (
        f"SAMMANFATTNING.totalt är {SAMMAN['värden']['totalt']}, "
        f"men de klara kvittona summerar till {totalt}."
    )


def test_momsen_ar_omraknad_per_kvitto():
    moms = sum(
        _moms(Decimal(m["belopp"]), Decimal(m["momssats"])) for m in KLARA
    )
    assert str(moms) == SAMMAN["värden"]["moms"], (
        f"SAMMANFATTNING.moms är {SAMMAN['värden']['moms']}, omräkningen ger {moms}."
    )


def test_antalen_stammer():
    v = SAMMAN["värden"]
    assert int(v["antal"]) == len(KLARA) + len(GRANSKA)
    assert int(v["antalKlara"]) == len(KLARA)
    assert int(v["antalGranska"]) == len(GRANSKA)


def test_kategorisummorna_stammer():
    per: dict[str, tuple[int, Decimal]] = {}
    for m in KLARA:
        etikett = m["kategoriEtikett"]
        antal, summa = per.get(etikett, (0, Decimal("0")))
        per[etikett] = (antal + 1, summa + Decimal(m["belopp"]))
    for etikett, antal, summa in SAMMAN["kategorier"]:
        assert etikett in per, f"Kategorin {etikett} finns i sammanfattningen men inte i mejlen."
        assert per[etikett] == (int(antal), Decimal(summa)), (
            f"{etikett}: sammanfattningen säger ({antal}, {summa}), mejlen ger {per[etikett]}."
        )
    assert len(SAMMAN["kategorier"]) == len(per), "En kategori saknas i sammanfattningen."


def _kr_text(v: Decimal) -> str:
    heltal, _, dec = f"{v:.2f}".partition(".")
    grupperat = ""
    for i, tecken in enumerate(reversed(heltal)):
        if i and i % 3 == 0:
            grupperat = " " + grupperat
        grupperat = tecken + grupperat
    return f"{grupperat},{dec}"


def test_fragornas_belopp_ar_harledbara():
    """Varje kronbelopp i svaren måste finnas på sidan eller vara en summa av
    det som gör det. Tillåtna: radbelopp, radens moms, kategorisummor, totalen,
    totala momsen, samt resor + resor & logi (svaret säger uttryckligen att det
    är den summan)."""
    tillatna: set[str] = set()
    for m in KLARA:
        tillatna.add(_kr_text(Decimal(m["belopp"])).replace(" ", " "))
        tillatna.add(_kr_text(_moms(Decimal(m["belopp"]), Decimal(m["momssats"]))).replace(" ", " "))
    for _, _, summa in SAMMAN["kategorier"]:
        tillatna.add(_kr_text(Decimal(summa)).replace(" ", " "))
    tillatna.add(_kr_text(Decimal(SAMMAN["värden"]["totalt"])).replace(" ", " "))
    tillatna.add(_kr_text(Decimal(SAMMAN["värden"]["moms"])).replace(" ", " "))
    resor = {e: Decimal(s) for e, _, s in SAMMAN["kategorier"]}
    tillatna.add(
        _kr_text(resor.get("Resor & transport", Decimal(0)) + resor.get("Logi", Decimal(0))).replace(
            " ", " "
        )
    )

    fragor = KALLA.split("export const FRAGOR")[1]
    belopp_i_svar = re.findall(r"(\d[\d ]*\d,\d{2}) kr", fragor)
    assert belopp_i_svar, "Inga belopp hittades i FRAGOR — testet mäter ingenting."
    for b in belopp_i_svar:
        assert b in tillatna, (
            f"Beloppet {b!r} i ett FRAGOR-svar går inte att härleda ur sidan. "
            f"Tillåtna: {sorted(tillatna)}"
        )


def test_demon_ar_nabar():
    appshell = (ROT / "components" / "AppShell.tsx").read_text(encoding="utf-8")
    assert '"/dashboard/kvitton": "/demo/kvitton"' in appshell, (
        "DEMO_VAGAR saknar kvittovägen — demolänken i railen bryts."
    )
    demosida = (ROT / "app" / "demo" / "[[...slug]]" / "page.tsx").read_text(encoding="utf-8")
    assert 'case "kvitton"' in demosida and "KvittoDemo" in demosida, (
        "/demo/kvitton renderar inte KvittoDemo."
    )
    komponent = (ROT / "components" / "kvitton" / "KvittoDemo.tsx").read_text(encoding="utf-8")
    assert "påhittade" in komponent, (
        "Demon saknar sin exempelmärkning. Siffror som ser ut att komma ur en "
        "körning måste säga att de inte gör det."
    )
