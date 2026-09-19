#!/usr/bin/env python
"""Byter Livrustnings seedade kunskapsbas i drift mot versionen från nya sajten.

    python scripts/livrustning_kb_synk.py --env development            # visar planen
    python scripts/livrustning_kb_synk.py --env development --apply

`app/tenants/livrustning_kb.py` skrevs om 2026-09-19 efter Livrustnings nya
webbplats. `seed_kb` rör aldrig en riktig kunds bas när den redan har innehåll,
så den gamla versionen (Wix-sajten: webbutik, hjärtstartarförsäljning,
08-972247, Nacka) ligger kvar i drift tills den byts här — och
supportagenten svarar ur den.

Vad skriptet rör, och bara det:
- artiklar vars rubrik står i GAMLA (2026-08-05-seedningen) och inte i den nya
  filen: tas bort;
- artiklar vars rubrik står i den nya filen men med annat innehåll: tas bort
  och läggs in på nytt;
- rubriker i den nya filen som saknas: läggs in.
En artikel kunden själv skrivit har en rubrik som inte står i någon av listorna
och lämnas orörd. Allt går via API:t (DELETE kräver migration 069) med en
tenantnyckel som mintas med masternyckeln — samma mönster som
scripts/livrustning_produktkontext.py. Nycklar skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "snajp-support"))

from seed_demo import Api, deploy_env  # noqa: E402

from app.tenants.livrustning_kb import KB_ARTICLES  # noqa: E402

SLUG = "livrustning"
TENANT_NAME = "Livrustning AB"  # måste matcha ss_tenants.name — create_tenant är en upsert

#: Rubrikerna i seedningen från 2026-08-05 (gamla livrustning_kb.py, 5f1ef42).
GAMLA = (
    "Om Livrustning AB",
    "Kontaktuppgifter och adresser",
    "Utbildningar — översikt och upplägg",
    "Första hjälpen och HLR med hjärtstartare",
    "eHLR och eFörstaHjälpen — digitala utbildningar",
    "Brandutbildning",
    "Krisstöd och krishantering",
    "Hjärtstartare för hem, företag och förening",
    "Hjärtsäker zon enligt svensk standard SS280000",
    "Vad ingår när Livrustning hjälper er bli Hjärtsäker zon",
    "Nöjdhetsgaranti",
    "Ångerrätt och öppet köp — ångra köp, returnera eller skicka tillbaka en vara",
    "Reklamation av skadad vara",
    "Garanti — vilken gäller i vilken situation",
    "Undantag från garantin",
    "Frakt och leverans",
    "Betalning, faktura och delbetalning",
    "Priser och offert",
    "Tvist och reklamationsnämnd",
    "Kvalitetspolicy",
    "Miljöpolicy",
    "Integritetspolicy och personuppgifter",
)


def _nyckel(titel: str) -> str:
    return " ".join((titel or "").split()).casefold()


def plan(befintliga: list[dict]) -> tuple[list[dict], list[dict]]:
    """(att ta bort, att lägga in). Ren funktion — testbar utan nät."""
    nya = {_nyckel(a["title"]): a for a in KB_ARTICLES}
    gamla = {_nyckel(t) for t in GAMLA}
    bort: list[dict] = []
    finns: set[str] = set()
    for artikel in befintliga:
        n = _nyckel(artikel.get("title", ""))
        if n in nya:
            if (artikel.get("content") or "").strip() == nya[n]["content"].strip() and n not in finns:
                finns.add(n)
            else:
                bort.append(artikel)
        elif n in gamla:
            bort.append(artikel)
    in_ = [a for n, a in nya.items() if n not in finns]
    return bort, in_


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, choices=["development", "main"])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas = store.get(f"{prefix}_API_URL")
    master = store.get(f"{prefix}_MASTER_API_KEY")
    if not bas or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL eller {prefix}_MASTER_API_KEY saknas i .env.deploy.")

    status, svar = Api(bas, master, skarpt=True).anrop(
        "POST", "/api/keys", {"tenant_name": TENANT_NAME, "slug": SLUG}
    )
    if not 200 <= status < 300:
        sys.exit(f"AVBRYTER: kunde inte hämta nyckel för {SLUG} ({status}) — {svar.get('fel', '')}")
    nyckel = svar.get("api_key") or svar.get("key")
    if not nyckel:
        sys.exit(f"AVBRYTER: /api/keys gav inget nyckelfält. Svarsnycklar: {sorted(svar)}")

    api = Api(bas, nyckel, skarpt=True)
    lista = api.get("/api/kb")
    if lista.get("tenant_name") != TENANT_NAME:
        sys.exit(f"AVBRYTER: nyckeln hör till {lista.get('tenant_name')!r}, inte {TENANT_NAME!r}.")
    befintliga = lista.get("articles", [])
    bort, in_ = plan(befintliga)
    print(f"Miljö: {args.env}  Tenant: {SLUG}  Artiklar nu: {len(befintliga)}")
    print(f"Tas bort: {len(bort)}")
    for a in bort:
        print(f"  - {a.get('title')}")
    print(f"Läggs in: {len(in_)}")
    for a in in_:
        print(f"  + {a['title']}")

    if not args.apply:
        print("TORRKÖRNING — inget skrivet. Kör med --apply.")
        return

    for a in bort:
        status, svar = api.anrop("DELETE", f"/api/kb/{a['id']}", None)
        if not 200 <= status < 300:
            sys.exit(f"AVBRYTER vid borttagning av {a.get('title')!r} ({status}) — {svar.get('fel', '')}")
    if in_:
        status, svar = api.anrop(
            "POST",
            "/api/kb",
            {"articles": [{k: a[k] for k in ("title", "content", "category")} for a in in_]},
        )
        if not 200 <= status < 300:
            sys.exit(f"AVBRYTER vid inläggning ({status}) — {svar.get('fel', '')}")
    print(f"Klart: {len(bort)} borttagna, {len(in_)} inlagda.")


if __name__ == "__main__":
    main()
