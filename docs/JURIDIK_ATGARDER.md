# Juridik — vad som är gjort och vad som är kvar

Motsvarar implementeringsplanen i `GDPR-Integritet-Rapport-Snajp.md`.
Statusen här är sanningen; planen är avsikten.

Uppdaterad 2026-08-24.

---

## Klart i kod

| Punkt | Vad som byggdes |
|---|---|
| **P0.1** | Startspärr mot DeepSeek i miljöer med riktig kunddata. `Settings.llm_provider_fault()` i `snajp-support/app/config.py`, enforcad i `app/main.py` (uppstart) och `app/agent/llm.py` (klientbygge). Test: `snajp-support/tests/test_dataskydd_provider.py` |
| **P0.3** | `/integritetspolicy`, `/villkor`, `/cookies` under `app/`. Delat skal: `components/marketing/JuridiskSida.tsx` |
| **P0.4** | `components/marketing/Sidfot.tsx` — bolagsidentifikation och juridiska länkar, renderad i marknadssidans sidfot och på varje juridisk sida |
| **P0.5** | `components/marketing/copy.ts` — dataskyddstexten säger nu att mejltexten bearbetas av en AI-leverantör, med länk till policyn |
| **P1.1** | Gallringsmekanismen: `supabase/migrations/048_gallring.sql` + `scripts/gallra.py`. **Perioden är inte satt** — se nedan |
| **P1.2** | `scripts/gdpr_radera.py` — sök, registerutdrag och radering per e-postadress |
| **P1.3** | Art. 14-sidfoten byggs i kod och kan inte väljas bort av modellen: `snajp-support/app/leads/utskicksfot.py`, påsatt i `app/agent/leads_tools.py` vid köning. Avregistreringslänken fungerar: `supabase/migrations/046_avregistreringslankar.sql` + `app/avregistrera/[token]/page.tsx` |
| **P1.5** | `INCIDENT_RESPONSE.md` |
| **P2** | `docs/registerforteckning.md` |

---

## Kvar — kräver en människa

### P0.1b · Skaffa en OpenAI-nyckel och byt provider  ▸ Anton  🔴 BRÅDSKANDE

**Läst ur Railway 2026-08-24, inte antaget:**

```
main         api:  LLM_PROVIDER='deepseek'   DEEPSEEK_API_KEY=<satt>   OPENAI_API_KEY SAKNAS
development  api:  LLM_PROVIDER='deepseek'   DEEPSEEK_API_KEY=<satt>   OPENAI_API_KEY SAKNAS
```

Kör `python scripts/llm_provider.py` för att se det aktuella läget själv —
skriptet skriver aldrig ut ett nyckelvärde.

**Två saker följer av det.**

För det första: produktionen skickar riktiga kunders mejl till DeepSeek just
nu. Det är inte något koden orsakar och inte något koden kan laga — spärren
kan bara vägra starta. Det här är den skarpa posten i hela dokumentet.

För det andra: `OPENAI_API_KEY` finns inte i någon miljö, så providern går
inte att bara vända. En tjänst som startar med `openai` men utan nyckel går
ner i simuleringsläge — den ser frisk ut och slutar producera riktiga svar,
vilket är ett sämre fel än ett som larmar.

**Ordning:**

1. Skaffa en OpenAI-nyckel (konto + betalkort — därför din hand och inte min).
2. Lägg `OPENAI_API_KEY` på `api` i **både** `main` och `development`.
   Kontrollera att den ligger där; anta det inte — samma fälla som Email
   Studio-nyckeln i `DEPLOY.md`.
3. Byt providern:

   ```bash
   python scripts/llm_provider.py --apply
   ```

   Skriptet vägrar byta på en tjänst som saknar nyckeln, så steg 2 går inte
   att hoppa över av misstag.
4. Deploya om `api` och kontrollera att den startar.

Sätt samtidigt på `api` i båda miljöerna:

```
PUBLIC_BASE_URL=https://snajp.se
```

Utan den kan avregistreringslänken inte byggas, och då blockerar
`send_guard` regel 2 varje utskick.

**Tills detta är gjort startar inte `api` på ny kod.** Deployen av
`64aba04` till `development` föll som avsett, med
`CRITICAL Startvägran: LLM_PROVIDER=deepseek är inte tillåtet i miljön
'development'` i loggen. Railway låter den föregående versionen ligga kvar, så
dev-backenden svarar fortfarande — på gammal kod. Nästa merge till `main`
kommer att falla likadant.

### P0.1c · Kontrollera Geminis avtalsnivå  ▸ Anton  🔴 BRÅDSKANDE

`LLM_PROVIDER=gemini` är satt i både `main` och `development` sedan
2026-08-24, och koden stödjer det nu. Överföringen till Kina är därmed
stoppad — men bytet är inte klart förrän en fråga är besvarad.

**Nyckeln som används är den som kodbasen själv beskriver som vald för
gratisnivån** (se kommentaren vid `gemini_api_key` i
`snajp-support/app/config.py`, och `scripts/keys.py`). Gratisnivåer hos
modelleverantörer tillåter typiskt leverantören att använda det som skickas in
för att förbättra sina produkter — alltså mänsklig granskning och träning.

Går det här på kunddata är det ett större problem än DeepSeek var, inte ett
mindre: DeepSeek var en överföring utan rätt avtal, det här vore en
överföring där vi aktivt lämnat bort innehållet.

**Att kontrollera, i den ordningen:**

1. Vilken nivå ligger `GEMINI_API_KEY` på — AI Studio gratis, AI Studio betald,
   eller Vertex AI? Bara de två senare ger normalt ett åtagande om att
   innehållet inte används för produktförbättring.
2. Finns ett DPA (personuppgiftsbiträdesavtal) med Google för den nivån?
3. Vilken dataregion behandlas prompten i, och vilken överföringsmekanism
   gäller (Googles DPF-certifiering eller SCC)?

Ligger nyckeln på gratisnivån: **byt till en betald nivå eller till OpenAI
innan fler kundmejl passerar.** Växlingen är ett kommando när nyckeln finns:

```bash
python scripts/llm_provider.py --satt openai --apply
```

Tills svaret finns säger `/integritetspolicy` inte längre att leverantören
"inte tränar på texten" — det påståendet togs bort, eftersom ett löfte i en
integritetspolicy är bindande. Skriv inte tillbaka det utan att ha läst
avtalet.

Fyll samtidigt i `region` för Google i `lib/bolag.ts` och i
`docs/registerforteckning.md`.

### P0.2 · Rotera den läckta Render-nyckeln  ▸ Anton

Nycklar och lösenord är undantaget i `CLAUDE.md` — jag rör dem inte.

1. Rotera nyckeln i Render.
2. Uppdatera `.env.deploy`.
3. **Bedöm om nyckeln gav åtkomst till persondata.** Om ja: kör
   `INCIDENT_RESPONSE.md` punkt 2–6. Posten ligger redan i incidentloggen där.

### P0.3b · Fyll i bolagsuppgifterna  ▸ Anton

`lib/bolag.ts` bär platshållare — jag gissar inte ett organisationsnummer, för
ett påhittat org.nr kan tillhöra ett annat bolag.

Fyll i: `namn` (registrerat bolagsnamn), `orgnr`, `postadress`,
`policyUppdaterad`, `DATASKYDD_MEJL`, och `region` för OpenAI och Railway i
`UNDERLEVERANTORER`.

Så länge de är platshållare visar sidfoten en gul varningsruta på varje publik
sida. Den försvinner av sig själv när fälten är ifyllda.

### P0.3c · Låt en jurist läsa de tre sidorna  ▸ Anton

Texterna är ett förstautkast. Varje juridisk sida visar en gul "Förstautkast"-ruta
tills någon tar bort den i `components/marketing/JuridiskSida.tsx`. Ta inte bort
den innan en jurist läst — särskilt inte ansvarsbegränsningen i `/villkor`, som
står tom med flit.

### P0.3d · Skaffa en riktig kontaktadress  ▸ Anton

`Snajpsupport@gmail.com` duger som svarsadress men inte som ett företags enda
officiella kontaktväg på en B2B-säljsida, och inte alls som adressen dit en
registrerad skickar sin begäran. Sätt upp `integritet@snajp.se` och lägg den i
`DATASKYDD_MEJL`.

### P1.1b · Besluta retentionsperioden  ▸ Anton + kund

Mekanismen finns, talet gör det inte — och ska inte gissas. Vanligt: 24–36
månader efter senaste aktivitet på ärendet.

När beslutet är taget:

```bash
python scripts/gallra.py --env railway-main --tenant <slug> --satt-policy 730 --beslutad-av "Anton"
```

Kör sedan en **torrkörning** och granska siffrorna innan `--apply`:

```bash
python scripts/gallra.py --env railway-main
```

Fyll därefter i perioden i `/integritetspolicy` (avsnittet "Hur länge vi sparar
uppgifter" bär en platshållare), i `docs/registerforteckning.md` och i
PUB-avtalet. Schemalägg `scripts/gallra.py --apply` som Railway-cron först när
en torrkörning granskats mot produktionen.

### P1.4 · Åtkomstskydda Railway-miljön `development`  ▸ Anton

`web-development-6c85.up.railway.app` speglar produktionen och innehåller
riktiga kunders ärenden och mejladresser. Verifiera att den inte är öppet
nåbar utan inloggning, motsvarande det SSO-skydd Vercel gav (se `DEPLOY.md`).
Saknar Railway motsvarighet: lägg minst ett lösenords- eller IP-skydd i
middleware innan fler kunder speglas dit.

Jag har inte Railway-åtkomst och kan inte verifiera det själv.

### P1.3b · Migrationerna måste köras  ▸ Anton

046 och 048 är skrivna men inte applicerade någonstans:

```bash
python scripts/railway_migrate.py --env development --apply
```

Verifiera i `development` först. Avregistreringssidan fungerar inte förrän 046
är körd, och `gallra.py` gör ingenting förrän 048 är körd.

### P2 · Kvar att göra löpande

- **DPIA för supportagenten** — mall finns hos IMY. Gäller den automatiska
  klassificeringen och eskaleringslogiken.
- **Intresseavvägning för kallmejlen** dokumenterad (art. 6.1 f).
- **Utloggningsknapp** — känd lucka i `STATUS.md`, hör till kontokontroll.
- **NextAuth/Supabase Auth-hybriden** — färre parallella auth-vägar.
- **Cookiebanner-beredskap** — ingen banner behövs idag. Bygg den inte i
  förväg för en cookie som inte kräver den.

---

## Inte gjort, och varför

- **PUB-avtalet** (`PUB-avtal-mall-Snajp.md`) — den filen finns inte i repot,
  så jag har inte kunnat skriva mot den. Villkorssidan och
  registerförteckningen refererar till avtalet; texten i det måste skrivas
  separat.
- **Engelska versioner av de juridiska sidorna** — medvetet utelämnade. Två
  språkversioner av ett avtal är två lydelser, och den dag de säger olika
  saker är frågan vilken som gäller. Se kommentaren i `JuridiskSida.tsx`.
- **`supabase/functions/generate-outreach`** — planen pekade ut den för
  art. 14-sidfoten. Den funktionen returnerar konserverad exempeltext och
  ligger på den döda Supabase-stacken; att lägga en juridisk sidfot i en
  attrapp hade sett ut som en åtgärd utan att vara en. Den riktiga vägen är
  `snajp-support/app/leads/`, och det är där den ligger nu.
