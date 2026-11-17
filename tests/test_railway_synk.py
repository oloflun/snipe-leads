"""Synkens regler (scripts/railway_synk.py:planera). Anton 2026-10-17: första
synken för över allt från development, därefter är main sanningen och
körningar gjorda i development flyttas aktivt."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "railway_synk", Path(__file__).resolve().parents[1] / "scripts" / "railway_synk.py"
)
synk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(synk)

T0 = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)


def _r(k, h, andrad):
    return {"andrad": andrad, "hash": h, "pmid": None}


def test_main_vinner_och_forsta_synken_ger_development():
    # b ändrades senast i development, men main är sanningen ändå.
    dev = {"a": _r("a", "1", T0), "b": _r("b", "1", T0 + timedelta(hours=1))}
    main = {"a": _r("a", "2", T0 + timedelta(hours=1)), "b": _r("b", "2", T0)}
    plan = synk.planera(dev, main, {}, forsta=False)
    assert sorted(plan["till_dev"]) == ["a", "b"] and not plan["till_main"]
    forsta = synk.planera(dev, main, {}, forsta=True)
    assert sorted(forsta["till_main"]) == ["a", "b"] and not forsta["till_dev"]


def test_development_korningar_stannar_tills_de_flyttas():
    dev = {"ny": _r("ny", "1", T0), "gammal": _r("gammal", "1", T0)}
    main = {"bara_main": _r("bara_main", "1", T0)}
    raderad_i_main = {"gammal": T0 + timedelta(minutes=5)}
    plan = synk.planera(dev, main, raderad_i_main, forsta=False)
    assert not plan["till_main"] and not plan["radera_main"]  # main skrivs aldrig efter första synken
    assert plan["radera_dev"] == ["gammal"]  # main raderade den
    assert plan["till_dev"] == ["bara_main"]
    # Första synken raderar aldrig och för över allt från development.
    forsta = synk.planera(dev, main, raderad_i_main, forsta=True)
    assert not forsta["radera_dev"] and sorted(forsta["till_main"]) == ["gammal", "ny"]


# -- Development före main (Anton 2026-11-16) -----------------------------------
#
# En migration körs i development vid pushen och i main först vid releasen.
# Kravet på exakt samma version stoppade synken hela den tiden: 2026-11-10 till
# 16 stod den röd för att 115 bara fanns i development.

M114 = "20261025090000_114_kampanj_id"
M115 = "20261110090000_115_lasvagsindex"
M116 = "20261115090000_116_demolank_och_svarsklass"


def test_development_far_ligga_fore_main_men_inte_tvartom():
    assert synk.schemalage({M114, M115}, {M114, M115}) == ([], [])
    assert synk.schemalage({M114, M115, M116}, {M114}) == ([M115, M116], [])
    assert synk.schemalage({M114}, {M114, M115}) == ([], [M115])


def test_gamla_liggarposter_under_bytta_namn_ar_inget_schema_som_skiljer():
    # Developments liggare bär poster som main saknar under samma namn (056,
    # 066, 092, sedda 2026-11-16). De ligger under den högsta versionen i båda
    # miljöerna och får varken stoppa synken eller räknas som "före".
    dev = {"056_orgnr_for_current_tenant", "20260919100000_066_rls_nullif_vakt", M114, M115}
    main = {"056_orgnr", M114, M115}
    assert synk.schemalage(dev, main) == ([], [])


def test_kolumnjamforelsen_skiljer_egna_kolumner_fran_det_som_inte_gar_att_spegla():
    gemensam = {"id": ("uuid", False), "body": ("text", False)}
    dev = {**gemensam, "svarsklass": ("text", False), "nyckel": ("text", True)}
    assert synk.jamfor_kolumner(dev, gemensam) == (["svarsklass", "nyckel"], [], [])
    # Main före development, eller en ändrad typ, går inte att spegla.
    assert synk.jamfor_kolumner(gemensam, {**gemensam, "ny": ("text", False)}) == ([], ["ny"], [])
    assert synk.jamfor_kolumner(gemensam, {"id": ("uuid", False), "body": ("jsonb", False)}) == ([], [], ["body"])


class _Markor:
    """En databasmarkör som minns frågorna och svarar ur en kö."""

    def __init__(self, svar=()):
        self.fragor: list[tuple[str, tuple]] = []
        self._svar = list(svar)

    def execute(self, sql, params=()):
        self.fragor.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self._svar.pop(0)

    def fetchall(self):
        return self._svar.pop(0)

    def inserts(self):
        return [f for f, _ in self.fragor if f.startswith("insert into")]


def test_utan_egna_kolumner_skrivs_hela_raden_som_forut():
    kalla = _Markor([[("a", '{"id": "a", "body": "x"}')]])
    mal = _Markor([("uuid",), (["id", "body"],)])
    assert synk.skriv(kalla, mal, "t", ["id"], ["a"], []) == []
    assert mal.inserts() == [
        'insert into public.t ("id", "body") select "id", "body" '
        "from jsonb_populate_recordset(null::public.t, %s::jsonb)"
    ]
    assert not any("jsonb_build_object" in f for f, _ in mal.fragor)


def test_med_egna_kolumner_behaller_befintliga_rader_sina_varden_och_nya_far_standard():
    kalla = _Markor([[("a", '{"id": "a", "body": "ny"}'), ("b", '{"id": "b", "body": "ny"}')]])
    # Målet: nyckelns typ, de skrivbara kolumnerna, och sedan de sammanslagna
    # raderna för de nycklar som redan finns där (bara a).
    mal = _Markor([("uuid",), (["id", "body", "svarsklass"],), [("a", '{"id": "a", "body": "ny", "svarsklass": "positivt"}')]])
    assert synk.skriv(kalla, mal, "t", ["id"], ["a", "b"], [], egna=["svarsklass", "genererad"]) == []
    sammanslagning = next(f for f, _ in mal.fragor if "jsonb_build_object" in f)
    assert "jsonb_build_object('svarsklass', x.\"svarsklass\")" in sammanslagning
    # Läsningen av de egna värdena sker före första borttagningen.
    ordning = [f for f, _ in mal.fragor]
    assert ordning.index(sammanslagning) < next(i for i, f in enumerate(ordning) if f.startswith("delete"))
    alla, gemensamma = mal.inserts()
    assert '("id", "body", "svarsklass")' in alla and '("id", "body")' in gemensamma
    # Rad a skrivs med sitt behållna värde, rad b med bara källans kolumner.
    varden = [p[0] for f, p in mal.fragor if f.startswith("insert into")]
    assert '"svarsklass": "positivt"' in varden[0] and '"id": "b"' in varden[1] and "svarsklass" not in varden[1]
