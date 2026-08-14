# Handoff till Sebbe — 2026-08-14

Skriven direkt efter att `main` fast-forwardades till produktion. Läs det här innan du drar
senaste `main` eller rör `app/api/snajp-support/_lib.ts` — din kod ligger nu ihopvävd med en
stor mängd nytt agent-backend-arbete, och en av dina två senaste commits fick en manuell
sammanslagning jag vill att du specifikt granskar.

**Följdokument:**
- `STATUS.md` (avsnittet daterat 2026-08-14, båda posterna) — kronologisk logg över allt.
- `session-logs/2026-08-14-session-log.md` — fullständig teknisk detalj om själva
  implementationen (grundningsgrind, skill-lås, instruktionslager, SOUL, DB-spegel).
- `snipe-leads.md` (repo-roten) — uppdaterad hub-doc, "Live"-sektionen längst upp är ny.
- `.claude/plans/b-rja-med-att-skapa-cheeky-crescent.md` — den fullständiga planen med
  motiveringar för varje designval, om du vill förstå *varför* något byggdes som det gjorde.

---

## 1. Vad som hände, i sammanfattning

`main` låg fryst på commit `a10d919` sedan 2026-05-24 — ett medvetet beslut från 2026-07-28:
`snipra.vercel.app` skulle INTE röras medan redesignen pågick på grenen `snajp-redesign`, som
under tiden gick 45 commits förbi `main`. Dina två kallstart-fixar (`64420ac`, `6581e42`,
30–31 juli) landade **på `snajp-redesign`**, inte på `main` — de nådde alltså aldrig produktion
förrän nu.

I dag instruerade Anton mig explicit, två gånger, att pusha allt till `main`. Jag verifierade
att det var en ren fast-forward (main hade noll egna commits `snajp-redesign` saknade),
klassificeraren i verktyget blockerade första försöket som en extra skyddsgrind mot
produktionspushar, Anton godkände explicit, och pushen gick igenom:

```
git push origin snajp-redesign:main
a10d919..858b533  snajp-redesign -> main
```

Det här triggade `.github/workflows/deploy-production.yml` på riktigt (den lyssnar på push till
`main`, och `vercel.json` har `git.deploymentEnabled: true`). Jag pollade tills den var klar:
**lyckades**, och **`snipra.vercel.app` är nu aliaserat till den nya deployen**
(`https://snipra-76rq0l4x3-olofluns-projects.vercel.app`). `Verify`-workflowet kördes samtidigt
och blev grönt, inklusive ett nytt `docker-smoke`-jobb (mer om det i §4).

**Render (backend) är opåverkad.** `render.yaml` har ingen branch-pin — Render styrs av sin egen
dashboard-inställning, historiskt satt till `development`. Den nya agentkoden (grundningsgrind
m.m.) finns alltså i frontend-bundlen på produktion nu, men backend-processen som faktiskt kör
agenterna är på en separat, oförändrad deploy-cykel.

---

## 2. Konflikten — läs det här innan du rör `_lib.ts`

Vid sammanslagningen av `snajp-redesign` mot din gren fanns EN riktig konflikt, i
`app/api/snajp-support/_lib.ts`, i funktionen `proxyToBackend`. Inte konkurrerande ändringar —
två oberoende förbättringar av samma funktion som råkade krocka på samma rader:

- **Din sida** (`6581e42`): ett retry-med-timeout-mönster (5 försök × 10 s) för att överleva
  Renders kallstart efter 15 minuters inaktivitet, plus `AbortController` per försök.
- **Den andra sidan** (redan i lokal historik innan min session): `apiKeyForTenant(tenantSlug)`
  — varje kund har sin egen nyckel i env i stället för att allt gick mot demo-nyckeln, vilket
  tidigare gjorde att all trafik skrevs till demo-tenanten Nordlys Handel oavsett kund.

Jag löste det genom att slå ihop båda: retry-loopen finns kvar oförändrad, men nyckeln slås upp
EN gång med `apiKeyForTenant(tenantSlug)` innan loopen börjar (inte per försök — den beror bara
på `tenantSlug`, inte på försöksnumret) och används sedan i varje försöks headers.

```ts
export async function proxyToBackend(path: string, init: RequestInit, tenantSlug?: string | null) {
  let lastCause: unknown;
  const apiKey = apiKeyForTenant(tenantSlug);   // <- din retry-loop, nu med rätt nyckel

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    // ... oförändrad retry/timeout-logik ...
    headers: { "X-API-Key": apiKey, ... }
```

**Verifierat, inte bara ihopklistrat:** `tsc --noEmit` rent, alla fyra route-filer
(`chat`, `jobs/[jobId]`, `triage`, `[...path]`) som anropar `proxyToBackend` mergade automatiskt
utan konflikt och behöll både din `maxDuration = 60`-tillägg och den tredje `tenantSlug`-parametern
där den redan skickades in (t.ex. `chat/route.ts` skickar fortfarande `tenant` som tredje argument).

**Be dig granska specifikt:** att jag inte missförstått avsikten med `SNAJP_INTERNAL_API_KEY`
vs. per-tenant-nyckeln i retry-sammanhanget — om en tenant SKA falla tillbaka på demo-nyckeln vid
upprepade fel (i stället för att fortsätta försöka med en nyckel som kanske roterats), säg till
så justerar vi det. Just nu är det samma nyckel i alla fem försöken, vilket verkade rätt men är
inte något jag kan bedöma din ursprungliga avsikt om.

Full diff: `git show 858b533 -- app/api/snajp-support/_lib.ts` (mergecommitten), eller
`git log --oneline app/api/snajp-support/_lib.ts` för hela historiken.

---

## 3. Vad som byggdes den här sessionen (kort — full detalj i session-loggen)

Sju arbetsströmmar, alla från en plan Anton godkände i förväg:

1. **Grundningsgrind** (`app/leads/grounding_gate.py`) — stoppar påhittade siffror/kundnamn i
   leads-utkast innan de köas. Motiverad av en skarp incident 2026-08-10 (en AI-genererad siffra
   som inte fanns i något underlag). En reparationsrunda, sedan mänsklig granskning om felet
   kvarstår — aldrig tyst köning.
2. **Skill-lås** — `agent-core/skills/` (de vendorade AI-instruktionerna) kan bara ändras med en
   maskinlokal nyckel (`SNAJP_SKILL_UNLOCK_KEY`, finns bara på Antons dator, aldrig i git) plus
   en `VENDOR-BUMP:`-rad i commit-meddelandet. **Om du någonsin behöver justera hur en agent
   svarar: rör INTE `agent-core/skills/`.** Skriv i stället en fil i `agent-core/overlays/` och
   bind den till steget — se `agent-core/overlays/leads-hard-rules.md` som exempel.
3. **Tre-lagers instruktionssystem** — `agent-core/AGENTS.md` (global policy, gäller alla kunder
   direkt) → overlays (pinnade, per steg) → SOUL (kundens egen tondokument, redigeras i
   `/settings/soul`, kan ALDRIG åsidosätta regler — bara ton).
4. **DB-spegel av skills** — byggd men **avstängd som default i alla miljöer**. Det var en
   medveten avgränsning från vad som ursprungligen begärdes ("läsbara varifrån som helst") —
   se plan-filen §W7 för resonemanget. Inte något du behöver bry dig om just nu.
5. **Produktionsbugg fixad:** `agent-core/` låg utanför Dockers byggkontext för
   `snajp-support`-imagen — skulle ha kraschat vid FÖRSTA riktiga agentanropet på Render (dolt
   tills en riktig `DEEPSEEK_API_KEY` sätts där). Fixat i `snajp-support/Dockerfile` +
   `render.yaml`. **Detta berör din del av koden om Render någonsin får en riktig nyckel** —
   innan den dagen hade tjänsten kraschat direkt.

---

## 4. Verifiering — vad som faktiskt är bevisat, inte bara påstått

- 366 backend-pytest + 27 arkitektur-invarianter, gröna både lokalt och i CI vid push.
- `tsc --noEmit` rent.
- **`docker-smoke`-jobbet (nytt i `verify.yml`) kördes på RIKTIGT i CI vid push till `main`** och
  blev grönt — jag hade bara Docker-simulerat det för hand lokalt (ingen Docker på min maskin),
  så det här är första gången buggfixen i punkt 3.5 ovan är bevisad i en riktig container.
- Fem UI-buggar hittades och fixades genom att faktiskt rendera sidan och läsa skärmdumpar
  (kontrastfel, en textruta som klipptes vid 320px bredd, m.m.) — se session-loggen om du är
  nyfiken på detaljerna.

**Inte verifierat än:**
- **Skarp körning mot riktiga DeepSeek-nycklar.** Grundningsgrinden är enhetstestad mot fixtur-
  data, aldrig körd mot riktig modelloutput. Planen kräver att man medvetet matar in ett påhittat
  påstående och bekräftar att grinden faktiskt fäller — inte gjort.
- **`DATABASE_URL` är fortfarande inte satt lokalt** — de nya storage-metoderna (SOUL-lagring,
  skill-spegel) är bara testade mot `MemoryStorage`, aldrig mot riktig Postgres/RLS.

---

## 5. Öppna punkter — vem som helst kan ta dessa

1. **Bekräfta DB-spegel-scopet** med Anton (§4 ovan) — jag byggde det snävare än den
   ursprungliga formuleringen, motiverat men inte omprövat.
2. **Skarp `run_live_tests.py --leads`-körning** mot riktiga nycklar — se §4.
3. Tre andra ställen i `components/WorkspaceViews.tsx` har samma `grid-cols-12`/`gap-x-8`-
   kollapsbugg som fixades i inställningssidan, vid smala skärmar. Inte åtgärdade, bara
   dokumenterade i en kodkommentar.
4. `--mineral`/`--danger`-färgtokens mäter 4.4:1 kontrast, precis under WCAG AA (4.5:1) —
   repo-brett, inte en del av den här sessionen.
5. `.claude/launch.json` har en okommitterad ändring (lägger till en `backend`-launch-config)
   som legat orörd sedan innan den här sessionen — inte min, inte rörd, ligger kvar lokalt hos
   Anton.

---

## 6. Om du bara har fem minuter

Läs §2 (konflikten i din fil) och §3 punkt 2 (skill-låset — påverkar hur DU justerar agent-
beteende härefter). Resten kan vänta.
