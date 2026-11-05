# SEO och AI-synlighet för snajp.se

Läget 2026-11-05, vad som är byggt, och det som kräver en människa. Beslutet och
resonemanget står i [BESLUT.md](BESLUT.md) (2026-11-05). Grinden är INV-SEO-001.

## Läget före ändringen

- **"snajp"**: etta, med sidlänk till Vårt team och en AI-översikt som beskriver
  bolaget rätt. Varumärket fungerar.
- **Allt annat** ("svenska leads", "b2b leads sverige", "svensk ai sdr",
  "leadsagent", "svensk support bot", "support sverige"): inte med alls.
- **Varför, mätt på sajten:** tre produktadresser (`/`, `/leads`, `/support`),
  ingen med sökordet i titeln ("Iris, Snajps leadsagent: din säljare som aldrig
  sover"). Ingen H1 på någon av dem: hjälterubriken var ett `<p>`. FAQ-svaren
  saknades i HTML:en. Ingen strukturerad data, ingen delningsbild, ingen
  llms.txt. Domänen är ung och har nästan inga inkommande länkar.

## Vad som är byggt

| Del | Var |
|---|---|
| Åtta sökordssidor, en fråga var | `lib/landningar.ts`, `lib/landningssidor.ts`, `app/<sida>/page.tsx` |
| Titlar och beskrivningar med sökorden, Open Graph, delningsbild | `lib/seo.ts:sidmeta`, `public/og/snajp.jpg` |
| H1 på produktsidorna, FAQ-svar i HTML:en | `LandingPhoto.tsx`, `FaqDragspel.tsx` |
| JSON-LD: Organization, WebSite, SoftwareApplication med pris, FAQPage, BreadcrumbList | `lib/seo.ts`, `components/JsonLd.tsx` |
| Sidfotslänkar till varje sökordssida från varje publik sida | `components/marketing/Sidfot.tsx` |
| `/llms.txt` för AI-assistenter | `lib/llms.ts` |
| Sitemap med sökordssidorna | `app/sitemap.ts` |
| IndexNow (Bing, och därmed ChatGPT:s och Copilots sökning) | `scripts/indexnow.py`, `.github/workflows/indexnow.yml` |
| Verifieringstaggar via miljövariabel | `GOOGLE_SITE_VERIFICATION`, `BING_SITE_VERIFICATION` |

**Priserna följer prislistan av sig själva.** Varje pris i en titel, beskrivning,
schemats `offers`, llms.txt och sökordssidornas text räknas ur `lib/pricing.ts`.
Ändras priset där ändras det överallt vid nästa deploy, och INV-SEO-001 fäller
ett belopp eller en bindningstid som skrivits in för hand. Efter en push till
main väntar IndexNow-flödet sex minuter, sedan tills sajten visar priserna och
varje sökordssida i koden, och anmäler därefter alla adresser, så att Bing
hämtar om sidorna direkt. Google hämtar om på egen hand,
oftast inom några dagar; vill man skynda på: "Begär indexering" i Search Console
för de sidor där priset står.

En sak följer INTE med: Snajps egen kunskapsbas för supportchatten
(`snajp-support/app/tenants/snajp_kb.py`) skriver priserna för hand och ska
ändras i samma svep, som kommentaren i `lib/pricing.ts` redan säger.

## Sökordskarta

En sida per avsikt, så att sidorna inte konkurrerar med varandra.

| Sökord | Sida | Bedömning |
|---|---|---|
| svensk AI SDR, AI SDR Sverige, AI-säljare, AI-säljagent | `/svensk-ai-sdr` | Liten konkurrens, mest bloggar och listor. Realistiskt topp 10 på veckor efter indexering. |
| leadsagent, svensk leadsagent | `/leads` | Varumärket leadsagent.io äger "leadsagent". "Svensk leadsagent" går att ta. |
| b2b leads, b2b-leads sverige, svenska leads, köpa leads | `/b2b-leads` | Exakt-matchande domäner (svenskaleads.se, leadkollen.se) leder. Kräver länkar för förstasidan. |
| b2b prospektering, prospektering b2b, leadsgenerering b2b, kalla mejl b2b | `/b2b-prospektering` | Informationssökningar. Guideinnehåll vinner här, sidan är byggd så. |
| svenska leads i inkorgen, leads levererade | `/leads-i-inkorgen` | Låg volym, men den sidlänk Anton bad om. |
| support på svenska, AI kundtjänst, AI kundservice, kundtjänst på svenska | `/support-pa-svenska` | "Support på svenska" är mest navigering (Apple, Microsoft). "AI kundtjänst" går att ta. |
| supportchatt, chatbot hemsida, AI chatbot hemsida, supportbot, chattbot svenska | `/supportchatt` | Kundo, ImBox, Ebbot och chattbot.se leder. Medelsvårt. |
| supportagent, AI supportagent, företagssupport | `/ai-supportagent` | "Företagssupport" är mest Telia/Telenor. "AI supportagent" går att ta. |
| AI-agent, AI-agenter företag, ai agent vad är det | `/ai-agenter` | Brett och informativt. Definitionen på sidan är skriven för att citeras. |

**De breda orden ("leads", "support", "AI-agent") är realistiskt utom räckhåll
på månader.** De ägs av sajter med tusentals inkommande länkar, och avsikten är
ofta en annan ("support" är Apple och Microsoft). Sidorna innehåller orden, men
placeringen avgörs av länkar och tid, inte av fler sidor. Mät dem, men styr på
de specifika orden.

## Det som kräver en människa

Ordningen är efter effekt.

### 1. Google Search Console (Anton, 10 minuter)

1. search.google.com/search-console → Lägg till egendom → **Domän** `snajp.se`.
   Google visar en TXT-post. Lägg in den hos Loopia (DNS för snajp.se), eller
   skicka den till agenten, som kan lägga in den via Loopias API.
   *Alternativ:* egendomstyp URL-prefix `https://www.snajp.se`, metod HTML-tagg,
   och sätt tokenet som `GOOGLE_SITE_VERIFICATION` i Railway (main).
2. Sitemaps → skicka in `https://www.snajp.se/sitemap.xml`.
3. URL-inspektion → **Begär indexering** för de åtta nya sidorna och `/`,
   `/leads`, `/support`.
4. Efter två veckor: Prestanda → Sökfrågor. Det är den enda riktiga källan till
   vilka sökord som faktiskt ger visningar.

Search Console kan inte "koppla sökord" till en sida. Sökorden kommer ur sidans
innehåll och ur länkarna till den; det är vad sökordssidorna är till för.

### 2. Bing Webmaster Tools (Anton, 5 minuter) — det här är ChatGPT

ChatGPT:s webbsökning och Copilot står till stor del på Bings index. Utan Bing
finns sidorna inte för dem.

1. bing.com/webmasters → **Importera från Google Search Console** (snabbast),
   eller verifiera med `BING_SITE_VERIFICATION` i Railway.
2. Skicka in sitemapen.
3. IndexNow sköts sedan av workflowet efter varje release.

robots.txt släpper redan in GPTBot, OAI-SearchBot, PerplexityBot, ClaudeBot och
Google-Extended (regeln `User-Agent: *`).

### 3. Google Företagsprofil (Anton)

business.google.com: Snajp, Göteborg, kategori programvaruföretag, webbplats
och kontaktadress. Stärker kunskapspanelen på "snajp" och lokala sökningar.

### 4. Synas där AI-svaren hämtar sina listor (störst effekt för ChatGPT)

AI-assistenter rekommenderar sällan ett bolag ur dess egen sajt. De citerar
listor och jämförelser. Varje post nedan kräver ett konto eller ett mejl från er,
och ett utskick sker bara med ert ja.

| Var | Vad | Varför |
|---|---|---|
| businesswith.se | Registrera Snajp under chattbotar och under leadgenerering | Låg i Googles AI-översikt på både "b2b leads sverige" och "svensk support bot" |
| revenuebase.ai, lista över AI SDR-plattformar i Sverige | Be om att bli listad | Listan räknar 52 svenska AI SDR-plattformar |
| alicelabs.ai/sv, "bästa AI-verktyg för försäljning i Sverige 2026" | Mejla redaktionen | Svensk topplista som AI-svar hämtar ur |
| revexa.io (blogg om AI SDR i Sverige), getrebelos.com (AI SDR-verktyg för Sverige), techsy.io/sv | Mejla skribenten med ett kort underlag | Låg på första sidan för "svensk ai sdr" |
| aiagentstore.ai | Lägg upp Iris och supportagenten | Kategori AI SDR / utgående säljagenter |
| G2, Capterra | Produktsidor | Vanliga källor för B2B-mjukvara i AI-svar |
| LinkedIn-sida för Snajp | Bolagssida med länk till sökordssidorna | Bekräftar bolaget som entitet |
| Product Hunt | En lansering av Iris | Länk och omnämnande |

Underlag att skicka: llms.txt (`https://www.snajp.se/llms.txt`) har allt en
redaktör behöver på en sida.

## Mätning: OpenSEO

[every-app/open-seo](https://github.com/every-app/open-seo) är ett öppet
alternativ till Semrush och Ahrefs (MIT-licens): sökordsresearch,
positionsbevakning, konkurrentanalys, länkar, sajtrevision och AI-synlighet,
med en MCP-server så att agenten kan läsa datan direkt.

- **Vad det ger här:** riktiga sökvolymer för Sverige (i dag finns bara Googles
  autoförslag, som visar att en fråga finns men inte hur ofta), placering per
  sökord vecka för vecka, och om ChatGPT och Googles AI-översikt nämner Snajp.
  Det är så "sluta inte förrän kraven är uppfyllda" går att mäta.
- **Vad det kostar:** datan kommer från DataForSEO, betalt per anrop. Antingen
  den hostade versionen (openseo.so, 10 USD/mån plus anropen) eller egen drift i
  Docker med egen DataForSEO-nyckel. Båda kräver ett konto och en betalning,
  alltså er hand.
- **När det är på plats:** lägg in sökorden i tabellen ovan i positionsbevakning
  (plats Sverige, språk svenska), koppla MCP-servern, och agenten kan följa upp
  varje vecka och föreslå nästa sida utifrån riktiga siffror.

## Nästa innehåll, när datan finns

Bygg efter vad Search Console och OpenSEO visar, inte efter gissning. De
troliga kandidaterna:

1. En guide: "Får man skicka kalla mejl till företag i Sverige?" (marknadsförings-
   lagen, GDPR, enskilda firmor). Informationssökning med verklig volym, och den
   typ av sida AI-svar citerar.
2. Jämförelsesidor mot alternativen, sakliga och med datum.
3. Ett kundcase så fort en kund godkänt det. Inga påhittade siffror.
