"""Ett test per spärr, plus ordningen mellan dem.

Om ett av de här testerna någon gång står i vägen: läs regelns motivering i
`app/leads/send_guard.py` innan du ändrar testet. Fem av de sex reglerna finns
av juridiska eller ekonomiska skäl, inte estetiska.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.leads.send_guard import (
    BLOCKERA,
    GRANSKA,
    GRANSKADE_FORSTA_UTSKICK,
    KARENS_DAGAR_PER_FORETAG,
    KOLA_OM,
    SKICKA,
    STOCKHOLM,
    TAK_PER_DAG,
    UPPTRAPPNING_STEG,
    UPPVARMNING_TAK_PER_DAG,
    Avsandare,
    Leveransutfall,
    TenantHistorik,
    Utskick,
    check_send_guard,
    foretagsnyckel,
)

AVSANDARE = Avsandare(
    foretagsnamn="Livrustning AB",
    orgnr="556824-9022",
    postadress="Rudsjövägen 112, 131 47 Nacka",
)

#: En brödtext som uppfyller regel 1, 2 och 4. Testerna nedan plockar bort
#: en bit i taget för att visa exakt vilken spärr som fäller vad.
FULLSTANDIG_TEXT = """
Hej,

vi utbildar arbetsplatser i hjärt-lungräddning och första hjälpen.

Vänliga hälsningar
Livrustning AB · Org.nr 556824-9022 · Rudsjövägen 112, 131 47 Nacka

Du får det här mejlet därför att vi är personuppgiftsansvarig för uppgiften.
Ändamål: att erbjuda utbildning. Uppgiften är hämtad från din arbetsgivares
offentliga webbplats. Du har rätt att invända och att få dina uppgifter
raderade.
Hur vi behandlar personuppgifter: https://livrustning.example/integritetspolicy

Avregistrera dig: https://livrustning.example/avregistrera?t=abc123
"""

#: En vardag klockan 10 svensk tid. 2026-08-17 är en måndag.
VARDAG_FORMIDDAG = datetime(2026, 8, 17, 10, 0, tzinfo=STOCKHOLM).astimezone(timezone.utc)


def historik(**overrides) -> TenantHistorik:
    bas = {
        "skickade_totalt": 50,
        "skickade_idag": 0,
        "tenant_alder_dagar": 365,
        # Hög nog att upptrappningstaket (5d) inte binder i tester som mäter
        # något annat; 5d:s egna tester sätter den själva.
        "storsta_dagsvolym": 500,
        "leverans": Leveransutfall(skickade=200, studsade=0, klagomal=0),
        "senaste_kontakt_med_foretaget": None,
        "suppressions": frozenset(),
        "tidigare_kontaktade": frozenset(),
        "egna_kunder": frozenset(),
    }
    return TenantHistorik(**(bas | overrides))


def utskick(**overrides) -> Utskick:
    bas = {
        "mottagare": "info@prospekt.example",
        "amne": "Utbildning i första hjälpen",
        "brodtext": FULLSTANDIG_TEXT,
        "foretagsnyckel": "5560000201",
        "personlig_adress": False,
    }
    return Utskick(**(bas | overrides))


def kor(**overrides):
    return check_send_guard(
        avsandare=overrides.pop("avsandare", AVSANDARE),
        utskick=overrides.pop("utskick", utskick()),
        historik=overrides.pop("historik", historik()),
        nu=overrides.pop("nu", VARDAG_FORMIDDAG),
    )


def test_ett_korrekt_utskick_slapps_igenom():
    """Kontrollen att spärrarna inte blockerar allt. Utan det här testet kan
    de fem nedan passera med en guard som alltid säger nej."""
    beslut = kor()
    assert beslut.atgard == SKICKA
    assert beslut.tillaten


# -- Regel 1: avsändaridentifikation ----------------------------------------


def test_regel_1_kraver_foretagsnamnet():
    """Marknadsföringslagen kräver identifierbar avsändare. Kravet gäller
    hyreskunden, inte Snajp."""
    beslut = kor(utskick=utskick(brodtext=FULLSTANDIG_TEXT.replace("Livrustning AB", "")))
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "1_avsandaridentifikation"
    assert "företagsnamn" in beslut.skal


@pytest.mark.parametrize("bortplockat", ["556824-9022", "Rudsjövägen 112, 131 47 Nacka"])
def test_regel_1_stoppar_aldrig_pa_orgnr_eller_adress(bortplockat):
    """Antons beslut 2026-10-10: org.nr och postadress tas med när de finns
    men får aldrig stoppa ett utskick."""
    beslut = kor(utskick=utskick(brodtext=FULLSTANDIG_TEXT.replace(bortplockat, "")))
    assert beslut.regel != "1_avsandaridentifikation"


def test_regel_1_faller_inte_pa_formatering():
    """Sidfotens adress kan ha radbrytning där mallen hade mellanslag.
    Falsklarm är hur en spärr blir bortkommenterad."""
    text = FULLSTANDIG_TEXT.replace(
        "Rudsjövägen 112, 131 47 Nacka", "Rudsjövägen 112,\n131 47   Nacka"
    )
    assert kor(utskick=utskick(brodtext=text)).atgard == SKICKA


# -- Regel 2: avregistrering ------------------------------------------------


def test_regel_2_kraver_en_lank():
    beslut = kor(
        utskick=utskick(
            brodtext=FULLSTANDIG_TEXT.replace(
                "https://livrustning.example/avregistrera?t=abc123", ""
            )
        )
    )
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "2_avregistrering"


def test_regel_2_godtar_inte_svara_stopp():
    """En uppmaning att svara lägger arbetet på mottagaren och går inte att
    verifiera maskinellt."""
    text = FULLSTANDIG_TEXT.replace(
        "Avregistrera dig: https://livrustning.example/avregistrera?t=abc123",
        "Svara STOPP så tar vi bort dig.",
    )
    assert kor(utskick=utskick(brodtext=text)).regel == "2_avregistrering"


def test_regel_2_kraver_policylank():
    """Integritetspolicylänken är obligatorisk i varje mejl (2026-09-20):
    art. 14-styckena i foten rymmer inte lagringstid, mottagare och rätten
    att klaga till IMY — länken bär resten."""
    text = FULLSTANDIG_TEXT.replace(
        "Hur vi behandlar personuppgifter: https://livrustning.example/integritetspolicy",
        "",
    )
    personlig = {"mottagare": "anna.svensson@prospekt.example", "personlig_adress": True}
    beslut = kor(utskick=utskick(brodtext=text, **personlig))
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "2_avregistrering"
    assert "integritetspolicy" in beslut.skal


def test_regel_2_policylanken_kravs_inte_till_en_funktionsadress():
    """Sebbe 2026-10-24: policylänken bär art. 14.2 och krävs bara vid en
    personlig adress, som art. 14 självt (regel 4). Till info@ går den korta
    foten med avsändare och avregistrering."""
    text = (
        "Hej,\n\nEtt kort erbjudande.\n\n--\nLivrustning AB, org.nr 556824-9022\n\n"
        "Vill du inte få fler mejl från oss: https://livrustning.example/avregistrera/abc"
    )
    assert kor(utskick=utskick(brodtext=text)).atgard == SKICKA
    personlig = utskick(brodtext=text, mottagare="anna.svensson@prospekt.example", personlig_adress=True)
    assert kor(utskick=personlig).atgard == BLOCKERA


def test_regel_2_policylank_utan_policyord_i_urlen():
    """Kundens policysida kan heta vad som helst — ordet "personuppgifter" på
    samma rad som länken räcker, vilket är exakt vad utskicksfoten skriver."""
    text = FULLSTANDIG_TEXT.replace(
        "Hur vi behandlar personuppgifter: https://livrustning.example/integritetspolicy",
        "Hur vi behandlar personuppgifter: https://livrustning.example/om-oss/policy",
    )
    assert kor(utskick=utskick(brodtext=text)).atgard == SKICKA


# -- Regel 3: suppression ---------------------------------------------------


def test_regel_3_avregistrerad_adress_blockeras():
    beslut = kor(historik=historik(suppressions=frozenset({"INFO@prospekt.example"})))
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "3_suppression"


def test_regel_3_egen_kund_blockeras():
    beslut = kor(historik=historik(egna_kunder=frozenset({"info@prospekt.example"})))
    assert beslut.regel == "3_suppression"
    assert "kundlista" in beslut.skal


def test_regel_3_tidigare_kontaktad_blockeras():
    beslut = kor(historik=historik(tidigare_kontaktade=frozenset({"info@prospekt.example"})))
    assert beslut.regel == "3_suppression"


def test_regel_3_gar_fore_allt_annat():
    """Den enda regeln vars brott är oåterkalleligt mot en person som
    uttryckligen bett att slippa. Ett mejl som dessutom saknar sidfot ska
    fällas på suppression, inte på formatering."""
    beslut = kor(
        utskick=utskick(brodtext="Hej! Köp något."),
        historik=historik(suppressions=frozenset({"info@prospekt.example"})),
    )
    assert beslut.regel == "3_suppression"


# -- Regel 4: personuppgiftsflagga ------------------------------------------


def test_regel_4_personlig_adress_utan_art14_blockeras():
    text = FULLSTANDIG_TEXT.replace(
        "Uppgiften är hämtad från din arbetsgivares\noffentliga webbplats.", ""
    )
    beslut = kor(
        utskick=utskick(
            mottagare="anna.lindqvist@prospekt.example",
            personlig_adress=True,
            brodtext=text,
        )
    )
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "4_personuppgiftsflagga"
    assert "varifrån uppgiften kom" in beslut.skal


def test_regel_4_personlig_adress_med_art14_slapps_igenom():
    beslut = kor(
        utskick=utskick(mottagare="anna.lindqvist@prospekt.example", personlig_adress=True)
    )
    assert beslut.atgard == SKICKA


def test_regel_4_gäller_inte_funktionsadress():
    """info@ och kontakt@ är inte personuppgifter."""
    text = FULLSTANDIG_TEXT.replace(
        "Uppgiften är hämtad från din arbetsgivares\noffentliga webbplats.", ""
    )
    assert kor(utskick=utskick(brodtext=text, personlig_adress=False)).atgard == SKICKA


# -- Regel 5: volymtak ------------------------------------------------------


def test_regel_5_dagstaket_under_uppvarmningen():
    beslut = kor(
        historik=historik(tenant_alder_dagar=3, skickade_idag=UPPVARMNING_TAK_PER_DAG)
    )
    assert beslut.atgard == KOLA_OM
    assert beslut.regel == "5_volymtak"


def test_regel_5_dagstaket_slutar_galla_efter_uppvarmningen():
    """Efter uppvärmningen gäller upptrappningstaket (5d), inte 20-taket: en
    etablerad dagsvolym binder inte."""
    assert kor(historik=historik(tenant_alder_dagar=90, skickade_idag=30)).atgard == SKICKA


def test_regel_5d_upptrappningen_ar_flack():
    """Sebbe 2026-10-24: dubblingen (20 → 40 → 80 → 160) släppte ut ~600
    kallmejl på några dagar. Taket är största dagsvolymen senaste sju dagarna
    plus UPPTRAPPNING_STEG."""
    tak = 20 + UPPTRAPPNING_STEG
    beslut = kor(historik=historik(tenant_alder_dagar=90, storsta_dagsvolym=20, skickade_idag=tak))
    assert beslut.atgard == KOLA_OM and beslut.regel == "5_volymtak"
    assert f"{tak} av {tak}" in beslut.skal
    # Under taket skickas det.
    h = historik(tenant_alder_dagar=90, storsta_dagsvolym=20, skickade_idag=tak - 1)
    assert kor(historik=h).atgard == SKICKA


def test_regel_5d_har_ett_tak_per_dag():
    """Hur mycket som än skickats förut går högst TAK_PER_DAG ut om dagen."""
    h = historik(tenant_alder_dagar=90, storsta_dagsvolym=160, skickade_idag=TAK_PER_DAG)
    beslut = kor(historik=h)
    assert beslut.atgard == KOLA_OM and f"{TAK_PER_DAG} av {TAK_PER_DAG}" in beslut.skal


def test_regel_5d_golvet_ar_uppvarmningstaket():
    """Efter en veckas tystnad är största dagsvolymen 0 — kurvan börjar om
    från uppvärmningens golv (20), inte från noll."""
    h = historik(tenant_alder_dagar=90, storsta_dagsvolym=0, skickade_idag=UPPVARMNING_TAK_PER_DAG - 1)
    assert kor(historik=h).atgard == SKICKA
    h = historik(tenant_alder_dagar=90, storsta_dagsvolym=0, skickade_idag=UPPVARMNING_TAK_PER_DAG)
    assert kor(historik=h).atgard == KOLA_OM


def test_regel_5d_galler_aven_skicka_nu():
    """Skicka nu släpper bara kontorstiden (5a). Volymtaket skyddar domänens
    rykte mot volymen, inte mot klockslaget, och gäller därför direkt också."""
    h = historik(tenant_alder_dagar=90, storsta_dagsvolym=20, skickade_idag=40)
    beslut = kor(historik=h, utskick=utskick(direkt=True))
    assert beslut.atgard == KOLA_OM and beslut.regel == "5_volymtak"


# -- Regel 5e: leveransstopp ------------------------------------------------


def test_regel_5e_ett_klagomal_pausar_utskicken():
    """Ett klagomål på färre än tusen skickade är över 0,1 %. Gäller även
    under uppvärmningen och för Skicka nu."""
    for h, u in (
        (historik(leverans=Leveransutfall(skickade=300, studsade=0, klagomal=1)), utskick()),
        (historik(tenant_alder_dagar=3, skickade_idag=0,
                  leverans=Leveransutfall(skickade=40, studsade=0, klagomal=1)), utskick()),
        (historik(leverans=Leveransutfall(skickade=300, studsade=0, klagomal=1)), utskick(direkt=True)),
    ):
        beslut = kor(historik=h, utskick=u)
        assert beslut.atgard == KOLA_OM and beslut.regel == "5_leveransstopp", beslut.skal
        assert "skräppost" in beslut.skal


def test_regel_5e_studs_over_tre_procent_pausar():
    beslut = kor(historik=historik(leverans=Leveransutfall(skickade=100, studsade=4, klagomal=0)))
    assert beslut.atgard == KOLA_OM and beslut.regel == "5_leveransstopp"
    assert "4 av 100" in beslut.skal and "4,0 %" in beslut.skal
    # Exakt på gränsen skickas det.
    assert kor(historik=historik(leverans=Leveransutfall(skickade=100, studsade=3, klagomal=0))).atgard == SKICKA


def test_regel_5e_studs_bedoms_forst_med_underlag():
    """Två studsar av de tio första är inte en trend."""
    assert kor(historik=historik(leverans=Leveransutfall(skickade=10, studsade=2, klagomal=0))).atgard == SKICKA


def test_regel_5_karens_per_foretag():
    senaste = VARDAG_FORMIDDAG - timedelta(days=KARENS_DAGAR_PER_FORETAG - 1)
    beslut = kor(historik=historik(senaste_kontakt_med_foretaget=senaste))
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "5_volymtak"


def test_regel_5_karens_slapper_efter_90_dagar():
    senaste = VARDAG_FORMIDDAG - timedelta(days=KARENS_DAGAR_PER_FORETAG + 1)
    assert kor(historik=historik(senaste_kontakt_med_foretaget=senaste)).atgard == SKICKA


@pytest.mark.parametrize(
    "tidpunkt",
    [
        datetime(2026, 8, 17, 3, 14, tzinfo=STOCKHOLM),   # natt
        datetime(2026, 8, 17, 7, 59, tzinfo=STOCKHOLM),   # för tidigt
        datetime(2026, 8, 17, 17, 0, tzinfo=STOCKHOLM),   # för sent
        datetime(2026, 8, 15, 10, 0, tzinfo=STOCKHOLM),   # lördag
        datetime(2026, 8, 16, 10, 0, tzinfo=STOCKHOLM),   # söndag
    ],
)
def test_regel_5_utanfor_kontorstid_koas_om(tidpunkt):
    beslut = kor(nu=tidpunkt.astimezone(timezone.utc))
    assert beslut.atgard == KOLA_OM
    assert beslut.regel == "5_volymtak"


def test_regel_5_raknar_i_svensk_tid_inte_utc():
    """07:30 UTC är 09:30 i Stockholm på sommaren — alltså inom fönstret.
    Räknades det i UTC hade varje morgon före 10:00 svensk tid köats om."""
    nu = datetime(2026, 8, 17, 7, 30, tzinfo=timezone.utc)
    assert kor(nu=nu).atgard == SKICKA


# -- Regel 6: granskningskö -------------------------------------------------


@pytest.mark.parametrize("skickade", range(GRANSKADE_FORSTA_UTSKICK))
def test_regel_6_de_forsta_utskicken_granskas(skickade):
    beslut = kor(historik=historik(skickade_totalt=skickade))
    assert beslut.atgard == GRANSKA
    assert beslut.regel == "6_granskningsko"


def test_regel_6_slapper_efter_tre():
    assert kor(historik=historik(skickade_totalt=GRANSKADE_FORSTA_UTSKICK)).atgard == SKICKA


def test_regel_6_ligger_sist():
    """Ett mejl som bryter mot regel 2 ska blockeras, inte läggas i en
    granskningskö där en människa förväntas upptäcka samma sak."""
    beslut = kor(
        utskick=utskick(brodtext=FULLSTANDIG_TEXT.replace("https://livrustning.example/avregistrera?t=abc123", "")),
        historik=historik(skickade_totalt=0),
    )
    assert beslut.regel == "2_avregistrering"


# -- Företagsnyckeln --------------------------------------------------------


def test_foretagsnyckeln_foredrar_orgnr():
    """Den enda identifierare som överlever att bolaget byter domän."""
    assert foretagsnyckel(orgnr="556824-9022", epost="a@b.se", hemsida="b.se") == "5568249022"


def test_foretagsnyckeln_faller_tillbaka_pa_doman():
    assert foretagsnyckel(orgnr=None, epost=None, hemsida="https://www.Bolaget.se/om") == "bolaget.se"
    assert foretagsnyckel(orgnr="", epost="info@bolaget.se", hemsida=None) == "bolaget.se"


def test_foretagsnyckeln_ar_tom_nar_inget_finns():
    assert foretagsnyckel(orgnr=None, epost=None, hemsida=None) == ""
