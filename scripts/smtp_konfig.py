#!/usr/bin/env python3
"""Sätt den kundvända SMTP-sändvägen i Railway — med bevis före, inte hopp.

    python scripts/smtp_konfig.py --env development            # visa läget
    python scripts/smtp_konfig.py --env development --apply    # testa + sätt
    python scripts/smtp_konfig.py --env development --testmejl du@exempel.se

## Varför skriptet finns

Sändvägen (`app/leads/send_provider.py`, `app/email_pipeline/sender.py`) är
byggd och väntar bara på fyra variabler. Att sätta dem för hand i Railways
dashboard går, men då finns ingen kontroll av att uppgifterna FUNGERAR — och
symptomet på ett fel lösenord är inte ett felmeddelande vid deploy, utan mejl
som tyst inte går fram i drift.

Därför loggar skriptet in på SMTP-servern FÖRE det rör Railway. Går inte
inloggningen sätts ingenting, och du får veta varför direkt.

## Vilket konto

`snajp.se` har e-post hos Loopia, och domänens SPF-post är

    v=spf1 include:spf.loopia.se -all

`-all` betyder HÅRT avslag: bara Loopias servrar får skicka som @snajp.se.
Ett Gmail-konto med `From: hej@snajp.se` skulle alltså inte hamna i
skräpposten — det skulle avvisas. Kontot MÅSTE därför vara en brevlåda på
snajp.se hos Loopia (`mailcluster.loopia.se`, port 587 STARTTLS; 465 svarar
inte där, uppmätt 2026-08-28).

Brevlådan skapas i Loopias kundzon under E-post. Det är det enda steget som
kräver en människa: LoopiaAPI-uppgifterna i `.env.deploy` är tomma, och ett
kontolösenord är undantaget i CLAUDE.md oavsett.

## Läckagespärr

Lösenordet läses med `getpass` — det syns aldrig på skärmen, hamnar aldrig i
shell-historiken och skrivs aldrig ut.
"""
from __future__ import annotations

import argparse
import getpass
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway_provision import (  # noqa: E402
    envs_by_name,
    services_by_name,
    set_vars,
    state,
)

# Windows-konsolen kör cp1252 och kan inte koda alla tecken vi skriver ut.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Loopias utgående server. Port 587 med STARTTLS.
STANDARD_VARD = "mailcluster.loopia.se"
STANDARD_PORT = 587

#: Variablerna sändvägen läser (DEPLOY.md § Kundvänd utgående SMTP).
NYCKLAR = (
    "RESEND_API_KEY",
    "EMAIL_PROVIDER",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_FROM_NAME",
)

TIDSTAK = 20


def las_variabler(env_id: str, service_id: str) -> dict:
    from railway import gql
    from railway_provision import PROJECT_ID

    data = gql(
        "query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }",
        {"p": PROJECT_ID, "e": env_id, "s": service_id},
    )
    return data["variables"]


def visa_lage(miljo: str, varden: dict) -> None:
    print(f"\n[{miljo}/api] sändvägens variabler:")
    saknas = []
    for nyckel in NYCKLAR:
        satt = bool(str(varden.get(nyckel, "")).strip())
        print(f"    {nyckel:16} {'satt' if satt else '—'}")
        if not satt and nyckel in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
            saknas.append(nyckel)
    if str(varden.get("RESEND_API_KEY", "")).strip():
        print("\n  Sändvägen är PÅ via Resend (HTTPS) — SMTP-fälten spelar ingen roll.")
        return
    if saknas:
        print(f"\n  Sändvägen är AV. Saknas: {', '.join(saknas)}")
        print("  Backenden väljer LoggingSendProvider — ingenting skickas.")
    else:
        print("\n  Sändvägen är PÅ (alla tre obligatoriska satta).")


def testa_inloggning(vard: str, port: int, anvandare: str, losenord: str) -> str | None:
    """Loggar in på riktigt. Returnerar felsträng, eller None när det gick."""
    try:
        with smtplib.SMTP(vard, port, timeout=TIDSTAK) as server:
            server.starttls()
            server.login(anvandare, losenord)
        return None
    except smtplib.SMTPAuthenticationError as fel:
        # Felet betyder olika saker hos olika leverantörer, och ett generiskt
        # "fel lösenord" skickar folk att leta på fel ställe. Gmail avvisar
        # ALLTID kontolösenordet — det som krävs är ett app-lösenord, och det
        # alternativet finns inte ens i menyn förrän tvåstegsverifiering är på.
        if "gmail" in vard.lower() or "google" in vard.lower():
            rad = (
                "Gmail accepterar aldrig kontolösenordet över SMTP. Du behöver ett "
                "APP-LÖSENORD (16 tecken): myaccount.google.com -> Säkerhet -> "
                "App-lösenord. Alternativet visas bara om tvåstegsverifiering "
                "redan är påslagen på kontot."
            )
        else:
            rad = (
                f"Kontrollera att brevlådan {anvandare} finns och att lösenordet "
                f"är brevlådans eget — inte kundzonens inloggning."
            )
        return f"Servern avvisade inloggningen ({fel.smtp_code}). {rad}"
    except Exception as fel:  # noqa: BLE001
        return f"{type(fel).__name__}: {str(fel)[:160]}"


def skicka_testmejl(
    vard: str, port: int, anvandare: str, losenord: str, avsandare: str, mottagare: str
) -> str | None:
    meddelande = EmailMessage()
    meddelande["Subject"] = "Snajp: sändvägen fungerar"
    meddelande["From"] = avsandare
    meddelande["To"] = mottagare
    meddelande.set_content(
        "Det här mejlet skickades av scripts/smtp_konfig.py.\n\n"
        "Kommer det fram betyder det att SMTP-uppgifterna är rätt och att "
        "Loopia släpper igenom utskick från kontot.\n"
    )
    try:
        with smtplib.SMTP(vard, port, timeout=TIDSTAK) as server:
            server.starttls()
            server.login(anvandare, losenord)
            server.send_message(meddelande)
        return None
    except Exception as fel:  # noqa: BLE001
        return f"{type(fel).__name__}: {str(fel)[:160]}"


def satt_resend(args, env_id: str, service_id: str) -> int:
    """HTTPS-vägen. Ingen inloggning att testa — nyckeln prövas av första
    utskicket, och Resend svarar då med vad som är fel (overifierad domän,
    ogiltig nyckel, kvot slut). Ett provmejl härifrån hade krävt en verifierad
    domän ändå, så kontrollen görs bäst genom appen."""
    avsandare = (args.avsandare_resend or args.avsandare or "").strip()
    if not avsandare:
        avsandare = input("\n  Avsändaradress (måste vara verifierad hos Resend): ").strip()
    if "@" not in avsandare:
        print("  Ogiltig avsändaradress — inget gjort.")
        return 1

    nyckel = "".join(getpass.getpass("Resend API-nyckel (syns inte): ").split())
    if not nyckel.startswith("re_"):
        print("  Resend-nycklar börjar med 're_'. Kontrollera att du klistrade rätt sträng.")
        return 1

    set_vars(
        service_id,
        env_id,
        {
            "RESEND_API_KEY": nyckel,
            "SMTP_FROM": avsandare,
            "SMTP_FROM_NAME": args.namn,
            "EMAIL_PROVIDER": "resend",
        },
    )
    print(f"\n  Satt i {args.env}/api. Railway deployar om tjänsten automatiskt.")
    print("  Verifiera när den är uppe — varningen om sändväg ska vara borta:")
    print("    curl -s https://api-development-5cc3.up.railway.app/health/ready")
    print("  Skicka sedan ett riktigt svar från kundtjänstvyn och kontrollera att")
    print("  det kommer fram. Resend loggar varje försök i sin dashboard.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", default="development", choices=["development", "main"])
    p.add_argument("--apply", action="store_true", help="Testa inloggningen och sätt variablerna.")
    p.add_argument("--anvandare", help="Brevlådan, t.ex. hej@snajp.se. Frågas annars.")
    p.add_argument("--vard", default=STANDARD_VARD)
    p.add_argument("--port", type=int, default=STANDARD_PORT)
    p.add_argument("--avsandare", help="From-adress. Standard: samma som --anvandare.")
    p.add_argument("--namn", default="Snajp", help="Visningsnamn i From. Standard: Snajp.")
    p.add_argument(
        "--resend",
        action="store_true",
        help="Sätt HTTPS-vägen (Resend) i stället för SMTP. Frågar efter API-nyckeln. "
             "Det här är vägen som fungerar på Railways nuvarande plan.",
    )
    p.add_argument("--avsandare-resend", help="From-adress för Resend, t.ex. hej@snajp.se.")
    p.add_argument("--testmejl", help="Skicka ett provmejl hit efter att inloggningen gått.")
    args = p.parse_args()

    projekt = state()
    miljoer = envs_by_name(projekt)
    tjanster = services_by_name(projekt)
    env_id = miljoer.get(args.env)
    api = tjanster.get("api")
    if not env_id or not api:
        print(f"Hittade inte miljön {args.env!r} eller tjänsten 'api' i Railway.")
        return 1

    varden = las_variabler(env_id, api["id"])
    visa_lage(args.env, varden)

    if not args.apply and not args.testmejl:
        print("\n  Kör med --apply för att sätta dem (inloggningen testas först).")
        return 0

    if args.resend:
        return satt_resend(args, env_id, api["id"])

    anvandare = args.anvandare or input("\nBrevlåda (t.ex. hej@snajp.se): ").strip()
    if not anvandare or "@" not in anvandare:
        print("  Ogiltig adress — inget gjort.")
        return 1
    rått = getpass.getpass(f"Lösenord för {anvandare} (syns inte): ")
    # ALLA mellanslag bort, inte bara i kanterna. Google visar app-lösenord som
    # fyra grupper om fyra ("abcd efgh ijkl mnop"), och en kopiering tar med
    # mellanslagen — som ger 535 fast lösenordet är rätt. Inget riktigt
    # SMTP-lösenord bärs av sina mellanslag, så det här kan inte förstöra ett.
    losenord = "".join(rått.split())
    if not losenord:
        print("  Tomt lösenord — inget gjort.")
        return 1
    if losenord != rått.strip():
        print("  (Tog bort mellanslag ur lösenordet — Google visar app-lösenord grupperat.)")
    avsandare = (args.avsandare or anvandare).strip()

    print(f"\n  Loggar in på {args.vard}:{args.port} som {anvandare} …")
    fel = testa_inloggning(args.vard, args.port, anvandare, losenord)
    if fel:
        print(f"  MISSLYCKADES: {fel}")
        print("  Ingenting har satts i Railway.")
        return 1
    print("  Inloggningen gick igenom — FRÅN DEN HÄR MASKINEN.")
    print()
    print("  VARNING: det beviset gäller inte automatiskt i drift.")
    print("  Railway blockerar utgående SMTP (portarna 25/465/587/2525) på")
    print("  planerna Free, Trial och Hobby — bara Pro och uppåt släpper igenom.")
    print("  Projektet brave-passion ligger på TRIAL (kontrollerat 2026-08-28), så")
    print("  containern får 'Network is unreachable' även med rätt lösenord.")
    print("  Samma sak hände på Render 2026-07-30, se commit 0d3ac1d.")
    print("  Vägen som fungerar på trial är HTTPS-utskick (Resend) — inte SMTP.")
    print()

    if args.testmejl:
        print(f"  Skickar provmejl till {args.testmejl} …")
        fel = skicka_testmejl(args.vard, args.port, anvandare, losenord, avsandare, args.testmejl)
        if fel:
            print(f"  Provmejlet gick INTE att skicka: {fel}")
            print("  Inloggningen fungerar men utskicket stoppades — sätter inget.")
            return 1
        print("  Provmejlet är skickat. Kontrollera inkorgen innan du litar på vägen.")

    if not args.apply:
        print("\n  (Kör med --apply för att också sätta variablerna.)")
        return 0

    set_vars(
        api["id"],
        env_id,
        {
            "SMTP_HOST": args.vard,
            "SMTP_PORT": str(args.port),
            "SMTP_USER": anvandare,
            "SMTP_PASSWORD": losenord,
            "SMTP_FROM": avsandare,
            "SMTP_FROM_NAME": args.namn,
        },
    )
    print(f"\n  Satt i {args.env}/api. Railway deployar om tjänsten automatiskt.")
    print("  Verifiera när den är uppe:")
    print("    curl -s https://<api-url>/health/ready")
    print("  Varningen 'Ingen riktig sändväg' ska då vara BORTA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
