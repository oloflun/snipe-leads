import pytest

from app.simulation.sim_triage import classify


def test_betalning():
    result = classify("Dubbeldragning", "Min faktura drogs två gånger från kortet.")
    assert result["category"] == "betalning"
    assert not result["escalate"]


def test_leverans():
    result = classify("Var är paketet?", "Mitt paket är försenat och spårningen uppdateras inte.")
    assert result["category"] == "leverans"


def test_teknisk_support():
    result = classify("", "Jag kan inte logga in, får felkod E-101 i kassan.")
    assert result["category"] == "teknisk_support"


def test_retur():
    result = classify("Trasig vara", "Varan kom fram skadad och jag vill göra en reklamation.")
    assert result["category"] == "retur_reklamation"


def test_konto_gdpr_eskaleras():
    # Kategorin konto finns inte i databasens check-villkor, så GDPR-ärenden
    # hamnar i ovrigt. Det som faktiskt spelar roll är att de eskaleras.
    result = classify("GDPR", "Jag vill radera mitt konto och alla personuppgifter.")
    assert result["category"] == "ovrigt"
    assert result["escalate"]


def test_garanti_far_eget_fack():
    result = classify("Garanti", "Hur lång är garantin på hjärtstartaren jag köpte?")
    assert result["category"] == "garanti"


def test_utbildning_far_eget_fack():
    result = classify("Kurs", "Vi är 15 personer och vill boka en HLR-kurs.")
    assert result["category"] == "utbildning"


def test_aterbetalning_eskaleras():
    result = classify("", "Jag vill ha pengarna tillbaka NU!!")
    assert result["escalate"]
    assert result["sentiment"] < 0.5


def test_ovrigt():
    result = classify("Fråga", "Har ni öppet på midsommarafton?")
    assert result["category"] == "ovrigt"


# -- Eskaleringsmönstret får inte matcha inuti andra ord ---------------------
#
# Uppmätt 2026-08-21: ett vanligt leveransmejl eskalerades som juridiskt hot
# eftersom "dagARNa" innehåller bokstäverna i ARN. En falsk eskalering ser ut
# som försiktighet och felanmäls aldrig — den syns bara som att kundtjänsten
# får ärenden agenten kunde ha svarat på.


@pytest.mark.parametrize(
    "text",
    [
        "Levererar ni till ombud? Jag är sällan hemma på dagarna.",
        "Har ni något garn i blått?",
        "Vi har små barn hemma, går det att få leverans på helgen?",
        "Jag fick en varning i appen, vad betyder den?",
        "Priset på fakturan stämmer inte med det som stod i kassan.",
    ],
)
def test_vanliga_ord_eskalerar_inte(text):
    assert classify("", text)["escalate"] is False, (
        "Mönstret matchar inuti ett vanligt ord. Kunden får en människa på ett "
        "ärende agenten kunde svarat på, och ingen felanmäler det."
    )


@pytest.mark.parametrize(
    "text",
    [
        "Jag anmäler er till ARN om ni inte svarar.",
        "ARN:s beslut säger något annat.",
        "Jag kommer att stämma er om detta inte löser sig.",
        "Vi överväger en stämning.",
        "Jag vill ha pengarna tillbaka och kräver kompensation.",
        "Radera mitt konto enligt GDPR.",
    ],
)
def test_riktiga_hot_eskalerar_fortfarande(text):
    assert classify("", text)["escalate"] is True
