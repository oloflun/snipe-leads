"""INV-DEPLOY-002 — varje Railway-tjänst som byggs ur repot har en UTSKRIVEN
gren, och byggkontexten står i kod.

Bakgrunden är mätt, inte befarad. `serviceCreate` med bara `source: {repo}`
väljer tyst repots default-gren. Följden blev att `web` byggde `development` i
tre deployer i rad medan felsökningen letade i byggkontexten — felmeddelandet
(`"/package-lock.json": not found`) var sant, men det beskrev en ANNAN commit
än den som just pushats.

Det är samma klass av fel som render.yaml fick `branch:` för efter två
produktionsincidenter, och samma klass som Root Directory, som återgick till
`snajp-support` av sig självt och fällde ett Docker-bygge två gånger. Gemensamt:
ett fält som styr vad som körs, som inte syns i någon diff.

Formen är statisk med flit — testet läser provisioneringsskriptet, inte
Railways API. Ett test som frågar API:t hade krävt nätverk och en giltig token
i CI, och hade dessutom mätt tillståndet EFTER att någon ändrat i dashboarden
i stället för att kräva att ändringen står i kod.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROVISION = ROOT / "scripts" / "railway_provision.py"


@pytest.fixture(scope="module")
def source() -> str:
    assert PROVISION.exists(), f"{PROVISION} saknas — invarianten mäter ingenting."
    return PROVISION.read_text(encoding="utf-8")


def test_grenen_ar_utskriven(source: str):
    """En namngiven gren PER MILJÖ, inte 'repots default'.

    Uppgraderad från en enda BRANCH-konstant till ENVIRONMENTS-mappen när
    upplägget blev två miljöer: gren-per-miljö är själva mekanismen som gör
    main och development åtskiljbara, och den bärs av deployment-triggern.
    """
    match = re.search(r"ENVIRONMENTS\s*:\s*dict\[str,\s*str\]\s*=\s*\{([^}]+)\}", source)
    assert match, "ENVIRONMENTS-mappen saknas — grenen per miljö blir då odefinierad."
    body = match.group(1)
    assert '"railway-main"' in body and '"railway-development"' in body, (
        "ENVIRONMENTS måste binda main och development till sina grenar."
    )


def test_grenen_satts_via_deployment_trigger(source: str):
    """Grenen sätts på deployment-triggern, som är miljöspecifik.

    serviceConnect sätter tjänstens default-gren och gäller ALLA miljöer — fel
    verktyg när två miljöer ska följa olika grenar. deploymentTriggerCreate bär
    både branch och environmentId, vilket är det som gör dev och main
    åtskiljbara. Det var frånvaron av en miljöspecifik gren som lät web bygga
    fel gren i tre deployer i rad.
    """
    assert "deploymentTriggerCreate" in source, (
        "railway_provision.py skapar aldrig en deployment-trigger — grenen blir "
        "då tjänstens default och gäller alla miljöer."
    )
    assert re.search(r'"branch":\s*branch', source), (
        "deployment-triggern sätts utan branch. Då väljer Railway repots "
        "default-gren och tjänsten bygger tyst fel kod."
    )


def test_grenen_uppdateras_for_befintlig_trigger(source: str):
    """Fällan var att triggern redan fanns och pekade fel.

    ensure_trigger måste UPPDATERA en befintlig trigger vars gren avviker, inte
    bara skapa nya. En trigger som redan pekar mot fel gren är den som aldrig
    blir rättad annars.
    """
    assert "deploymentTriggerUpdate" in source, (
        "En befintlig trigger med fel gren rättas aldrig — den byggde fel kod "
        "och skulle fortsätta göra det."
    )


def test_byggkontexten_star_i_kod(source: str):
    """agent-core/ ligger utanför snajp-support/ och kan inte COPY:as om
    kontexten är undermappen. Fältet har fällt bygget tre gånger totalt."""
    assert 'dockerfilePath="snajp-support/Dockerfile"' in source
    assert source.count('rootDirectory="/"') >= 2, (
        "Minst api och web måste ha byggkontexten satt explicit i kod."
    )


def test_api_har_egen_dockerignore(source: str):
    """Rotens .dockerignore är en denylist; api:s allowlist bor bredvid sin
    Dockerfile.

    Allowlisten i repo-roten släppte in agent-core och snajp-support/app och
    inget annat. Den var skriven för api och gällde alla — web-tjänstens hela
    Next-app filtrerades bort innan bygget började. BuildKit läser
    `<Dockerfile>.dockerignore` före rotens, vilket gör att båda kan ha rätt.
    """
    api_ignore = ROOT / "snajp-support" / "Dockerfile.dockerignore"
    assert api_ignore.exists(), (
        "snajp-support/Dockerfile.dockerignore saknas — då gäller repo-rotens "
        "fil för api-bygget, och agent-core riskerar att inte följa med."
    )
    assert "!agent-core" in api_ignore.read_text(encoding="utf-8")

    root_ignore = ROOT / ".dockerignore"
    if root_ignore.exists():
        text = root_ignore.read_text(encoding="utf-8")
        assert not re.search(r"^\*\*$", text, re.MULTILINE), (
            "Repo-rotens .dockerignore är en allowlist igen. Den filtrerar då "
            "bort Next-appen ur web-tjänstens byggkontext."
        )
