"""INV-TENANT-001 — kundregistret och nyckelnamnen hänger ihop.

Två kopplingar som bara syns i drift när de går sönder, och som båda är rena
namnkonventioner utan kompilatorstöd:

1. `supportKeyEnv` i `lib/tenants/<slug>.ts` måste vara
   `SNAJP_KEY_<SLUG>`. Stämmer den inte läser koden en env-variabel som ingen
   satt, och `requireSnajpTenant()` svarar 503 — långt från orsaken.

2. Backendens `_slugify()` och Next-sidans slug måste ge samma resultat. Gör de
   inte det skapar `POST /api/keys` en tenant med EN slug medan configfilen och
   workspace-raden pekar på en annan, och felet syns som en 409 först när
   någon försöker logga in.

Båda kontrolleras statiskt: de kostar millisekunder och fångar felet i den
commit som införde det, i stället för i produktionsloggen en vecka senare.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TENANTS_DIR = ROOT / "lib" / "tenants"
INDEX = TENANTS_DIR / "index.ts"

#: Filer i lib/tenants/ som inte är kunder.
NOT_TENANTS = {"index.ts", "types.ts", "server.ts"}


def _tenant_files() -> list[Path]:
    return sorted(p for p in TENANTS_DIR.glob("*.ts") if p.name not in NOT_TENANTS)


def _field(source: str, name: str) -> str | None:
    match = re.search(rf'{name}:\s*"([^"]+)"', source)
    return match.group(1) if match else None


def _slugify(name: str) -> str:
    """Spegel av backendens _slugify i snajp-support/app/api/keys.py."""
    lowered = name.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or "tenant"


def test_det_finns_kunder_att_kontrollera():
    """Slutar globben hitta filer blir allt nedan grönt av fel skäl."""
    assert _tenant_files(), f"Inga kundfiler i {TENANTS_DIR} — testet mäter ingenting."


@pytest.mark.parametrize("path", _tenant_files(), ids=lambda p: p.stem)
def test_supportkeyenv_foljer_konventionen(path: Path):
    source = path.read_text(encoding="utf-8")
    slug = _field(source, "slug")
    key_env = _field(source, "supportKeyEnv")

    assert slug, f"{path.name} saknar slug."
    assert key_env, f"{path.name} saknar supportKeyEnv."

    forvantat = f"SNAJP_KEY_{slug.upper().replace('-', '_')}"
    assert key_env == forvantat, (
        f"{path.name}: supportKeyEnv={key_env!r}, förväntat {forvantat!r}. "
        "Koden slår upp process.env[supportKeyEnv] — stämmer inte namnet läser "
        "den en variabel ingen satt, och kunden får 503 utan att det syns var."
    )


@pytest.mark.parametrize("path", _tenant_files(), ids=lambda p: p.stem)
def test_filnamnet_ar_sluggen(path: Path):
    """Onboarding-skriptet genererar <slug>.ts och importerar på filnamnet."""
    slug = _field(path.read_text(encoding="utf-8"), "slug")
    assert slug == path.stem, (
        f"{path.name} deklarerar slug={slug!r}. Filnamn och slug måste vara "
        "samma, annars hittar varken importen eller onboarding-skriptet rätt."
    )


@pytest.mark.parametrize("path", _tenant_files(), ids=lambda p: p.stem)
def test_sluggen_overlever_backendens_slugify(path: Path):
    """Backenden kör _slugify på det den får. En slug som inte är en fixpunkt
    ändras på vägen in, och då pekar configfil och tenant åt olika håll."""
    slug = _field(path.read_text(encoding="utf-8"), "slug")
    assert _slugify(slug) == slug, (
        f"{slug!r} blir {_slugify(slug)!r} genom backendens _slugify. "
        "Tenanten hade fått ett annat namn än configfilen pekar på."
    )


@pytest.mark.parametrize("path", _tenant_files(), ids=lambda p: p.stem)
def test_kunden_ar_registrerad_i_index(path: Path):
    """En configfil som inte står i registret är osynlig för getTenant() —
    filen finns, allt ser rätt ut, och kunden får 409."""
    index = INDEX.read_text(encoding="utf-8")
    assert f'from "./{path.stem}"' in index, (
        f"{path.name} importeras inte i index.ts."
    )
    variabel = re.sub(r"[^a-z0-9]", "", path.stem)
    registret = re.search(r"const tenants: Record<string, Tenant> = \{(.*?)\}", index, re.DOTALL)
    assert registret and variabel in registret.group(1), (
        f"{variabel!r} saknas i tenants-registret i index.ts."
    )
