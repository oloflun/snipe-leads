"""Render är avvecklat: ingen kod i repot får kunna nå, skriva till eller
återskapa den gamla stacken.

Borttaget 2026-11-18 (docs/BESLUT.md): `scripts/keys.py --push-render`, som
kunde skriva backend-hemligheter och DeepSeek som leverantör till båda
Render-tjänsterna och starta en deploy, `scripts/verify_render.py`, som den
lånade API-adressen och nyckeln ur, och blueprinten `snajp-support/render.yaml`,
vars egen kommentar sa att en blueprint som ligger kvar är en tjänst som kan
återuppstå. Samtidigt försvann keys.py:s skrivväg mot Vercel (`--push`,
`--pull`), som bara tjänade samma döda stack.

Testet letar i det som kan köras eller deploya: skripten och arbetsflödena.
Dokument och historik får fortsätta nämna Render.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEYS = ROOT / "scripts" / "keys.py"

#: Renders API och tjänstedomän. Ihopsatta så att filen inte själv innehåller
#: strängarna den letar efter.
_SPAR = ("api." + "render.com", "on" + "render.com", "RENDER_" + "API_KEY", "RENDER_" + "SERVICES")


def _korbara_filer() -> list[Path]:
    filer = [
        p for p in sorted((ROOT / "scripts").rglob("*"))
        if p.is_file() and p.suffix in (".py", ".mjs", ".js", ".ts", ".sh", ".ps1", ".cmd", ".vbs")
    ]
    filer += sorted((ROOT / ".github").rglob("*.yml"))
    filer += sorted((ROOT / ".github").rglob("*.yaml"))
    return filer


def test_blueprinten_finns_inte():
    for namn in ("render.yaml", "render.yml"):
        for plats in (ROOT, ROOT / "snajp-support"):
            assert not (plats / namn).exists(), (
                f"{(plats / namn).relative_to(ROOT).as_posix()} finns igen. En blueprint "
                "som ligger kvar är en tjänst som kan återuppstå; Render är avvecklat."
            )


def test_driftkontrollen_mot_render_finns_inte():
    assert not (ROOT / "scripts" / "verify_render.py").exists()


def test_keys_har_ingen_vag_till_render_eller_vercel():
    text = KEYS.read_text(encoding="utf-8")
    for spar in ("push-render", "push_render", "verify_render", *_SPAR):
        assert spar not in text, f"scripts/keys.py innehåller {spar!r} igen."
    for spar in ("vercel_env_set", '"--push"', '"--pull"', '"vercel"'):
        assert spar not in text, (
            f"scripts/keys.py innehåller {spar!r} igen. Vercel-projektet för appen "
            "är avvecklat; driftens nycklar går till Railway med --push-railway."
        )


def test_inget_skript_eller_arbetsflode_nar_render():
    filer = _korbara_filer()
    assert KEYS in filer, "scripts/keys.py hittades inte — testet mäter ingenting."
    traffar = [
        f"{p.relative_to(ROOT).as_posix()}: {spar}"
        for p in filer
        for spar in _SPAR
        if spar in p.read_text(encoding="utf-8", errors="replace")
    ]
    assert not traffar, f"Kod som når Render finns igen: {traffar}"
