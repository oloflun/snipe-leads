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
    return {"andrad": andrad, "hash": h, "rad": {"id": k, "h": h}}


def test_main_vinner_och_forsta_synken_ger_development():
    # b ändrades senast i development, men main är sanningen ändå.
    dev = {"a": _r("a", "1", T0), "b": _r("b", "1", T0 + timedelta(hours=1))}
    main = {"a": _r("a", "2", T0 + timedelta(hours=1)), "b": _r("b", "2", T0)}
    plan = synk.planera(dev, main, {}, forsta=False)
    assert sorted(r["id"] for r in plan["till_dev"]) == ["a", "b"] and not plan["till_main"]
    forsta = synk.planera(dev, main, {}, forsta=True)
    assert sorted(r["id"] for r in forsta["till_main"]) == ["a", "b"] and not forsta["till_dev"]


def test_development_korningar_stannar_tills_de_flyttas():
    dev = {"ny": _r("ny", "1", T0), "gammal": _r("gammal", "1", T0)}
    main = {"bara_main": _r("bara_main", "1", T0)}
    raderad_i_main = {"gammal": T0 + timedelta(minutes=5)}
    plan = synk.planera(dev, main, raderad_i_main, forsta=False)
    assert not plan["till_main"] and not plan["radera_main"]  # main skrivs aldrig efter första synken
    assert plan["radera_dev"] == ["gammal"]  # main raderade den
    assert [r["id"] for r in plan["till_dev"]] == ["bara_main"]
    # Första synken raderar aldrig och för över allt från development.
    forsta = synk.planera(dev, main, raderad_i_main, forsta=True)
    assert not forsta["radera_dev"] and sorted(r["id"] for r in forsta["till_main"]) == ["gammal", "ny"]
