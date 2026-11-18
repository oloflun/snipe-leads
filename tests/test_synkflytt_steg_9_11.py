"""Synkflytten (docs/compliance/synkflytt-plan.md), kodstegen 2026-11-19:

* scripts/railway.py faller tillbaka på Railways inloggade CLI när
  RAILWAY_TOKEN saknas eller avvisas, och variablerna (som kan bära lösenord)
  går via stdin, aldrig som argument.
* scripts/releasens_migrationer.py: PR-kontrollen utan databas.
* scripts/railway_provision.py öppnar inte mains port igen när den är stängd.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
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


railway = _ladda("railway")
releasen = _ladda("releasens_migrationer")


# -- railway.py: reserven genom CLI:t ----------------------------------------


class _Kort:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


def test_utan_token_gar_fragan_genom_cli_med_variablerna_via_stdin(monkeypatch, tmp_path):
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    monkeypatch.setattr(railway, "REPO_ROOT", tmp_path)  # ingen .env.deploy
    monkeypatch.setattr("shutil.which", lambda _: "C:/railway.cmd")
    sett: dict = {}

    def kor(argv, **kw):
        sett["argv"], sett["input"] = argv, kw.get("input")
        sett["fraga"] = Path(argv[argv.index("--file") + 1]).read_text(encoding="utf-8")
        return _Kort(json.dumps({"data": {"me": {"email": "x"}}}))

    monkeypatch.setattr(subprocess, "run", kor)
    data = railway.gql("query { me { email } }", {"losen": "hemligt-varde"})
    assert data == {"me": {"email": "x"}}
    assert sett["argv"][0] == "C:/railway.cmd"
    assert "hemligt-varde" not in " ".join(sett["argv"])  # aldrig som argument
    assert json.loads(sett["input"]) == {"losen": "hemligt-varde"}
    assert sett["fraga"] == "query { me { email } }"


def test_avvisad_token_ger_reserven_men_ett_fel_i_fragan_gor_det_inte(monkeypatch):
    assert railway._avvisad({"errors": [{"message": "Not Authorized"}]})
    assert not railway._avvisad({"errors": [{"message": "Field 'x' doesn't exist"}]})
    assert not railway._avvisad({"data": {}})


def test_fel_fran_cli_kastar_runtimeerror(monkeypatch, tmp_path):
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    monkeypatch.setattr(railway, "REPO_ROOT", tmp_path)
    monkeypatch.setattr("shutil.which", lambda _: "railway")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Kort(json.dumps({"errors": [{"message": "nej"}]})))
    with pytest.raises(RuntimeError, match="nej"):
        railway.gql("query { x }")


# -- releasens_migrationer.py -------------------------------------------------


def test_repots_versioner_ar_samma_namn_som_liggaren(tmp_path):
    (tmp_path / "20261118110000_122_synk_lasroll.sql").write_text("select 1;", encoding="utf-8")
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    assert releasen.repots_versioner(tmp_path) == {"000_auth_compat", "20261118110000_122_synk_lasroll"}


def test_bedom_och_rapport():
    repo = {"000_auth_compat", "a", "b", "c"}
    okorda, releasens = releasen.bedom(repo, dev={"000_auth_compat", "a", "b"}, main={"000_auth_compat", "a"})
    assert okorda == ["c"] and releasens == ["b", "c"]
    text = releasen.rapport(okorda, releasens)
    assert "- b" in text and "okörda" in text
    assert "inga, schemat är redan aktuellt" in releasen.rapport([], [])


class _Api(BaseHTTPRequestHandler):
    versioner = ["000_auth_compat", "a"]

    def do_GET(self):  # noqa: N802
        if self.headers.get("X-Schema-Nyckel") != "ratt":
            self.send_response(401)
            self.end_headers()
            return
        kropp = json.dumps({"miljo": "development", "versioner": self.versioner}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(kropp)

    def log_message(self, *a):
        pass


@pytest.fixture
def api():
    server = HTTPServer(("127.0.0.1", 0), _Api)
    traad = threading.Thread(target=server.serve_forever, daemon=True)
    traad.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_hamta_las_versionerna_och_visar_aldrig_nyckeln(api):
    assert releasen.hamta(api, "ratt") == {"000_auth_compat", "a"}
    with pytest.raises(RuntimeError) as fel:
        releasen.hamta(api, "fel-nyckel")
    assert "401" in str(fel.value) and "fel-nyckel" not in str(fel.value)


def test_main_faller_nar_development_saknar_en_migration(api, monkeypatch, tmp_path):
    monkeypatch.setenv("SCHEMA_LASNYCKEL", "ratt")
    monkeypatch.setenv("DEV_API_URL", api)
    monkeypatch.setenv("MAIN_API_URL", api)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "sammanfattning.md"))
    monkeypatch.setattr(releasen, "repots_versioner", lambda: {"000_auth_compat", "a", "b"})
    assert releasen.main() == 1
    assert "- b" in (tmp_path / "sammanfattning.md").read_text(encoding="utf-8")
    monkeypatch.setattr(releasen, "repots_versioner", lambda: {"000_auth_compat", "a"})
    assert releasen.main() == 0


def test_main_utan_variabler_ger_2(monkeypatch):
    for n in ("SCHEMA_LASNYCKEL", "DEV_API_URL", "MAIN_API_URL"):
        monkeypatch.delenv(n, raising=False)
    assert releasen.main() == 2


# -- workflowen och provisioneringen ------------------------------------------


def test_workflowen_valjer_https_vagen_nar_nyckeln_finns():
    yml = (ROT / ".github" / "workflows" / "migrera.yml").read_text(encoding="utf-8")
    granska = yml[yml.index("  granska:"):]
    assert "SCHEMA_LASNYCKEL: ${{ secrets.SCHEMA_LASNYCKEL }}" in granska
    assert "python scripts/releasens_migrationer.py" in granska
    # Den gamla vägen (databasen över porten) körs bara när HTTPS-vägen hoppades över.
    assert granska.count("if: steps.https.outcome == 'skipped'") == 2


def test_provisioneringen_oppnar_inte_mains_port_igen():
    kod = (SKRIPT / "railway_provision.py").read_text(encoding="utf-8")
    vakt = kod.index('if env_name == "main" and not store.get("RAILWAY_MAIN_PG_HOST")')
    skapa = kod.index("tcpProxyCreate")
    assert vakt < skapa, "vakten för main måste stå före proxyskapandet"
    assert 'elif not store.get(f"RAILWAY_{env_name.upper()}_PG_HOST")' in kod
