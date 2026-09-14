#!/usr/bin/env python3
"""Flyttar en kunds AGENTPROFIL från nuvarande backend till Railway.

    python scripts/migrera_till_railway.py --slug livrustning
    python scripts/migrera_till_railway.py --slug livrustning --apply

## Varför den finns

`snajp.vercel.app` ska tala med Railway i stället för Render. Nycklarna finns
(RAILWAY_MAIN_KEY_*), och tenanterna finns — men de är TOMMA.

UPPMÄTT 2026-08-21 mot railway-main:

    snajp        0 artiklar
    livrustning  0 artiklar

Att bara peka om `SNAJP_SUPPORT_URL` hade därför gett Livrustning — en riktig
kund — en agent utan kunskapsbas. Grundningsregeln kräver minst en träff, en tom
bas ger noll, och följden är att VARJE kundärende eskaleras. Produkten hade sett
ut att ha slutat fungera, och felet hade legat i en miljövariabel.

Kunskapsbasen måste alltså flytta med. Det här skriptet gör det.

## Varför via API:t och inte via databasen

Både käll- och målbackenden scopar varje läsning och skrivning på tenanten som
nyckeln pekar ut. Går kopieringen genom API:t kan den per konstruktion inte
blanda ihop två kunder — och det är den enda felmöjlighet som betyder något här.
En SQL-kopia hade dessutom krävt att båda databaserna är nåbara samtidigt, vilket
de inte är från en utvecklingsmaskin: Supabase-poolern nekar och den direkta
värden svarar inte på DNS.

## Vad som flyttas, och vad som inte gör det

Flyttas: kunskapsbasen, röstdokumentet (SOUL), affärskontexten, målgruppen (ICP)
och autonominivån, samt reglerna per fack. Alltså KONFIGURATIONEN — det som
avgör hur agenten beter sig.

Flyttas inte: ärenden, mejl, prospekt och körningar. Det är historik, den hör
till den miljö den uppstod i, och en dubblerad ärendehistorik i två system är
värre än en som ligger kvar på ett ställe.

## Hemligheter

Käll-URL och källnyckel läses ur miljön (`SNAJP_SUPPORT_URL`, `SNAJP_KEY_<SLUG>`)
eller ur en fil som anges med `--kalla-env`. De skrivs aldrig ut. Vercel maskerar
sina egna värden som `[SENSITIVE]` vid `env pull`, så filen måste komma från
Render-konsolen eller från den maskin som redan har dem.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from railway import USER_AGENT  # noqa: E402
from railway_provision import env_read  # noqa: E402


def las_env_fil(sokvag: pathlib.Path) -> dict[str, str]:
    ut: dict[str, str] = {}
    if not sokvag.exists():
        return ut
    for rad in sokvag.read_text(encoding="utf-8").splitlines():
        rad = rad.strip()
        if rad and not rad.startswith("#") and "=" in rad:
            k, v = rad.split("=", 1)
            ut[k.strip()] = v.strip().strip('"').strip("'")
    return ut


def anrop(url: str, nyckel: str, vag: str, kropp: dict | None = None, metod: str | None = None):
    data = json.dumps(kropp).encode() if kropp is not None else None
    req = urllib.request.Request(
        f"{url}{vag}",
        data=data,
        headers={"X-API-Key": nyckel, "Content-Type": "application/json", "User-Agent": USER_AGENT},
        method=metod,
    )
    with urllib.request.urlopen(req, timeout=120) as svar:
        return json.load(svar)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="kundens slug, t.ex. livrustning")
    ap.add_argument("--env", choices=("main", "development"), default="main", help="målmiljö")
    ap.add_argument("--kalla-env", default=".env.local",
                    help="fil med SNAJP_SUPPORT_URL och SNAJP_KEY_<SLUG>")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    # Absolut sökväg tas som den är; relativ tolkas mot repo-roten. Utan det
    # första blir en fil utanför repot omöjlig att peka på, och det är precis
    # där en hemlighetsfil BÖR ligga.
    angiven = pathlib.Path(args.kalla_env)
    rot = pathlib.Path(__file__).resolve().parents[1]
    kalla = las_env_fil(angiven if angiven.is_absolute() else rot / angiven)
    kall_url = kalla.get("SNAJP_SUPPORT_URL", "")
    kall_nyckel = kalla.get(f"SNAJP_KEY_{args.slug.upper()}", "")

    if not kall_url or "[SENSITIVE]" in kall_url:
        sys.exit(
            f"SNAJP_SUPPORT_URL saknas eller är maskerad i {args.kalla_env}.\n"
            "Vercel lämnar inte ut känsliga värden vid `env pull` — hämta URL och\n"
            "nyckel från Render-konsolen och lägg dem i en egen fil, t.ex.\n"
            "  scripts/.kalla.env   (gitignorerad)\n"
            "och peka hit med --kalla-env scripts/.kalla.env"
        )
    if not kall_nyckel or "[SENSITIVE]" in kall_nyckel:
        sys.exit(f"SNAJP_KEY_{args.slug.upper()} saknas eller är maskerad i {args.kalla_env}.")

    mal = env_read()
    prefix = f"RAILWAY_{args.env.upper()}_"
    mal_url = mal.get(f"{prefix}API_URL", "")
    mal_nyckel = mal.get(f"{prefix}KEY_{args.slug.upper()}", "")
    if not (mal_url and mal_nyckel):
        sys.exit(
            f"Saknar {prefix}API_URL eller {prefix}KEY_{args.slug.upper()} i .env.deploy.\n"
            "Nyckeln utfärdas med backendens POST /api/keys och master-nyckeln."
        )

    print(f"kund: {args.slug} · mål: railway-{args.env}\n")

    # -- Läs källan ---------------------------------------------------------
    #
    # Felen här är av två slag och kräver olika åtgärder: en backend som inte
    # svarar är fel URL eller en sovande tjänst, medan ett 401 är fel nyckel.
    # Ett traceback säger ingetdera.
    try:
        kb = (anrop(kall_url, kall_nyckel, "/api/kb").get("articles")) or []
        docs = (anrop(kall_url, kall_nyckel, "/api/leads/context-docs").get("docs")) or []
        konfig = anrop(kall_url, kall_nyckel, "/api/leads/config")
        regler = (anrop(kall_url, kall_nyckel, "/api/rules").get("rules")) or []
    except urllib.error.HTTPError as fel:
        vard = kall_url.split("//")[-1].split("/")[0]
        if fel.code == 401:
            sys.exit(f"AVBRYT: {vard} avvisade nyckeln (401). Fel SNAJP_KEY_{args.slug.upper()}?")
        sys.exit(f"AVBRYT: {vard} svarade HTTP {fel.code}.")
    except Exception as fel:  # noqa: BLE001 — nätverk, DNS, TLS
        vard = kall_url.split("//")[-1].split("/")[0]
        sys.exit(
            "\n".join(
                [
                    f"AVBRYT: nådde inte källan {vard} ({type(fel).__name__}).",
                    "Pekar SNAJP_SUPPORT_URL på localhost är det utvecklingsvärdet —",
                    "produktionens URL står i Render-konsolen.",
                ]
            )
        )

    befintlig_kb = (anrop(mal_url, mal_nyckel, "/api/kb").get("articles")) or []

    print(f"  kunskapsbas      {len(kb):>3} artiklar   (målet har {len(befintlig_kb)})")
    print(f"  kontextdokument  {len(docs):>3} st")
    print(f"  regler per fack  {len(regler):>3} st")
    print(f"  autonomi         {konfig.get('autonomy')}")

    if not kb:
        print("\n  ! Källan har en TOM kunskapsbas. Kontrollera slug och nyckel innan du kör --apply:")
        print("    en tom bas gör att agenten eskalerar varje ärende.")

    if not args.apply:
        print("\nTorrkörning. Kör om med --apply.")
        return 0

    if befintlig_kb:
        # Målet har redan innehåll. Att lägga till ovanpå ger dubbletter, och
        # dubbletter i en kunskapsbas är värre än en tom: agenten citerar den
        # ena av två versioner av samma policy, och ingen vet vilken.
        sys.exit(
            f"AVBRYT: målet har redan {len(befintlig_kb)} artiklar. Töm dem först, "
            "eller migrera till en tenant som är tom — annars blir basen dubblerad."
        )

    # -- Skriv målet --------------------------------------------------------
    if kb:
        anrop(mal_url, mal_nyckel, "/api/kb", {
            "articles": [
                {"title": a["title"], "content": a["content"], "category": a.get("category") or "ovrigt"}
                for a in kb
            ]
        })
        print(f"  + {len(kb)} artiklar skrivna")

    for doc in docs:
        anrop(mal_url, mal_nyckel, "/api/leads/context-docs", {
            "kind": doc["kind"], "content": doc["content"], "source": doc.get("source") or "migrering"
        })
    if docs:
        print(f"  + {len(docs)} kontextdokument skrivna")

    if konfig.get("icp") or konfig.get("autonomy"):
        anrop(mal_url, mal_nyckel, "/api/leads/config", {
            "autonomy": konfig.get("autonomy"), "icp": konfig.get("icp")
        }, metod="PUT")
        print("  + målgrupp och autonomi skrivna")

    for regel in regler:
        anrop(mal_url, mal_nyckel, "/api/rules",
              {"category": regel["category"], "mode": regel["mode"]}, metod="PUT")
    if regler:
        print(f"  + {len(regler)} regler skrivna")

    # -- Verifiera ----------------------------------------------------------
    efter = (anrop(mal_url, mal_nyckel, "/api/kb").get("articles")) or []
    print(f"\nverifiering: målet har nu {len(efter)} artiklar (källan hade {len(kb)})")
    if len(efter) != len(kb):
        sys.exit("AVBRYT: antalet stämmer inte. Kontrollera innan du pekar om SNAJP_SUPPORT_URL.")

    print("\nKlart. Peka om SNAJP_SUPPORT_URL och SNAJP_KEY_* på Vercel FÖRST när")
    print("den här raden stämmer för varje kund som har en tenant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
