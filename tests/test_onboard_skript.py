"""Onboardingskripten mot dagens drift: scripts/onboard_tenant.py,
scripts/fyll_kundregister.py och miljönamnen i scripts/gallra.py.

Utan databas och utan nätverk (samma hermetik som test_konvertera_testkund.py):
`.env.deploy` läses aldrig, urlopen och Railway-anropen är ersatta med fällor
som fäller testet om de nås.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fyll_kundregister as fk  # noqa: E402
import gdpr_verktyg  # noqa: E402
import onboard_tenant as ot  # noqa: E402

ONBOARD_KALLA = (SCRIPTS / "onboard_tenant.py").read_text(encoding="utf-8")


# --- onboard_tenant.py --------------------------------------------------------


@pytest.mark.parametrize(
    "spar",
    [
        "vercel_env_set",
        "vercel_scopes",
        "rest/v1",
        "SUPABASE_SERVICE_ROLE_KEY",
        "NEXT_PUBLIC_SUPABASE_URL",
        "supabase.co",
        "Prefer",
    ],
)
def test_onboard_har_ingen_vag_mot_gamla_stacken(spar):
    assert spar not in ONBOARD_KALLA


def test_onboard_importerar_inget_vercel_eller_supabase():
    trad = ast.parse(ONBOARD_KALLA)
    namn = set()
    for nod in ast.walk(trad):
        if isinstance(nod, ast.ImportFrom):
            namn.update(a.name for a in nod.names)
            namn.add(nod.module or "")
        elif isinstance(nod, ast.Import):
            namn.update(a.name for a in nod.names)
    assert not {n for n in namn if "vercel" in n.lower() or "supabase" in n.lower()}


def test_onboard_kanner_bara_railway_miljoerna():
    from railway_provision import ENVIRONMENTS

    assert set(ot.MILJOER) == set(ENVIRONMENTS) == {"development", "main"}


def test_create_tenant_and_key_ar_kvar_for_railway_tenant_keys():
    # railway_tenant_keys.py importerar funktionen; den får inte försvinna.
    assert callable(ot.create_tenant_and_key)
    assert '"kraver_avtal": True' in ONBOARD_KALLA


@pytest.fixture
def utan_natverk(monkeypatch, tmp_path):
    """Fällor för varje sidoeffekt. Ett anrop av någon av dem fäller testet."""

    def falla(namn):
        def _f(*a, **k):
            raise AssertionError(f"{namn} anropades i en torrkörning")

        return _f

    for namn in ("create_tenant_and_key", "env_set", "state", "set_vars", "deploy",
                 "write_tenant_config", "write_kb_module"):
        monkeypatch.setattr(ot, namn, falla(namn))
    monkeypatch.setattr(ot.urllib.request, "urlopen", falla("urlopen"))
    monkeypatch.setattr(ot, "guard_gitignored", lambda: None)
    monkeypatch.setattr(
        ot,
        "env_read",
        lambda: {
            "RAILWAY_DEVELOPMENT_API_URL": "https://api.exempel.invalid",
            "RAILWAY_DEVELOPMENT_MASTER_API_KEY": "x",
            "RAILWAY_MAIN_API_URL": "https://api-main.exempel.invalid",
            "RAILWAY_MAIN_MASTER_API_KEY": "y",
        },
    )


def test_torrkorning_ar_standard_och_rör_ingenting(utan_natverk, capsys):
    assert ot.main(["--name", "Bolaget AB"]) == 0
    ut = capsys.readouterr().out
    assert "TORRKÖRNING" in ut
    assert "RAILWAY_DEVELOPMENT_KEY_BOLAGET_AB" in ut
    assert "SNAJP_KEY_BOLAGET_AB" in ut


def test_main_kraver_produktionskvitto(utan_natverk):
    with pytest.raises(SystemExit):
        ot.main(["--name", "Bolaget AB", "--env", "main"])


def test_gamla_miljonamn_vagras(utan_natverk):
    for gammal in ("preview", "production"):
        with pytest.raises(SystemExit):
            ot.main(["--name", "Bolaget AB", "--env", gammal])


def test_juridiska_stegen_i_dokumentets_ordning():
    text = ot.juridiska_steg("bolaget", "development")
    assert "docs/pilot_onboarding.md" in text
    ordning = [
        "Personuppgiftsbiträdesavtalet",
        "fyll_kundregister.py --slug bolaget",
        "Avtal signerat",
        "kundmall_informationstext.md",
        "policy_url",
        "gallra.py --env railway-development --tenant bolaget --satt-policy",
    ]
    positioner = [text.index(s) for s in ordning]
    assert positioner == sorted(positioner)


def test_juridiska_stegen_mot_main_bar_kvitto_och_ratt_miljo():
    text = ot.juridiska_steg("bolaget", "main")
    assert "--env main --jag-menar-produktion" in text
    assert "--env railway-main" in text


def test_arbetsytan_ar_ett_manuellt_steg():
    text = ot.manuella_steg("bolaget", "development")
    assert "railway_link_admin_workspace.py" in text
    assert "link_workspace_tenant" in text
    assert "seed_kb" not in text  # läser snajp-support/.env, inte Railway


def test_registreringen_i_index_ts_traffar_dagens_register(tmp_path, monkeypatch):
    tenants = tmp_path / "tenants"
    tenants.mkdir()
    original = (ROOT / "lib" / "tenants" / "index.ts").read_bytes().decode("utf-8")
    (tenants / "index.ts").write_bytes(original.encode("utf-8"))
    monkeypatch.setattr(ot, "TENANTS_DIR", tenants)
    assert ot.write_tenant_config("bolaget-ab", "Bolaget AB") is not None
    index = (tenants / "index.ts").read_bytes().decode("utf-8")
    # Filens egna radslut behålls (CRLF i en Windows-utcheckning, LF annars).
    assert ("\r\n" in index) == ("\r\n" in original)
    if "\r\n" in original:
        assert "\n" not in index.replace("\r\n", "")
    index = index.replace("\r\n", "\n")
    assert 'import { bolagetab } from "./bolaget-ab";' in index
    assert "const tenants: Record<string, Tenant> = {\n  bolagetab,\n" in index


# --- fyll_kundregister.py -----------------------------------------------------


def test_orgnr_och_adress_spärrar_inte():
    blockerar, bor = fk.grindlage("Bolaget AB", {"policy_url": "https://bolaget.se/integritet"})
    assert blockerar == []
    assert bor == ["orgnr", "foretagsadress"]


def test_foretagsnamn_och_policy_url_blockerar():
    blockerar, bor = fk.grindlage("", {"orgnr": "556824-9022", "foretagsadress": "Gatan 1"})
    assert len(blockerar) == 2
    assert blockerar[0].startswith("företagsnamn")
    assert blockerar[1].startswith("policy_url")
    assert bor == []


def test_allt_ifyllt():
    falt = {"orgnr": "556824-9022", "foretagsadress": "Gatan 1", "policy_url": "https://x.se/p"}
    assert fk.grindlage("Bolaget AB", falt) == ([], [])


def test_docstringen_kallar_inte_orgnr_en_sparr():
    doc = fk.__doc__ or ""
    assert "regel 1 vill se företagsnamn, organisationsnummer och postadress" not in doc
    assert "stoppar ALDRIG ett utskick" in doc


# --- gallra.py ----------------------------------------------------------------


def test_gallras_exempel_anvander_dagens_miljonamn():
    kalla = (SCRIPTS / "gallra.py").read_text(encoding="utf-8")
    trad = ast.parse(kalla)
    assert "dsn_for" in kalla  # samma hjälpmodul, samma vägran mot gamla stacken
    doc = ast.get_docstring(trad) or ""
    exempel = [r.split("--env", 1)[1].split()[0] for r in doc.splitlines() if "--env" in r]
    assert exempel, "gallra.py har inga --env-exempel"
    assert set(exempel) <= set(gdpr_verktyg.DAGENS_MILJOER)
