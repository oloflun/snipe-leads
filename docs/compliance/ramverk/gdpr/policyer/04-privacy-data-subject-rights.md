# Privacy & Data-Subject Rights

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); begäransloggen kvartalsvis |
| Ramverkets mall | `frk_pt_685e410082a807a0274b4531` (avdelning `gov`) |
| Täcker kontroller | Lawful Basis Register (`frk_ct_69e918e7f403f696c2577de1`), Privacy Notice (`frk_ct_69e918e7f7739946f5034799`), Data Subject Rights Request Workflow (`frk_ct_69e918eb724c553d2e5749ea`), Automated Decision-Making Safeguards (`frk_ct_69e918eb8f6e80605d3fa3e5`) |
| Täcker krav | LBT-2, LBT-3, PR-1 till PR-7 |

## Syfte

Personuppgifter ska behandlas med en rättslig grund, de registrerade ska veta vad som händer, och deras begäranden ska besvaras i tid.

## Omfattning

Två roller med olika skyldigheter:

- **Snajp som ansvarig:** konton, egna kallmejl (leadsagenten för Snajp), support till egna kunder, webbpoolen (`docs/registerforteckning.md` A1–A3).
- **Snajp som biträde:** kundens kunders mejl och chattar, kundernas leadsutskick, kvitton (registerförteckningen B1–B3). Här är det kunden som svarar den registrerade. Snajp hjälper kunden (`docs/pub-avtal.md` §7).

## Rättslig grund och minimering (LBT-2)

- Registret över rättsliga grunder är `docs/registerforteckning.md`. Konton: avtal (6.1 b). Egna kallmejl: berättigat intresse (6.1 f) med intresseavvägningen i `docs/intresseavvagning_kallmejl.md`. Den är ett ogranskat utkast och ska läsas av jurist och beslutas av Anton, [FYLL: datum] (JURIDIK_ATGARDER #7).
- Supporten till egna kunder har i dag två grunder angivna ("avtal / berättigat intresse"). Anton väljer en, [FYLL: datum].
- En ny behandling får inte starta innan den har en rad i registerförteckningen med rättslig grund.
- Formulär och API:er ses över en gång per år för fält som inte används.

## Integritetspolicy (LBT-3)

- Publik på `/integritetspolicy` på svenska och engelska.
- Den ska uppdateras inom 30 dagar efter en väsentlig ändring av behandlingen. Kända fel som ska rättas före första kund, ansvarig agent efter Antons beslut:
  - Den lovar 24 månaders automatisk, loggad gallring som inte körs (`app/integritetspolicy/IntegritetspolicySida.tsx:86-90`; JURIDIK_ATGARDER #8).
  - Org.nr och adress saknas (`lib/bolag.ts:41-42`; #5).
  - Rätten till begränsning, rätten till dataportabilitet och rätten att återkalla samtycke nämns inte (rad 92-95).
  - Demolänkens spårning per mottagare nämns inte, och cookiesidan säger att beteende inte mäts (#17).
  - Datum för senaste ändring visas inte, och texten är inte juristgranskad (#7).
- Gamla versioner finns i git-historiken. Det räcker som arkiv.

## Begäranden från registrerade (PR-1 till PR-6)

**Kanal.** Den registrerade skriver till dataskyddsadressen. Den är `kontakt@snajp.se` tills `integritet@snajp.se` finns (`lib/bolag.ts:79`). Avregistrering från utskick sker med länken i varje mejl och gäller direkt (`app/avregistrera/[token]/page.tsx`).

**Så går det till:**

1. Anton bekräftar mottagandet och skriver in begäran i loggen samma arbetsdag.
2. Identiteten kontrolleras: svaret skickas bara till den adress uppgifterna gäller, eller efter en kontrollfråga om begäran kommer från en annan adress.
3. Gäller begäran en kunds kunder hänvisas den registrerade till kunden, och kunden underrättas utan dröjsmål.
4. Svar inom en månad. Förlängning med högst två månader meddelas inom den första månaden, med skäl.
5. Utfall och datum skrivs i loggen.

**Verktyg per rättighet:**

| Rättighet | Verktyg i dag | Status |
|---|---|---|
| Tillgång (PR-1) | `scripts/gdpr_radera.py` sökläge och `--export` | Finns men har aldrig körts mot en verklig begäran. Utökningen till nya tabeller är inte committad |
| Rättelse (PR-2) | Ingen rutin. Rättas för hand i adminytan eller databasen | Rutin ska skrivas, [FYLL: datum], ansvarig agent |
| Radering (PR-3) | `gdpr_radera.py --radera`. Spärrlistan och kvitton behålls, med skäl | Aldrig körd skarpt. Når inte testmiljön, Redis eller den gamla Supabase-databasen |
| Begränsning (PR-4) | Inget | Ska lösas, till exempel genom att markera kontakten som spärrad utan att radera, [FYLL: datum], ansvarig agent |
| Portabilitet (PR-5) | `--export` ger JSON | Gäller bara uppgifter som personen själv lämnat, med avtal eller samtycke som grund |
| Invändning (PR-6) | Avregistreringslänken; spärren gäller hela kunden och överlever radering (`send_guard.py:288-329`) | Fungerar för direktmarknadsföring. Invändning mot annan behandling görs via dataskyddsadressen |

**Loggen.** Begäranden loggas i `docs/compliance/loggar/begaranden.md` (inte i det publika repot): datum in, vem, rättighet, identitetskontroll, svarsdatum, utfall. Loggen finns inte än; den ska läggas upp [FYLL: datum], ansvarig Anton. Den sparas i tre år.

## Samtycke

Snajp bygger i dag ingen behandling på samtycke. Cookiesidan lovar en samtyckesruta innan någon icke-nödvändig cookie sätts (`app/cookies/CookiesSida.tsx`). Demolänkens `sessionStorage`-mätning är inte bedömd mot LEK 9 kap. 28 §; Anton beslutar (JURIDIK_ATGARDER #17).

## Automatiserade beslut (PR-7)

- Bedömningen står i `../matris.md` (PR-7) och `docs/dpia_supportagenten.md` §4.
- Supportagenten levereras med Utkast i varje kategori. Kunden kan ställa en kategori på Auto, och då bär kunden bedömningen enligt art. 22 (`app/villkor/VillkorSida.tsx`; `docs/pub-avtal.md` 13.4).
- Vid onboarding gås autonominivån igenom med kunden, och kunden bekräftar valet skriftligt (`docs/pilot_onboarding.md`, steg 6).
- **Ska införas:** en kodstyrd AI-upplysning i chattens första svar och i varje automatiskt skickat mejlsvar (JURIDIK_ATGARDER #12), [FYLL: datum], ansvarig agent efter Antons ja. Den ger också den registrerade en väg att be om en människa.

## Register och spårbarhet

- Registerförteckningen (art. 30) ska ange kategorier, ändamål, grund, mottagare, överföringar och skydd. Den finns men saknar de flesta lagringstider.
- Begäransloggen sparas i tre år.

## Mätning

Varje kvartal: registerförteckningen stämmer med koden, policyn stämmer med registerförteckningen, och alla begäranden besvarades i tid.

## Undantag

Förlängd svarstid och avslag dokumenteras med skäl i loggen.

## Brister

Missad frist eller behandling utan rad i registerförteckningen hanteras enligt incidentpolicyn och tas upp av Anton.

## Förbättring

Policyn och integritetspolicyn uppdateras efter frågor från registrerade, kunder och IMY.
