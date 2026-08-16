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
SCRIPTS = ROOT / "scripts"


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
    for path in SCRIPTS.glob("*.py"):
        if path.name == "railway_seed_dev.py":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"copy_expert\(.*from stdin", text, re.IGNORECASE):
            # Om en sådan väg tillkommer måste den granskas medvetet — då
            # uppdateras den här listan uttryckligen.
            pytest.fail(
                f"{path.name} innehåller en bulk-COPY-import. Om det är avsiktligt "
                f"och säkert, undanta filen här med ett skrivet skäl."
            )
