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
    """En namngiven gren, inte 'repots default'."""
    match = re.search(r'^BRANCH\s*=\s*"([^"]+)"', source, re.MULTILINE)
    assert match, "BRANCH saknas i railway_provision.py — grenen blir då repots default, tyst."
    assert match.group(1).strip(), "BRANCH är tom."


def test_serviceconnect_satter_grenen(source: str):
    """Det räcker inte att BRANCH finns — den måste faktiskt skickas till Railway.

    Konstanten fanns redan när felet uppstod. Den användes bara aldrig.
    """
    assert "serviceConnect" in source, "railway_provision.py anropar aldrig serviceConnect."
    connect = source[source.index("serviceConnect") : source.index("serviceConnect") + 400]
    assert '"branch": BRANCH' in connect, (
        "serviceConnect anropas utan branch: BRANCH. Då väljer Railway repots "
        "default-gren, och tjänsten bygger tyst fel kod."
    )


def test_grenen_satts_aven_for_befintlig_tjanst(source: str):
    """Fällan var att tjänsten redan fanns.

    Ett `if name in services: return` hade hoppat över grenvalet för precis de
    tjänster som redan drivit fel — alltså i det enda läge där kontrollen behövs.
    """
    assert re.search(r"if apply and source\.get\(\"repo\"\)", source), (
        "Grenen sätts inte om för en tjänst som redan finns. Den tjänst som "
        "redan pekar fel är den som aldrig blir rättad."
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
