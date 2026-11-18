"""Webbens databasroll har exakt de rättigheter webben behöver (migration 126).

Två håll, båda mot hela migrationskedjan i CI-jobbet `databas`:

1. **Inte för mycket.** `snajp_web`:s rättigheter i `public` och `auth` jämförs
   med listan `TILLATET` nedan. En rättighet som inte står där fäller testet,
   också en som en ny migration ger eller som `alter default privileges` ger en
   ny tabell. Detsamma gäller läsrätten på `auth.users` för PUBLIC och
   `snajp_app` (ISO 27001 A.8.2, A.8.3, A.5.15).

2. **Inte för lite.** Varje SQL-sats i webbens källkod (filerna som importerar
   `lib/db.ts`) körs som `snajp_web` med EXPLAIN. EXPLAIN prövar rättigheterna på
   tabeller, kolumner och funktioner, och tabellerna i policyernas underfrågor,
   utan att köra något. En saknad rättighet ger "permission denied" här i
   stället för i drift. Satserna läses ur källan, så en ny fråga i webben prövas
   utan att någon behöver komma ihåg det.

Lägger du till en fråga mot en ny tabell i webben: ge rättigheten i en ny
migration och lägg raden i `TILLATET`. Vägrar allt annat än en lokal databas
utan spegelmarkör.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
WEB_DSN = os.environ.get("GALLRING_TEST_WEB_DSN", "")

pytestmark = pytest.mark.skipif(
    not (DSN and WEB_DSN),
    reason="Kräver GALLRING_TEST_DSN och GALLRING_TEST_WEB_DSN mot en tom testdatabas.",
)

ROOT = Path(__file__).resolve().parents[3]
_LOKALA = {"localhost", "127.0.0.1", "::1"}

#: (schema.tabell) → rättigheter. "select" = hela tabellen;
#: "update(a,b)" = bara de kolumnerna. Källa: migration 126; 127 tog bort
#: "update(is_demo)" på workspaces (demon markeras genom markera_demoarbetsyta()).
TILLATET: dict[str, set[str]] = {
    "auth.users": {
        "select",
        "insert(email,email_confirmed_at,encrypted_password,raw_user_meta_data)",
        "update(encrypted_password,updated_at)",
    },
    "public.workspaces": {"select"},
    "public.profiles": {"select"},
    "public.platform_admins": {"select"},
    "public.password_reset_tokens": {"select", "insert", "delete", "update(used_at)"},
    "public.demo_requests": {"insert"},
    "public.notification_preferences": {"select", "insert", "update"},
    "public.saljlista": {"select", "insert", "update", "delete"},
    "public.workspace_invites": {"select", "insert", "delete"},
    "public.business_contexts": {"select", "insert", "update"},
    "public.contacts": {"select"},
    "public.generated_emails": {"select", "update(body,status,subject)"},
    "public.ss_tenants": {"select(id,name,slug)"},
}

_PRIVILEGIER = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _anslut(dsn: str) -> asyncpg.Connection:
    assert urlsplit(dsn).hostname in _LOKALA, "Testet körs bara mot en lokal databas."
    conn = await asyncpg.connect(dsn)
    assert not await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    return conn


async def _rattigheter(conn, roll: str, scheman=("public", "auth")) -> dict[str, set[str]]:
    """Rollens faktiska rättigheter i samma form som TILLATET."""
    ut: dict[str, set[str]] = {}
    tabellniva = await conn.fetch(
        """
        select n.nspname || '.' || c.relname as tabell, p.priv
          from pg_class c
          join pg_namespace n on n.oid = c.relnamespace
          cross join unnest($2::text[]) as p(priv)
         where n.nspname = any($3::text[])
           and c.relkind in ('r', 'v', 'm', 'p', 'f')
           and has_table_privilege($1, c.oid, p.priv)
        """,
        roll, list(_PRIVILEGIER), list(scheman),
    )
    for r in tabellniva:
        ut.setdefault(r["tabell"], set()).add(r["priv"].lower())
    # Kolumnrättigheter där rollen saknar rättigheten på hela tabellen.
    kolumner = await conn.fetch(
        """
        select n.nspname || '.' || c.relname as tabell, p.priv, a.attname
          from pg_class c
          join pg_namespace n on n.oid = c.relnamespace
          join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
          cross join unnest(array['SELECT','INSERT','UPDATE','REFERENCES']) as p(priv)
         where n.nspname = any($2::text[])
           and c.relkind in ('r', 'v', 'm', 'p', 'f')
           and not has_table_privilege($1, c.oid, p.priv)
           and has_column_privilege($1, c.oid, a.attnum, p.priv)
        """,
        roll, list(scheman),
    )
    per: dict[tuple[str, str], list[str]] = {}
    for r in kolumner:
        per.setdefault((r["tabell"], r["priv"].lower()), []).append(r["attname"])
    for (tabell, priv), cols in per.items():
        ut.setdefault(tabell, set()).add(f"{priv}({','.join(sorted(cols))})")
    return ut


@pytest.mark.anyio
async def test_snajp_web_har_inget_utover_listan():
    conn = await _anslut(DSN)
    try:
        faktiska = await _rattigheter(conn, "snajp_web")
        for_mycket = {
            t: sorted(p - TILLATET.get(t, set())) for t, p in faktiska.items() if p - TILLATET.get(t, set())
        }
        assert not for_mycket, f"snajp_web har rättigheter utöver listan (migration 126): {for_mycket}"
        for_lite = {t: sorted(p - faktiska.get(t, set())) for t, p in TILLATET.items() if p - faktiska.get(t, set())}
        assert not for_lite, f"snajp_web saknar rättigheter som webben behöver: {for_lite}"
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_nya_tabeller_ger_inte_webben_rattigheter():
    conn = await _anslut(DSN)
    try:
        rader = await conn.fetch(
            """
            select d.defaclobjtype::text as typ, d.defaclacl::text as acl
              from pg_default_acl d
             where d.defaclnamespace = 'public'::regnamespace
            """
        )
        for r in rader:
            if r["typ"] == "r":
                assert "snajp_web=" not in r["acl"], f"standardrättighet för snajp_web på nya tabeller: {r['acl']}"
        await conn.execute("create table public.test_rattighet_126 (id int)")
        try:
            for priv in ("select", "insert", "update", "delete"):
                assert not await conn.fetchval(
                    "select has_table_privilege('snajp_web', 'public.test_rattighet_126', $1)", priv
                ), priv
        finally:
            await conn.execute("drop table public.test_rattighet_126")
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_auth_users_ar_inte_last_for_alla():
    conn = await _anslut(DSN)
    try:
        assert not await conn.fetchval("select has_table_privilege('public', 'auth.users', 'select')")
        app = await _rattigheter(conn, "snajp_app", scheman=("auth",))
        assert app == {"auth.users": {"select(email,id)"}}, app
        # Påminnelsens fråga i api:t (storage/postgres.py) behöver bara de två.
        for roll in ("snajp_app",):
            assert await conn.fetchval(
                "select has_column_privilege($1, 'auth.users', 'email', 'select')", roll
            )
            assert not await conn.fetchval(
                "select has_column_privilege($1, 'auth.users', 'encrypted_password', 'select')", roll
            )
    finally:
        await conn.close()


# --- Webbens egna frågor ------------------------------------------------------

_ANROP = re.compile(
    r"(?:\bsql|\bsqlAsUser|\.query)\s*(?:<[^>]*>)?\(\s*(?:[A-Za-z_.]+\s*,\s*)?(`[^`]*`|\"[^\"]*\")",
    re.S,
)


def _webbfiler() -> list[Path]:
    filer = []
    for katalog in ("app", "lib", "components"):
        for p in (ROOT / katalog).rglob("*.ts*"):
            if p.name.endswith(".test.ts") or "node_modules" in p.parts:
                continue
            text = p.read_text(encoding="utf-8")
            # Statisk import och dynamisk (`await import("@/lib/db")`).
            if re.search(r"(?:from\s+|import\(\s*)[\"']@/lib/db[\"']", text):
                filer.append(p)
    return sorted(filer)


def _expandera(fil: Path, sats: str) -> list[str]:
    """Fyll i de få mallarna webben bygger frågor med. En okänd mall fäller."""
    if "${" not in sats:
        return [sats]
    text = fil.read_text(encoding="utf-8")
    if m := re.search(r"const KOLUMNER = `([^`]*)`", text):
        sats = sats.replace("${KOLUMNER}", m.group(1))
    if "${namn}" in sats:
        falt_text = (ROOT / "lib" / "leads" / "saljlista.ts").read_text(encoding="utf-8")
        falt = re.findall(r"\"(\w+)\"", re.search(r"SALJLISTA_FALT = \[(.*?)\]", falt_text, re.S).group(1))
        assert falt, "SALJLISTA_FALT gick inte att läsa"
        return [
            sats.replace("${namn}", f).replace("${typ}", "::date" if f == "senast_kontaktad" else "")
            for f in falt
        ]
    assert "${" not in sats, f"okänd mall i {fil.relative_to(ROOT).as_posix()}: {sats[:120]}"
    return [sats]


def _webbens_satser() -> list[tuple[str, str]]:
    ut = []
    for fil in _webbfiler():
        text = fil.read_text(encoding="utf-8")
        for m in _ANROP.finditer(text):
            sats = m.group(1)[1:-1]
            for s in _expandera(fil, sats):
                ut.append((fil.relative_to(ROOT).as_posix(), s))
    return ut


def test_satserna_hittas():
    # Vakt mot att parsern tyst slutar hitta något och allt blir grönt.
    satser = _webbens_satser()
    filer = {f for f, _ in satser}
    assert len(satser) >= 50, len(satser)
    for f in (
        "lib/auth.ts", "lib/actions/auth.ts", "lib/workspace.ts", "lib/actions/saljlista.ts",
        "lib/actions/onboarding.ts", "lib/data/emails.ts",
    ):
        assert f in filer, f
    # Varje fil som importerar lib/db utom en ren hjälpfil ger minst en sats.
    for fil in _webbfiler():
        rel = fil.relative_to(ROOT).as_posix()
        assert rel in filer, f"ingen SQL hittad i {rel}"


@pytest.mark.anyio
async def test_webbens_satser_gar_att_kora_som_snajp_web():
    web = await _anslut(WEB_DSN)
    fel = []
    try:
        for fil, sats in _webbens_satser():
            antal = max((int(n) for n in re.findall(r"\$(\d+)", sats)), default=0)
            try:
                async with web.transaction():
                    await web.fetch("explain " + sats, *([None] * antal))
            except asyncpg.PostgresError as e:
                # Också andra fel: en sats som inte går att förbereda prövar inget.
                fel.append(f"{fil}: {type(e).__name__}: {e} :: {' '.join(sats.split())[:160]}")
    finally:
        await web.close()
    assert not fel, "webbens frågor saknar rättigheter som snajp_web:\n" + "\n".join(fel)


@pytest.mark.anyio
async def test_explain_fäller_en_saknad_rattighet():
    # Kontrollprovet: utan det kunde testet ovan vara grönt för att EXPLAIN inte
    # prövar något. Varje sats här SKA vägras.
    web = await _anslut(WEB_DSN)
    try:
        for sats, antal in (
            ("select key_hash from public.ss_api_keys", 0),  # tabell utan rättighet
            ("update public.workspaces set name = $1", 1),  # kolumn utan update-rätt
            ("update public.workspaces set is_demo = $1", 1),  # borta sedan 127
            ("select active from public.ss_tenants", 0),  # kolumn utan läsrätt
            ("update auth.users set email = $1", 1),  # e-posten får webben inte ändra
            ("select public.ensure_workspace_for_user($1::uuid, $2::text)", 2),  # funktion utan EXECUTE
        ):
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                async with web.transaction():
                    await web.fetch("explain " + sats, *([None] * antal))
    finally:
        await web.close()
