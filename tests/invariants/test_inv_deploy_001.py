"""INV-DEPLOY-001 — skill-registret finns i den byggda containern.

Buggen som motiverar testet (2026-08-14): Render-blueprinten satte
`rootDir: snajp-support`, alltså var Dockers byggkontext snajp-support/.
agent-core/ ligger i repo-roten, UTANFÖR kontexten, och kunde därför inte
COPY:as ens om någon försökte. I containern blev
`registry.AGENT_CORE_ROOT` (parents[3]) = `/agent-core`, som inte finns.

Det lömska var inte kraschen utan TIMINGEN. Agentimporterna är uppskjutna in
i request-handlers (api/leads.py:87,158,182, api/chat.py:52), så containern
startade GRÖNT, /health/live svarade OK, och felet kom först på det första
riktiga agentanropet som UnknownSkillError. Dessutom maskerat av att
simuleringsläget (is_simulation()) kortsluter före playbook-importen.
Nettoeffekten: felet utlöstes av att man satte nyckeln för att gå live.

Anpassad 2026-11-18: Render är avvecklat och blueprinten borttagen ur repot
(docs/BESLUT.md). Skyddet är detsamma, men driftens byggkontext står nu i
scripts/railway_provision.py, som är den fil som faktiskt styr Railway. Att
varje miljö har en utskriven gren vaktas av INV-DEPLOY-002 och upprepas inte
här.

Det här testet är den STATISKA halvan (snabb, körs i varje pytest-svep). Den
SKARPA halvan är docker-smoke-jobbet i .github/workflows/verify.yml, som
faktiskt bygger imagen och importerar en playbook i den. Behåll båda: det här
testet fångar en felaktig byggkontext på sekunder, men bara ett riktigt bygge
bevisar att filerna kom med.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "snajp-support" / "Dockerfile"
PROVISION = ROOT / "scripts" / "railway_provision.py"
# BuildKit läser `<Dockerfile>.dockerignore` FÖRE repo-rotens. Allowlisten
# flyttade dit när web-tjänsten tillkom: skriven för api gällde den alla, och
# filtrerade bort hela Next-appen ur web-bygget. Se INV-DEPLOY-002.
DOCKERIGNORE = ROOT / "snajp-support" / "Dockerfile.dockerignore"


def _api_instansens_byggfalt() -> str:
    """Argumenten till det `instance_update`-anrop som bär api:s Dockerfile.

    Kontrollen ska gälla just api-tjänsten, den som bygger snajp-support/Dockerfile.
    En räkning av förekomster i hela filen hade varit grön även om api tappat
    sin byggkontext och web råkat ha kvar sin."""
    text = PROVISION.read_text(encoding="utf-8")
    for match in re.finditer(r"instance_update\((.*?)\)\n", text, re.DOTALL):
        if "snajp-support/Dockerfile" in match.group(1):
            return match.group(1)
    raise AssertionError(
        "Hittar inget instance_update-anrop med dockerfilePath snajp-support/Dockerfile "
        "i scripts/railway_provision.py. Då står api:s byggkontext inte i kod, och "
        "testet mäter ingenting."
    )


def test_api_bygger_fran_repo_roten():
    """agent-core/ ligger utanför snajp-support/. Är byggkontexten undermappen
    snarare än repo-roten kan den inte COPY:as: inte "blir svår att", KAN INTE."""
    falt = _api_instansens_byggfalt()
    assert 'rootDirectory="/"' in falt, (
        "api-tjänstens rootDirectory måste vara '/' (repo-roten). agent-core/ ligger "
        "utanför snajp-support/ och Docker kan inte COPY:a utanför byggkontexten: "
        "containern skulle starta grönt och falla först på det första agentanropet."
    )
    assert 'dockerfilePath="snajp-support/Dockerfile"' in falt, (
        "api-tjänstens dockerfilePath måste peka på snajp-support/Dockerfile "
        "relativt repo-roten."
    )


def test_dockerfile_copies_agent_core():
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(r"^\s*COPY\s+agent-core\s+", text, re.MULTILINE), (
        "Dockerfile saknar `COPY agent-core ...`. Utan den finns inga skills "
        "i imagen och varje parse_skill_name() kastar UnknownSkillError vid "
        "första agentanropet."
    )


def test_dockerfile_preserves_the_repo_directory_depth():
    """parents[N] i koden räknar katalognivåer. Plattar imagen ut layouten
    går registry (parents[3]), context_pack (parents[2]) och configs env_file
    (parent.parent) sönder tyst — de pekar bara på fel ställe, de felar inte."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(r"^\s*COPY\s+snajp-support/app\s+\./snajp-support/app", text, re.MULTILINE), (
        "app/ måste kopieras till ./snajp-support/app så att djupet under /srv "
        "speglar repot. Kopieras den till ./app hamnar agent-core en nivå fel."
    )
    assert re.search(r"^\s*COPY\s+agent-core\s+\./agent-core", text, re.MULTILINE), (
        "agent-core/ måste ligga som syskon till snajp-support/ under /srv."
    )


def test_dockerignore_allowlists_agent_core():
    """Byggkontexten är repo-roten, som innehåller node_modules/, .next/,
    .git/ och .shots/. Utan ignorefil skickas allt till daemonen. Och
    listan måste vara en ALLOWLIST — en denylist ruttnar tyst när någon
    lägger till en ny stor katalog.

    Filen ligger bredvid Dockerfilen, inte i repo-roten: BuildKit läser
    `<Dockerfile>.dockerignore` först, och en allowlist i roten gällde ALLA
    tjänster — den raderade Next-appen ur web-tjänstens byggkontext."""
    assert DOCKERIGNORE.is_file(), (
        "snajp-support/Dockerfile.dockerignore saknas. Utan den gäller repo-rotens "
        "denylist för api-bygget, och byggkontexten sväller till hela repot."
    )
    lines = [
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "**" in lines, (
        "Dockerfile.dockerignore måste börja med `**` (allowlist-idiomet). En "
        "denylist släpper igenom nästa stora katalog någon lägger i repo-roten."
    )
    for required in ("!agent-core", "!snajp-support/app", "!snajp-support/requirements.txt"):
        assert required in lines, (
            f"snajp-support/Dockerfile.dockerignore saknar {required!r} — bygget skulle fela."
        )


def test_driften_satter_aldrig_skill_source():
    """DB-spegeln (INV-SKILL-007) är en granskningspost, inte en
    uppdateringskanal. Kan produktionen läsa skill-text som containern inte
    har på disk är git bara källa till sanning i intentionen.

    Det som skriver driftens variabler är skripten i scripts/ (provisionering,
    nyckelpush, synk) och arbetsflödena i .github/workflows/. Ingen av dem får
    nämna SKILL_SOURCE."""
    kallor = sorted((ROOT / "scripts").glob("*.py")) + sorted(
        (ROOT / ".github" / "workflows").glob("*.yml")
    )
    assert PROVISION in kallor, "scripts/railway_provision.py saknas — testet mäter ingenting."
    traffar = [
        p.relative_to(ROOT).as_posix()
        for p in kallor
        if "SKILL_SOURCE" in p.read_text(encoding="utf-8")
    ]
    assert not traffar, (
        f"{traffar} nämner SKILL_SOURCE. Produktionen ska läsa skills från "
        "filsystemet — DB-spegeln är opt-in och lokal."
    )
