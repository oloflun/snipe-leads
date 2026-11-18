"""INV-DATA-008 — Synken skriver bara till development, och hos Railway läser
den main med en roll som inte kan skriva.

Synken ska flytta från GitHub Actions till en cron-tjänst i Railway-miljön main
(docs/compliance/synkflytt-plan.md, upplägg A). Där pekar det privata
värdnamnet `postgres.railway.internal` på PRODUKTIONEN, och samma avbild kan
kopieras till en annan miljö med ett klick. Den här filen prövar spärrarna som
står före första frågan, och det som gör riktningen mekanisk:

  a) Anslutningarna läses ur miljövariabler inne hos Railway, annars som förut
     ur .env.deploy (eller ur Actions-hemligheterna som miljövariabler).
  b) Fel miljö, samma databas på båda sidor, developments värd på mains
     privata nät, okrypterad sträcka eller --forsta i tjänsten: AVBRYT.
  c) Hos Railway får main-anslutningen inte kunna skriva något i public.
  d) Replica-läget sätts aldrig på main utanför första synken (en läsroll får
     inte sätta det, och main skrivs inte då).
  e) Ett rådgivande lås gör att två synkar aldrig skriver samtidigt.
  f) Utfallet skrivs bara till en databas vars markör säger development.
  g) Läsrollens migration ger bara läsrätt, saknar lösenord och kan inte logga in.

Skripten laddas med en psycopg2-stubbe: CI:s backendmiljö har asyncpg, inte
psycopg2, och inget test här öppnar en databas.
"""

from __future__ import annotations

import importlib
import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKRIPT = ROOT / "scripts"
MIGRATION = ROOT / "supabase" / "migrations" / "20261118090000_120_synk_lasroll.sql"

MAIN_PRIVAT = "postgresql://synk_las:x@postgres.railway.internal:5432/railway"
DEV_PROXY = "postgresql://postgres:y@dev.proxy.rlwy.net:41234/railway?sslmode=require"

_MILJO = (
    "SYNK_MAIN_PG_URL", "SYNK_DEVELOPMENT_PG_URL", "MIGRERA_PG_URL", "RAILWAY_ENVIRONMENT_NAME",
    "SYNK_APPLY", "MIGRERA_APPLY", "RAILWAY_PG_PASSWORD", "RAILWAY_PG_HOST", "RAILWAY_PG_PORT",
    *(f"RAILWAY_{m}_PG_{v}" for m in ("MAIN", "DEVELOPMENT") for v in ("PASSWORD", "HOST", "PORT")),
)


@pytest.fixture
def s(monkeypatch):
    """railway_synk, railway_migrate och railway_drift, nyladdade mot en stubbe."""
    pg = types.ModuleType("psycopg2")
    pg.Error = type("Error", (Exception,), {})
    pg.extras = types.ModuleType("psycopg2.extras")

    def _ingen_databas(*_a, **_k):
        raise AssertionError("testet får inte öppna en databas")

    pg.connect = _ingen_databas
    monkeypatch.setitem(sys.modules, "psycopg2", pg)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", pg.extras)
    for namn in ("railway", "railway_provision", "railway_migrate", "railway_synk", "railway_drift",
                 "railway_synk_anslut"):
        monkeypatch.delitem(sys.modules, namn, raising=False)
    for namn in _MILJO:
        monkeypatch.delenv(namn, raising=False)
    monkeypatch.syspath_prepend(str(SKRIPT))
    synk = importlib.import_module("railway_synk")
    migrate = importlib.import_module("railway_migrate")
    drift = importlib.import_module("railway_drift")
    # Ingen .env.deploy i testet, även om utvecklaren har en.
    monkeypatch.setattr(synk, "env_read", lambda: {})
    monkeypatch.setattr(migrate, "env_read", lambda: {})
    return SimpleNamespace(synk=synk, migrate=migrate, drift=drift, pg=pg)


class _Markor:
    def __init__(self, svar=()):
        self.fragor: list[tuple[str, tuple]] = []
        self._svar = list(svar)

    def execute(self, sql, params=()):
        self.fragor.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self._svar.pop(0)


class _Anslutning:
    def __init__(self, svar=()):
        self.markor = _Markor(svar)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.markor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


# -- a) Anslutningarna -----------------------------------------------------------


def test_hos_railway_laser_synken_anslutningarna_ur_miljon(s, monkeypatch):
    monkeypatch.setenv("SYNK_MAIN_PG_URL", MAIN_PRIVAT)
    monkeypatch.setenv("SYNK_DEVELOPMENT_PG_URL", DEV_PROXY)
    assert s.synk.anslutningar() == (MAIN_PRIVAT, DEV_PROXY, True)


def test_en_ensam_url_ar_en_halv_konfiguration_och_stoppar(s, monkeypatch):
    monkeypatch.setenv("SYNK_DEVELOPMENT_PG_URL", DEV_PROXY)
    with pytest.raises(SystemExit, match="AVBRYT"):
        s.synk.anslutningar()


def test_utan_railwayvariabler_ar_det_som_forut_med_actions_hemligheterna_som_reserv(s, monkeypatch):
    for miljo, varde in (("MAIN", "m"), ("DEVELOPMENT", "d")):
        monkeypatch.setenv(f"RAILWAY_{miljo}_PG_PASSWORD", f"{varde}pw")
        monkeypatch.setenv(f"RAILWAY_{miljo}_PG_HOST", f"{varde}.proxy.rlwy.net")
        monkeypatch.setenv(f"RAILWAY_{miljo}_PG_PORT", "5432")
    main_url, dev_url, railway = s.synk.anslutningar()
    assert not railway
    assert main_url == "postgresql://postgres:mpw@m.proxy.rlwy.net:5432/railway"
    assert dev_url == "postgresql://postgres:dpw@d.proxy.rlwy.net:5432/railway"


def test_filen_gar_fore_miljon_och_development_far_aldrig_mains_gamla_namn(s, monkeypatch):
    fil = {"RAILWAY_MAIN_PG_PASSWORD": "fil", "RAILWAY_MAIN_PG_HOST": "f", "RAILWAY_MAIN_PG_PORT": "1"}
    monkeypatch.setenv("RAILWAY_MAIN_PG_PASSWORD", "miljo")
    assert s.migrate.dsn(fil, "main") == "postgresql://postgres:fil@f:1/railway"
    # De gamla omiljöade namnen tillhör main; development faller aldrig dit.
    monkeypatch.setenv("RAILWAY_PG_PASSWORD", "p")
    monkeypatch.setenv("RAILWAY_PG_HOST", "h")
    monkeypatch.setenv("RAILWAY_PG_PORT", "1")
    with pytest.raises(SystemExit):
        s.migrate.dsn({}, "development")
    assert s.migrate.dsn({}, "main") == "postgresql://postgres:miljo@h:1/railway"


# -- b) Spärrarna före första frågan ---------------------------------------------


def test_giltig_konfiguration_hos_railway_gar_igenom(s):
    s.synk.kontrollera_anslutningar(MAIN_PRIVAT, DEV_PROXY, railway=True, forsta=False, miljo="main")


@pytest.mark.parametrize("miljo", ["development", "staging", ""])
def test_synken_kors_bara_i_railwaymiljon_main(s, miljo):
    with pytest.raises(SystemExit, match="AVBRYT"):
        s.synk.kontrollera_anslutningar(MAIN_PRIVAT, DEV_PROXY, railway=True, forsta=False, miljo=miljo)


def test_samma_databas_pa_bada_sidor_stoppar_i_alla_lagen(s):
    for railway in (True, False):
        with pytest.raises(SystemExit, match="samma databas"):
            s.synk.kontrollera_anslutningar(DEV_PROXY, DEV_PROXY, railway=railway, forsta=False, miljo="main")


def test_developments_vard_far_inte_ligga_pa_mains_privata_nat(s):
    # Inom miljön main är postgres.railway.internal PRODUKTIONEN.
    fel = "postgresql://postgres:y@postgres.railway.internal:5432/railway?sslmode=require"
    with pytest.raises(SystemExit, match="railway.internal"):
        s.synk.kontrollera_anslutningar(
            "postgresql://synk_las:x@annan.railway.internal:5432/railway", fel,
            railway=True, forsta=False, miljo="main",
        )


@pytest.mark.parametrize("fraga", ["", "?sslmode=prefer", "?sslmode=disable"])
def test_stracka_over_publik_port_kraver_tls(s, fraga):
    utan_tls = "postgresql://postgres:y@dev.proxy.rlwy.net:41234/railway" + fraga
    with pytest.raises(SystemExit, match="sslmode"):
        s.synk.kontrollera_anslutningar(MAIN_PRIVAT, utan_tls, railway=True, forsta=False, miljo="main")


def test_forsta_synken_skriver_till_main_och_gar_aldrig_i_tjansten(s):
    with pytest.raises(SystemExit, match="forsta"):
        s.synk.kontrollera_anslutningar(MAIN_PRIVAT, DEV_PROXY, railway=True, forsta=True, miljo="main")


def test_fran_actions_ar_spararna_som_forut(s):
    # Ingen Railway-miljö, proxyvärdar utan sslmode: dagens anslutningar.
    s.synk.kontrollera_anslutningar(
        "postgresql://postgres:a@m.proxy.rlwy.net:1/railway",
        "postgresql://postgres:b@d.proxy.rlwy.net:2/railway",
        railway=False, forsta=False, miljo=None,
    )


# -- c) Main-anslutningen kan inte skriva -----------------------------------------


def test_lasrollen_kontrolleras_mot_databasens_egna_rattigheter(s):
    kan = _Markor([(True,)])
    assert s.synk.main_kan_skriva(kan) is True
    sql = kan.fragor[0][0]
    assert "rolsuper" in sql and "has_table_privilege" in sql
    for ratt in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
        assert ratt in sql
    assert s.synk.main_kan_skriva(_Markor([(False,)])) is False


def test_main_oppnas_skrivskyddat_och_kontrolleras_hos_railway():
    kalla = (SKRIPT / "railway_synk.py").read_text(encoding="utf-8")
    assert "mn.set_session(readonly=True)" in kalla
    assert re.search(r"if railway and main_kan_skriva\(mc\):\s*\n\s*sys\.exit\(", kalla)


# -- d) Replica-läget -------------------------------------------------------------


def test_replicalaget_satts_pa_main_bara_i_forsta_synken(s):
    dc, mc = object(), object()
    assert s.synk.replikamal(dc, mc, forsta=False) == (dc,)
    assert s.synk.replikamal(dc, mc, forsta=True) == (dc, mc)
    kalla = (SKRIPT / "railway_synk.py").read_text(encoding="utf-8")
    assert "for c in (dc, mc):\n        c.execute(\"set session_replication_role" not in kalla


# -- e) Låset ---------------------------------------------------------------------


def test_last_ar_ett_radgivande_las_pa_development(s):
    ledig, upptagen = _Markor([(True,)]), _Markor([(False,)])
    assert s.synk.ta_las(ledig) is True
    assert s.synk.ta_las(upptagen) is False
    sql, params = ledig.fragor[0]
    assert "pg_try_advisory_lock(hashtext(%s))" in sql and params == (s.synk.LAS,)


def test_last_tas_fore_forsta_skrivningen():
    kalla = (SKRIPT / "railway_synk.py").read_text(encoding="utf-8")
    las = kalla.index("if args.apply and not ta_las(dc):")
    assert las < kalla.index('dc.execute("alter table public.mirror_meta add column if not exists lage text")')
    assert las < kalla.index("set session_replication_role = replica")


def test_migrationerna_vantar_pa_varandra(s):
    kalla = (SKRIPT / "railway_migrate.py").read_text(encoding="utf-8")
    assert "pg_advisory_lock(hashtext(%s))" in kalla


# -- f) Utfallet ------------------------------------------------------------------


def test_utfallet_skrivs_bara_dar_markoren_sager_development(s):
    # Ingen mirror_meta: inget skrivs (fel databas).
    ingen = _Anslutning([(False,)])
    s.synk.skriv_utfall(ingen, "ok")
    assert ingen.commits == 0 and not any(f.startswith(("alter", "update")) for f, _ in ingen.markor.fragor)
    # Tabellen finns men utan developmentrad (en tom tabell i main): inget skrivs.
    main = _Anslutning([(True,), (0,)])
    s.synk.skriv_utfall(main, "ok")
    assert main.commits == 0 and not any(f.startswith(("alter", "update")) for f, _ in main.markor.fragor)


def test_utfallet_bar_tid_utfall_och_antal_men_inga_rader(s):
    dev = _Anslutning([(True,), (1,)])
    s.synk.skriv_utfall(dev, "hoppade:2", {"ss_emails": {"till_dev": 3}})
    assert dev.rollbacks == 1 and dev.commits == 1
    update = next((f, p) for f, p in dev.markor.fragor if f.startswith("update"))
    assert "senaste_forsok_at = now()" in update[0] and "where environment = %s" in update[0]
    assert update[1][0] == "hoppade:2" and update[1][1] == '{"ss_emails": {"till_dev": 3}}'
    assert update[1][2] == "development"


def test_ett_fel_i_utfallsskrivningen_faller_inte_synken(s):
    class _Trasig(_Anslutning):
        def cursor(self):
            raise s.pg.Error("anslutningen är borta")

    s.synk.skriv_utfall(_Trasig(), "ok")  # ingen exception


def test_antalen_ar_bara_siffror_per_tabell(s):
    planer = {
        "ss_emails": (["id"], {"till_main": [], "till_dev": ["a", "b"], "radera_main": [], "radera_dev": ["c"]}),
        "prospects": (["id"], {"till_main": [], "till_dev": [], "radera_main": [], "radera_dev": []}),
    }
    assert s.synk.antal_per_tabell(planer) == {"ss_emails": {"till_dev": 2, "radera_dev": 1}}


# -- Startkommandot hos Railway ---------------------------------------------------


def test_startkommandot_kor_synken_bara_i_main_och_skarpt_bara_med_flaggan(s):
    with pytest.raises(SystemExit, match="main"):
        s.drift.kommandon("synk", {"RAILWAY_ENVIRONMENT_NAME": "development"})
    torr = s.drift.kommandon("synk", {"RAILWAY_ENVIRONMENT_NAME": "main"})
    assert len(torr) == 1 and torr[0][-1].endswith("railway_synk.py")
    skarp = s.drift.kommandon("synk", {"RAILWAY_ENVIRONMENT_NAME": "main", "SYNK_APPLY": "1"})
    assert skarp[0][-1] == "--apply"
    assert "--forsta" not in " ".join(" ".join(k) for k in skarp)


def test_startkommandot_migrerar_den_egna_miljon(s):
    with pytest.raises(SystemExit):
        s.drift.kommandon("migrera", {})
    steg = s.drift.kommandon("migrera", {"RAILWAY_ENVIRONMENT_NAME": "development", "MIGRERA_APPLY": "1"})
    assert len(steg) == 2
    assert steg[0][-3:] == ["--env", "development", "--apply"]
    assert steg[1][-2:] == ["--env", "development"]  # kontrollen efteråt, som i migrera.yml
    assert s.drift.kommandon("migrera", {"RAILWAY_ENVIRONMENT_NAME": "main"})[0][-2:] == ["--env", "main"]
    with pytest.raises(SystemExit):
        s.drift.kommandon("okant", {"RAILWAY_ENVIRONMENT_NAME": "main"})


def test_migrationstjanstens_url_hor_till_sin_egen_miljo(s, monkeypatch):
    monkeypatch.setenv("MIGRERA_PG_URL", "postgresql://postgres:z@postgres.railway.internal:5432/railway")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "development")
    assert s.migrate.anslutning("development").startswith("postgresql://")
    with pytest.raises(SystemExit, match="AVBRYT"):
        s.migrate.anslutning("main")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME")
    with pytest.raises(SystemExit, match="AVBRYT"):
        s.migrate.anslutning("development")


# -- Ägarens handgrepp: lösenordet och tjänstens variabler --------------------------


def test_anslutningsskriptet_bygger_variabler_som_klarar_synkens_sparrar(s):
    anslut = importlib.import_module("railway_synk_anslut")
    store = {"RAILWAY_DEVELOPMENT_PG_PASSWORD": "p/w", "RAILWAY_DEVELOPMENT_PG_HOST": "d.proxy.rlwy.net",
             "RAILWAY_DEVELOPMENT_PG_PORT": "41234"}
    varden = anslut.urls(store, "hemligt")
    assert varden["SYNK_MAIN_PG_URL"] == "postgresql://synk_las:hemligt@postgres.railway.internal:5432/railway"
    assert varden["SYNK_DEVELOPMENT_PG_URL"] == (
        "postgresql://postgres:p%2Fw@d.proxy.rlwy.net:41234/railway?sslmode=require"
    )
    with pytest.raises(SystemExit):
        anslut.urls({}, "hemligt")


def test_anslutningsskriptet_skriver_aldrig_ut_losenordet_och_ror_bara_main():
    kalla = (SKRIPT / "railway_synk_anslut.py").read_text(encoding="utf-8")
    for rad in kalla.splitlines():
        if "print(" in rad:
            rad = rad.replace("len(losen)", "")  # längden, inte värdet
            assert "losen)" not in rad and "{losen}" not in rad and "varden" not in rad, rad
    assert "dsn(store, MAIN)" in kalla and kalla.count("psycopg2.connect(") == 1
    assert "env_set(" not in kalla  # aldrig till .env.deploy
    assert "log_statement = 'none'" in kalla


# -- g) Läsrollens migration ------------------------------------------------------


def test_lasrollen_far_bara_lasa_och_saknar_losenord():
    sql = MIGRATION.read_text(encoding="utf-8")
    kod = "\n".join(r for r in sql.splitlines() if not r.strip().startswith("--")).lower()
    assert "create role synk_las nologin bypassrls" in kod
    assert "password" not in kod and " login" not in kod.replace("nologin", "")
    assert "default_transaction_read_only = on" in kod
    assert not re.search(r"grant\s+(insert|update|delete|truncate|all)", kod)
    assert "grant select on table public.%i to synk_las" in kod
    assert "grant select on table supabase_migrations.schema_migrations to synk_las" in kod


def test_lasrollen_far_lasa_varje_synkad_tabell(s):
    sql = MIGRATION.read_text(encoding="utf-8")
    for tabell in (*s.synk.SYNK, "ss_tenants", "synk_raderingar", "mirror_meta"):
        assert f"'{tabell}'" in sql, tabell
