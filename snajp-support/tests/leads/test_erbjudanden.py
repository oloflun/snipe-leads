"""Erbjudandena i kalla mejl (app/leads/erbjudanden.py) och stilkontrollen
(app/leads/stilkontroll.py): katalogen, tilldelningen, valideringen,
mätningen och faktagrinden mot kundens villkor. Allt i minne, inget LLM."""

from collections import Counter

import pytest

from app.leads import erbjudanden, stilkontroll
from app.leads.grounding_gate import build_permitted_facts, check_grounding
from app.storage.memory import MemoryStorage

TENANT = "tenant-erbjudanden"


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Katalogen ------------------------------------------------------------


def test_katalogen_har_tre_erbjudanden_och_gemensamma_regler():
    katalog = erbjudanden.katalog()
    assert list(katalog) == ["gratis_prov", "garanti", "pilot"]
    assert katalog["gratis_prov"].namn == "Testa gratis"
    assert "Gemensamt för alla erbjudanden" in erbjudanden.gemensamt()
    for e in katalog.values():
        # Metaraderna är katalogens, inte skrivregler till modellen.
        assert "**Namn:**" not in e.regler and "**Kräver villkor:**" not in e.regler
        assert "**Så bär mejlet erbjudandet:**" in e.regler


def test_blocket_bar_gemensamt_avsnitt_och_villkoren_ordagrant():
    villkor = "Fem kvalificerade leads med färdiga första mejl, utan kostnad. Svara ja så skickar vi dem."
    block = erbjudanden.block("gratis_prov", villkor)
    assert block.startswith("## Erbjudandet i det här mejlet")
    assert "stycke 2 och 3" in block and "aldrig med en fråga" in block
    assert "Gemensamt för alla erbjudanden" in block
    assert "### Testa gratis" in block
    assert block.endswith(f"### Villkor för erbjudandet\n{villkor}")


# -- Kundens val och tilldelningen -----------------------------------------


def test_bara_aktiva_med_villkor_och_vikt_ar_valbara():
    val = erbjudanden.normalisera(
        {
            "aktiva": [
                {"nyckel": "pilot", "vikt": 2},
                {"nyckel": "gratis_prov", "vikt": 1},
                {"nyckel": "garanti", "vikt": 3},  # saknar villkor
                {"nyckel": "okant", "vikt": 5},
            ],
            "villkor": {"pilot": "20 platser.", "gratis_prov": "Fem leads gratis.", "garanti": "  "},
        }
    )
    # Katalogens ordning, inte kundens.
    assert erbjudanden.valbara(val) == [("gratis_prov", 1), ("pilot", 2)]
    val["aktiva"][0]["vikt"] = 0  # vikt noll
    assert erbjudanden.valbara(val) == [("gratis_prov", 1)]


#: Snajps tre agenter med villkor per produkt (exemplen i katalogens artefakt).
VILLKOR_PER_PRODUKT = {
    "gratis_prov": {
        "Iris": "Fem kvalificerade leads med färdiga första mejl, utan kostnad.",
        "Kvittohanterare": "Vi gör fem kvitton klara att ladda ned, utan kostnad.",
        "Supportagent": "En demolänk där ni lägger in era vanligaste frågor och testar själva.",
    },
    "garanti": {"Iris": "Minst 10 nya kunddialoger inom 90 dagar, annars förlängd provperiod utan kostnad."},
}


def test_villkoret_valjs_per_produkt():
    villkor = erbjudanden.normalisera({"villkor": VILLKOR_PER_PRODUKT})["villkor"]
    assert erbjudanden.villkor_for(villkor["gratis_prov"], "supportagent").startswith("En demolänk")
    assert erbjudanden.villkor_for(villkor["gratis_prov"], None) == ""
    assert erbjudanden.villkor_for(villkor["garanti"], "Supportagent") == ""
    # En text för alla produkter gäller alltid, också utan vald produkt.
    assert erbjudanden.villkor_for("Gäller allt.", None) == "Gäller allt."


def test_ett_supportagentprospekt_far_aldrig_ett_irisvillkor():
    """Felet i varv 3: villkoren fanns per erbjudande, så ett Supportagent-mejl
    fick Iris-villkoret "tio bolag med färdiga mejl"."""
    val = erbjudanden.normalisera(
        {"aktiva": [{"nyckel": "gratis_prov", "vikt": 1}, {"nyckel": "garanti", "vikt": 5}],
         "villkor": VILLKOR_PER_PRODUKT}
    )
    # Garantin har bara ett Iris-villkor: den kan aldrig väljas för Supportagenten.
    assert erbjudanden.valbara(val, "Supportagent") == [("gratis_prov", 1)]
    assert erbjudanden.valbara(val, "Iris") == [("gratis_prov", 1), ("garanti", 5)]
    # Utan vald produkt gäller bara villkor för alla produkter, och här finns inga.
    assert erbjudanden.valbara(val, None) == []
    iris_texter = set(VILLKOR_PER_PRODUKT["garanti"].values()) | {VILLKOR_PER_PRODUKT["gratis_prov"]["Iris"]}
    for i in range(200):
        nyckel = erbjudanden.tilldela(TENANT, f"p-{i}", erbjudanden.valbara(val, "Supportagent"))
        assert erbjudanden.villkor_for(val["villkor"][nyckel], "Supportagent") not in iris_texter


def test_tilldelningen_ar_deterministisk_och_foljer_vikterna():
    armar = [("gratis_prov", 1), ("garanti", 3)]
    assert erbjudanden.tilldela(TENANT, "p-1", armar) == erbjudanden.tilldela(TENANT, "p-1", armar)
    utfall = Counter(erbjudanden.tilldela(TENANT, f"p-{i}", armar) for i in range(1000))
    assert set(utfall) == {"gratis_prov", "garanti"}
    assert 0.20 < utfall["gratis_prov"] / 1000 < 0.30, utfall
    assert erbjudanden.tilldela(TENANT, "p-1", []) is None


def test_valideringen_kraver_kanda_nycklar_och_villkor():
    with pytest.raises(ValueError, match="Okänt erbjudande"):
        erbjudanden.validera([{"nyckel": "rabatt", "vikt": 1}], {})
    with pytest.raises(ValueError, match="Fyll i villkoren för Testa gratis"):
        erbjudanden.validera([{"nyckel": "gratis_prov", "vikt": 1}], {})
    with pytest.raises(ValueError, match="Fyll i villkoren för Testa gratis"):
        erbjudanden.validera([{"nyckel": "gratis_prov", "vikt": 1}], {"gratis_prov": {"Iris": " "}}, ["Iris"])
    with pytest.raises(ValueError, match="två gånger"):
        erbjudanden.validera(
            [{"nyckel": "pilot", "vikt": 1}, {"nyckel": "pilot", "vikt": 2}], {"pilot": "20 platser."}
        )
    with pytest.raises(ValueError, match="inte finns bland era produkter"):
        erbjudanden.validera([], {"pilot": {"Okänd agent": "20 platser."}}, ["Iris"])
    ok = erbjudanden.validera([{"nyckel": "pilot", "vikt": 4}], {"pilot": "20 platser, 50 % första året."})
    assert ok == {"aktiva": [{"nyckel": "pilot", "vikt": 4}], "villkor": {"pilot": "20 platser, 50 % första året."}}
    # Villkor för minst en produkt räcker; tomma produktfält faller bort.
    per = erbjudanden.validera(
        [{"nyckel": "pilot", "vikt": 1}], {"pilot": {"iris": "10 platser.", "Supportagent": ""}}, ["Iris", "Supportagent"]
    )
    assert per["villkor"] == {"pilot": {"iris": "10 platser."}}


def test_produkten_lases_ur_researchen():
    assert erbjudanden.produkt_ur_research('{"vald_produkt": {"namn": "Iris", "nytta": "x"}}') == "Iris"
    assert erbjudanden.produkt_ur_research('{"produkt": "Supportagent"}') == "Supportagent"
    assert erbjudanden.produkt_ur_research('{"vald_produkt": null}') is None
    assert erbjudanden.produkt_ur_research("inte json") is None


@pytest.mark.anyio
async def test_for_trad_utan_aktiva_ar_none_och_rör_inget():
    storage = MemoryStorage()
    prospekt = await storage.create_prospect(TENANT, company_name="Bolaget")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
    assert await erbjudanden.for_trad(storage, TENANT, trad) is None
    assert storage.offers == [] and trad["offer_id"] is None


@pytest.mark.anyio
async def test_for_trad_sparar_valet_en_offersrad_per_nyckel():
    storage = MemoryStorage()
    await storage.set_agent_settings(
        TENANT, agent_type="leads",
        settings={"erbjudanden": {"aktiva": [{"nyckel": "gratis_prov", "vikt": 1}],
                                  "villkor": VILLKOR_PER_PRODUKT}},
    )
    valda = []
    for namn in ("A", "B"):
        prospekt = await storage.create_prospect(TENANT, company_name=namn)
        trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
        valda.append(await erbjudanden.for_trad(storage, TENANT, trad, "Kvittohanterare"))
        assert trad["offer_id"] == storage.offers[0]["id"]
    assert [v.nyckel for v in valda] == ["gratis_prov", "gratis_prov"]
    # Produktens eget villkor, inte en annan produkts.
    assert valda[0].villkor == VILLKOR_PER_PRODUKT["gratis_prov"]["Kvittohanterare"]
    assert len(storage.offers) == 1

    # Utan vald produkt finns inget villkor som gäller: dagens beteende.
    prospekt = await storage.create_prospect(TENANT, company_name="C")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
    assert await erbjudanden.for_trad(storage, TENANT, trad) is None
    assert trad["offer_id"] is None


# -- Mätningen ------------------------------------------------------------


def test_z_testet():
    assert erbjudanden.p_varde(10, 100, 10, 100) == pytest.approx(1.0)
    # 30 % mot 10 % på 100 vardera: z ≈ 3,54.
    assert erbjudanden.p_varde(30, 100, 10, 100) == pytest.approx(0.0004, abs=0.0001)
    assert erbjudanden.p_varde(0, 50, 0, 50) == 1.0
    assert erbjudanden.p_varde(1, 0, 1, 10) == 1.0


def _rad(nyckel, skickade, positiva, svar=None):
    return {"nyckel": nyckel, "utkast": skickade, "skickade": skickade,
            "svar": positiva if svar is None else svar, "positiva": positiva, "moten": 0}


def test_ledare_kraver_trettio_skickade_och_signifikans():
    # För få skickade i den ena armen: ingen ledare trots stor skillnad.
    tidigt = erbjudanden.sammanstall([_rad("gratis_prov", 29, 15), _rad("pilot", 100, 2)])
    assert tidigt["ledare"] is None
    assert {a["lage"] for a in tidigt["armar"]} == {"for_tidigt"}

    klart = erbjudanden.sammanstall([_rad("gratis_prov", 100, 30, svar=40), _rad("pilot", 100, 10)])
    assert klart["ledare"] == "gratis_prov"
    arm = next(a for a in klart["armar"] if a["nyckel"] == "gratis_prov")
    assert arm["lage"] == "leder"
    assert arm["svarsfrekvens"] == 0.4 and arm["positiv_andel"] == 0.3
    # Arm utan data finns med, utan andelar.
    tom = next(a for a in klart["armar"] if a["nyckel"] == "garanti")
    assert tom["skickade"] == 0 and tom["positiv_andel"] is None

    jamnt = erbjudanden.sammanstall([_rad("gratis_prov", 100, 12), _rad("pilot", 100, 10)])
    assert jamnt["ledare"] is None and jamnt["p_varde"] > 0.05


@pytest.mark.anyio
async def test_utfallet_harleds_ur_tradarnas_lage():
    storage = MemoryStorage()

    async def trad_med(nyckel: str, *, skickat: bool, status: str | None = None, kalla: str = "kod",
                       samtal: str | None = None):
        prospekt = await storage.create_prospect(TENANT, company_name=f"Bolag {len(storage.offers)}{nyckel}{status}")
        trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
        await storage.tilldela_erbjudande(TENANT, trad["id"], nyckel=nyckel)
        koat = await storage.queue_outreach_message(
            TENANT, thread_id=trad["id"], body="Hej", subject="Ä", humanizer_variant="snajp:humanizer-svenska",
            scheduled_at=None, status="awaiting_review",
        )
        if skickat:
            await storage.update_prospect(TENANT, prospekt["id"], status="contacted")
            await storage.mark_outreach_message_sent(TENANT, koat["message"]["id"], "2026-10-10T09:00:00+00:00")
        if status:
            await storage.update_prospect(TENANT, prospekt["id"], status=status, status_kalla=kalla)
        if samtal:
            await storage.add_lead_samtal(TENANT, prospect_id=prospekt["id"], utfall=samtal,
                                          aterkom_datum=None, anteckning=None)

    await trad_med("gratis_prov", skickat=False)  # bara utkast
    await trad_med("gratis_prov", skickat=True)  # skickat, inget svar
    await trad_med("gratis_prov", skickat=True, status="meeting")  # positivt svar (svar.py, kod)
    await trad_med("gratis_prov", skickat=True, status="lost")  # negativt svar
    await trad_med("pilot", skickat=True, samtal="mote")  # möte via samtalslistan
    await trad_med("pilot", skickat=True, status="meeting", kalla="manuell")  # flyttad för hand

    rader = {r["nyckel"]: r for r in await storage.erbjudande_utfall(TENANT)}
    assert rader["gratis_prov"] == {"nyckel": "gratis_prov", "utkast": 4, "skickade": 3, "svar": 2,
                                      "positiva": 1, "moten": 0}
    # Ett mötesutfall och en manuell flytt till möte är möten, inte svar.
    assert rader["pilot"] == {"nyckel": "pilot", "utkast": 2, "skickade": 2, "svar": 0,
                                  "positiva": 0, "moten": 2}


# -- Faktagrinden mot villkoren -------------------------------------------


def test_faktagrinden_slapper_villkorens_siffror_men_faller_andra():
    villkor = "Första 30 dagarna utan kostnad, sedan 495 kr i månaden. Ingen bindningstid."
    fakta = build_permitted_facts(
        context_pack="", research_evidence=(), offer_summary=f"Pilot\n{villkor}",
        brief="", tenant_name="Snajp", company_name="Bolaget",
    )
    assert check_grounding("De första 30 dagarna kostar inget, sedan 495 kr i månaden.", fakta).ok
    falld = check_grounding("De första 60 dagarna kostar inget.", fakta)
    assert not falld.ok and [c.raw for c in falld.unsupported] == ["60"]
    utan_villkor = build_permitted_facts(
        context_pack="", research_evidence=(), offer_summary="Pilot",
        brief="", tenant_name="Snajp", company_name="Bolaget",
    )
    assert not check_grounding("De första 30 dagarna kostar inget.", utan_villkor).ok


# -- Stilkontrollen -------------------------------------------------------

BRA = (
    "Hej Anna,\n\n"
    "När man driver en redovisningsbyrå med få anställda är det ofta mejlen från kunderna som tar kvällarna. "
    "Känner du igen dig?\n\n"
    "Vår Supportagent svarar på de vanliga frågorna åt er, så att du hinner med bokslutsarbetet. "
    "Testa den på era egna frågor, det tar 15–20 minuter.\n\n"
    "Följ länken så kommer du igång: snajp.se/demo"
)


def test_ett_mejl_i_skrivstilen_ger_inga_fynd():
    assert stilkontroll.kontrollera(BRA).anmarkningar == []


@pytest.mark.parametrize(
    ("text", "kod"),
    [
        ("Vi hjälper till — snabbt.", "tankstreck"),
        ("Vi hjälper till - snabbt.", "tankstreck"),
        ("Jag såg att ni bygger hus.", "jag_ser_att"),
        ("Jag ser att ni har en ny butik.", "jag_ser_att"),
        ("Vi har utvecklat ett verktyg.", "vi_har_skapat"),
        ("Iris är en AI-agent som skriver mejl.", "ar_en_ai_agent"),
        ("Det hjälper er att effektivisera arbetet.", "effektivisera"),
        ("Ni får högre effektivitet.", "effektivisera"),
        ("I dagens läge behövs det.", "i_dagens"),
        ("Vi är marknadsledande på området.", "superlativ"),
        ("Hör av er i dag!", "utropstecken"),
        ("Agenten läser mejlen. Agenten svarar också.", "samma_start"),
        ("Det här är en mening som har alldeles för många ord för att någon ska orka läsa den hela vägen "
         "fram till slutet utan att tappa bort sig på vägen.", "lang_mening"),
        ("Ni får tre saker: färdiga mejl, en lista och en uppföljning.", "kolonlista"),
        ("Svara ja.\n\nVänliga hälsningar,\nSnajp", "halsningsfras"),
        ("Svara ja.\n\nMed vänlig hälsning", "halsningsfras"),
        ("Vår agent hittar kunderna. Har ni 15 minuter nästa vecka?", "slutar_med_fraga"),
        ("Hej,\n\n" + "Vår agent hittar nya kunder åt er varje vecka. " * 11, "for_langt"),
    ],
)
def test_markorerna_fangas(text, kod):
    assert kod in {a.kod for a in stilkontroll.kontrollera(text).anmarkningar}
    assert all(a.allvarlig for a in stilkontroll.kontrollera(text).anmarkningar)


@pytest.mark.parametrize(
    "text",
    [
        "Boka 15–20 minuter nästa vecka.",
        "Ring 070-123 45 67 om det passar.",
        # En igenkänningsfråga tidigt är tillåten; bara avslutningen får inte vara en fråga.
        "Blir offerterna liggande hos er också? Svara ja så skickar jag fem leads.",
        "Mötet börjar 10:30 på torsdag.",
        "Ni får mer tid till det ni gör bäst.",
        "PS: Provperioden är 30 dagar, utan bindningstid.",
        "Agenten läser mejlen. Den svarar också.",
    ],
)
def test_ofarliga_formuleringar_fangas_inte(text):
    assert stilkontroll.kontrollera(text).anmarkningar == []


def test_nittio_ord_ar_okej_men_inte_nittioett():
    nittio = "Hej,\n\n" + " ".join(["ord"] * 89) + " slut."
    assert "for_langt" not in {a.kod for a in stilkontroll.kontrollera(nittio).anmarkningar}
    nittioett = "Hej,\n\n" + " ".join(["ord"] * 90) + " slut."
    assert "for_langt" in {a.kod for a in stilkontroll.kontrollera(nittioett).anmarkningar}
    # Signaturen och foten räknas inte.
    med_signatur = nittio + "\n\nVänliga hälsningar,\nAnna Andersson\nSnajp AB\n\n--\nSnajp AB, org.nr 556000-0000"
    assert "for_langt" not in {a.kod for a in stilkontroll.kontrollera(med_signatur).anmarkningar}


def test_batchkontrollen_hittar_samma_ingang_och_uppmaning():
    annan = (
        "Hej,\n\nFör ett litet byggbolag är det ofta offerterna som får vänta. Är det så hos er också?\n\n"
        "Vår Iris hittar nya kunder åt er.\n\nFölj länken så kommer du igång: snajp.se/demo"
    )
    tredje = "Hej,\n\nFör en verkstad är det kvittona som skaver.\n\nSvara ja så skickar jag dem."
    fynd = stilkontroll.kontrollera_batch([BRA, annan, tredje])
    assert [a.kod for a in fynd[0]] == ["samma_uppmaning"]
    assert [a.kod for a in fynd[1]] == ["samma_uppmaning"]
    assert fynd[2] == []
    assert [a.kod for a in stilkontroll.mot_andra(BRA, [BRA])] == ["samma_ingang", "samma_uppmaning"]
    # Signaturen och foten räknas inte som uppmaning.
    med_fot = BRA + "\n\nVänliga hälsningar,\nSnajp\n\n--\nSnajp AB, org.nr 556000-0000"
    assert stilkontroll.uppmaning(med_fot) == "följ länken så kommer du igång: snajp.se/demo"
