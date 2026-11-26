"""INV-HJALP-001 — Hjälprutans vägar går under hjälpens nyckel, med identiteten ur sessionen.

Hjälprutan (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 2 och 5) är kundens väg in
till Snajps EGEN supportagent och till plattformsärendena. Tenantgränsen är
hela poängen: hjälpens nyckel får aldrig nå en kunds data, och kundens nyckel
får aldrig nå plattformsärendena. Tre sätt att bryta den, ett test för varje:

1. En väg som går genom ``proxyAsTenant`` (eller den anonyma
   ``proxyToBackend``/``apiKeyForTenant``) använder KUNDENS nyckel. Varje väg
   under app/api/snajp-support/hjalp ska i stället läsa ``SNAJP_KEY_SNAJP_HJALP``.
2. ``arbetsyta`` ger agenten den anropande kundens interna nyckeltal; under
   hjälpens nyckel hade det varit Snajps egna. Fältet sätts aldrig.
3. Identiteten (avsändaradressen, rapportören, arbetsytan, rollen) får inte
   komma ur klientens kropp. Vägarna grindar på sessionen och lämnar kroppen
   till ``lib/snajp/hjalp.ts``, som bygger identiteten på servern. Beteendet
   där är låst av ``lib/snajp/hjalp.test.ts``; det här testet låser att
   vägarna faktiskt går den vägen.

Statiskt med flit, som INV-SEC-010: det fäller en NY väg som någon lägger till
utan att ta ställning, i CI och utan nätverk.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HJALP_DIR = ROOT / "app" / "api" / "snajp-support" / "hjalp"
HJALP_LIB = ROOT / "lib" / "snajp" / "hjalp.ts"

#: Vägarna kontraktet kräver (planen del 2 och 5). En väg som försvinner ur
#: katalogen ska fälla testet, inte göra det tomt grönt.
VANTADE = {
    "route.ts",
    "jobb/[jobId]/route.ts",
    "samtal/route.ts",
    "arenden/route.ts",
    "arenden/[id]/svar/route.ts",
    "arenden/[id]/utslag/route.ts",
}

FORBJUDNA_NYCKELVAGAR = ("proxyAsTenant", "proxyToBackend", "apiKeyForTenant", "requireSnajpTenant")

#: Fält som bär identiteten. De får bara sättas i lib/snajp/hjalp.ts, ur sessionen.
IDENTITETSFALT = (
    "customer_email",
    "customer_name",
    "rapportor_user_id",
    "rapportor_namn",
    "kund_workspace_id",
    "kund_tenant_slug",
    "besok_av_admin",
)


def _vagar() -> list[Path]:
    return sorted(HJALP_DIR.rglob("route.ts"))


def _rel(p: Path) -> str:
    return p.relative_to(HJALP_DIR).as_posix()


def test_vagarna_finns():
    assert HJALP_LIB.exists(), "lib/snajp/hjalp.ts saknas."
    funna = {_rel(p) for p in _vagar()}
    saknas = VANTADE - funna
    assert not saknas, f"Hjälprutans vägar saknas: {sorted(saknas)}"


@pytest.mark.parametrize("vag", _vagar(), ids=_rel)
def test_vagen_gar_under_hjalpens_nyckel(vag: Path):
    kalla = vag.read_text(encoding="utf-8")
    for forbjuden in FORBJUDNA_NYCKELVAGAR:
        assert forbjuden not in kalla, (
            f"{_rel(vag)} använder {forbjuden}, alltså kundens (eller den anonyma) nyckel. "
            "Hjälprutan går under hjälpens egen nyckel: process.env.SNAJP_KEY_SNAJP_HJALP via tillHjalpen."
        )
    assert "process.env.SNAJP_KEY_SNAJP_HJALP" in kalla, f"{_rel(vag)} läser inte SNAJP_KEY_SNAJP_HJALP."
    assert "tillHjalpen(" in kalla, f"{_rel(vag)} skickar inte vidare genom tillHjalpen i lib/snajp/hjalp.ts."


@pytest.mark.parametrize("vag", _vagar(), ids=_rel)
def test_vagen_grindar_pa_sessionen_och_bygger_identiteten_pa_servern(vag: Path):
    kalla = vag.read_text(encoding="utf-8")
    assert "getWorkspaceContext()" in kalla, f"{_rel(vag)} grindar inte på sessionen (getWorkspaceContext)."
    grind = kalla.index("getWorkspaceContext()")
    vidare = kalla.index("tillHjalpen(")
    assert grind < vidare, f"{_rel(vag)}: sessionsgrinden måste stå före anropet till backenden."
    assert "hjalpIdentitet(" in kalla, f"{_rel(vag)} bygger inte identiteten med hjalpIdentitet."
    for falt in IDENTITETSFALT:
        assert falt not in kalla, (
            f"{_rel(vag)} nämner {falt}. Identiteten byggs i lib/snajp/hjalp.ts ur sessionen, "
            "aldrig i vägen och aldrig ur klientens kropp."
        )


@pytest.mark.parametrize("fil", [*_vagar(), HJALP_LIB], ids=lambda p: p.relative_to(ROOT).as_posix())
def test_arbetsyta_satts_aldrig(fil: Path):
    kalla = fil.read_text(encoding="utf-8")
    # Kommentarer får förklara varför fältet saknas; bara koden räknas.
    kod = re.sub(r"/\*.*?\*/", "", kalla, flags=re.DOTALL)
    kod = re.sub(r"(^|\s)//.*$", r"\1", kod, flags=re.MULTILINE)
    assert "arbetsyta" not in kod, (
        f"{fil.relative_to(ROOT).as_posix()} sätter eller läser `arbetsyta`. Under hjälpens nyckel "
        "hade agenten fått Snajps egna nyckeltal; fältet ska aldrig följa med."
    )


def test_avsandaren_byggs_ur_sessionens_anvandare():
    kalla = HJALP_LIB.read_text(encoding="utf-8")
    assert 'HJALP_DOMAN = "@kund.snajp.se"' in kalla
    assert "customer_email: hjalpAvsandare(id.userId)" in kalla
    assert "rapportor_user_id: id.userId" in kalla
    assert "userId: context.user.id" in kalla
    assert "is_test: false" in kalla


def test_arende_id_valideras_innan_det_hamnar_i_sokvagen():
    for vag in _vagar():
        if "[id]" in _rel(vag) or "[jobId]" in _rel(vag):
            kalla = vag.read_text(encoding="utf-8")
            assert "arUuid(" in kalla, f"{_rel(vag)} lägger ett id ur adressen i backendens sökväg utan att pröva det."
