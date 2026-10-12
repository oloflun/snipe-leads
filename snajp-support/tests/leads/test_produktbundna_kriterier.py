"""Snajps omkörning 2026-10-12: profilen kompilerades till tre produktbundna
måste-kriterier (B2B för Iris, B2C för Supportagenten, kvitton för
Kvittohanteraren), och varje bolag skulle uppfylla alla tre. Ett kriterium
bundet till en annan produkt än den researchen valde gäller inte leadet."""

from app.leads.bedomning import MISS, OKAND, TRAFF, bedom, bunden_till_annan_produkt

PRODUKTER = ["Iris, leadsagenten", "Supportagenten", "Kvittohanteraren"]
PROFIL = {
    "kommuner": ["Göteborg"],
    "kriterier": [
        {"id": "k1", "text": "Företag som säljer till andra företag (B2B) för Iris (Leads)", "krav": "maste", "vikt": 1},
        {"id": "k2", "text": "Företag som har privatpersoner som kunder (B2C) för Supportagenten", "krav": "maste", "vikt": 1},
        {"id": "k3", "text": "Företag som samlar kvitton manuellt för Kvittohanteraren", "krav": "maste", "vikt": 1},
    ],
}
KORPUS = "Vi vänder oss till såväl privatpersoner som företag och fastighetsbolag."
JA_B2B = {"kriterie_id": "k1", "utslag": "ja", "resonemang": "Säljer till företag.",
          "belagg": [{"url": "https://x.se", "citat": "företag och fastighetsbolag"}]}
KP = {"kriterie_id": "kp", "utslag": "ja", "resonemang": "Behöver nya företagskunder.",
      "belagg": [{"url": "https://x.se", "citat": "företag och fastighetsbolag"}]}


def test_bundet_till_annan_produkt():
    k2 = PROFIL["kriterier"][1]
    assert bunden_till_annan_produkt(k2, "Iris, leadsagenten", PRODUKTER) == "Supportagenten"
    assert bunden_till_annan_produkt(PROFIL["kriterier"][0], "Iris, leadsagenten", PRODUKTER) is None
    assert bunden_till_annan_produkt(k2, None, PRODUKTER) is None
    assert bunden_till_annan_produkt({"text": "Har en gammal hemsida"}, "Iris", PRODUKTER) is None


def test_bara_den_valda_produktens_kriterium_galler():
    fynd = {"postnummer": "421 32", "bedomningar": [JA_B2B, KP]}
    med = bedom(PROFIL, fynd, korpus=KORPUS, produkt_vald=True, produkt="Iris, leadsagenten", produkter=PRODUKTER)
    assert med["qualified"] is True and med["niva"] in ("A", "B"), med["disqualifiers"]
    rader = {r["nyckel"]: r for r in med["score_breakdown"]}
    assert rader["k1"]["utfall"] == TRAFF and rader["k1"]["hart"] is True
    assert rader["k2"]["utfall"] == OKAND and rader["k2"]["hart"] is False and "Supportagenten" in rader["k2"]["motivering"]

    # Utan produkten gäller alla tre som förut, och de obelagda fäller.
    utan = bedom(PROFIL, fynd, korpus=KORPUS, produkt_vald=True)
    assert utan["qualified"] is False
    assert any("Supportagenten" in d for d in utan["disqualifiers"])
    assert {r["nyckel"]: r["utfall"] for r in utan["score_breakdown"]}["k1"] == TRAFF
    assert MISS not in {r["utfall"] for r in utan["score_breakdown"] if r["nyckel"] == "k1"}
