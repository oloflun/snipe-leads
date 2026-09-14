#!/usr/bin/env python3
"""LoopiaAPI-uppgifterna in i .env.deploy — utan att lösenordet syns någonstans.

    python scripts/loopia_nycklar.py            # frågar efter båda
    python scripts/loopia_nycklar.py --kontroll # visar vad som är satt, skriver inget

## Varför ett skript och inte en instruktion

`scripts/loopia_dns.py` läser `LOOPIA_API_USER` och `LOOPIA_API_PASSWORD` ur
`.env.deploy` (via `railway_provision.env_read`). Att sätta dem för hand är
tre steg där ett av dem är att inte råka spara lösenordet på fel ställe.

## Varför lösenordet ALDRIG tas som argument

Ett kommandoradsargument hamnar i skalets historik och i processlistan, där
det ligger kvar långt efter att fönstret stängts. `getpass` läser utan att
eka och utan att spara. Samma läckagespärr som CLAUDE.md beskriver: en `cat`
under felsökning läcker lika mycket som ett `echo`.

Skriptet skriver bara. Att uppgifterna FUNGERAR avgörs av
`python scripts/loopia_dns.py`, som gör ett riktigt anrop mot Loopia — ett
sparat värde är inte ett verifierat värde.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_provision import env_read, env_set  # noqa: E402

ANV = "LOOPIA_API_USER"
LOS = "LOOPIA_API_PASSWORD"


def visa(env: dict[str, str]) -> None:
    """Status utan att avslöja värdet. Längd + fyra sista räcker för att
    känna igen rätt uppgift; resten är onödig exponering i en loggad terminal."""
    for nyckel in (ANV, LOS):
        varde = env.get(nyckel, "")
        if not varde:
            print(f"  {nyckel:22} SAKNAS")
        elif nyckel == ANV:
            print(f"  {nyckel:22} {varde}")  # användarnamnet är inte hemligt
        else:
            print(f"  {nyckel:22} satt ({len(varde)} tecken, slutar …{varde[-4:]})")


def main() -> int:
    p = argparse.ArgumentParser(description="Skriv LoopiaAPI-uppgifter till .env.deploy.")
    p.add_argument("--kontroll", action="store_true", help="visa status, skriv ingenting")
    args = p.parse_args()

    if args.kontroll:
        print("\n.env.deploy:")
        visa(env_read())
        return 0

    print("\nLoopiaAPI-uppgifter -> .env.deploy (gitignorerad)")
    print("Skapas i kundzonen under Kontoinställningar → LoopiaAPI.")
    print("Det är en EGEN inloggning, skild från ditt Loopia-kontolösenord.\n")

    anv = input(f"{ANV} (t.ex. snajp@loopiaapi): ").strip()
    if not anv:
        print("Avbrutet — inget användarnamn angivet.")
        return 1
    if not anv.endswith("@loopiaapi"):
        # Den vanligaste felinmatningen är kontots e-postadress. Den
        # autentiserar inte mot RPCSERV och felet syns först vid anropet.
        print(f"\nOBS: '{anv}' slutar inte på '@loopiaapi'.")
        if input("Är det ändå rätt API-användare? [j/N]: ").strip().lower() != "j":
            print("Avbrutet.")
            return 1

    los = getpass.getpass(f"{LOS} (visas inte): ").strip()
    if not los:
        print("Avbrutet — inget lösenord angivet.")
        return 1

    print()
    env_set(ANV, anv)
    env_set(LOS, los)

    print("\nSparat. Kontroll (läser tillbaka ur filen):")
    visa(env_read())
    print("\nVerifiera mot Loopia på riktigt — sparat är inte samma sak som fungerande:")
    print("  python scripts/loopia_dns.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
