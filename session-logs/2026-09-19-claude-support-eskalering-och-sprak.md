# Sessionslogg — 2026-09-18/19 — Support-agentens eskalering, överlämning och språk (Ebbot-modellen)

## Sammanfattning
Sebbe bad om en kvalitetshöjning av Support-agenten med konkurrenten Ebbot som förebild. Den här sessionen gjorde först en kort research av Ebbots produktsidor, dokumentation och demochatt (godkänd av Sebbe), och byggde sedan fyra saker: fasta eskaleringsregler i kod, sömlös överlämning i samma chattfönster med en ny medarbetarvy (Chattar) i supportportalen, inställningar per kund, samt en faktagrind och svar på kundens språk. Allt ligger på `development` och är testat som kund på dev med den riktiga modellen. Release-PR:en development → main (#22) är skapad; migrationerna och integrationsnyckeln är klara i main, så den väntar bara på Antons merge.

## Vad som ändrades

### Nya filer
- `snajp-support/app/agent/support_regler.py` — kundens regler (eskalering, tonläge, faktakontroll, ämnesområde, språk), orsakskoder för överlämning, igenkänning av "jag vill prata med en människa" och "ja" på agentens erbjudande.
- `snajp-support/app/agent/support_faktagrind.py` — faktagrinden: kontaktuppgifter, siffror och löften måste finnas i kunskapsbasen, med tre nivåer per kund.
- `snajp-support/app/agent/support_texter.py` — de fasta replikerna (kvittens, överlämning, osäkerhet) på svenska och engelska.
- `snajp-support/app/agent/overlamning.py` — medarbetarens sida: hela samtalsutskriften, medarbetarens svar, återlämning till agenten.
- `snajp-support/app/api/chattar.py` — `GET/POST /api/chattar…` för portalens Chattar-vy.
- `snajp-support/app/api/support_config.py` — `GET/PUT /api/support/config`, kundens regler.
- `supabase/migrations/066_support_samtalslage.sql` — tabellen `ss_chat_state` (samtalsläge per kund) och kolumnen `ss_messages.author`.
- `app/api/snajp-support/chat/samtal/route.ts` (anonym, allowlistad i INV-SEC-010) och `.../testchatt/samtal/route.ts` — chattfönstrets hämtning av sitt eget samtal.
- `support-webb/components/vyer/ChattarVy.tsx` + `support-webb/app/(portal)/chattar/page.tsx` — medarbetarens vy.
- `components/settings/SupportEskalering.tsx` — inställningspanelen under Regler.
- `snajp-support/lokal_support.py` — lokal backend med fejkmodell på port 8000 och 8010 i samma process, för att prova hela flödet utan nycklar.
- Tester: `tests/agent/test_support_eskalering.py`, `tests/agent/test_support_sprak.py`, `tests/api/test_chattar_api.py`.

### Ändrade filer
- `snajp-support/app/agent/support_agent.py` — beslutslogiken (fyra svarslägen, fasta triggers, räknare för misslyckade rundor), överlämningsvägen utan LLM, faktagrinden med reparationsrunda, språkstödet, samtalsläget. Kanalsessionen har kokat in sina krokar och rättningar i samma fil.
- `snajp-support/app/storage/{base,memory,postgres}.py` — samtalsläge, `find_customer`, `author` på meddelanden, `sprak`.
- `snajp-support/app/api/{chat,schemas}.py`, `app/main.py`, `app/minne/arbetsminne.py` — den publika samtalshämtningen, nya scheman, routrar, medarbetarens repliker märkta "Kollegan".
- `components/snajp/SupportChat.tsx` — pollar medarbetarens svar efter en överlämning, återställer samtalet vid omladdning, etiketten "Medarbetare", höger-till-vänster-text.
- `agent-core/overlays/support-conversation.md` — uttrycklig osäkerhet, nästa steg, överlämningens form.
- `ARCHITECTURE_INVARIANTS.md` — ny invariant INV-ESC-001.
- `support-webb/components/Sidebar.tsx`, `support-webb/lib/api.ts`, `components/WorkspaceViews.tsx`, `tests/invariants/test_inv_sec_010.py`, `.claude/launch.json`.

### Flyttat/raderat
- Inget.

## Beslut
- **Eskalering avgörs i kod, inte av modellen.** Modellen levererar signaler; koden fattar beslutet mot kundens gränser — samma princip som påhoppsgrinden. Skäl: ett beslut att lämna över ska inte gå att prata bort.
- **"Jag vill prata med en människa" är en trigger.** Tidigare kunde eskaleringssteget rösta nej. Ett befintligt test som krävde det skrevs om med datum och motivering.
- **Standardvärdena ger samma beteende som förut.** En kund som aldrig rör inställningarna märker ingen skillnad utöver de nya triggerna.
- **Utanför ämnet: standard är "erbjud en människa", inte överlämning.** En väderfråga ska inte pinga en medarbetare. Kunden kan välja "lämna över direkt".
- **Överlämnat samtal gäller i 24 timmar från senaste livstecken.** Sedan tar agenten nya meddelanden igen, så en kund som återvänder efter två dygn får svar.
- **Chattfönstret hämtar medarbetarens svar genom pollning** (4 s de första två minuterna, sedan 10 s, max 30 min). Enkelt och robust. Den anonyma hämtningen läser bara tillbaka slumpade sessionsidentiteter, aldrig en gissningsbar mejladress.
- **Faktagrinden är deterministisk och jämför talets storlek, inte enheten.** Två falsklarm i kundtestet ("14:00" och "3,990 SEK") visade att enhets- och formatjämförelse stryker korrekta svar.
- **Svar på kundens språk är standard.** Kunskapsbasen söks på svenska. Den svenska humaniseraren hoppas över på andra språk, eftersom den hade översatt tillbaka.
- **Kanaler och integrationer gjordes av en annan session** på Sebbes uttryckliga order, inte här.
- **Medarbetarsidan testades på dev via portalens API, inte via inloggat gränssnitt.** Jag loggar inte in med någons uppgifter och förfalskar inte en sessionskaka. Gränssnittet testades lokalt.

## Kontext och diskussion
- Ebbot-researchen: deras styrka är ramverket (regler per kund, överlämning som inbyggd funktion, orsak per överlämning). I praktiken saknade deras demochatt tak för förtydliganden och märkte inte frustration. Därför räknas "fattar du inte?" hos oss.
- Sebbes gränser: inga visuella ändringar på hemsidan, utom där det krävs för funktionen (godkänt). Chattar-vyn, inställningspanelen och medarbetaretiketten är de frontendändringar som gjordes.
- Tre sessioner arbetade parallellt i samma arbetsträd: den här, "Flera kanaler och integrationer" och mot slutet "Marknadsföring: Dashboard och agent-optimering". Samordning skedde via meddelanden, med filspärrar och commits med explicita sökvägar.
- **Två misstag från min sida:** jag skrev av misstag två gånger i `support_agent.py` medan kanalsessionen ägde filen. Båda gångerna återställdes filen inom sekunder, byte för byte, och sessionen fick veta det.
- Testeskaleringar på dev i Snajps egen tenant skickade troligen interna larmmejl till Snajps inkorg. Testsamtalen är återlämnade.
- Kundtesterna (mina och kanalsessionens) hittade sex fel som alla är rättade och omverifierade på dev. Två av dem kom från min språkpatch: kraschen när modellen gav utkastet som ett objekt, och mejlmallsformatet på engelska.

## Öppna trådar
- **PR #22 till main väntar bara på Antons merge.** Stegen före merge är klara: 066, 067 och 068 är körda mot main (verifierat med torrkörning vid sessionens slut), och `INTEGRATION_NYCKEL` finns i main. Efter mergen körs `python scripts/verify_railway.py`. Pushar marknadssessionen en migration 069 före mergen måste den också köras mot main först.
- **Marknadssessionens arbete** (textstädning, webbplatsskanning till kunskapsbasen med migration 069, tokenöversyn) var inte klart vid sessionens slut. Den sessionen pushar själv och säger till Sebbe om 069.
- `snipe-v60`: ingen notis går till kundföretagets medarbetare vid eskalering, bara Snajps interna larm. Nästa steg: mejla användare med notisen "Eskalering" påslagen.
- `snipe-njh`: en överlämning som löper ut utan medarbetarsvar försvinner ur Chattar-listan. Nästa steg: lista obesvarade överlämningar även efter 24 timmar.
- `snipe-pgz`: den anonyma routen `POST /api/chat/samtal` saknar rate limit. Nästa steg: tak per IP som på `/api/chat`.
- Fasta repliker finns bara på svenska och engelska, och påhoppsspärrens svar bara på svenska.
- Supportportalens inloggade vyer är inte granskade på dev, bara lokalt.

## Överlämningar till andra projekt
- Inga den här sessionen.

## Läget efter sessionen
Support-agenten eskalerar enligt fasta regler per kund, lämnar över sömlöst i samma chatt och svarar på kundens språk, och allt är i drift på development (`5f1ef42`). Produktionen kör fortfarande `c3e4fbd`. Nästa steg är releasen: Antons merge och sedan en verifiering. Migrationerna och nyckeln i main är klara. Därefter är notisen till kundföretaget vid eskalering (`snipe-v60`) den viktigaste uppföljningen, eftersom en överlämning bara är sömlös om någon hos kunden får veta om den.

<!-- session-state
date: 2026-09-19
type: feature-build-and-release
files_created:
  - snajp-support/app/agent/support_regler.py
  - snajp-support/app/agent/support_faktagrind.py
  - snajp-support/app/agent/support_texter.py
  - snajp-support/app/agent/overlamning.py
  - snajp-support/app/api/chattar.py
  - snajp-support/app/api/support_config.py
  - supabase/migrations/066_support_samtalslage.sql
  - support-webb/components/vyer/ChattarVy.tsx
  - components/settings/SupportEskalering.tsx
  - snajp-support/lokal_support.py
files_modified:
  - snajp-support/app/agent/support_agent.py
  - snajp-support/app/storage/postgres.py
  - components/snajp/SupportChat.tsx
  - agent-core/overlays/support-conversation.md
  - ARCHITECTURE_INVARIANTS.md
decisions_made: 10
open_threads: 7
handoffs_pending: []
priority_changes: true
status_updated: true
goals_updated: yes
next_session_focus: "Verifiera produktionen efter Antons merge av PR #22, sedan snipe-v60 notis till kundföretaget vid eskalering"
session-state -->
