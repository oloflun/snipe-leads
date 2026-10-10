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


def test_katalogen_har_sex_erbjudanden_och_gemensamma_regler():
    katalog = erbjudanden.katalog()
    assert list(katalog) == [
        "riskfri_start", "se_det_forst", "forsta_resultatet", "gjort_at_er", "ratt_tid", "tva_vagar",
    ]
    assert katalog["riskfri_start"].namn == "Riskfri start"
    assert "Gemensamt för alla erbjudanden" in erbjudanden.gemensamt()
    for e in katalog.values():
        # Metaraderna är katalogens, inte skrivregler till modellen.
        assert "**Namn:**" not in e.regler and "**Kräver villkor:**" not in e.regler
        assert "**Uppmaningen:**" in e.regler


def test_blocket_bar_gemensamt_avsnitt_och_villkoren_ordagrant():
    villkor = "Två månader utan kostnad. Ingen bindningstid, uppsägning med 30 dagars varsel."
    block = erbjudanden.block("riskfri_start", villkor)
    assert block.startswith("## Erbjudandet i det här mejlet")
    assert "Gemensamt för alla erbjudanden" in block
    assert "### Riskfri start" in block
    assert block.endswith(f"### Villkor för erbjudandet\n{villkor}")


# -- Kundens val och tilldelningen -----------------------------------------


def test_bara_aktiva_med_villkor_och_vikt_ar_valbara():
    val = erbjudanden.normalisera(
        {
            "aktiva": [
                {"nyckel": "tva_vagar", "vikt": 2},
                {"nyckel": "riskfri_start", "vikt": 1},
                {"nyckel": "se_det_forst", "vikt": 3},  # saknar villkor
                {"nyckel": "gjort_at_er", "vikt": 0},  # vikt noll
                {"nyckel": "okant", "vikt": 5},
            ],
            "villkor": {"tva_vagar": "Utkast eller hela flödet.", "riskfri_start": "En månad gratis.",
                        "gjort_at_er": "Vi sätter upp det."},
        }
    )
    # Katalogens ordning, inte kundens.
    assert erbjudanden.valbara(val) == [("riskfri_start", 1), ("tva_vagar", 2)]


def test_tilldelningen_ar_deterministisk_och_foljer_vikterna():
    armar = [("riskfri_start", 1), ("se_det_forst", 3)]
    assert erbjudanden.tilldela(TENANT, "p-1", armar) == erbjudanden.tilldela(TENANT, "p-1", armar)
    utfall = Counter(erbjudanden.tilldela(TENANT, f"p-{i}", armar) for i in range(1000))
    assert set(utfall) == {"riskfri_start", "se_det_forst"}
    assert 0.20 < utfall["riskfri_start"] / 1000 < 0.30, utfall
    assert erbjudanden.tilldela(TENANT, "p-1", []) is None


def test_valideringen_kraver_kanda_nycklar_och_villkor():
    with pytest.raises(ValueError, match="Okänt erbjudande"):
        erbjudanden.validera([{"nyckel": "rabatt", "vikt": 1}], {})
    with pytest.raises(ValueError, match="Fyll i villkoren för Riskfri start"):
        erbjudanden.validera([{"nyckel": "riskfri_start", "vikt": 1}], {})
    with pytest.raises(ValueError, match="två gånger"):
        erbjudanden.validera(
            [{"nyckel": "ratt_tid", "vikt": 1}, {"nyckel": "ratt_tid", "vikt": 2}], {"ratt_tid": "Bokslutet."}
        )
    ok = erbjudanden.validera([{"nyckel": "ratt_tid", "vikt": 4}], {"ratt_tid": "Före bokslutet 31 december."})
    assert ok == {"aktiva": [{"nyckel": "ratt_tid", "vikt": 4}], "villkor": {"ratt_tid": "Före bokslutet 31 december."}}


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
        settings={"erbjudanden": {"aktiva": [{"nyckel": "se_det_forst", "vikt": 1}],
                                  "villkor": {"se_det_forst": "Tre färdiga mejl till företag ni väljer."}}},
    )
    valda = []
    for namn in ("A", "B"):
        prospekt = await storage.create_prospect(TENANT, company_name=namn)
        trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
        valda.append(await erbjudanden.for_trad(storage, TENANT, trad))
        assert trad["offer_id"] == storage.offers[0]["id"]
    assert [v.nyckel for v in valda] == ["se_det_forst", "se_det_forst"]
    assert valda[0].villkor == "Tre färdiga mejl till företag ni väljer."
    assert len(storage.offers) == 1


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
    tidigt = erbjudanden.sammanstall([_rad("riskfri_start", 29, 15), _rad("tva_vagar", 100, 2)])
    assert tidigt["ledare"] is None
    assert {a["lage"] for a in tidigt["armar"]} == {"for_tidigt"}

    klart = erbjudanden.sammanstall([_rad("riskfri_start", 100, 30, svar=40), _rad("tva_vagar", 100, 10)])
    assert klart["ledare"] == "riskfri_start"
    arm = next(a for a in klart["armar"] if a["nyckel"] == "riskfri_start")
    assert arm["lage"] == "leder"
    assert arm["svarsfrekvens"] == 0.4 and arm["positiv_andel"] == 0.3
    # Arm utan data finns med, utan andelar.
    tom = next(a for a in klart["armar"] if a["nyckel"] == "ratt_tid")
    assert tom["skickade"] == 0 and tom["positiv_andel"] is None

    jamnt = erbjudanden.sammanstall([_rad("riskfri_start", 100, 12), _rad("tva_vagar", 100, 10)])
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

    await trad_med("riskfri_start", skickat=False)  # bara utkast
    await trad_med("riskfri_start", skickat=True)  # skickat, inget svar
    await trad_med("riskfri_start", skickat=True, status="meeting")  # positivt svar (svar.py, kod)
    await trad_med("riskfri_start", skickat=True, status="lost")  # negativt svar
    await trad_med("tva_vagar", skickat=True, samtal="mote")  # möte via samtalslistan
    await trad_med("tva_vagar", skickat=True, status="meeting", kalla="manuell")  # flyttad för hand

    rader = {r["nyckel"]: r for r in await storage.erbjudande_utfall(TENANT)}
    assert rader["riskfri_start"] == {"nyckel": "riskfri_start", "utkast": 4, "skickade": 3, "svar": 2,
                                      "positiva": 1, "moten": 0}
    # Ett mötesutfall och en manuell flytt till möte är möten, inte svar.
    assert rader["tva_vagar"] == {"nyckel": "tva_vagar", "utkast": 2, "skickade": 2, "svar": 0,
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
    "Vår Supportagent svarar på de vanliga frågorna åt er, så att du får mer tid till bokslutsarbetet.\n\n"
    "Har du 15–20 minuter nästa vecka?"
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
        ("Har ni tid i veckan?\n\nVänliga hälsningar,\nSnajp", "halsningsfras"),
        ("Har ni tid i veckan?\n\nMed vänlig hälsning", "halsningsfras"),
    ],
)
def test_markorerna_fangas(text, kod):
    assert kod in {a.kod for a in stilkontroll.kontrollera(text).anmarkningar}
    assert all(a.allvarlig for a in stilkontroll.kontrollera(text).anmarkningar)


@pytest.mark.parametrize(
    "text",
    [
        "Har ni 15–20 minuter nästa vecka?",
        "Ring 070-123 45 67 om det passar.",
        "Mötet börjar 10:30 på torsdag.",
        "Ni får mer tid till det ni gör bäst.",
        "PS: Provperioden är 30 dagar, utan bindningstid.",
        "Agenten läser mejlen. Den svarar också.",
    ],
)
def test_ofarliga_formuleringar_fangas_inte(text):
    assert stilkontroll.kontrollera(text).anmarkningar == []


def test_batchkontrollen_hittar_samma_ingang_och_uppmaning():
    annan = (
        "Hej,\n\nFör ett litet byggbolag är det ofta offerterna som får vänta. Är det så hos er också?\n\n"
        "Vår Iris hittar nya kunder åt er.\n\nHar du 15–20 minuter nästa vecka?"
    )
    tredje = "Hej,\n\nFör en verkstad är det kvittona som skaver.\n\nPassar torsdag?"
    fynd = stilkontroll.kontrollera_batch([BRA, annan, tredje])
    assert [a.kod for a in fynd[0]] == ["samma_uppmaning"]
    assert [a.kod for a in fynd[1]] == ["samma_uppmaning"]
    assert fynd[2] == []
    assert [a.kod for a in stilkontroll.mot_andra(BRA, [BRA])] == ["samma_ingang", "samma_uppmaning"]
    # Signaturen och foten räknas inte som uppmaning.
    med_fot = BRA + "\n\nVänliga hälsningar,\nSnajp\n\n--\nSnajp AB, org.nr 556000-0000"
    assert stilkontroll.uppmaning(med_fot) == "har du 15–20 minuter nästa vecka?"
