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
    result = classify("GDPR", "Jag vill radera mitt konto och alla personuppgifter.")
    assert result["category"] == "konto"
    assert result["escalate"]


def test_aterbetalning_eskaleras():
    result = classify("", "Jag vill ha pengarna tillbaka NU!!")
    assert result["escalate"]
    assert result["sentiment"] < 0.5


def test_ovrigt():
    result = classify("Fråga", "Har ni öppet på midsommarafton?")
    assert result["category"] == "ovrigt"
