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
    UPPVARMNING_TAK_PER_DAG,
    Avsandare,
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

Avregistrera dig: https://livrustning.example/avregistrera?t=abc123
"""

#: En vardag klockan 10 svensk tid. 2026-08-17 är en måndag.
VARDAG_FORMIDDAG = datetime(2026, 8, 17, 10, 0, tzinfo=STOCKHOLM).astimezone(timezone.utc)


def historik(**overrides) -> TenantHistorik:
    bas = {
        "skickade_totalt": 50,
        "skickade_idag": 0,
        "tenant_alder_dagar": 365,
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


@pytest.mark.parametrize(
    "bortplockat,forvantat_ord",
    [
        ("Livrustning AB", "företagsnamn"),
        ("556824-9022", "organisationsnummer"),
        ("Rudsjövägen 112, 131 47 Nacka", "postadress"),
    ],
)
def test_regel_1_kraver_alla_tre_identitetsuppgifterna(bortplockat, forvantat_ord):
    """Marknadsföringslagen kräver identifierbar avsändare, e-handelslagen
    org.nr. Kravet gäller hyreskunden, inte Snajp."""
    beslut = kor(utskick=utskick(brodtext=FULLSTANDIG_TEXT.replace(bortplockat, "")))
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "1_avsandaridentifikation"
    assert forvantat_ord in beslut.skal


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
    """Taket är en uppvärmningskurva, inte ett permanent tak."""
    assert kor(historik=historik(tenant_alder_dagar=90, skickade_idag=50)).atgard == SKICKA


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
