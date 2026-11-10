"""Demochattens IP-tak läser rätt adress (Fas 0-fyndet H10, 2026-11-09).

Taket per IP är demons kostnadstak. Det lästes ur FÖRSTA värdet i
X-Forwarded-For, och det värdet skriver besökaren själv: den som skickade ett
nytt påhittat värde per anrop hade inget tak alls. Kantproxyn lägger den
adress den själv såg SIST i listan, och det är det enda värdet vi litar på.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.api.demo import _client_ip


def _begaran(huvud: dict[str, str], klient: str | None = "10.0.0.7"):
    return SimpleNamespace(
        headers=huvud,
        client=SimpleNamespace(host=klient) if klient else None,
    )


def test_pahittat_forsta_varde_styr_inte_taket():
    assert _client_ip(_begaran({"x-forwarded-for": "1.2.3.4, 203.0.113.9"})) == "203.0.113.9"


def test_ensamt_varde_ar_kantproxyns():
    assert _client_ip(_begaran({"x-forwarded-for": "203.0.113.9"})) == "203.0.113.9"


def test_tomma_led_och_blanksteg_tals():
    assert _client_ip(_begaran({"x-forwarded-for": " 1.2.3.4 ,, 203.0.113.9 , "})) == "203.0.113.9"


def test_utan_huvud_galler_anslutningens_adress():
    assert _client_ip(_begaran({})) == "10.0.0.7"
    assert _client_ip(_begaran({}, klient=None)) == "unknown"
