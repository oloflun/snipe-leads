#!/usr/bin/env python3
"""Verifiera snajp.se hos Resend — domänen, DNS-posterna och kontrollen.

    python scripts/resend_doman.py                    # visa läget (torrkörning)
    python scripts/resend_doman.py --apply            # lägg till + skriv DNS
    python scripts/resend_doman.py --apply --verifiera # och be Resend kontrollera

## Vad det löser

Att verifiera en avsändardomän är fyra moment i två dashboards, och det
mellersta — att föra över tre DNS-poster för hand — är där felen sker:
posten hamnar på apex i stället för på underdomänen, DKIM-strängen bryts vid
kopiering, eller så råkar någon röra MX-posten och slår ut den inkommande
posten. Det här skriptet gör hela kedjan och kan köras om.

## Regionen är ett engångsval

`REGION` nedan är `eu-west-1` med flit. Resend behandlar varje mottagares
adress och hela mejltexten, alltså personuppgifter — samma resonemang som
fällde DeepSeek i CLAUDE.md. Regionen går INTE att ändra efter att domänen
skapats; den måste raderas och läggas upp igen. Ändra inte konstanten utan
att det beslutet tas om.

## Nycklar

`RESEND_FULL_API_KEY` i `.env.deploy` — en nyckel med **full behörighet**.
Den sändnings-nyckel som ligger i Railway (`RESEND_API_KEY`) duger inte:
API:t svarar `restricted_api_key` på allt utom `/emails`. Skapas på
resend.com under API Keys.

`LOOPIA_API_USER` / `LOOPIA_API_PASSWORD` — samma som scripts/loopia_dns.py.

## Vad skriptet ALDRIG rör

Poster på apex (`@`). Där ligger MX:en för `kontakt@snajp.se` och domänens
SPF. Resends poster hör hemma på underdomäner, och en skrivning mot `@`
vore ett fel även om Resend bad om det — därför vägrar `skriv_post` den.

Leakagespärr: nycklarna läses ur `.env.deploy` och skrivs aldrig ut.
"""
from __future__ import annotations

import argparse
import sys
import xmlrpc.client
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway_provision import env_read  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOOPIA_ENDPOINT = "https://api.loopia.se/RPCSERV"
RESEND_BAS = "https://api.resend.com"
DOMAN = "snajp.se"

#: Se modulens docstring — engångsval, ändra inte utan nytt beslut.
REGION = "eu-west-1"

#: Poster på det här namnet skrivs aldrig. Apex bär MX och SPF för den
#: inkommande posten; en felskrivning där tystar kundens mejl.
FORBJUDET_NAMN = {"@", "", DOMAN, DOMAN + "."}


def loopia() -> tuple[xmlrpc.client.ServerProxy, str, str]:
    env = env_read()
    anv, los = env.get("LOOPIA_API_USER", ""), env.get("LOOPIA_API_PASSWORD", "")
    if not anv or not los:
        raise SystemExit("LOOPIA_API_USER/LOOPIA_API_PASSWORD saknas i .env.deploy.")
    return xmlrpc.client.ServerProxy(LOOPIA_ENDPOINT, encoding="utf-8", allow_none=True), anv, los


def resend_klient():
    import httpx

    nyckel = env_read().get("RESEND_FULL_API_KEY", "")
    if not nyckel:
        raise SystemExit(
            "RESEND_FULL_API_KEY saknas i .env.deploy.\n"
            "Sändnings-nyckeln i Railway duger inte — den svarar 'restricted_api_key'\n"
            "på allt utom /emails. Skapa en nyckel med Full access på resend.com."
        )
    return httpx.Client(
        base_url=RESEND_BAS,
        timeout=45,
        headers={"Authorization": f"Bearer {nyckel}", "Content-Type": "application/json"},
    )


def hamta_eller_skapa_doman(k, apply: bool) -> dict | None:
    """Domänposten hos Resend, skapad om den saknas. None i torrkörning."""
    svar = k.get("/domains")
    svar.raise_for_status()
    for d in svar.json().get("data") or []:
        if d.get("name") == DOMAN:
            print(f"  Resend: {DOMAN} finns redan (status={d.get('status')}, region={d.get('region')})")
            if d.get("region") != REGION:
                print(
                    f"  VARNING: regionen är {d.get('region')}, inte {REGION}. Den går inte att\n"
                    f"  ändra — domänen måste raderas i Resend och läggas upp igen."
                )
            return k.get(f"/domains/{d['id']}").json()

    if not apply:
        print(f"  SKULLE lägga till {DOMAN} hos Resend i regionen {REGION}.")
        return None

    ny = k.post("/domains", json={"name": DOMAN, "region": REGION})
    if ny.status_code >= 400:
        raise SystemExit(f"Resend avvisade domänen ({ny.status_code}): {ny.text[:300]}")
    data = ny.json()
    print(f"  Resend: la till {DOMAN} i {REGION} (id={data.get('id')})")
    return k.get(f"/domains/{data['id']}").json()


def under_och_namn(post: dict) -> str:
    """Underdomänen posten hör till, i Loopias namngivning.

    Resend anger fullständiga namn (`send.snajp.se`); Loopia vill ha delen
    före domänen (`send`). Apex blir `@`, som vi vägrar skriva till.
    """
    namn = str(post.get("name", "")).strip().rstrip(".")
    if namn in (DOMAN, ""):
        return "@"
    if namn.endswith("." + DOMAN):
        return namn[: -(len(DOMAN) + 1)]
    return namn


def skriv_post(api, anv, los, under: str, typ: str, varde: str, prio: int, apply: bool) -> None:
    if under in FORBJUDET_NAMN:
        print(f"  VÄGRAR skriva {typ} på apex ({under}) — där bor MX och SPF. Hoppar över.")
        return

    befintliga = api.getZoneRecords(anv, los, DOMAN, under) or []
    for r in befintliga:
        if r.get("type") == typ and str(r.get("rdata", "")).rstrip(".") == varde.rstrip("."):
            print(f"  {under:26} {typ:5} finns redan")
            return

    if not apply:
        print(f"  {under:26} {typ:5} SKULLE sättas -> {varde[:60]}")
        return

    if under not in (api.getSubdomains(anv, los, DOMAN) or []):
        api.addSubdomain(anv, los, DOMAN, under)
        print(f"  {under:26} skapade underdomänen")

    svar = api.addZoneRecord(
        anv, los, DOMAN, under, {"type": typ, "ttl": 3600, "priority": prio, "rdata": varde}
    )
    print(f"  {under:26} {typ:5} satt -> {varde[:60]}  ({svar})")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--apply", action="store_true", help="Skriv på riktigt.")
    p.add_argument("--verifiera", action="store_true", help="Be Resend kontrollera posterna efteråt.")
    args = p.parse_args()

    k = resend_klient()
    print(f"Resend-domän ({REGION}):")
    doman = hamta_eller_skapa_doman(k, args.apply)
    if doman is None:
        print("\nTorrkörning — kör med --apply för att lägga till domänen och skriva DNS.")
        return 0

    poster = doman.get("records") or []
    if not poster:
        print("  Resend returnerade inga DNS-poster. Inget att skriva.")
        return 1

    print(f"\nDNS hos Loopia ({len(poster)} poster):")
    api, anv, los = loopia()
    for post in poster:
        skriv_post(
            api,
            anv,
            los,
            under_och_namn(post),
            str(post.get("type", "")).upper(),
            str(post.get("value", "")).strip(),
            int(post.get("priority") or 0),
            args.apply,
        )

    if args.verifiera and args.apply:
        print("\nBer Resend verifiera …")
        svar = k.post(f"/domains/{doman['id']}/verify")
        print(f"  {svar.status_code}: {svar.text[:200]}")
        laget = k.get(f"/domains/{doman['id']}").json()
        print(f"  status: {laget.get('status')}")
        print("  (DNS kan ta några minuter att slå igenom — kör om vid 'pending'.)")

    print("\nKvar som handgrepp: aliaset hej@ -> kontakt@ i Loopias kundzon.")
    print("Loopias API exponerar inga e-postmetoder (alla svarar 404).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
