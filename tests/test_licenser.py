"""scripts/licenser.py: SPDX-tolkningen, vitlistan och lockfilsläsningen.

Inget nätverk och ingen installation: lockfilen är syntetisk och metadata
byggs som ett email.message.Message, samma form som importlib.metadata ger.
"""

from __future__ import annotations

import email.message
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import licenser as L  # noqa: E402


@pytest.mark.parametrize(
    "uttryck, klass",
    [
        ("MIT", "tillatande"),
        ("Apache-2.0", "tillatande"),
        ("(MIT OR Apache-2.0)", "tillatande"),
        ("MIT OR GPL-3.0", "tillatande"),
        ("GPL-3.0-only OR MIT", "tillatande"),
        ("MIT AND GPL-3.0", "copyleft"),
        ("Apache-2.0 AND LGPL-3.0-or-later AND MIT", "copyleft"),
        ("LGPL-3.0-or-later", "copyleft"),
        ("AGPL-3.0", "copyleft"),
        ("MPL-2.0", "copyleft"),
        ("CC-BY-SA-4.0", "copyleft"),
        ("SSPL-1.0", "copyleft"),
        ("GPL-2.0 WITH Classpath-exception-2.0", "copyleft"),
        ("(AFL-2.1 OR BSD-3-Clause)", "tillatande"),
        ("MIT AND (GPL-2.0 OR BSD-2-Clause)", "tillatande"),
        ("(MIT AND GPL-2.0) OR ISC", "tillatande"),
        ("Hittepå-1.0", "okand"),
        ("Hittepå-1.0 OR MIT", "tillatande"),
        ("Hittepå-1.0 AND MIT", "okand"),
        ("GPL-3.0 OR Hittepå-1.0", "okand"),
        ("Standard 'no charge' license: https://gsap.com/standard-license.", "okand"),
        ("", "okand"),
        (None, "okand"),
        ("MIT AND", "okand"),
        ("(MIT", "okand"),
    ],
)
def test_tolka(uttryck, klass):
    assert L.tolka(uttryck) == klass


def test_normalisera_fritext():
    assert L.normalisera("MIT License") == "MIT"
    assert L.normalisera("Apache 2.0") == "Apache-2.0"
    assert L.normalisera(None) == L.OKAND
    assert L.normalisera("UNKNOWN") == L.OKAND
    lang = "BSD 3-Clause License\n\nCopyright (c) 2020, någon\n" + "x" * 500
    assert L.normalisera(lang) == "BSD-3-Clause"


def _meta(**falt) -> email.message.Message:
    m = email.message.Message()
    for nyckel, varde in falt.items():
        for v in varde if isinstance(varde, list) else [varde]:
            m[nyckel.replace("_", "-")] = v
    return m


def test_pip_licens_ordning():
    # License-Expression går före allt annat.
    assert L.pip_licens(_meta(License_Expression="MIT", License="GPL")) == (
        "MIT",
        "License-Expression",
    )
    # Flera licensklassificerare blir ett OR-uttryck; den nakna "OSI Approved" räknas inte.
    lic, kalla = L.pip_licens(
        _meta(
            Classifier=[
                "License :: OSI Approved",
                "License :: OSI Approved :: MIT License",
                "License :: OSI Approved :: Apache Software License",
                "Programming Language :: Python",
            ]
        )
    )
    assert (lic, kalla) == ("Apache-2.0 OR MIT", "klassificerare")
    assert L.tolka(lic) == "tillatande"
    lic, _ = L.pip_licens(
        _meta(Classifier="License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)")
    )
    assert L.tolka(lic) == "copyleft"
    assert L.pip_licens(_meta()) == (L.OKAND, "License-fält")


def test_syntetisk_lockfil(tmp_path):
    lock = {
        "name": "x",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "x", "version": "1.0.0"},
            "node_modules/a": {"version": "1.0.0", "license": "MIT"},
            "node_modules/b": {"version": "2.0.0", "license": "ISC", "dev": True},
            "node_modules/c": {"version": "3.0.0"},
            "node_modules/d": {"version": "1.0.0", "license": "MIT", "devOptional": True},
            "node_modules/@s/e": {"version": "0.1.0", "license": "LGPL-3.0-or-later", "optional": True},
            # Samma paket på två ställen i trädet: ett per (namn, version), prod vinner.
            "node_modules/b/node_modules/a": {"version": "1.0.0", "license": "MIT", "dev": True},
            "node_modules/f/node_modules/b": {"version": "2.0.0", "license": "ISC"},
            "node_modules/lank": {"resolved": "../annan", "link": True},
            "node_modules/g": {"version": "1.0.0", "license": {"type": "BSD", "url": "x"}},
        },
    }
    fil = tmp_path / "package-lock.json"
    fil.write_text(json.dumps(lock), encoding="utf-8")
    paket = {p.namn: p for p in L.las_lockfil(fil, "web")}
    assert set(paket) == {"a", "b", "c", "d", "@s/e", "g"}
    assert paket["a"].prod and paket["a"].licens == "MIT"
    assert paket["b"].prod  # nås också från ett prod-paket
    assert not paket["d"].prod
    assert paket["c"].licens == L.OKAND and paket["c"].klass == "okand"
    assert paket["@s/e"].prod and paket["@s/e"].klass == "copyleft"
    assert paket["g"].licens == "BSD" and paket["g"].klass == "tillatande"


def test_lockfil_v1_vagras(tmp_path):
    fil = tmp_path / "package-lock.json"
    fil.write_text(json.dumps({"lockfileVersion": 1, "dependencies": {}}), encoding="utf-8")
    with pytest.raises(SystemExit):
        L.las_lockfil(fil, "web")


@pytest.mark.parametrize(
    "version, spec, ok",
    [
        ("1.3.4", "*", True),
        ("1.3.4", "1.3.4", True),
        ("1.3.5", "1.3.4", False),
        ("1.3.4", ">=1,<2", True),
        ("2.0.0", ">=1,<2", False),
        ("0.35.5", ">=0.35,<1", True),
        ("0.34.9", ">=0.35,<1", False),
        ("2026.6.17", ">=2024", True),
    ],
)
def test_version_matchar(version, spec, ok):
    assert L.version_matchar(version, spec) is ok


def _paket(namn="lib", version="1.0.0", licens="LGPL-3.0", eko="npm"):
    return L.Paket(eko, "web", namn, version, licens, "lockfil", True)


def test_vitlistan(tmp_path, capsys):
    fil = tmp_path / "vit.json"
    fil.write_text(
        json.dumps(
            {
                "undantag": [
                    {
                        "ekosystem": "npm",
                        "paket": "lib",
                        "version": ">=1,<2",
                        "licens": "LGPL-3.0",
                        "motivering": "obeslutad, kräver Antons godkännande",
                        "godkant_av": "",
                    },
                    {
                        "ekosystem": "npm",
                        "paket": "gammal",
                        "version": "*",
                        "licens": "GPL-2.0",
                        "motivering": "bedömd",
                        "godkant_av": "Anton",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    vit = L.las_vitlista(fil)
    post = L.undantag_for(_paket(), vit)
    assert post is not None and L.ar_obeslutad(post)
    # Annan version, annan licens eller annat ekosystem: undantaget gäller inte.
    assert L.undantag_for(_paket(version="2.0.0"), vit) is None
    assert L.undantag_for(_paket(licens="GPL-3.0"), vit) is None
    assert L.undantag_for(_paket(eko="pip"), vit) is None

    # Grinden: undantaget (även obeslutat) släpper igenom, tillåtande passerar,
    # copyleft och okänt utan undantag fäller.
    assert L.kontrollera([_paket(), _paket("ok", licens="MIT")], vit, []) == 0
    assert L.kontrollera([_paket(licens="GPL-3.0")], vit, []) == 1
    assert L.kontrollera([_paket("x", licens=L.OKAND)], vit, []) == 1
    # En ofullständig miljö fäller.
    assert L.kontrollera([], vit, ["fastapi"]) == 1
    ut = capsys.readouterr().out
    assert "gammal" in ut and "kan strykas" in ut


def test_vitlista_utan_motivering_vagras(tmp_path):
    fil = tmp_path / "vit.json"
    fil.write_text(
        json.dumps(
            {"undantag": [{"ekosystem": "npm", "paket": "a", "version": "*", "licens": "GPL-3.0"}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        L.las_vitlista(fil)


def test_requirements_test_delen_ar_dev(tmp_path):
    fil = tmp_path / "requirements.txt"
    fil.write_text(
        "fastapi>=0.115\nuvicorn[standard]>=0.30  # kommentar\n"
        'tzdata>=2024.1; sys_platform == "nosuchplatform"\n'
        "# test\npytest>=8.0\n",
        encoding="utf-8",
    )
    krav = L.lasa_krav(fil, allt_dev=False)
    assert krav == [("fastapi", set(), True), ("uvicorn", {"standard"}, True), ("pytest", set(), False)]
