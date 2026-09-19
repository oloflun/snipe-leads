"""scripts/livrustning_kb_synk.py — planen rör bara artiklar vi själva seedat."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "snajp-support"))

import livrustning_kb_synk as synk  # noqa: E402


def _ny(index: int = 0) -> dict:
    return synk.KB_ARTICLES[index]


def test_gamla_seedartiklar_tas_bort_och_alla_nya_laggs_in():
    befintliga = [{"id": "1", "title": "Frakt och leverans", "content": "Gammal webbutik."}]
    bort, in_ = synk.plan(befintliga)
    assert [a["id"] for a in bort] == ["1"]
    assert len(in_) == len(synk.KB_ARTICLES)


def test_kundens_egna_artiklar_rors_inte():
    befintliga = [{"id": "9", "title": "Parkering vid kurslokalen", "content": "Egen text."}]
    bort, _ = synk.plan(befintliga)
    assert bort == []


def test_oforandrad_artikel_lamnas_och_laggs_inte_in_igen():
    befintliga = [{"id": "2", "title": _ny()["title"], "content": _ny()["content"]}]
    bort, in_ = synk.plan(befintliga)
    assert bort == []
    assert _ny()["title"] not in {a["title"] for a in in_}


def test_andrad_artikel_med_ny_rubrik_byts():
    befintliga = [{"id": "3", "title": _ny()["title"], "content": "Äldre formulering."}]
    bort, in_ = synk.plan(befintliga)
    assert [a["id"] for a in bort] == ["3"]
    assert _ny()["title"] in {a["title"] for a in in_}


def test_dubblett_av_ny_artikel_tas_bort():
    rad = {"title": _ny()["title"], "content": _ny()["content"]}
    bort, in_ = synk.plan([{"id": "4", **rad}, {"id": "5", **rad}])
    assert [a["id"] for a in bort] == ["5"]
    assert _ny()["title"] not in {a["title"] for a in in_}
