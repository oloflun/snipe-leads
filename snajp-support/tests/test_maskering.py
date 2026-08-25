"""Maskeringen ska ta personnummer och INGENTING ANNAT.

Balansen är hela poängen. Ett mönster som fäller för brett gör texten
obegriplig för modellen, svaren sämre — och då tar någon bort maskeringen,
vilket är hur en spärr dör. Testerna nedan är därför två listor: vad som MÅSTE
maskeras, och vad som ALDRIG får maskeras.

Numren är konstruerade för att passera Luhn men hör inte till någon person —
de är räknade fram i testet, inte hämtade någonstans ifrån.
"""

import pytest

from app.moderation.maskering import (
    PLATSHALLARE,
    antal_maskerade,
    ar_personnummer,
    maskera_personnummer,
)


def _med_kontrollsiffra(nio: str) -> str:
    """Bygger ett giltigt tionummer ur nio siffror, så att testdata inte är
    ett riktigt personnummer som råkat skrivas av."""
    summa = 0
    for i, tecken in enumerate(nio):
        varde = int(tecken) * (2 if i % 2 == 0 else 1)
        summa += varde - 9 if varde > 9 else varde
    return nio + str((10 - summa % 10) % 10)


GILTIGT_10 = _med_kontrollsiffra("850101123")          # 850101-XXXX
GILTIGT_SAMORDNING = _med_kontrollsiffra("850161123")  # dag + 60


def test_maskerar_med_bindestreck():
    text = f"Hej, mitt personnummer är {GILTIGT_10[:6]}-{GILTIGT_10[6:]}. Kolla min order."
    ut = maskera_personnummer(text)
    assert PLATSHALLARE in ut
    assert GILTIGT_10[6:] not in ut


def test_maskerar_utan_avskiljare():
    assert maskera_personnummer(f"nr {GILTIGT_10} tack") == f"nr {PLATSHALLARE} tack"


def test_maskerar_tolvsiffrigt():
    assert PLATSHALLARE in maskera_personnummer(f"19{GILTIGT_10}")


def test_maskerar_plus_for_over_hundra():
    assert PLATSHALLARE in maskera_personnummer(f"{GILTIGT_10[:6]}+{GILTIGT_10[6:]}")


def test_maskerar_samordningsnummer():
    """Dag + 60. Bärs ofta av personer som har mest att förlora på en läcka —
    utan datumregeln maskeras de inte alls."""
    assert PLATSHALLARE in maskera_personnummer(GILTIGT_SAMORDNING)


def test_maskerar_flera_i_samma_text():
    text = f"{GILTIGT_10} och {GILTIGT_SAMORDNING}"
    assert maskera_personnummer(text).count(PLATSHALLARE) == 2
    assert antal_maskerade(text) == 2


# -- Vad som ALDRIG får maskeras ---------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Ordernummer 1234567890",          # tio siffror, faller på Luhn/datum
        "Faktura 2024001234",              # ser ut som datum men Luhn faller
        "Ring mig på 070-1234567",         # telefonnummer
        "Beloppet var 1 234 kr",
        "Vi levererar 2026-08-24",         # ett datum
        "Referens ABC-1234",
        "",
    ],
)
def test_maskerar_inte_annat(text):
    assert maskera_personnummer(text) == text


def test_datum_som_inte_finns_maskeras_inte():
    """Sex siffror som passerar Luhn men inte är ett datum ska stå kvar.
    Utan datumkontrollen fälls var tionde ordernummer."""
    kandidat = _med_kontrollsiffra("859901123")  # månad 99
    assert maskera_personnummer(kandidat) == kandidat


def test_idempotent():
    en = maskera_personnummer(f"nr {GILTIGT_10}")
    assert maskera_personnummer(en) == en


def test_ar_personnummer():
    assert ar_personnummer(GILTIGT_10)
    assert ar_personnummer(f"{GILTIGT_10[:6]}-{GILTIGT_10[6:]}")
    assert not ar_personnummer("1234567890")
    assert not ar_personnummer("hej")
