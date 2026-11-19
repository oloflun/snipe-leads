"""scripts/railway_baslinje.py utan nätverk: maskeringen och jämförelsen."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SKRIPT = Path(__file__).resolve().parents[1] / "scripts" / "railway_baslinje.py"
_spec = importlib.util.spec_from_file_location("railway_baslinje", _SKRIPT)
rb = importlib.util.module_from_spec(_spec)
sys.modules["railway_baslinje"] = rb
_spec.loader.exec_module(rb)


# ---------------------------------------------------------------- maskeringen

HEMLIGA = {
    "DATABASE_URL": "postgresql://postgres:hemligtlosen@postgres.railway.internal:5432/railway",
    "REDIS_URL": "redis://default:hemligtlosen@redis.railway.internal:6379",
    "GEMINI_API_KEY": "AIzaFAKEFAKEFAKE",
    "AUTH_SECRET": "abc123",
    "OKANT_NAMN": "ofarligt-ord",  # okänt namn är en hemlighet även med ofarligt värde
    "SMTP_FROM": "hej@example.se",
    "WEBBPOOL_MOTTAGARE": '{"alunix": "x"}',
    "IMAP_PASSWORD_SNAJP": "true",  # booleskt värde men namnet bär PASSWORD
    "FOO_TOKEN_MODEL": "modell-x-1",  # mönstret *_MODEL men namnet bär TOKEN
}


@pytest.mark.parametrize("namn,varde", sorted(HEMLIGA.items()))
def test_hemligt_varde_slapps_aldrig(namn, varde):
    assert rb.synligt_varde(namn, varde) is None
    ut = rb.till_json(rb.maskera_variabler({namn: varde}))
    assert namn in ut
    assert varde not in ut
    assert "hemligtlosen" not in ut


@pytest.mark.parametrize("namn,varde", [
    ("LLM_PROVIDER", "postgresql://u:p@h/db"),        # vitlistat namn, fel form
    ("SITE_URL", "https://user:pass@www.snajp.se"),   # URL med inloggning
    ("SITE_URL", "https://www.snajp.se/?token=abc"),  # query kan bära en nyckel
    ("PUBLIC_BASE_URL", "ftp://example.se"),
    ("WEBBPOOL_FORDELNING", "sk-live-abcdef"),        # flagga som inte är boolesk
    ("INBOX_POLL_SECONDS", "300; rm -rf /"),
    ("MODEL", "En Lång Text Med Mellanslag"),
    ("RAILWAY_PUBLIC_DOMAIN", "user@host"),
    ("LLM_PROVIDER", 42),
])
def test_vitlistat_namn_med_fel_form_doljs(namn, varde):
    assert rb.synligt_varde(namn, varde) is None


@pytest.mark.parametrize("namn,varde", [
    ("LLM_PROVIDER", "gemini"),
    ("MODEL", "gemini-2.5-flash"),
    ("GEMINI_MODEL", "gemini-2.5-pro"),
    ("RAILWAY_ENVIRONMENT_NAME", "development"),
    ("WEBBPOOL_FORDELNING", "1"),
    ("GALLRING_AKTIV", "false"),
    ("INBOX_POLL_SECONDS", "300"),
    ("SITE_URL", "https://www.snajp.se"),
    ("SNAJP_SUPPORT_INTERNAL_URL", "http://snipe-leads.railway.internal:8080"),
    ("RAILWAY_SERVICE_WEB_URL", "www.snajp.se"),
])
def test_ofarliga_varden_syns(namn, varde):
    assert rb.synligt_varde(namn, varde) == varde


def test_maskera_variabler_form():
    ut = rb.maskera_variabler({"LLM_PROVIDER": "gemini", "DATABASE_URL": HEMLIGA["DATABASE_URL"]})
    assert ut == {"variabler": ["DATABASE_URL", "LLM_PROVIDER"], "varden": {"LLM_PROVIDER": "gemini"}}


def test_rensa_text_maskerar_url_med_losenord_helt():
    ut = rb.rensa_text("psql postgresql://postgres:hemligtlosen@db.example:5432/x -c 'select 1'")
    assert "hemligtlosen" not in ut and "postgres:" not in ut and "db.example" not in ut
    assert "<maskerad url>" in ut
    assert rb.rensa_text("API_KEY=abc ./start.sh") == "<maskerat: möjlig hemlighet>"
    assert rb.rensa_text(["node server.js"]) == ["node server.js"]
    assert rb.rensa_text(None) is None


def test_regioner_ur_konfig_laser_bara_regionen():
    konfig = {"services": {"s1": {"deploy": {"multiRegionConfig": {"ams": {"numReplicas": 2}}},
                                  "variables": {"X": {"value": "hemligtlosen"}}}}}
    assert rb.regioner_ur_konfig(konfig, "s1") == {"ams": 2}
    assert rb.regioner_ur_konfig(konfig, "saknas") is None
    assert rb.regioner_ur_konfig(None, "s1") is None


def test_hamta_skriver_aldrig_hemligt_varde():
    """Hela kedjan med ett falskt API: inget hemligt värde når baslinjen."""
    projekt = {"project": {"name": "brave-passion",
        "environments": {"edges": [{"node": {
            "id": "e1", "name": "main",
            "config": {"services": {"s1": {"deploy": {"multiRegionConfig": {"ams": {"numReplicas": 1}}},
                                           "variables": {"DATABASE_URL": {"value": HEMLIGA["DATABASE_URL"]}}}}},
            "deploymentTriggers": {"edges": [{"node": {"serviceId": "s1", "repository": "o/r", "branch": "main",
                                                        "provider": "github", "checkSuites": False}}]},
            "volumeInstances": {"edges": []},
        }}]},
        "services": {"edges": [{"node": {"id": "s1", "name": "api", "serviceInstances": {"edges": [{"node": {
            "environmentId": "e1", "deletedAt": None, "source": {"repo": "o/r", "image": None},
            "startCommand": "run postgresql://u:hemligtlosen@h/db",
            "domains": {"serviceDomains": [{"domain": "api.example"}], "customDomains": []},
        }}]}}}]},
    }}

    def falsk(fraga, variabler):
        if "project(" in fraga:
            return copy.deepcopy(projekt)
        return {"variables": dict(HEMLIGA, LLM_PROVIDER="gemini"), "tcpProxies": []}

    ut = rb.till_json(rb.hamta(falsk))
    for v in HEMLIGA.values():
        if len(v) > 5:  # korta värden ("true") kan förekomma i JSON-syntaxen; de prövas ovan
            assert v not in ut
    assert "hemligtlosen" not in ut
    data = json.loads(ut)
    api = data["miljoer"]["main"]["tjanster"]["api"]
    assert api["varden"] == {"LLM_PROVIDER": "gemini"}
    assert "DATABASE_URL" in api["variabler"]
    assert api["installningar"]["regioner_och_repliker"] == {"ams": 1}
    assert api["installningar"]["deploy_trigger"][0]["gren"] == "main"


# ---------------------------------------------------------------- jämförelsen

def _baslinje():
    return {
        "projekt": "brave-passion",
        "hamtad": "2026-11-18T00:00:00Z",
        "miljoer": {"main": {"tjanster": {
            "api": {
                "installningar": {"region": "ams", "halsokontroll": {"sokvag": "/health/live"},
                                  "deploy_trigger": [{"gren": "main"}]},
                "variabler": ["DATABASE_URL", "LLM_PROVIDER"],
                "varden": {"LLM_PROVIDER": "gemini"},
            },
            "web": {"installningar": {}, "variabler": [], "varden": {}},
        }}},
    }


def test_identiskt_ger_inga_avvikelser():
    nu = _baslinje()
    nu["hamtad"] = "2026-11-19T12:00:00Z"  # hämtningstiden jämförs inte
    assert rb.jamfor(_baslinje(), nu) == []


def test_tillagd_och_borttagen_tjanst():
    nu = _baslinje()
    del nu["miljoer"]["main"]["tjanster"]["web"]
    nu["miljoer"]["main"]["tjanster"]["ny"] = {"installningar": {}, "variabler": [], "varden": {}}
    assert rb.jamfor(_baslinje(), nu) == ["+ tjänst [main/ny]", "- tjänst [main/web]"]


def test_tillagd_och_borttagen_miljo():
    nu = _baslinje()
    nu["miljoer"]["development"] = nu["miljoer"].pop("main")
    assert rb.jamfor(_baslinje(), nu) == ["+ miljö development", "- miljö main"]


def test_tillagd_och_borttagen_variabel():
    nu = _baslinje()
    api = nu["miljoer"]["main"]["tjanster"]["api"]
    api["variabler"] = ["LLM_PROVIDER", "NY_NYCKEL"]
    assert rb.jamfor(_baslinje(), nu) == [
        "- variabel [main/api] DATABASE_URL",
        "+ variabel [main/api] NY_NYCKEL",
    ]


def test_andrat_vitlistat_varde_och_vitlistat_som_blivit_dolt():
    nu = _baslinje()
    nu["miljoer"]["main"]["tjanster"]["api"]["varden"] = {"LLM_PROVIDER": "anthropic"}
    assert rb.jamfor(_baslinje(), nu) == ["~ värde [main/api] LLM_PROVIDER: gemini -> anthropic"]
    nu["miljoer"]["main"]["tjanster"]["api"]["varden"] = {}
    assert rb.jamfor(_baslinje(), nu) == ["~ värde [main/api] LLM_PROVIDER: gemini -> (satt)"]


def test_andrad_installning_en_rad_per_nyckel():
    nu = _baslinje()
    inst = nu["miljoer"]["main"]["tjanster"]["api"]["installningar"]
    inst["halsokontroll"]["sokvag"] = "/health"
    inst["deploy_trigger"] = [{"gren": "development"}]
    inst["sleep"] = True
    assert rb.jamfor(_baslinje(), nu) == [
        '~ inställning [main/api] deploy_trigger: [{"gren": "main"}] -> [{"gren": "development"}]',
        '~ inställning [main/api] halsokontroll.sokvag: "/health/live" -> "/health"',
        "~ inställning [main/api] sleep: null -> true",
    ]


def test_till_json_ar_deterministisk():
    a = rb.till_json(_baslinje())
    b = rb.till_json(json.loads(a))
    assert a == b and a.endswith("\n") and "\r" not in a


def test_gql_vagrar_mutation():
    with pytest.raises(ValueError):
        rb.gql("mutation { variableUpsert(input: {}) }", {})
