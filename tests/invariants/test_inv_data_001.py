"""INV-DATA-001 — dataspegeln går bara main → development, aldrig tillbaka.

Bakgrunden är en uttrycklig risk, inte en befarad. `railway_seed_dev.py`
truncar och skriver om en hel databas. Pekas dess mål av misstag mot main
raderas produktionens data och ersätts med dev:s testkörningar. Kunddata som
skapats i dev — ärenden, konton, prospekt — får aldrig nå main.

Skyddet är tre lager (hårdkodat mål, mirror_meta-markör, den här invarianten).
Den statiska kontrollen finns för att de två runtime-spärrarna sitter i kod som
kan redigeras: om någon lägger till en `--target`-flagga eller pekar om
TARGET_ENV fångas det HÄR, vid commit, i stället för i drift.

Formen är statisk med flit — samma som INV-DEPLOY-002. Ett test som körde
speglingen hade krävt två databaser och bevisat att lyckad kopiering fungerar,
vilket säger ingenting om spärren.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "scripts" / "railway_seed_dev.py"
SUPABASE_SEED = ROOT / "scripts" / "supabase_seed_dev.py"
SCRIPTS = ROOT / "scripts"

#: Speglingsskript som ÄR granskade och bär alla spärrar. Varje fil här
#: kontrolleras av test_vaktad_spegel_bar_alla_sparrar nedan — listan är
#: alltså inte ett undantag utan en skärpning.
VAKTADE_SPEGLAR = (SEED, SUPABASE_SEED)

#: Trippelciterad rå sträng: mönstret innehåller både ' och ", och varje
#: annan citering kräver escaping som är lätt att få fel.
TARGET_FLAGGA = re.compile(r"""add_argument\(\s*["']--target""")


@pytest.fixture(scope="module")
def seed_source() -> str:
    assert SEED.exists(), "scripts/railway_seed_dev.py saknas — spegeln har ingen spärr."
    return SEED.read_text(encoding="utf-8")


def test_malet_ar_hardkodat(seed_source: str):
    """Målmiljön är en konstant, inte ett argument."""
    assert re.search(r'^TARGET_ENV\s*=\s*"development"', seed_source, re.MULTILINE), (
        "TARGET_ENV måste vara hårdkodat till 'development'. Ett värde ur argv "
        "eller miljö kan pekas mot main."
    )


def test_ingen_target_flagga(seed_source: str):
    """En --target-flagga skulle göra riktningen valbar — precis det som inte får gå."""
    assert not re.search(r'add_argument\(\s*["\']--target', seed_source), (
        "railway_seed_dev.py får inte ha en --target-flagga. Målet är låst till "
        "development; en flagga gör riktningen valbar."
    )


def test_main_ar_aldrig_mal(seed_source: str):
    """Ingen kodväg får skicka SOURCE_ENV (main) som mål till dsn()."""
    # dsn(..., "main") eller dsn(..., SOURCE_ENV) i en skrivkontext skulle vända
    # riktningen. Målanslutningen (dst) ska ENDAST byggas ur TARGET_ENV.
    assert re.search(r'dst\s*=\s*psycopg2\.connect\(dsn\(env,\s*TARGET_ENV\)', seed_source), (
        "Målanslutningen dst måste byggas ur TARGET_ENV. Byggs den ur något "
        "annat kan speglingen skriva till main."
    )
    # Källan får vara main, men bara som KÄLLA.
    assert re.search(r'src\s*=\s*psycopg2\.connect\(dsn\(env,\s*SOURCE_ENV\)', seed_source)


def test_markorspärrarna_finns(seed_source: str):
    """Runtime-spärrarna får inte tas bort utan att testet märker det."""
    for guard in ("assert_source_is_main", "assert_target_is_dev", "mirror_meta"):
        assert guard in seed_source, f"Spärren {guard} saknas i railway_seed_dev.py."
    # Båda måste faktiskt ANROPAS, inte bara vara definierade.
    assert seed_source.count("assert_target_is_dev(") >= 2  # def + anrop
    assert seed_source.count("assert_source_is_main(") >= 2


def test_ingen_annan_scriptfil_bulkkopierar_mot_main():
    """En bulkkopiering (`copy ... from stdin`) mot main-DSN i någon ANNAN
    scriptfil vore en andra, ovaktad kanal in i produktionsdata."""
    vaktade = {p.name for p in VAKTADE_SPEGLAR}
    for path in SCRIPTS.glob("*.py"):
        if path.name in vaktade:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"copy_expert\(.*from stdin", text, re.IGNORECASE):
            # Om en sådan väg tillkommer måste den granskas medvetet — då
            # uppdateras den här listan uttryckligen.
            pytest.fail(
                f"{path.name} innehåller en bulk-COPY-import. Om det är avsiktligt "
                f"och säkert, undanta filen här med ett skrivet skäl."
            )


@pytest.mark.parametrize("path", VAKTADE_SPEGLAR, ids=lambda p: p.name)
def test_vaktad_spegel_bar_alla_sparrar(path):
    """Att stå i VAKTADE_SPEGLAR är inget undantag — det är ett krav.

    Catch-allen ovan hoppar över de här filerna, och utan det här testet vore
    listan därmed en väg att smita förbi kontrollen: lägg till filnamnet, och
    ingen granskar spärrarna. Här kontrolleras de i stället hårdare.
    """
    assert path.exists(), f"{path.name} saknas — spegeln har ingen spärr."
    source = path.read_text(encoding="utf-8")

    # Målet får aldrig komma ur argv.
    assert not TARGET_FLAGGA.search(source), (
        f"{path.name} får inte ha en --target-flagga. Målet ska vara hårdkodat."
    )

    # Markörspärrarna måste finnas OCH anropas, inte bara vara definierade.
    for guard in ("mirror_meta", "assert_target_is_dev"):
        assert guard in source, f"Spärren {guard} saknas i {path.name}."
    assert source.count("assert_target_is_dev(") >= 2, (
        f"assert_target_is_dev definieras men anropas inte i {path.name}."
    )

    # Lässidans spärr heter olika i de två skripten (main vs produktion), men
    # NÅGON källkontroll måste finnas — annars går det att spegla en spegel.
    assert re.search(r"def assert_source_is_\w+", source), (
        f"{path.name} saknar en källkontroll. Utan den kan en spegel speglas."
    )
