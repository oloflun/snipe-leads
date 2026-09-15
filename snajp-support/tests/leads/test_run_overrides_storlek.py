"""Formulärets storlek ska nå prompten även när den sparade ICP:n bär `size`.

Uppmätt 2026-09-15: en körning beställd på 10–49 anställda fällde Filed AB
mot "1-49". Den sparade ICP:n (normaliserad) bär både company_size och size,
och normalize_icp läser size SIST - överskrivningen skrevs bara till
company_size och försvann. test_run_overrides.py missade det eftersom dess
sparade ICP saknar size.
"""

from __future__ import annotations

from app.leads.context_pack import _med_overrides
from app.leads.icp import normalize_icp, render_icp

SPARAT = normalize_icp({"industries": ["Bygg"], "company_size": {"min": 1, "max": 49}})


def test_sparad_icp_bar_size_som_i_drift():
    assert SPARAT["size"]["anstallda_min"] == 1


def test_formularets_storlek_vinner_over_den_sparade():
    sammanslagen = normalize_icp(_med_overrides(SPARAT, {"anstallda_min": 10, "anstallda_max": 49}))
    assert sammanslagen["size"]["anstallda_min"] == 10
    assert sammanslagen["size"]["anstallda_max"] == 49
    assert sammanslagen["company_size"] == {"min": 10, "max": 49}
    assert "10" in render_icp(sammanslagen)


def test_bara_taket_overskrivs_golvet_behalls():
    sammanslagen = normalize_icp(_med_overrides(SPARAT, {"anstallda_max": 25}))
    assert sammanslagen["size"]["anstallda_min"] == 1
    assert sammanslagen["size"]["anstallda_max"] == 25
