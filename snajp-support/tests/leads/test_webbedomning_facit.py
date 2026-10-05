"""Webbkriteriet mot Antons facit (granskningen av Alunix-leadsen 2026-10-04).

Facit, med Antons ord i korthet:
  Byggarna Berggren  — en verkligt dålig/gammal sida            → träff
  Vicht Engineering  — påståendet stämde (sidan svarar inte)   → träff
  Torbens Byggservice— parkerad domän                           → listspåret, inte Iris
  Ställningskompaniet— gränsfall, "kan vara värt att höra av sig" → okänt
  Björkekärrs Bygg   — bra sida                                 → miss
  Eustaff            — verkligt professionell, scrollanimationer → miss
  Ostia              — internationellt bolag, fel målgrupp      → fälls på storlek

Riktiga sidor checkas inte in (de bär verkliga personers uppgifter).
Bildbedömningens betyg nedan är vad den ska ge enligt kalibreringen i
webbrevision.VISIONPROMPT; scripts/kalibrera_webbrevision.py kör den skarpt
mot de riktiga sajterna och jämför med samma facit.
"""

from __future__ import annotations

import pytest

from app.leads.bedomning import bedom, webbutslag
from app.leads.scoring import MISS, OKAND, TRAFF

KRITERIUM = "Företag med gamla hemsidor"

FACIT = [
    ("Byggarna Berggren", 2, TRAFF),
    ("Vicht Engineering", 3, TRAFF),
    ("Ställningskompaniet", 5, OKAND),
    ("Björkekärrs Bygg", 7, MISS),
    ("Eustaff", 9, MISS),
]


@pytest.mark.parametrize(("bolag", "modernitet", "vantat"), FACIT)
def test_webbkriteriet_foljer_facit(bolag, modernitet, vantat):
    utfall, motivering = webbutslag(KRITERIUM, {"modernitet": modernitet, "brister": ["Liten text"]})
    assert utfall == vantat, bolag
    assert f"modernitet {modernitet} av 10" in motivering


def test_riktningen_avgor_och_okand_riktning_lamnas_till_modellen():
    assert webbutslag("Har en modern och snabb webbplats", {"modernitet": 9})[0] == TRAFF
    assert webbutslag("Har en modern och snabb webbplats", {"modernitet": 2})[0] == MISS
    assert webbutslag("Webbplatsens innehåll", {"modernitet": 2}) is None
    assert webbutslag(KRITERIUM, None) is None


def test_sajt_som_inte_svarar_ar_en_traff():
    """Vicht: hemsidan svarade inte inom 10 sekunder, och Anton bekräftade utslaget."""
    assert webbutslag(KRITERIUM, {"svarar_inte": True})[0] == TRAFF


def test_utan_webbplats_avgors_i_kod_ur_profilen():
    """Förut kunde samma rad ("Ingen webbplats hittades") styrka både ja och nej."""
    assert webbutslag(KRITERIUM, {"saknas": True}, utan_webbplats=True)[0] == TRAFF
    assert webbutslag(KRITERIUM, {"saknas": True}, utan_webbplats=False)[0] == MISS


def _profil() -> dict:
    return {
        "anstallda_min": 1,
        "anstallda_max": 49,
        "kriterier": [{"id": "k1", "text": KRITERIUM, "krav": "maste", "vikt": 3, "belagg": "webbsignal"}],
    }


def test_modellens_ja_overstyrs_av_betyget():
    """Björkekärr fick 80 för "gamla hemsidor" 2026-10-04. Med ett betyg på 7
    fälls kriteriet i kod, vad modellen än svarade."""
    fynd = {"bedomningar": [{"kriterie_id": "k1", "utslag": "ja", "belagg": [{"citat": "Inga tecken"}]}],
            "antal_anstallda": 2}
    ut = bedom(_profil(), fynd, korpus="Inga tecken", kandidat={"website": "https://x.se"},
               webbrevision={"modernitet": 7, "rader": ["Visuell bedömning av startsidan: modernitet 7 av 10."]})
    rad = next(r for r in ut["score_breakdown"] if r["nyckel"] == "k1")
    assert rad["utfall"] == MISS and ut["niva"] == "C"
    assert rad["belagg"][0]["citat"].startswith("Visuell bedömning")


def test_internationellt_bolag_falls_pa_storlek():
    """Ostia: en anställd i den svenska enheten, men ett internationellt bolag."""
    fynd = {"bedomningar": [], "antal_anstallda": 1}
    ut = bedom(_profil(), fynd, korpus="", kandidat={}, webbrevision={"modernitet": 6, "internationell": True})
    rad = next(r for r in ut["score_breakdown"] if r["nyckel"] == "storlek")
    assert rad["utfall"] == MISS and ut["niva"] == "C"
