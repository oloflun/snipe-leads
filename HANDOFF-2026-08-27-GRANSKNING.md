# Handoff: go/no-go-granskning, verifiering av agentbackend-handoffen, fyra fixar

Skriven 2026-08-27 (natt) av Sebbe/Claude, som svar på Antons
`HANDOFF-2026-08-27-AGENTBACKEND.md`. Pushad till `development` enligt den
omlagda deploy-kedjan (spegelgrenen `railway-development` hålls i synk men
deployar inget).

**Status: fyra commits pushade, 1450 backendtester gröna (var 1444 + 1 röd),
335 rotvaktposter gröna, tsc rent.** Railway är bekräftat produktionsstacken
(Sebbes beslut). `main` är INTE rörd.

---

## 1. Vad som gjordes: en full lanseringsgranskning FÖRE Antons merge

En go/no-go-granskning av hela ytan kördes mot det gamla trädet (0327687):
inventering av varje route/kontroll, dataisolering, demodata, agentflöden,
admin, fakturering, teknisk produktionskontroll — plus live-verifiering mot
Railway dev (qa_vyer.mjs grön, API-prober, RLS-verifiering mot körande DB).
Beslutet då var NO-GO med tolv villkor. Sedan landade Antons 304-filersmerge
och löste flera av dem. Nedan är det OMBASERADE läget.

### Isoleringsintyget (består efter mergen — verifierat mot körande DB)

* **Railway dev: `snajp_web` och `snajp_app` är båda `bypassrls=false,
  superuser=false`** och äger inga tabeller (ägare: postgres). RLS PÅ på
  alla 64 publika tabeller. Fyra tabeller har RLS utan policyer = deny-all
  (fail-closed, avsiktligt för `workspace_tenant_keys`; kontrollera att
  `ss_gallringspolicy` utan policyer inte är en funktionsbugg — appen får
  noll rader ur den).
* Supabase-preview: RLS PÅ på 63/63. (Supabase-stacken är nu avvecklad för
  development; punkten kvarstår bara om `main`-cutovern dröjer.)
* Inga bekräftade kodläckage: tenant härleds ur session/API-nyckel, aldrig
  ur klientdata; `sql()` utan identitet används bara mot `auth.users`;
  inga cache-läckor; 404 i stället för 403 genomgående.
* Rolig bekräftelse i praktiken: mitt första verifieringsskript läste
  `ss_knowledge_base` OSKOPAT som snajp_app och fick noll rader ur en full
  tabell — FORCE RLS gjorde exakt sitt jobb.

## 2. Antons öppna trådar — tre av fem stängda

1. **RRF-fusionen mot riktig Postgres (snipe-lt9): STÄNGD.**
   `.env.deploy` bär `RAILWAY_DEVELOPMENT_APP_PASSWORD`, så jag körde
   `search_kb` som `snajp_app` mot dev: fulltext ensam ger 3 relevanta
   träffar för "leverans frakt spårning", hybrid med riktig vektordimension
   (1536 — Nordlys HAR embeddings) ger 3 träffar, nonsens ger 0, inga fel.
2. **Svar/uppföljning end-to-end mot Postgres: HALVSTÄNGD.**
   * Chat-E2E via riktiga HTTP-vägen (202 → jobb → completed): svaret var
     ordagrant KB-grundat ("2–4 vardagar, 49 kr, gratis över 499 kr").
     Embed + hybrid-RRF + agent + Postgres fungerar live.
   * `POST /api/leads/prospects` skrev korrekt (201, inkl. din nya
     ensure-thread-väg). Men `POST /api/leads/svar` föll BÅDA försöken på
     **429 "AI-leverantörens kvot är slut"** — Gemini-kvoten. Felvägen är
     snygg; happy path återstår. OBS: chatten gick igenom samtidigt, så
     svar-vägen träffar sannolikt en annan modell/kvotpott än chatten —
     värt en titt när kvoten är löst.
   * `POST /api/leads/uppfoljning/svep` svarar korrekt 422 "Affärskontexten
     saknas" — snajp-tenanten i dev saknar `product_marketing`-kontext.
     Seeda den så går svepet att köra på riktigt.
   * Kvarlämnat: TVÅ testprospekt "E2E Verifiering AB" i dev-snajp-tenanten
     (signal märkt "får raderas"). Ingen delete-väg finns — rensa med SQL
     eller låt ligga.
3. **`/dashboard/larande` inloggad: STÄNGD.** Playwright-besiktning mot dev
   som QA-kund OCH som admin (`/admin/larande`): 200, rätt h1, riktigt
   tomläge ("Inga förslag just nu"), noll JS-fel, noll 4xx. Själva
   godkänn-klicket gick inte att öva — inga förslag finns i dev — men
   mekaniken har ditt backendtest.
4. snipe-xl9 (mejlrouting av svar): fortsatt blockerad av SMTP-stubben.
5. snipe-a6i (pg_trgm): inte rörd.

## 3. Fyra commits — vad som fixades och varför

1. **`fix: agent_feedback listades äldst först vid lika tidsstämpel`** —
   ditt enda röda test (`test_feedback_sparas_och_listas_senast_forst`).
   Windows-klockan tickar grovt → identisk `created_at` → stabil sort
   behöll insättningsordningen. Listan reverseras nu före sorteringen.
2. **`fix: triage var enda LLM-vägen utan timtak`** — `/api/triage` är
   anonymt nåbar, 20 mejl/anrop, 1 embed + 1 LLM per mejl i skarpt läge,
   och hade ingen `enforce()`. Nu samma tak/429-form som chatten + två
   tester. (Var #5 i granskningens blockerarlista.)
3. **`feat: startvakt vägrar dev-masternyckeln i databasmiljö`** —
   `snajp_master_dev_key_change_me` står i repot och accepteras av
   `require_master_key`, som låser upp hela `/api/admin/*`. Nu dör en
   databasprocess med defaulten vid deploy, samma mönster som din
   dataskyddsspärr. Verifierat (bool-only) att BÅDA Railway-miljöerna har
   riktiga nycklar innan vakten committades — den fäller ingen deploy.
4. **`fix: frontend-robusthet`** — `app/error.tsx` + `global-error.tsx`
   (fanns inte: serverfel gav Nexts råa engelska felsida), SupportChat
   läser nu `detail` OCH `error` vid 429 (uppmätt: kvottexten blev "Okänt
   fel"), LeadsRunForm renderar 422-listor läsbart, supportinkorgen fick
   samma `EjAktiverad`-väntläge som du gav Svar/Bolagsregister/Kontakter
   (den var kvarglömd — kundens HUVUDVY visade driftinstruktionen), fyra
   hämtvägar utan catch (evigt skelett vid nätfel) lagade, 404-copyn bytt
   från utvecklarspråk.

## 4. Kvar före `main` + skarpa nycklar (ombaserad NO-GO-lista)

Lösta av din merge: ~~opt-out-kedjan~~ (svar.py + `app/avregistrera/[token]`),
~~integritetspolicy~~, ~~prospektsvar-hantering~~, ~~uppföljningsgenerator~~,
~~bokföring saknas på grenen~~, ~~rått 409 i leads-vyerna~~. Lösta av mina
commits: triage-taket, masternyckelvakten, felsidorna, 409 i supportinkorgen.

**Kvarstår, i prioritetsordning:**

1. ~~SMTP-providern är en attrapp~~ **BYGGD senare samma natt** (commit
   `cec72ad`): `SmtpMailer` (opt-in via SMTP_HOST/USER/PASSWORD, se
   DEPLOY.md), supportsvarens sändväg `email_pipeline/sender.py` med
   sändning-före-status (502 vid fel, utkast kvar som pending; autosvar
   degraderar till granskningskön), testmejl (`provider='mock'`) skickas
   aldrig. **Kvar är MÄNNISKOSTEGET:** välj avsändardomän/konto, skapa
   app-lösenord och sätt variablerna i Railway (CLAUDE.md-undantaget — inte
   agentens hand). Tills dess loggas utskick precis som förut, och
   /health/ready säger "Ingen riktig sändväg". Kvar är också per-tenant-
   avsändare (Del F) — supportsvar från globala kontot bryter trådningen i
   kundens mejlklient — samt glömt-lösenord/demo-länk i Next-appen
   (lib/actions/auth.ts), som har en EGEN sändvägslucka: Next når inte
   backendens SMTP-provider.
2. **Fakturering finns inte i kod**: inga fakturafält i strukturerad form
   (kundens orgnr ligger som fritext i `business_context.product`), ingen
   nummerserie, ingen moms, ingen betalleverantör. Manuell rutin krävs —
   och underlaget (prospekt/mejl per månad per tenant) finns bara som
   handskriven SQL. (Migration 044 plan_och_betalsatt är ett steg, men
   kedjan är inte komplett.)
3. **Snajps eget orgnr är `000000-0000`** (`lib/tenants/snajp.ts:67`) —
   filens egen kommentar kallar det lagbrott att visa externt. Regel 1 i
   send_guard kräver dessutom riktigt orgnr i sidfoten, så första riktiga
   utskicket BLOCKERAS av er egen guard tills det är ifyllt.
4. **Kvoterna som säljs (150 prospekt/300 mejl, 9/3 kr) finns inte i kod**,
   och `snajp_kb.py` låter supportagenten lova dem i chatt. Bygg mätningen
   eller ändra copy + KB.
5. **Tenant-provisionering för riktiga kunder är manuell** (medvetet, per
   `EjAktiverad`-dokumentationen) — men då måste "inom en arbetsdag"-löftet
   i väntlägen hållas operativt. Ingen notifiering finns när någon
   registrerar sig → lägg minst ett mejl/event till er själva.
6. **Admin-impersonering är skrivbar** ("läsläge" är bara bannern,
   `lib/snajp/tenant.ts`), och impersonationsloggen är best-effort.
7. **Jobbstore = memory i BÅDA Railway-miljöerna** (hälsan säger
   `jobs:"memory"`; ingen REDIS_URL i .env.deploy) — varje deploy tappar
   pågående chattjobb. Koppla Redis före skarp trafik.
8. **Publika chatten kringgår IP-taket** (`SupportChat` → `/api/chat`, bara
   delat tenant-tak 400/h; `/api/demo/chat` med IP+session-tak anropas
   aldrig av frontenden) + inget dygnstak + fail-open. Kräver dessutom att
   klient-IP forwardas genom Next-proxyn för att bli meningsfullt — därför
   INTE hastighetsfixat i natt.
9. **Gemini-kvoten**: dev är live men svar-vägen får 429 — spend/kvotläget
   hos leverantören måste redas ut före lansering (samma blockerare som
   bokföringens kvalitetskontroll).
10. Mindre: EN-växlaren översätter ~10 % av inloggad produkt och glömmer
    valet; ingen bekräftelsedialog på "Godkänn & skicka"; ingen
    CSP/X-Frame-Options; ingen Sentry; QA-lösenorden i `scripts/qa_vyer.mjs`
    bör roteras före riktiga kunder; `ss_gallringspolicy` utan RLS-policyer.

## 5. Verifiera själv

```bash
cd snajp-support && .venv/Scripts/python.exe -m pytest tests/ -q   # 1450 gröna
cd .. && snajp-support/.venv/Scripts/python.exe -m pytest tests/ -q # 335 gröna
npx tsc --noEmit
python scripts/verify_railway.py
```

E2E-skripten från i natt (read-only utom KB-seed/testprospekt) ligger i
sessionens scratchpad, inte i repot — de var engångsverifiering. Mönstren
finns beskrivna ovan om något ska göras om.
