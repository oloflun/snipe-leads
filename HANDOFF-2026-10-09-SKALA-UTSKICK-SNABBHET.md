# Handoff 2026-10-09 — körningar på 30–50 leads, skicka alla, utkastkvalitet, snabbare flikbyten

Till Anton, från Sebbes arbete 2026-10-09 (tre Claude-sessioner i samma arbetsträd
plus en worktree för prestandan). Allt ligger på `development`; main är orörd.

## 1. Läget just nu (2026-10-10 ~00:05)

| | Läge |
|---|---|
| git | `origin/development` = `2866342`. 35 commits i dag, `5e189b7` … `d9028d6` (+ merge). |
| development | Allt driftsatt: leadskedjan (`2b96372`, provkörd), Kunder & Data-rättningen (`98ace85`) och prestandan (`368b0a9`, `0ea7196`, `11372cb`; flikbyten 0,15–0,6 s, inga konsolfel). |
| main | Orörd. Inga migrationer i dag (senaste är fortfarande 109). Main har kvar tokenbudgeten 2M/dygn. |
| Utskick | **73 utkast är godkända och köade** (Sebbe körde Markera alla → Skicka 20:33). De skickas måndag 08:00 — men bara om Snajps org.nr och adress finns i Kunder & Data, annars stoppar regel 1 alla. Se §3.1. |
| Railway-variabler (dev) | Tokenbudgeten per dygn höjd 2M → 8M. LEADS_WORKERS 10, DB_POOL_MAX 20, LEADS_LLM_SAMTIDIGA 4 är kodens standard. |
| ScrapeGraph | Free Plan, 276 krediter kvar (~45 leads). |

## 2. Vad som byggdes

### 2.1 Skicka alla (Sebbe: "Det måste gå att … markera och skicka alla samtidigt")

| Del | Commits |
|---|---|
| Godkänn och skicka tar stoppade utkast; alla spärrar prövas om; sidfoten läggs på vid godkännandet; provkörningsleads kan flyttas över i samma steg; beskedet grupperas per orsak med åtgärd | `5e189b7`, `bb50682` |
| Stoppat utan text = "Inget utkast"; 422 vid flytt säger vad som saknas | `461c8f1` |
| Massutskicket visar förlopp (Skickar 12/50) | `a8c06eb` |
| Skickat visar datum och klockslag; Avbryt körningen bekräftas på sidan; produktrubriken klipps inte; smal detaljvy | `b1388e1`, `bcbd051`, `3f9f4cb`, `4a3bdfa` |

### 2.2 Org.nr hämtas vid körningen ("SE TILL ATT ALLA INFO … SOM BEHÖVS HÄMTAS VID KÖRNING")

- Bolagets egen sajt läses vid flytten (`b6871d7`): bara uttryckligt org.nr med giltig
  kontrollsiffra, juridisk person, aldrig personnummer. Gav 4 av 19.
- Merinfos företagssökning (`d=c`, aldrig personer) via ScrapeGraph i JS-läge, 2 krediter
  (`606a5af`). Gav 18 av 19. Två möjliga bolag → inget nummer; enskilda firmor väljs aldrig.
- **Anton bör veta:** detta är en ny användning av merinfo (uppslag på bolagsnamn, inte bara
  filter). Agenten flaggade det som ditt beslut; Sebbe beslutade att bygga. Säg till om det
  ska stängas av.

### 2.3 Körningar på 30–50 leads, och snabbare (Sebbe: "kan inte ta 10–15 minuter")

| Problem (uppmätt i dev) | Åtgärd | Commit |
|---|---|---|
| 40 beställda gav 6: Luleå/Sundsvall/Skellefteå saknades i kommunregistret, max 30 kandidater per körning | Norrlands kommuner och 800–989; okänt område fäller aldrig; rundor och kredittak skalar med beställningen | `fd53feb` |
| 2–3 researchjobb åt gången | LEADS_WORKERS 3 → 10, databaspoolen 5 → 20; inkorgens matchning mot alla prospekt (inte 500 senaste) | `740d8a1` |
| Sökrundan höll körningens lås 3–5 min | Rundan körs utanför låset | `9496369` |
| Första workern tog tio jobb ur kön | Ett jobb i taget | `988092a` |
| Bedömning och kontaktsökning ett bolag i taget | Samtidigt (6); körningar överlever deployer | `df581b2` |
| Körningar stod i Pågår efter deploy | Väckare varje minut | `bdc71d1` |
| Redis "max number of clients reached" fällde en körning | En läsare + arbetarpool per ström | `0edd957` |
| Första rundan tog 13 min innan research började | Rundor på 8 kandidater | `cfe932a` |
| Vertex 429 i minuter, alla researchjobb föll | Tak på 4 samtidiga LLM-anrop; byte till annan EU-region (west4, north1 — aldrig utanför EU); kvotfel körs om i stället för att gå förlorat | `159ff1d`, `0eee39b`, `7894d25` |
| api-processen stod still i 2–4 min | Regex i adresskyddet var kvadratisk (126 s → 0,5 s); CA-paketet lästes per klient | `4738f32` |
| 52 merinfo-sidor köptes för 8 leads | Bolag med levande domän hämtas först (gratis HEAD) | `2b96372` |
| Övrigt | Infrafel visas aldrig ordagrant för kunden; inkorgsloggen dämpad | `3f2866a`, `d0ee87c` |

**Resultat:** slutkörningen i dev från kundvyn gav **10 av 10 leads på 7:08** (förut 15:44),
15 bolag undersökta, 59 ScrapeGraph-krediter. Alla 10 hade org.nr, mejladress och utkast, och
alla utkast lästes manuellt. En körning på 40 är inte omkörd efter rättningarna (de två
40-körningarna i dag föll på Redis respektive Vertex innan fixarna).

### 2.4 Utkastkvalitet ("alla utkast är proffsiga, välformulerade, inga stavfel")

- Avslutning: dubbla hälsningsfraser borta, signaturen ersätter namnraden; ni/er genomgående
  när mejlet går till bolaget (`595f910`).
- Tilltal: "Hej Verkstad," / "Hej Luleå," spärras; tankstreck i intervall (`fec7d75`);
  redan köade utkast putsas vid Godkänn och skicka (`b65c565`).
- Produktnamn i genitiv och med versal; ingen utgången uppgift som ingång (`22953a8`).
- Fel bolags sajt (ort prövas mot registret), idiom som fact-gaten fällde, och korrektur
  på varje leadsutkast (`751f2af`).

### 2.5 Svarsflödet ("När ett lead svarar ska alla svar hamna under inkorg")

Testat end-to-end i dev: ett testsvar klassades som lead inom ~2 min, prospektet blev Svarat
och det väntande utkastet ställdes in. Testmejlet ligger kvar i Leads › Inkorg.

### 2.6 Snabbare flikbyten (worktree `perf/snabbare-navigering`)

Sebbe ville att flikbyten skulle gå snabbare. Det var inte servern som var långsam: Railways
loggar visade 30–300 ms, även i main. Tiden gick åt till för stora svar och till att ett
klick inte gav någon respons förrän hela serverrenderingen var klar. Commits `368b0a9`,
`0ea7196`, `11372cb`.

| | Före | Efter (uppmätt i dev, inloggad) |
|---|---|---|
| Synlig respons vid klick | ingen förrän sidan var klar | 2–120 ms (skelett, fliken markeras direkt) |
| /admin/agentanvandning | 17,7 MB, 2,4–5 s | 213 KB, 0,36 s |
| /admin/korningar | 7,3 MB, ~2 s | 170 KB, 0,5 s |
| Leads-flikens tre tyngsta anrop | 775 KB | 132 KB (gzip) |
| Tillbaka till en nyss lämnad flik | ny serverrendering | ~0,15 s ur routercachen |

- `loading.tsx` för /admin, /dashboard och /settings; `staleTimes.dynamic` 30 s.
- `resolveDashboardState`/`isPlatformAdmin` React-cachade per request.
- gzip på proxyns JSON-svar (`lib/http/komprimera.ts`) — varken Next eller Railways edge komprimerar route handlers.
- `/api/admin/runs?sammandrag=true` utan step_log/input/output.
- Webben når api:t via Railways privata nät (`SNAJP_SUPPORT_INTERNAL_URL`), med automatisk
  reserv till den publika adressen. Förut gick 652 av 653 anrop via den publika edgen.
- Körningspollningen pausar i dolda flikar (två öppna flikar hämtade 365 KB var tredje sekund).

Deployen krånglade tre gånger utan att något låg nere: Docker Hub gav 429 på basimagen (hämtas
nu från `public.ecr.aws/docker/library`), och `--host ::` fällde Railways healthcheck och är
återställd till `0.0.0.0`. En leadskörning startades om mitt i och togs upp av väckaren.
Inte mätt: kundernas egen dashboard och "Byt kund"-läget.

### 2.7 Skicka provmejl, signatur och logga (Sebbe: "Vi vill se hur utskicken ser ut", "UTKASTEN OCH ALLA MAIL MÅSTE HA SIGNATUREN VI HAR")

Commit `d9028d6` (23:55).

- **Skicka provmejl**: ett utkast eller ett skickat leadsmejl skickas till kundens EGEN adress
  (kopplad brevlåda, signaturens e-post, faktureringsmejl, domänens svarsadress) med samma
  rendering som det riktiga utskicket: HTML-signatur med logga, avsändare och svarsadress. Kön,
  leadet och Skickat rörs inte, och `Auto-Submitted` håller provet ur supportinkorgen. Saknas
  sidfoten säger svaret att det riktiga utskicket stoppas av regel 1. Knappen finns i
  Granskning, Körningens utkast och Skickat (inte i demon). `app/leads/provmejl.py`,
  `POST /api/leads/provmejl`.
- **Signaturen**: Godkänn och skicka lägger på den på utkast som köades innan den sattes;
  `scripts/lagg_pa_utskicksfot.py` lägger på signaturen före foten, och en kund utan org.nr
  hoppas över i stället för att stoppa skriptet.
- **Loggan** kommer med även när signaturblocket ändrats eller utkastet är äldre (bara bilden,
  ingen ogranskad text). Körningens utkast och Skickat visar mejlet med signatur och logga.
- Tester: 3141 gröna i backend, 639 i roten.

## 3. Vad som återstår, i prioritetsordning

1. **Anton eller Sebbe — före måndag 08:00:** Snajps org.nr och postadress i Kunder & Data
   (Admin → Kunder → Snajp → Uppgifter och kontakter; development, och main före release).
   Sebbe försökte spara två gånger i kväll men inget nådde servern (ingen PUT, ingen rad i
   `platform_events`): sidan svalde ett misslyckat sparande, t.ex. när fliken öppnats före en
   deploy. Rättat i `98ace85` — felet visas nu under knappen; ladda om (F5) och spara igen.
   Policy-URL:en är satt i dev. Snajp AB finns inte i registret, så agenten kan inte slå upp
   numret. Utan uppgifterna stoppas alla 73 köade utkast; med dem går alla ut måndag 08:00 —
   pausa kön om det inte är meningen.
2. **Anton:** inget mejl har hittills gått ut till något lead, varken i dev eller main (0 de
   senaste 28 dygnen). Provmejlet (§2.7) är vägen att se hur utskicket ser ut innan måndag.
3. **Anton:** godkänn eller stoppa org.nr-uppslaget i merinfo (§2.2).
4. **Anton:** ScrapeGraph Free Plan räcker till ~45 leads till. Uppgradering är en betalning.
   Merinfo ger 403 mot ärlig bot; det hållbara alternativet är ett register-API (allabolag).
5. **Agent:** kör om en körning på 40 leads i dev efter dagens fixar.
6. **Anton vid release:** tokenbudgeten i main (2M/dygn) behöver troligen höjas som i dev (8M),
   och main-webben behöver `SNAJP_SUPPORT_INTERNAL_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8080`
   (finns bara i dev; utan den går main den publika vägen — fungerar, bara långsammare).
7. **Anton:** main har ingen mejlsignatur alls för Snajp — leadsmejl från produktion skulle gå
   ut utan signatur och logga. Sätts under Inställningar i main (produktionsbeslut).
8. Loggans bild-URL pekar på dev-miljön (fungerar). Den finns också på www.snajp.se; bytet i
   dev-databasen nekades av behörighetsspärren och är inte gjort.
9. Öppet sedan förut: Kunskapsgruppen bortvald trots regel 12; två brevlådors hemligheter
   går inte att dekryptera i dev (spegelns krypterade lösenord); Vertex-kapaciteten varierar.

## 4. Fällor

- **Vertex 429 är regionens kapacitet**, inte vår kvot — att vänta hjälper inte, byt EU-region.
- **Redis Clouds anslutningstak (20)** nås av blockerande läsare per worker; håll en läsare
  per ström och process.
- **Kvadratiska regexar låser hela api-processen** (async): chatten och alla kunders anrop
  står still. Oankrade `[^…]*` på okänd HTML är farliga.
- **Git-hookarna fallerar på Sebbes maskin:** Windows Smart App Control blockerar `bd.exe`,
  som repots hookar anropar. Kvällens commits gick med hookarna överhoppade (Sebbes
  godkännande). Tillåt `bd.exe` i Windows-säkerhet för att få tillbaka dem.
- Docker Hub svarade 429 på api-bygget i kväll; basimagen hämtas nu via ECR Publics spegel (`0ea7196`).
