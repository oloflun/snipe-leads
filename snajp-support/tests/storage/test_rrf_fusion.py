"""RRF-fusionen i hybridsökningen (postgres._rrf_fusion) — ren funktion,
falsifierbar utan databas."""

from app.storage.postgres import _rrf_fusion


def _rad(id_, sim=0.5):
    return {
        "id": id_,
        "title": f"artikel-{id_}",
        "content": "…",
        "category": "ovrigt",
        "similarity": sim,
    }


def test_dokument_i_bada_listorna_vinner_over_ensamma_forstaplatser():
    """Kärnan i RRF: 'båda vägarna hittade den' är en starkare signal än en
    förstaplats i en enda lista."""
    vektor = [_rad("a"), _rad("b")]
    fulltext = [_rad("c"), _rad("b")]
    resultat = _rrf_fusion(vektor, fulltext, limit=3)
    assert resultat[0]["id"] == "b", [r["id"] for r in resultat]


def test_tom_vektorlista_ger_fulltextens_ordning():
    fulltext = [_rad("x"), _rad("y"), _rad("z")]
    resultat = _rrf_fusion([], fulltext, limit=3)
    assert [r["id"] for r in resultat] == ["x", "y", "z"]


def test_tom_fulltext_ger_vektorns_ordning():
    vektor = [_rad("x"), _rad("y")]
    assert [r["id"] for r in _rrf_fusion(vektor, [], limit=3)] == ["x", "y"]


def test_limit_kapas_efter_fusionen_inte_fore():
    """Ett dokument på plats 3 i BÅDA listorna ska kunna slå ettan i en —
    därför måste kandidatlistorna in i fusionen okapade."""
    vektor = [_rad("a"), _rad("b"), _rad("gemensam")]
    fulltext = [_rad("c"), _rad("d"), _rad("gemensam")]
    resultat = _rrf_fusion(vektor, fulltext, limit=1)
    assert resultat[0]["id"] == "gemensam"


def test_faltvarden_tas_fran_listan_som_rankade_dokumentet_forst():
    vektor = [_rad("b", sim=0.91)]
    fulltext = [_rad("b", sim=0.12)]
    resultat = _rrf_fusion(vektor, fulltext, limit=1)
    assert resultat[0]["similarity"] == 0.91


def test_bada_listorna_tomma_ger_tomt():
    assert _rrf_fusion([], [], limit=3) == []
