#!/usr/bin/env python
"""Omklassar listspårets rader med den nya kontaktsökningen. Torrkörning som standard.

    python scripts/omklassa_listspar.py                          # alla kunder, visar bara
    python scripts/omklassa_listspar.py --kund snajp             # en kund
    python scripts/omklassa_listspar.py --kund snajp --apply     # skapar prospekt, märker rader

Skälet (Antons regler 12–16, 2026-10-07): ungefär hälften av listspårets
300+ rader ("Utan webbplats, Iris <datum>") hade en webbplats, och
kontaktsökningen missade adresser som fanns där. Varje rad körs om genom
samma sökning och fördelning som körningen (discovery.hamta_person_kontakt,
sources/merinfo.fordela):

* mejl → ett Iris-prospekt (origin 'iris'). Research och utkast startas sedan
  i appen (Processa om), som för en körning ur en lista;
* bara telefon och en VD namngiven i registret → ringlistan (origin 'ring');
* inget kontaktsätt → raden står kvar som den är (ej kvalificerad). Har
  bolaget en sajt rapporteras det: det prövas om i nästa körning.

INGENTING RADERAS (Antons beslut 2026-10-07): raden står kvar i sin lista
och märks i signal_detalj med vart bolaget flyttades ("… → flyttad till Iris
2026-10-08"). Prospektet, dess källor och märkningen skrivs i EN transaktion
per rad. En redan märkt rad, eller ett bolag som redan är ett prospekt eller
en CRM-kund, hoppas över.

Kostnadsfritt: registrets uppgifter (VD, bolagsnummer, bolags-e-post) läses
ur kundens sidcache (merinfo-sidorna, 30 dygn), aldrig hämtade på nytt.
Webbsidorna hämtas direkt och gratis; ScrapeGraph och Gemini stängs av i
skriptet. Bara development: main vägras. Lösenordet läses ur .env.deploy
och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "snajp-support"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

#: Märkningen i signal_detalj, per spår. Raden raderas aldrig.
MARKERING = {"iris": "Iris", "ring": "ringlistan"}
_MARKERAD = " → flyttad till "
#: Prospektets profilkolumner som skriptet sätter (migration 031, 058, 081).
PROSPEKTFALT = (
    "orgnr", "website", "ort", "postnr", "anstallda", "omsattning", "sni",
    "contact_role", "contact_level", "contact_phone",
)
LAGLIG_GRUND_REGISTER = (
    "Berättigat intresse för B2B-prospektering; uppgiften hämtad ur en "
    "publik källa (GDPR art. 6.1 f), källänk bevarad."
)


def ar_markerad(signal_detalj: str | None) -> bool:
    return _MARKERAD in (signal_detalj or "")


def ny_signal_detalj(signal_detalj: str | None, spar: str, dag: str) -> str:
    """Skälet som stod kvar, plus vart bolaget flyttades och när."""
    return f"{(signal_detalj or '').strip()}{_MARKERAD}{MARKERING[spar]} {dag}".strip()


def kandidat_ur_rad(rad: dict[str, Any], bolag: dict[str, Any] | None) -> dict[str, Any]:
    """Listraden med registrets bolagsfakta (merinfo.tolka_bolag ur
    sidcachen) i kandidatens form, som körningen ser den."""
    from app.leads.sources import merinfo

    k = merinfo.till_kandidat(bolag, {}, None) if bolag and bolag.get("company_name") else {}
    return {
        **k,
        "company_name": rad["company_name"],
        "orgnr": rad.get("orgnr") or k.get("orgnr"),
        "ort": rad.get("ort") or k.get("ort"),
        "website": rad.get("website") or k.get("website"),
        "source_name": rad.get("source_name") or k.get("source_name"),
        "source_url": rad.get("source_url") or k.get("source_url"),
    }


def planera(
    rad: dict[str, Any], kandidat: dict[str, Any], kontakt: dict[str, Any] | None
) -> tuple[str, str | None, dict[str, Any] | None]:
    """(spår, skäl, prospektrad). Spåret är merinfo.fordela:s, eller
    "redan_flyttad" för en rad som redan märkts. Prospektraden (bara för
    iris och ring) är det som skrivs till prospects."""
    from app.leads.sources import merinfo

    if ar_markerad(rad.get("signal_detalj")):
        return "redan_flyttad", None, None
    spar, skal = merinfo.fordela(kandidat, kontakt)
    if spar not in MARKERING:
        return spar, skal, None
    k = merinfo.iris_kandidat(kandidat, kontakt) if spar == "iris" else merinfo.ringrad(kandidat, kontakt)
    prospekt = {
        "company_name": k["company_name"],
        "contact_name": k.get("contact_name"),
        "contact_email": k.get("contact_email"),
        **{f: k[f] for f in PROSPEKTFALT if k.get(f) is not None},
    }
    return spar, skal, prospekt


async def _sok(rad: dict[str, Any], bolag: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Kandidaten med webbplats och kontaktsökningens svar. Bara gratis vägar."""
    from app.leads import discovery
    from app.leads.platshallare import ar_platshallare
    from app.leads.sources import merinfo

    kandidat = kandidat_ur_rad(rad, bolag)
    webb = await merinfo._webbplats(kandidat, betald=False)
    if webb and await ar_platshallare(webb):
        webb = None
    kandidat = {**kandidat, "website": webb}
    kontakt = (
        await discovery.hamta_person_kontakt(
            webb, kandidat.get("vd_namn"), bolagsadress_racker=True, bolagsnamn=kandidat["company_name"]
        )
        if webb else None
    )
    return kandidat, kontakt


def _skriv(cur, tenant_id: str, rad: dict[str, Any], spar: str, prospekt: dict[str, Any], dag: str) -> None:
    """Prospekt, källor och märkning. Anroparen håller transaktionen."""
    from app.leads.discovery import LAGLIG_GRUND_EGEN_WEBB

    origin = "test" if rad["is_test"] else spar
    kolumner = ["tenant_id", "company_name", "contact_name", "contact_email", "origin"]
    varden: list[Any] = [tenant_id, prospekt["company_name"], prospekt.get("contact_name"),
                         prospekt.get("contact_email"), origin]
    for falt in PROSPEKTFALT:
        if falt in prospekt:
            kolumner.append(falt)
            varden.append(prospekt[falt])
    cur.execute(
        f"insert into prospects ({', '.join(kolumner)}) values ({', '.join(['%s'] * len(varden))}) returning id",
        varden,
    )
    prospekt_id = cur.fetchone()[0]
    kallor = []
    if prospekt.get("website"):
        kallor.append((prospekt["website"], "company_website", LAGLIG_GRUND_EGEN_WEBB))
    if rad.get("source_url"):
        kallor.append((rad["source_url"], "business_register", LAGLIG_GRUND_REGISTER))
    for url, typ, grund in kallor:
        cur.execute(
            "insert into prospect_sources (tenant_id, prospect_id, source_url, source_type, lawful_basis)"
            " values (%s, %s, %s, %s, %s)",
            (tenant_id, prospekt_id, url, typ, grund),
        )
    cur.execute(
        "update lead_list_items set signal_detalj = %s where id = %s and tenant_id = %s",
        (ny_signal_detalj(rad.get("signal_detalj"), spar, dag), rad["id"], tenant_id),
    )
    if cur.rowcount != 1:
        raise RuntimeError(f"märkte {cur.rowcount} rader, väntade 1; rullar tillbaka")


def main() -> int:
    # Windows-konsolen (cp1252) har inget "→" och fällde --help.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kund", help="kundens slug, t.ex. snajp (utan: alla kunder)")
    parser.add_argument("--env", choices=("development",), default="development",
                        help="bara development; main vägras")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    # Kostnadsfritt: ingen ScrapeGraph, ingen Gemini, direkthämtningen på.
    for nyckel in ("SCRAPEGRAPHAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_SERVICE_ACCOUNT_JSON", "DATABASE_URL"):
        os.environ[nyckel] = ""
    os.environ["LEADS_DIREKTHAMTNING"] = "1"
    os.environ["LEADS_PLATSHALLARKONTROLL"] = "1"

    import psycopg2

    from app.leads import upptagna
    from app.leads.sources import merinfo
    from railway_migrate import dsn
    from railway_provision import env_read

    dag = date.today().isoformat()
    conn = psycopg2.connect(dsn(env_read(), args.env), connect_timeout=20)
    conn.set_session(readonly=not args.apply)
    summa: Counter[str] = Counter()
    try:
        with conn.cursor() as cur:
            cur.execute("select id, slug from ss_tenants where %s::text is null or slug = %s", (args.kund, args.kund))
            kunder = cur.fetchall()
        if args.kund and not kunder:
            sys.exit(f"AVBRYTER: kunden {args.kund!r} finns inte.")
        for tenant_id, slug in kunder:
            with conn.cursor() as cur:
                cur.execute(
                    """select i.id, i.company_name, i.website, i.ort, i.orgnr, i.source_name, i.source_url,
                              i.signal_detalj, l.is_test
                       from lead_list_items i join lead_lists l on l.id = i.list_id
                       where i.tenant_id = %s and i.signal = 'listspar' order by i.created_at""",
                    (tenant_id,),
                )
                namn = [d[0] for d in cur.description]
                rader = [dict(zip(namn, r)) for r in cur.fetchall()]
                # Prospekt och CRM-kunder; listraderna själva räknas inte.
                cur.execute(
                    """select company_name, orgnr from prospects where tenant_id = %s
                       union select i.company_name, i.orgnr from lead_list_items i
                       join lead_lists l on l.id = i.list_id where i.tenant_id = %s and l.kalla = 'crm'""",
                    (tenant_id, tenant_id),
                )
                upptagna_nu = upptagna.bolagsnycklar(
                    [{"company_name": n, "orgnr": o} for n, o in cur.fetchall()]
                )
            if not rader:
                continue
            print(f"\n## {slug}: {len(rader)} listspårsrader")
            per_kund: Counter[str] = Counter()
            for rad in rader:
                bolag = None
                if rad.get("source_url"):
                    with conn.cursor() as cur:
                        cur.execute(
                            "select innehall from leads_sidcache where tenant_id = %s and url = %s and innehall is not null",
                            (tenant_id, rad["source_url"]),
                        )
                        cache = cur.fetchone()
                    bolag = merinfo.tolka_bolag(cache[0], rad["source_url"]) if cache else None
                kandidat, kontakt = asyncio.run(_sok(rad, bolag))
                spar, skal, prospekt = planera(rad, kandidat, kontakt)
                if prospekt and upptagna.upptagen(upptagna_nu, rad["company_name"], rad.get("orgnr")):
                    spar, skal, prospekt = "finns_redan", "Bolaget är redan ett prospekt eller en CRM-kund", None
                per_kund[spar] += 1
                if spar == "prova_om":
                    print(f"  prövas om: {rad['company_name']} ({kandidat.get('website')}): {skal}")
                if not (args.apply and prospekt):
                    continue
                try:
                    with conn:  # en transaktion per rad
                        with conn.cursor() as cur:
                            cur.execute("select set_config('app.tenant_id', %s, true)", (str(tenant_id),))
                            _skriv(cur, str(tenant_id), rad, spar, prospekt, dag)
                    upptagna_nu |= upptagna.bolagsnycklar([prospekt])
                except Exception as fel:  # noqa: BLE001 — en rad som faller ska inte fälla resten
                    per_kund[f"fel ({type(fel).__name__})"] += 1
                    print(f"  FEL för {rad['company_name']}: {type(fel).__name__}")
            for spar, antal in sorted(per_kund.items()):
                print(f"  {spar}: {antal}")
            summa.update(per_kund)
    finally:
        conn.close()
    print("\n## Totalt")
    for spar, antal in sorted(summa.items()):
        print(f"  {spar}: {antal}")
    if not args.apply:
        print("Inget ändrat; kör med --apply för att skapa prospekten och märka raderna.")
    else:
        print("Iris-prospekten saknar research: starta den i appen (Processa om).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
