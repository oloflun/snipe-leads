"""Avsiktlighetsgrinden för agent-core/skills/.

VAD DEN INTE ÄR: en säkerhetsmekanism. Vem som helst med skrivrättighet till
repot kan redigera en skill-fil direkt, och ingen nyckel i världen stoppar det.
Om du läser den här filen för att avgöra om skills är "skyddade" — det är de
inte, de är LÅSTA MOT MISSTAG.

VAD DEN ÄR: värdet finns bara i snajp-support/.env på en enda maskin, och
finns aldrig i Render, Vercel eller CI. Alltså kan varken en slarvig commit,
ett skript som "bara städar upp", eller en autonom agentkörning regenerera
manifestet eller publicera skills till databasen. Den som gör det måste sitta
vid rätt dator och mena det.

Den kompletterar INV-SKILL-005 (som gör en tyst ändring SYNLIG) med att göra
den ANSTRÄNGANDE, och INV-SKILL-006 (vendor-bump-trailern) med att göra den
DEKLARERAD.

    python scripts/keys.py --new-unlock-key      # generera (skriver aldrig värdet)
    python scripts/unlock_skills.py --rebuild-manifest
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

from .registry import AGENT_CORE_ROOT

UNLOCK_HASH_PATH = AGENT_CORE_ROOT / ".unlock-hash"


class SkillLockedError(RuntimeError):
    """Skills är låsta: nyckeln saknas eller matchar inte agent-core/.unlock-hash."""


def hash_key(key: str) -> str:
    """sha256 av nyckeln. Det är detta som committas — aldrig nyckeln själv."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def read_unlock_hash() -> str | None:
    """Den incheckade hashen, eller None om låset aldrig satts upp."""
    if not UNLOCK_HASH_PATH.is_file():
        return None
    value = UNLOCK_HASH_PATH.read_text(encoding="utf-8").strip()
    return value or None


def verify_unlock_key(key: str | None = None) -> None:
    """Kastar SkillLockedError om nyckeln saknas eller inte matchar.

    `key=None` läser get_settings().snajp_skill_unlock_key. Importen ligger
    inuti funktionen så att den här modulen kan användas av skript i repo-roten
    utan att dra in hela pydantic-settings-kedjan när nyckeln skickas explicit.
    """
    expected = read_unlock_hash()
    if expected is None:
        raise SkillLockedError(
            f"Låset är inte uppsatt: {UNLOCK_HASH_PATH} saknas eller är tom.\n"
            "Kör: python scripts/keys.py --new-unlock-key"
        )

    if key is None:
        from ..config import get_settings

        key = get_settings().snajp_skill_unlock_key

    if not key:
        raise SkillLockedError(
            "SNAJP_SKILL_UNLOCK_KEY är inte satt i snajp-support/.env.\n"
            "Skills ändras inte utan den. Justera output med en overlay i "
            "agent-core/overlays/ i stället — det är den sanktionerade "
            "finjusteringsytan (INV-SKILL-005).\n"
            "Har du tappat nyckeln: python scripts/keys.py --new-unlock-key"
        )

    if not hmac.compare_digest(hash_key(key), expected):
        raise SkillLockedError(
            "SNAJP_SKILL_UNLOCK_KEY matchar inte agent-core/.unlock-hash.\n"
            "Antingen är nyckeln fel, eller så roterades den på en annan maskin "
            "utan att .unlock-hash committades."
        )
