#!/usr/bin/env python
"""Fyller demokontot Nordlys Handel med det en demo faktiskt behöver.

    python scripts/seed_demo.py --env development            # visar planen
    python scripts/seed_demo.py --env development --apply
    python scripts/seed_demo.py --env development --apply --korningar
    python scripts/seed_demo.py --env development --apply --tenant snajp

Allt går över HTTPS mot backendens egna endpoints med tenantens API-nyckel.
Ingen SQL, ingen direktskrivning. Två skäl, och båda har kostat tid förut:

  * Railways Postgres sitter bakom en TCP-proxy på hög port, och en Claude
    Code-molnsession når bara port 443 (RAILWAY.md). Ett skript som kräver
    databasen går alltså inte att köra där alls.
  * En INSERT förbi API:t hoppar över embeddings, kategorikontrollen och
    versionsräkningen på kontextdokument. Raderna hade sett rätt ut i tabellen
    och ändå inte gått att söka fram.

Idempotent: artiklar matchas på titel, kontextdokument skrivs bara om texten
ändrats, konfiguration är PUT. Att köra det två gånger ska ge samma databas som
att köra det en gång.

`--korningar` KOSTAR PENGAR — åtta LLM-anrop per prospekt. Därför opt-in.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
NL2 = chr(10) * 2

DEMO_SLUG = "nordlys-handel"


# -- .env.deploy ------------------------------------------------------------

def deploy_env() -> dict[str, str]:
    fil = ROOT / ".env.deploy"
    if not fil.exists():
        sys.exit(
            "AVBRYTER: .env.deploy saknas. Skapa den med "
            "`RAILWAY_TOKEN=<token> python scripts/railway_env_bootstrap.py --apply`."
        )
    varden: dict[str, str] = {}
    for rad in fil.read_text(encoding="utf-8").splitlines():
        if rad.strip() and not rad.startswith("#") and "=" in rad:
            namn, _, varde = rad.partition("=")
            varden[namn.strip()] = varde.strip()
    return varden


# -- HTTP -------------------------------------------------------------------

class Api:
    def __init__(self, bas: str, nyckel: str, *, skarpt: bool):
        self.bas = bas.rstrip("/")
        self.nyckel = nyckel
        self.skarpt = skarpt

    def anrop(self, metod: str, vag: str, kropp: dict | None) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"{self.bas}{vag}",
            method=metod,
            data=json.dumps(kropp).encode("utf-8") if kropp is not None else None,
            headers={
                "X-API-Key": self.nyckel,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as svar:
                text = svar.read().decode("utf-8") or "{}"
                return svar.status, json.loads(text)
        except urllib.error.HTTPError as fel:
            return fel.code, {"fel": fel.read().decode("utf-8")[:300]}
        except Exception as fel:  # nätverk, inte HTTP — ska inte se ut som avslag
            return -1, {"fel": str(fel)[:300]}

    def get(self, vag: str) -> dict:
        status, svar = self.anrop("GET", vag, None)
        if status != 200:
            sys.exit(f"AVBRYTER: GET {vag} svarade {status} — {svar.get('fel', '')}")
        return svar

    def skriv(self, metod: str, vag: str, kropp: dict, vad: str) -> bool:
        """Skriver bara med --apply. Utan flaggan beskrivs åtgärden."""
        if not self.skarpt:
            print(f"  [torrkörning] {vad}")
            return True
        status, svar = self.anrop(metod, vag, kropp)
        if 200 <= status < 300:
            print(f"  {vad}: OK")
            return True
        print(f"  {vad}: FEL {status} {svar.get('fel', '')}")
        return False


# -- Innehållet -------------------------------------------------------------

AFFARSKONTEXT = NL2.join([
    "Vad vi säljer: Inredning och utemiljö för företag — förvaring, belysning, "
    "textil, krukor och trädgårdsredskap. Cirka 4 000 artiklar, allt lagerhållet "
    "i Jönköping, samma leveranstid året om.",

    "Vem vi säljer till: Fastighetsförvaltare, hotell, restauranger och kontor i "
    "Sverige som möblerar gemensamma ytor, entréer och utemiljöer. Tio till "
    "tvåhundra anställda, med egen inköpsfunktion och återkommande behov.",

    "Erbjudande: Fakturaköp efter kreditprövning, kostnadsställe och referens "
    "direkt på fakturan, kostnadsfri genomgång av beställningsportalen för upp "
    "till tio personer, och hemleverans utan extra avgift på skrymmande varor.",

    "Nästa steg vi vill ha: Ett kort samtal om hur inköpen görs i dag — inte en "
    "offert, inte en demo.",
])

SOUL = """Nordlys Handel skriver som en kunnig kollega, inte som en avdelning.

Ton: lugn, konkret, utan säljspråk. Vi lovar aldrig mer än vi vet. Står svaret
inte i vårt underlag säger vi det rakt ut och tar reda på det, i stället för att
formulera oss runt luckan.

Meningarna är korta. Ett stycke gör en sak. Vi skriver "vi" och "du", aldrig
"man". Vi använder siffror när vi har dem: "2 till 4 vardagar", inte "snabbt".

Ord vi inte använder: lösning, erbjudande, spännande, i dagsläget, vänligen,
återkomma i ärendet. Utropstecken används inte.

Så här inleder vi inte: "Tack för att du kontaktar oss!" Vi svarar på frågan
först och lägger det artiga sist, om det behövs alls.

I utskick: en anledning till att vi hör av oss, en observation om deras
verksamhet, en fråga. Aldrig en produktlista. Aldrig "jag såg att ni växer". Om
vi inte har något konkret att säga skickar vi ingenting.

Vi ber om ursäkt när vi haft fel: en gång, utan omskrivningar, och säger vad vi
gör åt det."""

ICP = {
    "industries": [
        "Fastighetsförvaltning",
        "Hotell och konferens",
        "Restaurang och café",
        "Kontor och coworking",
        "Trädgårdsanläggning",
    ],
    "exclude_industries": ["Bemanning", "Spel och betting", "Inkasso"],
    "geography": ["Sverige"],
    "roles": ["Fastighetschef", "Inköpsansvarig", "Platschef", "Kontorschef"],
    "must_have": [
        "Egna gemensamma ytor eller utemiljö",
        "Återkommande inköp, inte engångsköp",
    ],
    "deal_breakers": ["Färre än tio anställda", "Ingen egen inköpsfunktion"],
    "company_size": {"min": 10, "max": 200},
}

#: Alla tre lägena representerade, valda efter vad ett felaktigt svar får kosta.
#: Pengar och juridik går alltid till en människa. Orderstatus och leverans är
#: faktafrågor där kunskapsbasen har svaret ordagrant.
REGLER = {
    "orderstatus": "auto",
    "leverans": "auto",
    "garanti": "draft",
    "utbildning": "draft",
    "teknisk_support": "draft",
    "ovrigt": "draft",
    "retur_reklamation": "escalate",
    "betalning": "escalate",
}


# -- Stegen -----------------------------------------------------------------

def seeda_kb(api: Api, artiklar: list[dict]) -> None:
    print("Kunskapsbas:")
    befintliga = {a.get("title") for a in api.get("/api/kb").get("articles", [])}
    saknas = [a for a in artiklar if a["title"] not in befintliga]
    if not saknas:
        print(f"  {len(befintliga)} artiklar finns redan — inget att lägga till")
        return
    # En POST med hela listan: routen tar 1-50 artiklar, och ett anrop per
    # artikel hade betytt 22 embedding-anrop i följd med var sin timeout att
    # falla på.
    api.skriv(
        "POST",
        "/api/kb",
        {"articles": saknas},
        f"lägger till {len(saknas)} av {len(artiklar)} artiklar",
    )


def seeda_kontextdokument(api: Api, kind: str, innehall: str, vad: str) -> None:
    print(f"{vad}:")
    dokument = api.get(f"/api/leads/context-docs?kind={kind}").get("docs", [])
    senaste = max(dokument, key=lambda d: d.get("version", 0), default=None)
    if senaste and (senaste.get("content") or "").strip() == innehall.strip():
        print("  oförändrad — ingen ny version")
        return
    # Kontextdokument är append-only med versionsräknare. Att skriva samma text
    # igen skapar en version som inte betyder något, och versionsnumret är det
    # enda sättet att i efterhand se vad agenten läste vid en viss körning.
    api.skriv(
        "POST",
        "/api/leads/context-docs",
        {"kind": kind, "content": innehall, "source": "scripts/seed_demo.py"},
        f"skriver version {(senaste or {}).get('version', 0) + 1}",
    )


def seeda_soul(api: Api) -> None:
    print("Röstdokument:")
    nuvarande = (api.get("/api/leads/soul").get("content") or "").strip()
    if nuvarande == SOUL.strip():
        print("  oförändrat")
        return
    api.skriv("PUT", "/api/leads/soul", {"content": SOUL}, "skriver röstdokument")


def seeda_config(api: Api) -> None:
    print("Målgrupp och autonomi:")
    api.skriv(
        "PUT",
        "/api/leads/config",
        {"autonomy": "draft", "icp": ICP},
        "sätter ICP och autonominivå draft",
    )


def seeda_regler(api: Api) -> None:
    print("Regler per fack:")
    nuvarande = {r.get("category"): r.get("mode") for r in api.get("/api/rules").get("rules", [])}
    orort = 0
    for fack, lage in REGLER.items():
        if nuvarande.get(fack) == lage:
            orort += 1
            continue
        api.skriv("PUT", "/api/rules", {"category": fack, "mode": lage}, f"{fack} -> {lage}")
    if orort:
        print(f"  {orort} fack stod redan rätt")


def seeda_exempelbolag(api: Api, antal: int) -> None:
    print("Exempelbolag:")
    prospekt = api.get("/api/leads/prospects").get("prospects", [])
    exempel = [p for p in prospekt if p.get("origin") == "example"]
    if len(exempel) >= antal:
        print(f"  {len(exempel)} finns redan")
        return
    api.skriv(
        "POST",
        "/api/leads/prospects/exempel",
        {"limit": antal - len(exempel)},
        f"skapar {antal - len(exempel)} exempelbolag",
    )


def seeda_inkorg(api: Api) -> None:
    print("Inkorg:")
    # Routen byter UT de tidigare mock-mejlen i stället för att lägga till, och
    # rör bara provider='mock'. Att köra om den är alltså säkert och ger en
    # färsk inkorg — vilket är precis vad man vill inför en demo.
    api.skriv("POST", "/api/inbox/mock", {}, "genererar testmejl")


def seeda_korningar(api: Api, antal: int) -> None:
    print("Testkörningar (kostar pengar):")
    api.skriv(
        "POST",
        "/api/leads/runs/batch",
        {"limit": antal, "scope": "research", "is_test": True},
        f"startar {antal} körningar markerade som test",
    )


# -- main -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Fyller demokontot med innehåll.")
    parser.add_argument("--env", choices=["development", "main"], default="development")
    parser.add_argument("--tenant", choices=[DEMO_SLUG, "snajp"], default=DEMO_SLUG)
    parser.add_argument("--apply", action="store_true", help="skriv på riktigt")
    parser.add_argument("--antal-bolag", type=int, default=6)
    parser.add_argument(
        "--korningar",
        action="store_true",
        help="starta skarpa testkörningar — KOSTAR DeepSeek-krediter",
    )
    parser.add_argument("--antal-korningar", type=int, default=3)
    args = parser.parse_args()

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas = store.get(f"{prefix}_API_URL")
    if not bas:
        sys.exit(f"AVBRYTER: {prefix}_API_URL saknas i .env.deploy.")

    if args.tenant == DEMO_SLUG:
        nyckel = store.get(f"{prefix}_DEMO_API_KEY")
        if not nyckel:
            sys.exit(f"AVBRYTER: {prefix}_DEMO_API_KEY saknas i .env.deploy.")
        artiklar_slug = DEMO_SLUG
    else:
        # Snajps egen tenant har ingen nyckel i .env.deploy — den bor som
        # SNAJP_KEY_SNAJP på web-tjänsten och går inte att läsa tillbaka
        # därifrån. POST /api/keys är en upsert som ger en färsk nyckel för
        # det här körtillfället; den skrivs aldrig ner någonstans.
        master = store.get(f"{prefix}_MASTER_API_KEY")
        if not master:
            sys.exit(f"AVBRYTER: {prefix}_MASTER_API_KEY saknas i .env.deploy.")
        if not args.apply:
            sys.exit("--tenant snajp kräver --apply: nyckeln måste hämtas innan något kan läsas.")
        status, svar = Api(bas, master, skarpt=True).anrop(
            "POST", "/api/keys", {"tenant_name": "Snajp", "slug": "snajp"}
        )
        if not 200 <= status < 300:
            sys.exit(f"AVBRYTER: kunde inte hämta nyckel för snajp ({status}) — {svar.get('fel', '')}")
        nyckel = svar.get("api_key") or svar.get("key")
        if not nyckel:
            sys.exit(f"AVBRYTER: /api/keys gav inget nyckelfält. Svarsnycklar: {sorted(svar)}")
        artiklar_slug = "snajp"

    sys.path.insert(0, str(ROOT / "snajp-support"))
    from app.tenants import kb_for_tenant

    artiklar = kb_for_tenant(artiklar_slug)
    if not artiklar:
        sys.exit(f"AVBRYTER: ingen kunskapsbas registrerad för {artiklar_slug}.")

    api = Api(bas, nyckel, skarpt=args.apply)
    print(f"Miljö: {args.env}  Backend: {bas}  Tenant: {args.tenant}")
    print("TORRKÖRNING — inget skrivs. Lägg till --apply." if not args.apply else "SKARPT LÄGE.")
    print()

    seeda_kb(api, artiklar)

    # Resten är NORDLYS HANDELS innehåll — affärskontexten beskriver deras
    # sortiment, ICP:n deras målgrupp, röstdokumentet deras ton. Att skriva det
    # i Snajps egen tenant hade gett vår leads-agent instruktionen att sälja
    # krukor, och den sortens fel ser rimligt ut i varje enskild ruta.
    #
    # `--tenant snajp` seedar därför BARA kunskapsbasen. Snajps affärskontext
    # är verklig och skrivs i produkten, inte av ett demoskript.
    if args.tenant != DEMO_SLUG:
        print()
        print("Bara kunskapsbasen seedas för snajp — resten är Nordlys innehåll.")
        return

    seeda_kontextdokument(api, "product_marketing", AFFARSKONTEXT, "Affärskontext")
    seeda_soul(api)
    seeda_config(api)
    seeda_regler(api)
    seeda_exempelbolag(api, args.antal_bolag)
    seeda_inkorg(api)
    if args.korningar:
        seeda_korningar(api, args.antal_korningar)

    print()
    if args.apply:
        status = api.get("/api/leads/onboarding/status")
        print(f"Onboarding klar: {status.get('complete')}  saknas: {status.get('missing')}")
        print(f"Artiklar i basen: {len(api.get('/api/kb').get('articles', []))}")
    else:
        print("Kör om med --apply för att skriva.")


if __name__ == "__main__":
    main()
