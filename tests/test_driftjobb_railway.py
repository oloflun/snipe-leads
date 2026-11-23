"""Driftjobben hos Railway (2026-11-23): övervakningen som eget jobb,
startkommandot för den, och uppsättningen av tjänsterna.

GitHub slutade starta jobb för repot 2026-11-23, och synken, migrationerna
och övervakningen stod still. Testerna låser det som då byggdes: kontrollen
larmar på rätt saker, larmet går inte ut som en flod, och uppsättningen
skriver aldrig ett hemligt värde.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parents[1]
SKRIPT = ROT / "scripts"


def _ladda(namn: str):
    sys.path.insert(0, str(SKRIPT))
    spec = importlib.util.spec_from_file_location(namn, SKRIPT / f"{namn}.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


overvakning = _ladda("overvakning")
drift = _ladda("railway_drift")
driftjobb = _ladda("railway_driftjobb")

FRISK = {
    overvakning.WEBB_URL: (200, None),
    overvakning.API_HALSA_URL: (200, {"status": "ok", "mode": "live", "storage": "postgres", "jobs": "redis"}),
    overvakning.API_REDO_URL: (200, {"status": "ok", "degraded": False}),
}


def _hamtare(svar: dict):
    return lambda url: svar[url]


# -- Kontrollen --------------------------------------------------------------


def test_friskt_lage_ger_inga_avvikelser():
    assert overvakning.avvikelser(_hamtare(FRISK)) == []


def test_webben_nere_och_lagringen_borta_larmar_var_for_sig():
    svar = {**FRISK, overvakning.WEBB_URL: (502, None), overvakning.API_REDO_URL: (503, None)}
    rader = overvakning.avvikelser(_hamtare(svar))
    assert len(rader) == 2
    assert "HTTP 502" in rader[0] and "HTTP 503" in rader[1]
    assert "lagringen inte svarar" in rader[1]


def test_simulering_och_minneslagring_i_produktionen_ar_avvikelser():
    """200 räcker inte: ett api som svarar men kör på simulering eller i
    minnet är ett driftfel (health() i snajp-support/app/main.py)."""
    halsa = {"status": "ok", "mode": "simulation", "storage": "memory", "jobs": "redis"}
    rader = overvakning.avvikelser(_hamtare({**FRISK, overvakning.API_HALSA_URL: (200, halsa)}))
    assert [r for r in rader if "fältet mode är simulation" in r]
    assert [r for r in rader if "fältet storage är memory" in r]


def test_degraderat_lage_larmar():
    svar = {**FRISK, overvakning.API_REDO_URL: (200, {"status": "ok", "degraded": True})}
    assert overvakning.avvikelser(_hamtare(svar)) == [
        f"Beredskapskontrollen {overvakning.API_REDO_URL}: fältet degraded är true (väntat false)."
    ]


def test_ett_svar_som_inte_ar_json_larmar():
    rader = overvakning.avvikelser(_hamtare({**FRISK, overvakning.API_HALSA_URL: (200, None)}))
    assert rader == [f"Hälsokontrollen {overvakning.API_HALSA_URL} svarade inte med JSON."]


@pytest.mark.parametrize(
    "varde, ut",
    [("ok", "ok"), (None, "(saknas)"), ("", "(saknas)"), (True, "true"),
     ("<script>alert(1)</script>", "(oväntat värde)"), ("x" * 40, "(oväntat värde)")],
)
def test_faltvarden_saneras_innan_de_nar_ett_mejl(varde, ut):
    assert overvakning.sanera(varde) == ut


# -- Larmet ------------------------------------------------------------------


def test_samma_avvikelse_i_samma_block_ger_samma_nyckel():
    rader = ["Webbens startsida svarade HTTP 502 (väntat 200)."]
    a = overvakning.larmnyckel(rader, datetime(2026, 11, 23, 12, 5, tzinfo=timezone.utc))
    b = overvakning.larmnyckel(rader, datetime(2026, 11, 23, 17, 55, tzinfo=timezone.utc))
    assert a == b  # 12–18 är ett block: mejltjänsten skickar inte en gång till


def test_ny_avvikelse_eller_nytt_block_ger_ny_nyckel():
    nu = datetime(2026, 11, 23, 12, 5, tzinfo=timezone.utc)
    grund = overvakning.larmnyckel(["a"], nu)
    assert overvakning.larmnyckel(["a", "b"], nu) != grund
    assert overvakning.larmnyckel(["a"], datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc)) != grund
    assert overvakning.larmnyckel(["a"], datetime(2026, 11, 24, 12, 5, tzinfo=timezone.utc)) != grund


def test_larmet_utan_mejltjanst_sager_det_i_loggen():
    rad = overvakning.skicka_larm(["x"], datetime(2026, 11, 23, tzinfo=timezone.utc), environ={})
    assert rad.startswith("LARMET SKICKADES INTE")


def test_provlarmet_har_eget_amne_sa_att_det_inte_las_som_ett_avbrott():
    amne, text = overvakning.larmmejl([overvakning.SIMULERAT], datetime(2026, 11, 23, tzinfo=timezone.utc))
    assert "prov" in amne and "Inget är nere" in text


# -- Startkommandot ----------------------------------------------------------


def test_overvakningen_kors_i_development_och_inte_i_main():
    steg = drift.kommandon("overvakning", {"RAILWAY_ENVIRONMENT_NAME": "development"})
    assert len(steg) == 1 and steg[0][-1].endswith("overvakning.py")
    with pytest.raises(SystemExit, match="development"):
        drift.kommandon("overvakning", {"RAILWAY_ENVIRONMENT_NAME": "main"})
    with pytest.raises(SystemExit):
        drift.kommandon("overvakning", {})


# -- Uppsättningen -----------------------------------------------------------


def test_varje_jobb_bygger_driftavbilden_och_startar_startkommandot():
    for namn, jobb in driftjobb.JOBB.items():
        vill = driftjobb.onskat(jobb)
        assert vill["dockerfilePath"] == "railway/Dockerfile.drift", namn
        assert vill["startCommand"].startswith("python scripts/railway_drift.py "), namn
        assert vill["restartPolicyType"] == "NEVER", namn  # ett jobb som fallit startas inte om i en slinga
        assert "railway/Dockerfile.drift" in vill["watchPatterns"], namn


def test_uppsattningen_skriver_aldrig_ett_hemligt_varde():
    """Variablerna är referenser till andra tjänsters variabler eller öppna
    värden. Ett lösenord eller en nyckel i klartext får aldrig stå i repot."""
    for namn, jobb in driftjobb.JOBB.items():
        for variabel, varde in {**jobb["variabler"], **jobb["skarp"]}.items():
            utan_referenser = varde
            while "${{" in utan_referenser:
                i = utan_referenser.index("${{")
                utan_referenser = utan_referenser[:i] + utan_referenser[utan_referenser.index("}}", i) + 2 :]
            hemlig = any(ord_ in variabel for ord_ in ("KEY", "PASSWORD", "TOKEN", "SECRET", "LOSEN"))
            assert not (hemlig and utan_referenser.strip()), f"{namn}.{variabel} bär ett värde i klartext"
            if "://" in varde and "@" in varde:
                assert "${{" in varde.split("@")[0], f"{namn}.{variabel} bär ett lösenord i klartext"


def test_synken_och_migrationerna_torrkor_tills_skrivningen_slas_pa():
    """Skrivningen är en egen flagga (--skarp) och står aldrig bland de
    variabler som sätts när tjänsten skapas."""
    for namn in ("synk", "migrera-main"):
        jobb = driftjobb.JOBB[namn]
        assert jobb["skarp"] and not set(jobb["skarp"]) & set(jobb["variabler"]), namn


def test_produktionens_jobb_byggs_fran_main_och_overvakningen_fran_development():
    assert {n: (j["miljo"], j["gren"]) for n, j in driftjobb.JOBB.items()} == {
        "migrera-main": ("main", "main"),
        "synk": ("main", "main"),
        "overvakning": ("development", "development"),
    }


def test_skillnaden_ar_bara_det_som_avviker():
    vill = driftjobb.onskat(driftjobb.JOBB["synk"])
    assert driftjobb.skillnad(vill, vill) == {}
    assert driftjobb.skillnad({**vill, "cronSchedule": "0 * * * *"}, vill) == {"cronSchedule": "*/10 * * * *"}
    assert set(driftjobb.skillnad(None, vill)) >= {"startCommand", "dockerfilePath", "cronSchedule"}
