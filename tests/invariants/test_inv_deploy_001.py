"""INV-DEPLOY-001 — skill-registret finns i den byggda containern.

Buggen som motiverar testet (2026-08-14): `render.yaml` satte
`rootDir: snajp-support`, alltså var Dockers byggkontext snajp-support/.
agent-core/ ligger i repo-roten, UTANFÖR kontexten, och kunde därför inte
COPY:as ens om någon försökte. I containern blev
`registry.AGENT_CORE_ROOT` (parents[3]) = `/agent-core`, som inte finns.

Det lömska var inte kraschen utan TIMINGEN. Agentimporterna är uppskjutna in
i request-handlers (api/leads.py:87,158,182, api/chat.py:52), så containern
startade GRÖNT, /health/live svarade OK, och felet kom först på det första
riktiga agentanropet som UnknownSkillError. Dessutom maskerat av att Render
saknade DEEPSEEK_API_KEY — is_simulation() kortsluter före playbook-importen.
Nettoeffekten: felet utlöstes av att man satte nyckeln för att gå live.

Det här testet är den STATISKA halvan (snabb, körs i varje pytest-svep). Den
SKARPA halvan är docker-smoke-jobbet i .github/workflows/verify.yml, som
faktiskt bygger imagen och importerar en playbook i den. Behåll båda: det här
testet fångar en felaktig rootDir på sekunder, men bara ett riktigt bygge
bevisar att filerna kom med.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "snajp-support" / "Dockerfile"
RENDER_YAML = ROOT / "snajp-support" / "render.yaml"
DOCKERIGNORE = ROOT / ".dockerignore"


def _render_services() -> list[dict[str, str]]:
    """En dict per tjänst i render.yaml.

    Var tidigare `_render_service()` som platt-mappade HELA filen med
    `setdefault`, alltså första förekomsten av varje nyckel. Det fungerade så
    länge blueprinten hade en enda tjänst. När preview-tjänsten lades till blev
    testet BLINT för den: en medvetet felaktig `rootDir: snajp-support` på
    tjänst två gav fortfarande 5/5 gröna. Verifierat genom att sabotera filen
    och köra sviten — inte resonerat fram.

    Det är samma bugg som testet finns för att fånga, en nivå upp: kontrollen
    såg ut att gälla allt och gällde en delmängd.

    Handrullad i stället för PyYAML: invariantsviten körs med enbart
    snajp-support/requirements.txt installerat, och ett beroende för det här
    vore fel avvägning. Filen är vår egen och formatet är stabilt.
    """
    services: list[dict[str, str]] = []
    for line in RENDER_YAML.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or ":" not in stripped:
            continue
        # "- type: web" inleder en ny tjänst. envVars-posterna börjar också med
        # "- ", men de har nyckeln "key", inte "type".
        starts_service = stripped.startswith("- ") and stripped[2:].startswith("type:")
        stripped = stripped.lstrip("- ").strip()
        key, _, value = stripped.partition(":")
        if starts_service:
            services.append({})
        if services:
            services[-1].setdefault(key.strip(), value.strip())
    return services


def test_there_are_services_to_check():
    """Slutar parsern hitta tjänster blir allt nedan grönt av fel skäl."""
    services = _render_services()
    assert services, "Inga tjänster hittades i render.yaml — testet mäter ingenting."
    assert all(s.get("name") for s in services), "En tjänst saknar name."


@pytest.mark.parametrize("service", _render_services(), ids=lambda s: s.get("name", "?"))
def test_build_context_is_the_repo_root(service):
    """agent-core/ ligger utanför snajp-support/. Är byggkontexten snarare än
    repo-roten kan den inte COPY:as — inte "blir svår att", KAN INTE.

    Parametriserad över VARJE tjänst. Preview-tjänsten bygger samma image och
    kan fela på exakt samma sätt."""
    assert service.get("rootDir") == ".", (
        f"{service.get('name')}: rootDir={service.get('rootDir')!r}, måste vara '.'. "
        "agent-core/ ligger utanför snajp-support/ och Docker kan inte COPY:a "
        "utanför byggkontexten — containern skulle starta grönt och falla "
        "först på det första agentanropet."
    )
    assert service.get("dockerfilePath") == "./snajp-support/Dockerfile", (
        f"{service.get('name')}: dockerfilePath måste peka på "
        f"snajp-support/Dockerfile relativt repo-roten, fick "
        f"{service.get('dockerfilePath')!r}."
    )


@pytest.mark.parametrize("service", _render_services(), ids=lambda s: s.get("name", "?"))
def test_every_service_pins_its_branch(service):
    """Grenvalet ska stå i git, inte bara i Renders dashboard.

    Två produktionsincidenter kom ur att dashboardfältet pekade fel utan att
    synas i någon diff — en gång mot `development` medan frontenden deployade
    från `main`. Ett fält som inte syns i en pull request går inte att granska."""
    assert service.get("branch") in ("main", "development"), (
        f"{service.get('name')}: branch={service.get('branch')!r}. Varje tjänst "
        "måste peka ut sin gren explicit, annars styrs den av ett osynligt "
        "dashboardfält."
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
    .git/ och .shots/. Utan .dockerignore skickas allt till daemonen. Och
    listan måste vara en ALLOWLIST — en denylist ruttnar tyst när någon
    lägger till en ny stor katalog."""
    assert DOCKERIGNORE.is_file(), ".dockerignore saknas i repo-roten."
    lines = [
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "**" in lines, (
        ".dockerignore måste börja med `**` (allowlist-idiomet). En denylist "
        "släpper igenom nästa stora katalog någon lägger i repo-roten."
    )
    for required in ("!agent-core", "!snajp-support/app", "!snajp-support/requirements.txt"):
        assert required in lines, f".dockerignore saknar {required!r} — bygget skulle fela."


def test_render_never_pins_skill_source_to_db():
    """DB-spegeln (INV-SKILL-007) är en granskningspost, inte en
    uppdateringskanal. Kan produktionen läsa skill-text som containern inte
    har på disk är git bara källa till sanning i intentionen."""
    text = RENDER_YAML.read_text(encoding="utf-8")
    assert "SKILL_SOURCE" not in text, (
        "render.yaml sätter SKILL_SOURCE. Produktionen ska läsa skills från "
        "filsystemet — DB-spegeln är opt-in och lokal."
    )
