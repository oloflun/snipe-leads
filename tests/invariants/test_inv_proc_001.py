"""INV-PROC-001: varje PR mot development besvarar säkerhets- och AI-frågan.

Prövar att mallen, skriptet och CI-steget hänger ihop, och att skriptet
fäller en beskrivning utan svar och släpper igenom en med svar.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MALL = ROOT / ".github" / "pull_request_template.md"
ARBETSFLODE = ROOT / ".github" / "workflows" / "pr-granskning.yml"
SKRIPT = ROOT / "scripts" / "pr_granskning.py"


def _modul():
    spec = importlib.util.spec_from_file_location("pr_granskning", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_mallen_bar_avsnitten_som_skriptet_kraver():
    mall = MALL.read_text(encoding="utf-8")
    pg = _modul()
    for rubrik in pg.AVSNITT:
        assert f"## {rubrik}" in mall
    # Mallen som den står, utan kryss, ska fällas: annars är frågan inte ställd.
    assert len(pg.brister(mall)) == len(pg.AVSNITT)


def test_ikryssade_svar_godtas():
    pg = _modul()
    text = MALL.read_text(encoding="utf-8")
    text = text.replace("- [ ] Ändringen rör inte persondata", "- [x] Ändringen rör inte persondata", 1)
    text = text.replace("- [ ] Ingen prompt", "- [X] Ingen prompt", 1)
    assert pg.brister(text) == []


def test_ett_kryss_i_fel_avsnitt_raknas_inte():
    pg = _modul()
    text = "## Säkerhet och dataskydd\n- [x] Ändringen rör inte persondata\n## AI-påverkan\n- [ ] Ingen prompt\n"
    fel = pg.brister(text)
    assert len(fel) == 1 and "AI-påverkan" in fel[0]


def test_tom_beskrivning_falls():
    pg = _modul()
    assert len(pg.brister("")) == 2


def test_undantagen_ar_botar_och_andra_basgrenar():
    pg = _modul()
    bot = {"pull_request": {"user": {"login": "dependabot[bot]"}, "base": {"ref": "development"}}}
    release = {"pull_request": {"user": {"login": "oloflun"}, "base": {"ref": "main"}}}
    vanlig = {"pull_request": {"user": {"login": "oloflun"}, "base": {"ref": "development"}}}
    assert pg.undantag(bot) and pg.undantag(release)
    assert pg.undantag(vanlig) is None


def test_main_faller_en_pr_utan_svar(tmp_path, monkeypatch):
    pg = _modul()
    handelse = tmp_path / "event.json"
    handelse.write_text(json.dumps({"pull_request": {"user": {"login": "oloflun"},
                                                     "base": {"ref": "development"}, "body": "Fixar något."}}),
                        encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(handelse))
    assert pg.main([]) == 1


def test_ci_kor_skriptet_pa_varje_pull_request_och_vid_redigering():
    import yaml

    flode = yaml.safe_load(ARBETSFLODE.read_text(encoding="utf-8"))
    # PyYAML läser nyckeln `on` som True.
    utlosare = flode.get("on", flode.get(True))
    assert {"opened", "edited", "synchronize"} <= set(utlosare["pull_request"]["types"])
    steg = [s for jobb in flode["jobs"].values() for s in jobb["steps"]]
    assert any("scripts/pr_granskning.py" in (s.get("run") or "") for s in steg)
