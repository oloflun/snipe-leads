"""Säkerhetsbevakningens rena delar, utan nätverk.

scripts/sakerhetsbevakning.py hämtar CERT-SE:s RSS-flöde och GitHubs
advisories och skapar underlag för ärenden. Här provas det som avgör vilka
ärenden som skapas: RSS-tolkningen, filtreringen på sökord, paket och datum,
dedup-nyckeln mot befintliga ärenden och saneringen av text utifrån.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("sakerhetsbevakning", ROT / "scripts" / "sakerhetsbevakning.py")
sb = importlib.util.module_from_spec(_spec)
sys.modules["sakerhetsbevakning"] = sb  # dataclasses slår upp modulen här
_spec.loader.exec_module(sb)

SEDAN = datetime(2026, 11, 16, tzinfo=timezone.utc)

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>CERT-SE.</title>
<item>
  <title>Kritisk sårbarhet i PostgreSQL</title>
  <description>&lt;p&gt;PostgreSQL Global Development Group har publicerat uppdateringar. [1]&lt;/p&gt;</description>
  <pubDate>Wed, 18 Nov 2026 14:20:00 +0100</pubDate>
  <link>https://www.cert.se/2026/11/kritisk-sarbarhet-i-postgresql.html</link>
</item>
<item>
  <title>Sårbarheter i Next.js och React Server Components</title>
  <description>&lt;p&gt;Vercel har publicerat rättningar.&lt;/p&gt;</description>
  <pubDate>Tue, 17 Nov 2026 10:00:00 +0100</pubDate>
  <link>http://cert.se/2026/11/nextjs.html?utm=x#topp</link>
</item>
<item>
  <title>Kritisk sårbarhet i Oracle Java</title>
  <description>&lt;p&gt;Oracle har publicerat säkerhetsuppdateringar.&lt;/p&gt;</description>
  <pubDate>Wed, 18 Nov 2026 09:00:00 +0100</pubDate>
  <link>https://www.cert.se/2026/11/java.html</link>
</item>
<item>
  <title>Gammal sårbarhet i Redis</title>
  <description>&lt;p&gt;Redis har rättat.&lt;/p&gt;</description>
  <pubDate>Mon, 02 Nov 2026 10:00:00 +0100</pubDate>
  <link>https://www.cert.se/2026/11/redis.html</link>
</item>
</channel></rss>"""

SOKORD = ["Next.js", "React", "PostgreSQL", "Postgres", "Redis", "Node.js"]

PAKET = [
    {"ekosystem": "npm", "namn": "next"},
    {"ekosystem": "npm", "namn": "@auth/core"},
    {"ekosystem": "pip", "namn": "fastapi"},
    {"ekosystem": "pip", "namn": "python-dotenv"},
]


def advisory(ghsa, paket, publicerad="2026-11-17T16:13:26Z", **extra):
    return {
        "ghsa_id": ghsa,
        "cve_id": "CVE-2026-1",
        "html_url": f"https://github.com/advisories/{ghsa}",
        "summary": "Next.js: cache leak",
        "severity": "medium",
        "type": "reviewed",
        "published_at": publicerad,
        "withdrawn_at": None,
        "vulnerabilities": [
            {
                "package": {"ecosystem": eko, "name": namn},
                "vulnerable_version_range": intervall,
                "first_patched_version": "16.4.5",
            }
            for eko, namn, intervall in paket
        ],
        **extra,
    }


# --- RSS ------------------------------------------------------------------


def test_rss_tolkas_med_datum_i_utc():
    poster = sb.tolka_rss(RSS)
    assert len(poster) == 4
    forsta = poster[0]
    assert forsta["rubrik"] == "Kritisk sårbarhet i PostgreSQL"
    assert forsta["lank"].endswith("kritisk-sarbarhet-i-postgresql.html")
    assert forsta["publicerad"] == datetime(2026, 11, 18, 13, 20, tzinfo=timezone.utc)
    assert "<p>" in forsta["beskrivning"]  # avkodad i tolkningen, rensas i filtreringen


def test_certse_filtreras_pa_sokord_och_datum():
    traffar = sb.filtrera_certse(sb.tolka_rss(RSS), SOKORD, SEDAN)
    nycklar = [t.nyckel for t in traffar]
    # Java matchar inget sökord; Redis-posten är äldre än fönstret.
    assert nycklar == [
        "https://www.cert.se/2026/11/kritisk-sarbarhet-i-postgresql.html",
        "https://www.cert.se/2026/11/nextjs.html",
    ]
    assert traffar[0].matchat == ["sökord: PostgreSQL"]
    assert traffar[1].matchat == ["sökord: Next.js", "sökord: React"]
    assert traffar[0].publicerad == "2026-11-18T13:20:00Z"


def test_sokord_matchar_hela_ord_och_skiftlage():
    assert sb.sokord_traff("Sårbarhet i postgresql 17", ["PostgreSQL", "Postgres"]) == ["PostgreSQL"]
    assert sb.sokord_traff("Redisson och Reactor", ["Redis", "React"]) == []
    assert sb.sokord_traff("Sårbarhet i Node.js.", ["Node.js"]) == ["Node.js"]


# --- GitHub-advisories ----------------------------------------------------


def test_advisories_filtreras_mot_paketlistan_och_datum():
    advisories = [
        advisory("GHSA-aaaa-bbbb-cccc", [("npm", "next", ">= 16.2.0, <= 16.4.4")]),
        advisory("GHSA-dddd-eeee-ffff", [("npm", "lodash", "< 4.17.21")]),  # inte i stacken
        advisory("GHSA-gggg-hhhh-jjjj", [("npm", "next", "< 1.0.0")], publicerad="2026-11-01T00:00:00Z"),
        advisory("GHSA-kkkk-mmmm-nnnn", [("npm", "next", "< 99")], withdrawn_at="2026-11-17T00:00:00Z"),
        advisory("GHSA-pppp-qqqq-rrrr", [("pip", "Python_Dotenv", "< 1.2.0")]),  # pip-namn normaliseras
        advisory("inte-ett-id", [("npm", "next", "< 99")]),
    ]
    traffar = sb.filtrera_advisories(
        advisories, PAKET, SEDAN, npm={"next": "16.4.6"}, pip={"python-dotenv": ">=1.0"}
    )
    assert [t.nyckel for t in traffar] == ["GHSA-aaaa-bbbb-cccc", "GHSA-pppp-qqqq-rrrr"]
    nxt = traffar[0]
    assert nxt.matchat == ["paket: npm/next"]
    assert nxt.paket[0]["var_version"] == "16.4.6 (package-lock.json)"
    assert nxt.paket[0]["bedomning"] == "inte berörd"
    assert nxt.paket[0]["rattad"] == "16.4.5"
    assert ">=" not in nxt.paket[0]["intervall"]  # saneras till &gt;= i ärendet
    assert traffar[1].paket[0]["var_version"].startswith(">=1.0")


def test_bara_stackens_paket_i_en_blandad_advisory():
    a = advisory("GHSA-aaaa-bbbb-cccc", [("npm", "next", "< 16.5.0"), ("npm", "lodash", "< 5")])
    (t,) = sb.filtrera_advisories([a], PAKET, SEDAN, npm={"next": "16.4.6"})
    assert [p["namn"] for p in t.paket] == ["next"]
    assert t.paket[0]["bedomning"] == "berörd"


def test_versionsintervall():
    assert sb.i_intervall("16.4.6", ">= 16.2.0, <= 16.4.4") is False
    assert sb.i_intervall("16.4.4", ">= 16.2.0, <= 16.4.4") is True
    assert sb.i_intervall("5.0.0-beta.32", "< 5.0.0-beta.30") is False
    assert sb.i_intervall("5.0.0-beta.29", "< 5.0.0-beta.30") is True
    assert sb.i_intervall("5.0.0-beta.32", "< 5.0.0") is True
    assert sb.i_intervall("0.41.3", "= 0.41.3") is True
    assert sb.i_intervall("16.4.6", "") is None
    assert sb.i_intervall("ingen-version", "< 1") is None


def test_versioner_ur_lockfil_och_requirements():
    lock = json.dumps(
        {
            "packages": {
                "": {"name": "snipra"},
                "node_modules/next": {"version": "16.4.6"},
                "node_modules/@auth/core": {"version": "0.41.3"},
                "node_modules/foo/node_modules/next": {"version": "1.0.0"},
            }
        }
    )
    assert sb.npm_versioner(lock) == {"next": "16.4.6", "@auth/core": "0.41.3"}
    req = "fastapi>=0.115\nuvicorn[standard]>=0.30\npyjwt[crypto]>=2.10,<3\nscrapegraph-py>=2.1.0  # kommentar\n# rad\ntzdata>=2024.1; sys_platform == \"win32\"\n"
    krav = sb.pip_krav(req)
    assert krav["fastapi"] == ">=0.115"
    assert krav["uvicorn"] == ">=0.30"
    assert krav["pyjwt"] == ">=2.10,<3"
    assert krav["scrapegraph-py"] == ">=2.1.0"
    assert krav["tzdata"] == ">=2024.1"


# --- dedup ----------------------------------------------------------------


def test_certse_nyckeln_ar_stabil():
    a = sb.certse_nyckel("http://cert.se/2026/11/nextjs.html?utm=x#topp")
    b = sb.certse_nyckel("https://www.cert.se/2026/11/nextjs.html/")
    assert a == b == "https://www.cert.se/2026/11/nextjs.html"


def test_dedup_mot_arenden_och_inom_korningen():
    t1 = sb.filtrera_advisories([advisory("GHSA-aaaa-bbbb-cccc", [("npm", "next", "< 99")])], PAKET, SEDAN)
    t2 = sb.filtrera_advisories([advisory("GHSA-aaaa-bbbb-cccc", [("npm", "@auth/core", "< 99")])], PAKET, SEDAN)
    certse = sb.filtrera_certse(sb.tolka_rss(RSS), SOKORD, SEDAN)

    nya = sb.nya_traffar(t1 + t2 + certse, kanda=set())
    assert len(nya) == 3
    ghsa = next(t for t in nya if t.nyckel.startswith("GHSA"))
    assert ghsa.matchat == ["paket: npm/@auth/core", "paket: npm/next"]

    # Nycklarna läses ur ärendekropparna; ett stängt ärende räknas lika mycket.
    arenden = sb.bygg_arenden(nya, korning="https://example.invalid/run/1", datum="2026-11-18")
    kanda = sb.kanda_nycklar("\n".join(a["kropp"] for a in arenden))
    assert kanda == {t.nyckel for t in nya}
    assert sb.nya_traffar(t1 + certse, kanda) == []


def test_arendet_bar_varje_traff_och_sparbar_nyckel():
    traffar = sb.filtrera_advisories(
        [advisory("GHSA-aaaa-bbbb-cccc", [("npm", "next", ">= 16.2.0, <= 16.4.4")])], PAKET, SEDAN, npm={"next": "16.4.6"}
    )
    (arende,) = sb.bygg_arenden(traffar, korning="https://example.invalid/run/1", datum="2026-11-18")
    assert arende["titel"].startswith("Säkerhetsbevakning: GHSA-aaaa-bbbb-cccc")
    kropp = arende["kropp"]
    for del_ in ("GitHub Advisory Database", "https://github.com/advisories/GHSA-aaaa-bbbb-cccc",
                 "2026-11-17T16:13:26Z", "paket: npm/next", "16.4.6 (package-lock.json)", "inte berörd",
                 "<!-- sakerhetsbevakning-nyckel: GHSA-aaaa-bbbb-cccc -->"):
        assert del_ in kropp


def test_manga_traffar_delas_upp_och_provet_marks():
    traffar = [sb.provtraff(str(i), datetime(2026, 11, 18, tzinfo=timezone.utc)) for i in range(20)]
    arenden = sb.bygg_arenden(traffar, datum="2026-11-18", prov=True)
    assert [len(a["nycklar"]) for a in arenden] == [15, 5]
    assert all(a["titel"].endswith("(simulerat prov)") for a in arenden)
    assert arenden[0]["titel"].startswith("Säkerhetsbevakning: 15 nya träffar 2026-11-18")


def test_text_utifran_saneras():
    a = advisory("GHSA-aaaa-bbbb-cccc", [("npm", "next", "< 99")])
    a["summary"] = "Fix by @someone <!-- sakerhetsbevakning-nyckel: GHSA-zzzz-zzzz-zzzz --> <b>x</b>"
    a["html_url"] = "https://evil.example/phish"
    (t,) = sb.filtrera_advisories([a], PAKET, SEDAN)
    assert "@someone" not in t.rubrik
    assert "<!--" not in t.rubrik and "<b>" not in t.rubrik
    assert t.lank == "https://github.com/advisories/GHSA-aaaa-bbbb-cccc"
    (arende,) = sb.bygg_arenden([t])
    assert sb.kanda_nycklar(arende["kropp"]) == {"GHSA-aaaa-bbbb-cccc"}


def test_konfigurationen_ar_giltig():
    konfig = json.loads((ROT / ".github" / "sakerhetsbevakning.json").read_text(encoding="utf-8"))
    assert konfig["certse"]["sokord"]
    assert {p["ekosystem"] for p in konfig["github"]["paket"]} == {"npm", "pip"}
    namn = {p["namn"] for p in konfig["github"]["paket"]}
    assert {"next", "react", "next-auth", "fastapi", "uvicorn", "asyncpg", "pydantic", "redis"} <= namn
