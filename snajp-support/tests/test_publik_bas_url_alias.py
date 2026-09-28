"""PUBLIC_BASE_URL och PUBLIK_BAS_URL är samma inställning.

Granskningsfynd 2026-09-20: Railway, DEPLOY.md och handoffs säger
PUBLIC_BASE_URL, men pydantic-fältet `publik_bas_url` läste bara
PUBLIK_BAS_URL. Den satta variabeln lästes alltså aldrig: utskicksfoten
kunde inte byggas och send_guard hade blockerat varje utskick med ett
felmeddelande som pekade på bolagsuppgifterna i stället för på URL:en.
Aliaset i app/config.py gör båda namnen giltiga; det här testet fäller den
som tar bort ett av dem utan att läsa kommentaren där.
"""

from __future__ import annotations

import pytest

from app.config import Settings


@pytest.mark.parametrize("namn", ["PUBLIC_BASE_URL", "PUBLIK_BAS_URL"])
def test_bada_namnen_lases(namn, monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("PUBLIK_BAS_URL", raising=False)
    monkeypatch.setenv(namn, "https://exempel.se")
    assert Settings().publik_bas_url == "https://exempel.se"
