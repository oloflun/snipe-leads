#!/usr/bin/env python
"""Rättighetsflödet: hitta och radera allt om EN person.

    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se
    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se --export
    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se --export --fritext
    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se --radera
    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se --begransa "Riktigheten prövas"
    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se --hav-begransning "Prövningen klar"

Miljön är `railway-main` (produktionen). `railway-development` är en spegel
av main och ska inte vara målet för en begäran — se KOPIOR_SOM_INTE_NAS.

## Varför ett skript och inte en instruktion i ett dokument

Artikel 15 (tillgång) och artikel 17 (radering) har en tidsfrist på en månad.
En punktlista som säger "sök i ss_emails, sedan i contacts, sedan i..." kommer
att köras fel den dag det brådskar, och den som kör den kan inte i efterhand
visa vad som gjordes. Ett skript går att köra om, verifiera och falsifiera —
samma princip som redan gäller i CLAUDE.md.

## Tre lägen, i den ordning man använder dem

1. Utan flagga: SÖK. Visar var adressen förekommer, per tabell.
   Det här är också svaret på en tillgångsbegäran i första ledet.
2. `--export`: skriver ut allt som finns om personen som JSON. Det är den
   handling som lämnas ut vid en begäran om registerutdrag.
   `--fritext` lägger till en sökning efter adressen i löptext (promptar,
   loggar, mejltexter). Den är dyr och ger falska träffar, därför ett val.
3. `--radera`: raderar. Kräver att man skrivit adressen en gång till, för
   hand — se `_bekrafta`.

## Begränsning av behandling (art. 18)

`--begransa SKÄL` sätter en spärrmarkering i `behandlingsbegransningar`
(migration 124). Uppgifterna ligger kvar, men så länge markeringen är aktiv
stoppar sändningsspärren varje utskick till adressen hos alla kunder, och ett
inkommande mejl från adressen går till Att hantera utan klassning, Jev eller
AI-utkast. Gallringen (`gallra_tenant`, migration 144) rör inte adressens
uppgifter förrän markeringen hävts. `--hav-begransning SKÄL` hävs den; det kräver bekräftelse, för
art. 18.3 kräver att personen informerats innan begränsningen hävs. Raden
står kvar med tid och skäl som belägg för att begäran hanterats, och den
behålls också vid `--radera` (BEHALLS): en radering ska inte tyst häva en
begränsning.

Mot `railway-main` skrivs samma rad (samma id och tider) i development-spegeln
i samma körning, efter att main bekräftats (begransning_spegel.py). Spegeln
gallrar själv det synken inte för över, och dess gallring ser bara spegelns
egen tabell (Codex runda 15). Faller skrivningen i development avslutas
skriptet med kod 3; synken för över raden inom tio minuter, och spegelns
gallring kör inte skarpt utan en färsk överföring (migration 147). Samma
kommando igen skriver om raden i spegeln; det ändrar ingenting i main.

## Vad som INTE raderas, och varför

En rad i `suppressions` är kvar. Den innehåller adressen, men den finns just
för att adressen ALDRIG ska kontaktas igen — raderar man den försvinner
skyddet, och nästa körning kallmejlar samma person.

Att behålla den kräver ETT AKTIVT STEG, inte bara att man låter bli att
radera: `suppressions.contact_id` kaskaderar från `contacts`, så en radering
av kontakten hade tagit med sig avregistreringen på vägen. Skriptet nollar
kopplingen först. Upptäckt 2026-08-24 genom att läsa främmande nycklar i
databasen, inte genom att läsa koden — kaskaden syns inte på anropsstället. Det är den ena
undantagssituation där ett berättigat intresse väger tyngre än radering, och
den ska kunna förklaras för den som frågar. Skriptet säger det uttryckligen i
utskriften i stället för att tiga om det.

Kvitton (`bk_underlag`) är bokföringsunderlag och behålls också. Allt i
MANUELLT och alla fritextträffar raderas inte heller: där är det oklart vad
raderingen tar med sig, och då är en ärlig lista bättre än en gissning.

Förteckningen hålls i fas med schemat av tests/test_gdpr_radera.py, som läser
migrationerna och fäller en ny kolumn som ser ut som en personuppgift.
"""

from __future__ import annotations

import argparse
import json
import sys

import psycopg2

import begransning_spegel
from gdpr_verktyg import DAGENS_MILJOER, ENVIRONMENTS, dsn_for

begransning_dsn = dsn_for  # utbytbar i testerna

#: Underfrågor som pekar ut personens rader i föräldratabellerna. Samma villkor
#: som i TABELLER, så att utdraget och raderingen talar om samma rader.
_MEJL = "select id from ss_emails where lower(from_email) = lower(%s)"
_KUND = (
    "select customer_id from ss_customer_identifiers "
    "where type = 'email' and lower(value) = lower(%s)"
)
_KONTAKT = "select id from contacts where lower(email) = lower(%s)"
_PROSPEKT = "select id from prospects where lower(contact_email) = lower(%s)"
_TRAD = f"select id from outreach_threads where prospect_id in ({_PROSPEKT})"
_ARENDE = f"select id from ss_tickets where customer_id in ({_KUND})"
#: Felrapporterna ur Hjälprutan (156) bär ingen mejladress, bara rapportörens
#: användar-id. Vägen från adressen går därför genom auth.users.
_FELRAPPORT = (
    "select id from plattformsarenden where rapportor_user_id in "
    "(select id from auth.users where lower(email) = lower(%s))"
)

#: Var en e-postadress kan förekomma. Kolumnnamnet är inte samma överallt,
#: därför en explicit karta i stället för en gissning. Andra fältet är en
#: kolumn (jämförs skiftlägesokänsligt) eller ett färdigt villkor med `%s`.
#:
#: LISTAN MÅSTE VÄXA MED SCHEMAT. Läggs en tabell till som bär en
#: mejladress och den inte står här, så raderar det här skriptet inte allt —
#: och rapporterar ändå "klart". tests/test_gdpr_radera.py fäller det.
#:
#: ORDNINGEN ÄR RADERINGSORDNINGEN. `ss_emails.ticket_id` saknar kaskad, så
#: personens mejl måste vara borta innan `ss_customers` tar med sig ärendena.
TABELLER = [
    ("ss_emails", "from_email", "Inkommande kundmejl (bilagor, klassificeringar, utkast och beslutslogg följer med i kaskaden)."),
    ("contacts", "email", "Kontaktperson i leads-databasen."),
    ("prospects", "contact_email", "Prospekt. Trådar, meddelanden, kö, demolänkar, anteckningar, uppgifter, statuslogg, samtal och källor kaskaderar härifrån."),
    ("lead_list_items", "contact_email", "Listrad (sökt, kombinerad, importerad eller från CRM)."),
    ("ss_avregistreringslankar", "email", "Avregistreringslänk."),
    ("workspace_invites", "email", "Inbjudan till en arbetsyta som aldrig accepterades."),
    ("saljlista", "kontaktmail", "Säljlistan (kontaktperson, nummer, anteckningar)."),
    ("demo_requests", "epost", "Demoförfrågan från webbplatsen."),
    ("ss_customer_contacts", "mejl", "Kontaktperson hos en kund i kundregistret."),
    ("ss_customers", f"id in ({_KUND})", "Chatt- och supportkund. Identifierare, ärenden, meddelanden, kundminne, chattläge och kanalkontakter kaskaderar härifrån."),
    ("plattformsarenden", f"id in ({_FELRAPPORT})", "Felrapport ur Hjälprutan (namn, fritext, bild). Händelserna kaskaderar härifrån."),
]

#: Raderas ALDRIG. Se docstringen.
BEHALLS = [
    ("suppressions", "email", "Spärrlistan — raderas den kontaktas personen igen."),
    ("bk_underlag", "position(lower(%s) in lower(coalesce(mejl_avsandare, ''))) > 0",
     "Kvitto inläst från mejl. Kundens bokföringsunderlag (7 år, BFL 7 kap. 2 §) — begäran går till kunden."),
    ("behandlingsbegransningar", "email",
     "Begränsning av behandlingen (art. 18). Hävs med --hav-begransning, raderas inte."),
]

#: Försvinner i kaskaden när raden i föräldern (tredje fältet) raderas. De
#: raderas alltså inte här en och en, men de hör till utdraget och räknas i
#: sökningen. Testet kontrollerar att kaskaden finns i migrationerna.
KASKAD = [
    ("ss_email_attachments", f"email_id in ({_MEJL})", "ss_emails"),
    ("ss_classifications", f"email_id in ({_MEJL})", "ss_emails"),
    ("ss_drafts", f"email_id in ({_MEJL})", "ss_emails"),
    ("ss_human_reviews", f"draft_id in (select id from ss_drafts where email_id in ({_MEJL}))", "ss_emails"),
    ("ss_decision_log", f"email_id in ({_MEJL})", "ss_emails"),
    ("prospect_sources", f"prospect_id in ({_PROSPEKT})", "prospects"),
    ("outreach_threads", f"prospect_id in ({_PROSPEKT})", "prospects"),
    ("outreach_messages", f"thread_id in ({_TRAD})", "prospects"),
    ("send_queue", f"thread_id in ({_TRAD})", "prospects"),
    ("ss_demolankar", f"thread_id in ({_TRAD})", "prospects"),
    ("ss_demolank_handelser", f"token in (select token from ss_demolankar where thread_id in ({_TRAD}))", "prospects"),
    ("lead_anteckningar", f"prospect_id in ({_PROSPEKT})", "prospects"),
    ("lead_uppgifter", f"prospect_id in ({_PROSPEKT})", "prospects"),
    ("prospect_status_logg", f"prospect_id in ({_PROSPEKT})", "prospects"),
    ("lead_samtal", f"prospect_id in ({_PROSPEKT})", "prospects"),
    # Konversationens händelser (149): ett mejl utanför Snajp bär sin text i detalj.
    ("lead_handelser", f"prospect_id in ({_PROSPEKT})", "prospects"),
    ("ss_customer_identifiers", f"customer_id in ({_KUND})", "ss_customers"),
    ("ss_tickets", f"customer_id in ({_KUND})", "ss_customers"),
    ("ss_conversations", f"ticket_id in ({_ARENDE})", "ss_customers"),
    ("ss_messages", f"conversation_id in (select id from ss_conversations where ticket_id in ({_ARENDE}))", "ss_customers"),
    ("customer_memory", f"customer_id in ({_KUND})", "ss_customers"),
    ("ss_chat_state", f"customer_id in ({_KUND})", "ss_customers"),
    ("ss_channel_contacts", f"customer_id in ({_KUND})", "ss_customers"),
    ("plattformsarende_handelser", f"arende_id in ({_FELRAPPORT})", "plattformsarenden"),
]

#: Hittas och lämnas ut, men raderas INTE av skriptet: kräver manuellt beslut.
#: Id:na skrivs ut före raderingen, för flera av dem förlorar sin koppling
#: till personen när prospektet eller kontakten raderas (on delete set null).
MANUELLT = [
    ("agent_runs", f"prospect_id in ({_PROSPEKT}) or thread_id in ({_TRAD})",
     "Körningsloggar med hela promptar och svar (input, output, step_log). Kopplingen nollas vid radering."),
    ("generated_emails", f"contact_id in ({_KONTAKT})",
     "Genererade säljmejl. contact_id nollas vid radering; texten kan bära namnet."),
    ("leads_job_ledger", f"prospect_id in ({_PROSPEKT})",
     "Jobbliggaren. prospect_id saknar främmande nyckel och blir hängande; korning kan bära namn."),
    ("trial_paminnelser", "skickad_till", "Provperiodspåminnelse till kontots adress. Hör till kontot (admin_cleanup)."),
    ("platform_admin_bootstrap", "email", "Plattformsadmin. Hör till kontoflödet."),
    ("ss_customer_details", "faktureringsmejl", "Kundens faktureringsuppgifter. Avtal och fakturering — beslut per kund."),
    ("ss_mailboxes", "address", "Kundens kopplade brevlåda. Kopplas bort i kundens inställningar."),
    ("ss_sending_domains", "reply_to", "Kundens svarsadress för utskick."),
]

#: Löptext där adressen kan stå utan egen kolumn. Söks bara med --fritext
#: (en helskanning per tabell). Träffarna raderas aldrig automatiskt.
FRITEXT = [
    ("agent_runs", "concat_ws(' ', input, output, step_log::text, grounding::text)"),
    ("agent_feedback", "concat_ws(' ', comment, corrected_output)"),
    ("agent_evals", "concat_ws(' ', input, approved_output)"),
    ("agent_suggestions", "content::text"),
    ("platform_events", "concat_ws(' ', message, detail::text)"),
    ("leads_job_ledger", "concat_ws(' ', korning::text, error)"),
    ("audit_logs", "metadata::text"),
    ("generated_emails", "concat_ws(' ', subject, body)"),
    ("email_events", "metadata::text"),
    ("outreach_messages", "concat_ws(' ', subject, body)"),
    ("ss_emails", "body_text"),
    ("ss_messages", "content"),
    ("ss_drafts", "content"),
    ("ss_human_reviews", "concat_ws(' ', edited_content, note)"),
    ("ss_decision_log", "detail::text"),
    ("customer_memory", "fakta"),
    ("prospects", "concat_ws(' ', motivering, lagesbeskrivning, jev::text, signaler::text)"),
    ("lead_list_items", "concat_ws(' ', utkast::text, kallor::text)"),
    ("lead_anteckningar", "text"),
    ("lead_samtal", "anteckning"),
    ("saljlista", "anteckningar"),
    ("demo_requests", "meddelande"),
    ("leads_sidcache", "innehall"),
    ("prompt_lager", "text"),
]

#: Tabeller som KAN bära adressen i löptext utan att ha en egen adresskolumn
#: och som skriptet inte når alls. De ska nämnas i svaret till den
#: registrerade, för att ett registerutdrag som utelämnar dem är ofullständigt.
NAMNS_MANUELLT = [
    ("auth.users", "Konto hos oss (och profiles.full_name). Radering av ett KONTO är ett eget "
                   "flöde och görs inte härifrån — se scripts/admin_cleanup.py."),
]

#: Kopior som skriptet INTE når. Skrivs ut efter utdrag och radering, en rad
#: per kopia, så att den som handlägger begäran vet vad som återstår.
KOPIOR_SOM_INTE_NAS = [
    "Redis: jobbkön och cachen (kort livslängd) nås inte — kontrollera att inga köade jobb rör personen.",
    "development-spegeln: synkas från main; raderingar förs över vid nästa synk bara för tabellerna i "
    "railway_synk.SYNK (synk_raderingar). Övrigt måste raderas där separat.",
    "Schemana synk_kopia_<tid> i main och development (kopior före första synken) nås inte.",
    "Säkerhetskopior hos driftleverantören (Railway) nås inte — raderingen måste göras om vid en återställning.",
    "Den gamla Supabase-databasen nås inte (avsiktligt, den skrivs aldrig till) — kräver ett eget beslut.",
]

#: En rad identifieras med sin primärnyckel, vad den än heter.
_RADID = ("coalesce(to_jsonb(t)->>'id', to_jsonb(t)->>'job_id', to_jsonb(t)->>'hash', "
          "to_jsonb(t)->>'token', to_jsonb(t)->>'url', to_jsonb(t)->>'tenant_id')")


def _villkor(kolumn: str) -> str:
    """En kolumn jämförs skiftlägesokänsligt; ett villkor med `%s` används som det står."""
    return kolumn if "%s" in kolumn else f"lower({kolumn}) = lower(%s)"


def _param(villkor: str, epost: str) -> tuple[str, ...]:
    return (epost,) * villkor.count("%s")


def _sok(cur, epost: str) -> dict[str, int]:
    fynd: dict[str, int] = {}
    for tabell, kolumn, *_ in TABELLER + BEHALLS + KASKAD + MANUELLT:
        villkor = _villkor(kolumn)
        try:
            cur.execute(f"select count(*) from {tabell} where {villkor}", _param(villkor, epost))
            fynd[tabell] = cur.fetchone()[0]
        except psycopg2.errors.UndefinedTable:
            # Tabellen finns inte i den här miljön. Inte ett fel, men den ska
            # synas som OKÄND och inte som noll — skillnaden mellan "inget
            # hittat" och "kunde inte titta" är hela svaret.
            cur.connection.rollback()
            fynd[tabell] = -1
        except psycopg2.errors.UndefinedColumn:
            # Kolumnen finns inte. Det ÄR ett fel: kartan ovan har glidit isär
            # från schemat, och då raderar skriptet mindre än det påstår.
            #
            # Det hände: `outreach_threads` stod med kolumnen `prospect_email`,
            # som aldrig funnits — tråden länkar via `prospect_id`. Den gamla
            # felhanteringen fångade båda felen i samma gren och rapporterade
            # "okänd tabell", vilket dolde att kartan var fel.
            cur.connection.rollback()
            fynd[tabell] = -2
    return fynd


def _fritext(cur, epost: str) -> dict[str, list]:
    """Rad-id per tabell där adressen står i löptext. -1/-2 som i `_sok`."""
    ut: dict[str, list] = {}
    for tabell, uttryck in FRITEXT:
        try:
            cur.execute(
                f"select {_RADID} from {tabell} t where position(lower(%s) in lower({uttryck})) > 0",
                (epost,),
            )
            ut[tabell] = [rad[0] for rad in cur.fetchall()]
        except psycopg2.Error:
            cur.connection.rollback()
            ut[tabell] = ["kunde inte söka (tabell eller kolumn saknas)"]
    return ut


def _export(cur, epost: str) -> dict:
    ut: dict[str, list] = {}
    for tabell, kolumn, *_ in TABELLER + BEHALLS + KASKAD + MANUELLT:
        villkor = _villkor(kolumn)
        try:
            cur.execute(f"select to_jsonb(t) from {tabell} t where {villkor}", _param(villkor, epost))
            ut[tabell] = [rad[0] for rad in cur.fetchall()]
        except psycopg2.Error:
            cur.connection.rollback()
    return ut


def _manuella_id(cur, epost: str, fynd: dict[str, int]) -> dict[str, list]:
    ut: dict[str, list] = {}
    for tabell, kolumn, _ in MANUELLT:
        if fynd.get(tabell, -1) <= 0:
            continue
        villkor = _villkor(kolumn)
        cur.execute(f"select {_RADID} from {tabell} t where {villkor}", _param(villkor, epost))
        ut[tabell] = [rad[0] for rad in cur.fetchall()]
    return ut


def _skriv_kopior() -> None:
    print("\nKopior som det här skriptet INTE når:")
    for rad in KOPIOR_SOM_INTE_NAS:
        print(f"  - {rad}")


def _bekrafta(epost: str, atgard: str = "radering") -> None:
    """Adressen skrivs en gång till, för hand.

    Inte en `--force`-flagga: en flagga sitter kvar i shell-historiken och
    körs om av misstag. Att skriva adressen igen tvingar fram att man tittar
    på VILKEN adress som raderas, vilket är det enda felet som inte går att
    ångra här."""
    svar = input(f"Skriv adressen igen för att bekräfta {atgard} ({epost}): ").strip()
    if svar.lower() != epost.lower():
        sys.exit("AVBRYTER: adresserna stämmer inte överens. Ingenting ändrades.")


def _aktiv_begransning(cur, epost: str):
    """(id, skäl, begärd) för den aktiva begränsningen, None om ingen finns.
    Saknas tabellen (migration 124 inte körd) är det ett fel: då går varken
    att sätta eller pröva markeringen."""
    cur.execute(
        "select id, skal, begard_at from behandlingsbegransningar "
        "where lower(email) = lower(%s) and havd_at is null",
        (epost,),
    )
    return cur.fetchone()


def _senaste_begransning(cur, epost: str) -> dict | None:
    """Adressens senaste rad som JSON (den aktiva om en finns): det som speglas."""
    cur.execute(
        "select to_jsonb(b) from behandlingsbegransningar b where lower(email) = lower(%s) "
        "order by (havd_at is null) desc, begard_at desc limit 1",
        (epost.strip(),),
    )
    rad = cur.fetchone()
    return rad[0] if rad else None


def _begransning(cur, args) -> dict | None:
    """--begransa och --hav-begransning. Rör inga andra tabeller. Svarar med
    adressens senaste rad, som speglas till development (även när ingenting
    ändrades i main: det är omförsöket när spegeln missade förra gången)."""
    aktiv = _aktiv_begransning(cur, args.epost)
    if args.begransa:
        if aktiv:
            print(f"\nBegränsningen är redan aktiv sedan {aktiv[2]:%Y-%m-%d} ({aktiv[1]}). Ingen ändring.")
            return _senaste_begransning(cur, args.epost)
        cur.execute(
            "insert into behandlingsbegransningar (email, skal) values (lower(%s), %s) returning id",
            (args.epost.strip(), args.begransa.strip()),
        )
        print(f"\nBegränsning satt ({cur.fetchone()[0]}). Från och med nu:")
        print("  - inga utskick till adressen, hos någon kund (sändningsspärren);")
        print("  - inkommande mejl från adressen går till Att hantera utan AI.")
        print("Uppgifterna ligger kvar oförändrade. Utkast och research som redan finns rörs inte;")
        print("arkivera berörda leads i kundens vy om de inte ska ligga kvar som aktiva.")
    else:
        if not aktiv:
            print("\nIngen aktiv begränsning för adressen. Ingen ändring.")
            return _senaste_begransning(cur, args.epost)
        print("\nArt. 18.3: den registrerade ska ha informerats innan begränsningen hävs.")
        _bekrafta(args.epost, "hävning av begränsningen")
        cur.execute(
            "update behandlingsbegransningar set havd_at = now(), havd_skal = %s where id = %s",
            (args.hav_begransning.strip(), aktiv[0]),
        )
        print(f"Begränsningen hävd ({aktiv[0]}). Raden står kvar som belägg.")
    return _senaste_begransning(cur, args.epost)


def _spegla_till_development(rad: dict, epost: str) -> int:
    """Samma rad i development-spegeln, efter att main bekräftats. En hävd rad
    häver också en äldre aktiv rad för adressen som satts direkt i spegeln:
    spegeln ska visa main:s läge. Kod 3 om skrivningen faller."""
    try:
        with psycopg2.connect(begransning_dsn("railway-development")) as dev, dev.cursor() as cur:
            utfall = begransning_spegel.spegla_rad(cur, rad)
            if rad.get("havd_at"):
                cur.execute(
                    "update behandlingsbegransningar set havd_at = %s::timestamptz, havd_skal = %s "
                    "where lower(email) = lower(%s) and havd_at is null",
                    (rad["havd_at"], rad.get("havd_skal"), epost.strip()),
                )
    except (psycopg2.Error, SystemExit) as fel:
        orsak = type(fel).__name__ if isinstance(fel, psycopg2.Error) else str(fel)
        print(f"\nVARNING: markeringen kunde inte skrivas i development-spegeln ({orsak}).")
        print("Synken för över den inom tio minuter, och spegelns gallring kör inte skarpt")
        print("utan en färsk överföring (migration 147). Kör samma kommando igen för att försöka nu.")
        return 3
    if utfall == "krock":
        print("\nDevelopment-spegeln har redan en egen aktiv begränsning för adressen; den står kvar.")
    else:
        print("\nSamma markering skriven i development-spegeln.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--env", required=True, choices=sorted(ENVIRONMENTS),
        help=f"{' eller '.join(DAGENS_MILJOER)}. 'production' och 'preview' är den gamla "
             "stacken och godtas bara mot en lokal databas (scripts/lokal_stack.py).",
    )
    parser.add_argument("--epost", required=True)
    parser.add_argument("--export", action="store_true", help="Skriv ut allt som JSON.")
    parser.add_argument("--fritext", action="store_true", help="Sök också adressen i löptext (dyrt).")
    lage = parser.add_mutually_exclusive_group()
    lage.add_argument("--radera", action="store_true", help="Radera. Kräver bekräftelse.")
    lage.add_argument("--begransa", metavar="SKÄL",
                      help="Begränsa behandlingen (art. 18): stoppar utskick och automatisk behandling.")
    lage.add_argument("--hav-begransning", metavar="SKÄL",
                      help="Häv en aktiv begränsning. Kräver bekräftelse.")
    args = parser.parse_args()
    for flagga in ("begransa", "hav_begransning"):
        if getattr(args, flagga) is not None and not getattr(args, flagga).strip():
            parser.error("ett skäl krävs")

    with psycopg2.connect(dsn_for(args.env)) as conn, conn.cursor() as cur:
        fynd = _sok(cur, args.epost)

        print(f"\n{args.epost} i miljön {args.env}:\n")
        avsnitt = [
            ("Raderas med --radera:", TABELLER),
            ("Följer med i kaskaden:", KASKAD),
            ("Behålls med flit:", BEHALLS),
            ("Kräver manuellt beslut (raderas inte):", MANUELLT),
        ]
        for rubrik, lista in avsnitt:
            print(f"  {rubrik}")
            for tabell, _, beskrivning in lista:
                antal = fynd.get(tabell, -1)
                if antal == -2:
                    markering = "FEL: kolumn"
                elif antal < 0:
                    markering = "okänd tabell"
                else:
                    markering = f"{antal} rader"
                if lista is KASKAD:
                    beskrivning = f"(från {beskrivning})"
                print(f"    {tabell:<28} {markering:<16} {beskrivning}")

        if any(v == -2 for v in fynd.values()):
            print(
                "\n  FEL ovan betyder att tabellkartan i det här skriptet inte "
                "stämmer med schemat.\n  Radera INTE förrän den är rättad — "
                "skriptet raderar då mindre än det rapporterar."
            )

        try:
            aktiv = _aktiv_begransning(cur, args.epost)
            print("\n  Begränsning av behandlingen (art. 18): "
                  + (f"AKTIV sedan {aktiv[2]:%Y-%m-%d} ({aktiv[1]})" if aktiv else "ingen aktiv"))
        except psycopg2.errors.UndefinedTable:
            cur.connection.rollback()
            print("\n  Begränsning av behandlingen (art. 18): okänd (migration 124 saknas i miljön)")

        print("\n  Söks inte automatiskt, men hör till svaret:")
        for tabell, beskrivning in NAMNS_MANUELLT:
            print(f"    {tabell:<26} {beskrivning}")

        fritext = _fritext(cur, args.epost) if args.fritext else {}
        if args.fritext:
            print("\n  Adressen i löptext (kräver manuellt beslut, raderas inte):")
            for tabell, rader in fritext.items():
                if rader:
                    print(f"    {tabell:<26} {len(rader)} rader: {', '.join(map(str, rader[:20]))}")
        else:
            print("\n  Löptext (promptar, loggar, mejltexter) söktes inte. Lägg till --fritext.")

        if args.export:
            utdrag = _export(cur, args.epost)
            if args.fritext:
                utdrag["fritext_kraver_manuellt_beslut"] = fritext
            print("\n--- REGISTERUTDRAG (JSON) ---")
            print(json.dumps(utdrag, indent=2, ensure_ascii=False, default=str))

        if args.begransa is not None or args.hav_begransning is not None:
            rad = _begransning(cur, args)
            conn.commit()  # main först: spegeln får aldrig ett läge main inte har
            if rad is not None and args.env == "railway-main":
                return _spegla_till_development(rad, args.epost)
            return 0

        if not args.radera:
            print("\nIngenting raderades. Lägg till --radera för att göra det.")
            if args.export:
                _skriv_kopior()
            return 0

        _bekrafta(args.epost)

        if any(v == -2 for v in fynd.values()):
            sys.exit(
                "AVBRYTER: tabellkartan stämmer inte med schemat (FEL ovan). "
                "Rätta den först — annars raderas mindre än vad som rapporteras."
            )

        # Före raderingen: flera manuella rader förlorar kopplingen till
        # personen när prospektet eller kontakten försvinner (set null).
        for tabell, rader in _manuella_id(cur, args.epost, fynd).items():
            print(f"  KRÄVER MANUELLT BESLUT {tabell}: {', '.join(map(str, rader))}")

        # SPÄRRLISTAN FÖRST. `suppressions.contact_id` kaskaderar från
        # `contacts`, så en radering av kontakten hade tyst tagit med sig
        # avregistreringen — alltså precis det skydd det här skriptet lovar
        # att behålla, borttaget av den åtgärd som skulle skydda personen.
        #
        # Kopplingen nollas i stället. Raden blir kvar med adressen och sin
        # tenant, vilket är allt `send_guard` regel 3 behöver.
        cur.execute(
            """
            update suppressions set contact_id = null
             where contact_id in (select id from contacts where lower(email) = lower(%s))
            """,
            (args.epost,),
        )
        if cur.rowcount:
            print(f"  suppressions: kopplade loss {cur.rowcount} rader så de överlever")

        totalt = 0
        for tabell, kolumn, _ in TABELLER:
            if fynd.get(tabell, -1) <= 0:
                continue
            villkor = _villkor(kolumn)
            cur.execute(f"delete from {tabell} where {villkor}", _param(villkor, args.epost))
            print(f"  {tabell}: raderade {cur.rowcount} rader")
            totalt += cur.rowcount

        kaskad = sum(max(fynd.get(tabell, 0), 0) for tabell, *_ in KASKAD)
        print(f"\nKlart. {totalt} rader raderade, och {kaskad} rader med dem i kaskaden.")
        print(
            "Kvar med flit: raden i suppressions. Den bär adressen, men den är "
            "skyddet mot att personen kontaktas igen — raderas den försvinner "
            "skyddet. Det ska stå i svaret till den registrerade."
        )
        print("Kvar: kvitton (bokföringsunderlag) och raderna under KRÄVER MANUELLT BESLUT ovan.")
        _skriv_kopior()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
