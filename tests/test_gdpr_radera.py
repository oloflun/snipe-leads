"""Rättighetsverktyget (scripts/gdpr_radera.py) mot schemat i migrationerna.

Ingen databas: testerna läser db/migrations/*.sql och skriptets
tabellförteckning. Det de fångar är att verktyget halkar efter schemat — det
hände en gång (ingen ändring 2026-08-25 → 2026-11-17 medan ringlistan,
listorna, säljlistan, demolänkarna och kundregistret tillkom).

En ny tabell med en kolumn som ser ut som en personuppgift fäller
`test_varje_personuppgiftskolumn_ar_hanterad` tills den antingen står i
skriptets förteckning eller i UNDANTAG nedan, med motivering.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MIGRATIONER = ROOT / "db" / "migrations"

sys.path.insert(0, str(SCRIPTS))  # gdpr_radera importerar gdpr_verktyg som toppmodul
_spec = importlib.util.spec_from_file_location("gdpr_radera", SCRIPTS / "gdpr_radera.py")
gdpr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gdpr)
import gdpr_verktyg  # noqa: E402

#: Kolumner som ser ut som personuppgifter men inte är det, eller som hör
#: hemma i ett annat flöde. Nyckel "tabell.kolumn", värde motiveringen.
UNDANTAG = {
    "workspaces.name": "Arbetsytans (kundbolagets) namn.",
    "profiles.full_name": "Kontoanvändare: kontoflödet (auth.users, scripts/admin_cleanup.py), nämns i NAMNS_MANUELLT.",
    "companies.name": "Bolagsnamn i den gamla leadsmodellen.",
    "campaigns.name": "Kampanjens namn.",
    "sequences.name": "Sekvensens namn.",
    "ss_agent_metrics.metric_name": "Mätvärdets namn.",
    "ss_api_keys.tenant_name": "Kundens (bolagets) namn.",
    "ss_tenants.name": "Kundens (bolagets) namn.",
    "agent_skill_packs.playbook_name": "Playbookens namn.",
    "agent_skill_files.namespace": "Skillkatalogens namnrymd.",
    "offers.name": "Erbjudandets namn.",
    "ss_integrations.namn": "Integrationens namn.",
    "ss_integrations.hemlighetsnamn": "Namn på krypterade nycklar, inte värden.",
    "ss_channel_connections.namn": "Kanalanslutningens namn.",
    "ss_channel_connections.hemlighetsnamn": "Namn på krypterade nycklar, inte värden.",
    "lead_vyer.namn": "Sparad filtervy.",
    "crm_anslutningar.namn": "Anslutningens namn (källsystemet).",
    "crm_affarssteg.namn": "Namnet på ett steg på kundens affärstavla (Ny, Vunnen …).",
    "ss_api_keys.namn": "Nyckelns etikett.",
    "webbpool.company_name": "Bolagsnivå utan kontakter (INV-SEC-008).",
    "notification_preferences.email_enabled": "En boolesk inställning, ingen adress.",
    "email_events.generated_email_id": "Främmande nyckel; händelserna hör till generated_emails (MANUELLT), metadata söks med --fritext.",
}


# --- Schemat ur migrationerna ------------------------------------------------

_HOPPA = {"primary", "unique", "constraint", "check", "foreign", "exclude", "like"}
_FK = r"references\s+(?:\w+\.)?(\w+)\s*\([^)]*\)(?:\s+on\s+delete\s+(cascade|set null|restrict|no action|set default))?"


def _satser():
    for fil in sorted(MIGRATIONER.glob("*.sql")):
        text = fil.read_text(encoding="utf-8").lower()
        text = re.sub(r"--[^\n]*", "", text)
        text = re.sub(r"\$(\w*)\$.*?\$\1\$", "", text, flags=re.S)  # do- och funktionskroppar
        for sats in text.split(";"):
            if sats.strip():
                yield sats.strip()


def _schema():
    """(tabeller: namn → kolumner, fks: [(barn, kolumn, förälder, regel)])."""
    tabeller: dict[str, set[str]] = {}
    fks: list[tuple[str, str, str, str]] = []
    for sats in _satser():
        if m := re.match(r"create table (?:if not exists )?(?:public\.)?(\w+)\s*\((.*)\)\s*$", sats, re.S):
            namn = m.group(1)
            kolumner = tabeller.setdefault(namn, set())
            for rad in m.group(2).split("\n"):
                k = re.match(r"\s*([a-z_][a-z0-9_]*)\s+[a-z]", rad)
                if not k or k.group(1) in _HOPPA:
                    continue
                kolumner.add(k.group(1))
                if f := re.search(_FK, rad):
                    fks.append((namn, k.group(1), f.group(1), f.group(2) or "no action"))
        elif m := re.match(r"alter table (?:if exists )?(?:only )?(?:public\.)?(\w+)\s+rename to (\w+)", sats):
            gammal, ny = m.groups()
            if gammal in tabeller:
                tabeller[ny] = tabeller.pop(gammal)
            fks = [tuple(ny if x == gammal else x for x in fk) for fk in fks]
        elif m := re.match(r"alter table (?:if exists )?(?:only )?(?:public\.)?(\w+)\b", sats):
            namn = m.group(1)
            for k in re.finditer(r"add column (?:if not exists )?(\w+)\s+\w+([^,]*)", sats, re.S):
                tabeller.setdefault(namn, set()).add(k.group(1))
                if f := re.search(_FK, k.group(2), re.S):
                    fks.append((namn, k.group(1), f.group(1), f.group(2) or "no action"))
        elif m := re.match(r"drop table (?:if exists )?(?:public\.)?(\w+)", sats):
            tabeller.pop(m.group(1), None)
            fks = [fk for fk in fks if m.group(1) not in (fk[0], fk[2])]
    return tabeller, fks


TABELLER, FKS = _schema()
PERSONUPPGIFT = re.compile(
    r"email|epost|e_post|mejl|mail|namn|name|telefon|phone|kontaktperson|kontaktnummer|adress|address"
)


def _kaskad(rot: str) -> set[str]:
    """Tabellerna vars rader försvinner när en rad i `rot` raderas."""
    ut, andrad = {rot}, True
    while andrad:
        andrad = False
        for barn, _, foralder, regel in FKS:
            if foralder in ut and regel == "cascade" and barn not in ut:
                ut.add(barn)
                andrad = True
    return ut


def _namn(lista) -> list[str]:
    return [rad[0] for rad in lista]


RADERAS = _namn(gdpr.TABELLER)
HANTERADE = set(RADERAS) | {
    tabell for lista in ("BEHALLS", "MANUELLT", "KASKAD") for tabell in _namn(getattr(gdpr, lista, []))
}


# --- Testerna ----------------------------------------------------------------

def test_parsern_ser_schemat():
    # Vakt mot att parsern tyst slutar fungera och allt blir grönt.
    assert {"prospects", "lead_samtal", "saljlista", "ss_demolankar", "customer_memory"} <= set(TABELLER)
    assert "snajp_saljlista" not in TABELLER  # omdöpt i 103
    assert "contact_phone" in TABELLER["prospects"]
    assert ("suppressions", "contact_id", "contacts", "cascade") in FKS
    assert ("agent_runs", "prospect_id", "prospects", "set null") in FKS


def test_varje_personuppgiftskolumn_ar_hanterad():
    saknas = sorted(
        f"{tabell}.{kolumn}"
        for tabell, kolumner in TABELLER.items()
        for kolumn in kolumner
        if PERSONUPPGIFT.search(kolumn)
        and tabell not in HANTERADE
        and f"{tabell}.{kolumn}" not in UNDANTAG
    )
    assert not saknas, (
        "Kolumner som ser ut som personuppgifter men varken står i scripts/gdpr_radera.py "
        f"eller i UNDANTAG här: {saknas}"
    )


def test_tabellerna_i_forteckningen_finns_i_schemat():
    for lista in (gdpr.TABELLER, gdpr.BEHALLS, gdpr.MANUELLT, gdpr.KASKAD, gdpr.FRITEXT):
        for rad in lista:
            assert rad[0] in TABELLER, f"{rad[0]} finns inte (längre) i migrationerna"
    # En enkel kolumn (utan %s) ska finnas på tabellen — felet som dolde
    # outreach_threads.prospect_email i augusti.
    for tabell, kolumn, _ in gdpr.TABELLER + gdpr.BEHALLS + gdpr.MANUELLT:
        if "%s" not in kolumn:
            assert kolumn in TABELLER[tabell], f"{tabell}.{kolumn} finns inte i schemat"


def test_sparrlistan_raderas_aldrig():
    assert "suppressions" in _namn(gdpr.BEHALLS)
    assert "suppressions" not in RADERAS
    assert "suppressions" not in _namn(gdpr.KASKAD)
    kalla = (SCRIPTS / "gdpr_radera.py").read_text(encoding="utf-8")
    assert "delete from suppressions" not in kalla.lower()
    # contacts → suppressions kaskaderar. Kopplingen måste nollas FÖRE
    # raderingsslingan, annars tar raderingen av kontakten med sig spärren.
    for tabell in RADERAS:
        if "suppressions" in _kaskad(tabell):
            assert tabell == "contacts", f"{tabell} kaskaderar till spärrlistan"
    nolla = kalla.index("update suppressions set contact_id = null")
    slinga = kalla.index("for tabell, kolumn, _ in TABELLER:\n            if fynd")
    assert nolla < slinga


def test_inget_som_behalls_forsvinner_i_en_kaskad():
    behalls = set(_namn(gdpr.BEHALLS)) - {"suppressions"}  # spärren: se testet ovan
    for tabell in RADERAS:
        assert not (_kaskad(tabell) & behalls), f"radering i {tabell} tar med sig {behalls}"


def test_kaskadraderna_foljer_verkligen_med():
    for tabell, villkor, foralder in gdpr.KASKAD:
        assert foralder in RADERAS, f"{tabell}: föräldern {foralder} raderas inte"
        assert tabell in _kaskad(foralder), f"{tabell} kaskaderar inte från {foralder}"
        assert "%s" in villkor


def test_raderingsordningen_haller_for_framande_nycklar():
    """En främmande nyckel utan kaskad in i något som raderas kräver att
    barnet redan är borta (tidigare i ordningen, eller i samma kaskad)."""
    redan_borta: set[str] = set()
    for tabell in RADERAS:
        borta_nu = _kaskad(tabell)
        for barn, kolumn, foralder, regel in FKS:
            if foralder in borta_nu and regel in ("no action", "restrict"):
                assert barn in borta_nu or barn in redan_borta, (
                    f"{barn}.{kolumn} → {foralder} saknar kaskad och raderas inte före {tabell}"
                )
        redan_borta |= borta_nu


def test_manuella_beslut_raderas_inte_av_skriptet():
    manuellt = set(_namn(gdpr.MANUELLT))
    assert not manuellt & set(RADERAS)
    for tabell in RADERAS:
        assert not (_kaskad(tabell) & manuellt), f"radering i {tabell} kaskaderar in i ett manuellt beslut"


def test_undantagen_ar_inte_inaktuella():
    for nyckel in UNDANTAG:
        tabell, kolumn = nyckel.split(".")
        assert kolumn in TABELLER.get(tabell, set()), f"{nyckel} finns inte längre — stryk undantaget"


def test_kopiorna_som_inte_nas_namns():
    text = " ".join(gdpr.KOPIOR_SOM_INTE_NAS).lower()
    for kopia in ("redis", "development", "säkerhetskopior", "supabase"):
        assert kopia in text


@pytest.mark.parametrize("dsn", [
    "postgresql://postgres:x@db.abcdefgh.supabase.co:5432/postgres",
    "host=db.example.com dbname=postgres",
])
def test_gamla_stacken_vagras_mot_fjarrdatabas(monkeypatch, dsn):
    monkeypatch.setenv("DATABASE_URL", dsn)
    monkeypatch.setenv("PREVIEW_DATABASE_URL", dsn)
    for env in ("production", "preview"):
        with pytest.raises(SystemExit):
            gdpr_verktyg.dsn_for(env)


def test_gamla_stacken_godtas_mot_lokal_stack(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:localdev@127.0.0.1:5432/railway")
    assert gdpr_verktyg.dsn_for("production").endswith("@127.0.0.1:5432/railway")
