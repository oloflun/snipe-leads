# Handoff till Anton (oloflun) — allt sedan din senaste commit

Din senaste commit är `46b676b` (2026-08-21 09:30, "handoff för demovyn").
Allt nedan är de **41 commits** som lagts till på `development` sedan dess,
fram till `4a89818` (2026-08-23 15:24). `development`, `railway-development`
och `railway-main` står alla på `4a89818`. `main` (den gamla Vercel/Render-
stacken) är orörd på `860c74d`.

Fyra tidigare handoffar täcker delar av perioden i mer detalj och länkas i
respektive avsnitt nedan i stället för att upprepas här:
[`handoffs/2026-08-21-demovy/HANDOFF.md`](../2026-08-21-demovy/HANDOFF.md) (din
egen, startpunkten), [`handoffs/2026-08-21-kvall-cutover/HANDOFF.md`](../2026-08-21-kvall-cutover/HANDOFF.md),
och de två `doc:`-commits `f99fb17` och `63b00e0` (innehåll i
[`MIGRATIONS-PENDING.md`](../../MIGRATIONS-PENDING.md)).

---

## 1. Det som kräver DIG, i prioritetsordning

### 1.1 PR #9 väntar fortfarande på en granskare som inte är författaren

<https://github.com/oloflun/snipe-leads/pull/9>

Läget just nu (hämtat live inför den här handoffen):

```
state              OPEN
mergeable          MERGEABLE
mergeStateStatus   BLOCKED
reviewDecision     REVIEW_REQUIRED
reviews            []
```

Samma spärr som i kväll-cutover-handoffen för två dagar sedan: PR:en är
skapad av `bergmansebastian2002`, GitHub tillåter inte självgodkännande, och
du äger repot. `gh pr merge --admin` och `gh pr review --approve` är båda
provade och avsiktligt blockerade av behörigheterna. **Det här kräver att du
går in och trycker Approve**, annars kan den aldrig mergas mekaniskt.

### 1.2 Gemini-API:t — löst sedan din handoff, men värt att veta varför embeddings funkar nu

Detta var punkt 1.1 i din egen handoff. Det är löst: en ny `GEMINI_API_KEY`
aktiverades, och två följdfel fixades (modellen ger 3072 dimensioner mot en
`vector(1536)`-kolumn, och `EMBEDDING_MODEL` pekade på ett OpenAI-namn). 159
artiklar har vektorer i development, 41 i railway-main, 0 misslyckade.
Ingenting kvar att göra här — noterat så du vet att det inte längre är öppet.

### 1.3 Skärmdumparna i historiken — fortfarande ditt beslut, olöst

Din punkt 1.2 är **inte** åtgärdad av mig. De två skärmdumparna med
Livrustnings namn, omsättning och adminens mejladress ligger fortfarande kvar
i commit `0acb104` i historiken. Jag har inte rört git-historik. Se din egen
handoff §1.2 för alternativen (låt ligga / `git filter-repo` + force-push /
gör repot privat).

### 1.4 LoopiaAPI-lösenord för DNS mot `www.snajp.se`

`scripts/loopia_dns.py` (ny, `4a89818`) sköter CNAME-posten mot Loopia
automatiskt — men den behöver en `LoopiaAPI`-inloggning (skild från ditt
kontolösenord), skapad i kundzonen under **Kontoinställningar → LoopiaAPI**,
och lagd i `.env.deploy` som `LOOPIA_API_USER` / `LOOPIA_API_PASSWORD`. Det är
ett kontolösenord — ett av undantagen i `CLAUDE.md` som alltid kräver dig.
Skriptet säger exakt detta i stället för att bara falla på en anslutning.

Apex-domänen (`snajp.se` utan `www`) är **medvetet manuell** — en CNAME kan
inte ligga på apex, och Railway tillåter bara en egen domän per tjänst (redan
tagen av `www`). Kvar är Loopias egen webbvidarebefordran, som inte går att
sätta via API. Skriptet upptäcker och påminner om steget, det gör det inte åt
dig.

### 1.5 Verifiera PWA-installationen på en riktig iOS-telefon

Manifest, ikoner, service worker och installationsdialogen är byggda och
verifierade i devtools/emulering på alla tre plattformar (`fb545d2`,
`fb9592b`, `faee48b`), men iOS cachar ikon och namn hårt och devtools bevisar
inte att "Lägg till på hemskärmen" faktiskt ger rätt resultat. Det måste
provas i Safari på en fysisk telefon.

### 1.6 `SNAJP_SUPPORT_URL` på Vercel pekar fortfarande på den gamla Render-backenden

`railway-main` kör sedan `b5277d1` (2026-08-22) samma kod som `development`,
verifierat grönt i produktion (triage, en fullständig agentkörning, testmail,
inkorgssynk). Men URL-bytet på Vercel är **inte gjort** — det är nu ett beslut
att fatta, inte en blockering. Se `MIGRATIONS-PENDING.md` §"railway-main:
cutovern är GJORD" för hela verifieringstabellen.

---

## 2. Vad som byggdes, i ordning

### 2.1 Fem "påhittad data i betald arbetsyta"-buggar, samma familj, hittade genom att faktiskt läsa varje sida

Detta är den enskilt största arbetsinsatsen i perioden. Efter demovyn (din
sista commit) gjordes en genomgång sida för sida av vad en **inloggad,
betalande** kund faktiskt ser, inte bara demokontot:

| Vy | Vad den visade förut | Commit |
|---|---|---|
| Analys | Hårdkodade siffror (188 skick, 21 svar, 6 möten) för varje kund | `2a454af` |
| Bolagslista + detaljsida | Fem påhittade bolag; okänt id föll tillbaka på `companies[0]` (fel bolags research under rätt rubrik) | `9519e8e` |
| Svar + Kontakter | Sju hårdkodade svar från påhittade personer; `findContact` samma fallback-bugg | `2f5b502` |
| Assistentfliken | Ett skrivet men aldrig kört samtal, omärkt | `1c8cf85` |
| Email Studio (tomläge) | Ett annat bolags säljmejl, omärkt | `b5277d1` |

Gemensam princip i alla fem: hellre en ärligt tom vy eller ett tydligt
"exempel"-märke än ett påstående som ser ut som agentens verkliga arbete.
`WorkspaceViews.tsx` är efter detta nere på en enda import ur `mock-data.ts`
(`workflowSteps`, som beskriver arbetssättet och inte utger sig för kunddata).

### 2.2 Email Studio svarade aldrig från en modell för en riktig kund (`de4c300`)

`OPENAI_API_KEY` var aldrig satt på webbtjänsten i någon miljö, så
`useSimulation` var sann även för inloggade, betalande kunder — alla åtta
åtgärder gav mallgenererad text med `success: true`, omöjlig att skilja från
en riktig omskrivning utom genom att den tog noll sekunder. Löst med två
grepp: leverantören är nu konfigurerbar (DeepSeek som fallback, samma
leverantör agenterna redan använder), och ett simulerat svar **säger** det nu
(`simulated`-fält + "Exempelsvar" i UI). Samma commit fixade även tre
endpoints som gav 500 i stället för 404 på ett felstavat id.

### 2.3 Onboarding-väntan såg ut som ett haveri (`34731e3`)

En ny kund vars arbetsyta ännu inte kopplats till en tenant fick 409 med
texten "Sätt workspaces.slug och ss_tenant_id" rakt i gränssnittet — en
databasinstruktion, inte ett kundmeddelande. Väntetiden i sig är avsiktlig
(en människa ska välja slug och bygga kunskapsbasen, samma resonemang som i
`lib/snajp/testtenant.ts`), men felet bär nu en kod (`ej_aktiverad` vs.
`nyckel_saknas`) och en lugn `EjAktiverad`-komponent i stället för
databastext. **Kvarstår, utanför denna ändring:** en arbetsyta utan slug syns
inte i `/admin/kunder`, så en väntande kund kan vara osynlig för er.

### 2.4 Admin kan nu öppna vilken kunds arbetsyta som helst (`b50a44b`)

Tredje läget vid sidan av admin/demo: `kund:<slug>` i cookien, tre oberoende
lås (session→platform_admins, en ny DB-funktion `tenant_api_key_for_admin()`
med parametertvång, ingen databasfråga utan att grinden passerat), gul banner
på varje undersida, och en logg (`platform_events` via
`log_admin_impersonation()`, skriven **före** redirect så ett besök alltid
lämnar ett spår). Ny invariant-liknande skydd, men **migration 042 som krävs
är inte applicerad** på Supabase development (den grenen är avstädd, se 2.7)
— kundläget svarar 409 tills funktionerna finns i den databas som faktiskt
används (Railway har den redan).

### 2.5 Inkorgen: en knapp som alltid misslyckades, och tre kringfixar

`faf5098`: "Synka inkorg" läste globala miljövariabler oavsett tenant (hade de
varit satta hade en kunds synk läst en annan kunds brevlåda) och pratade om
`IMAP_HOST`/`USER`/`PASSWORD` till kunden. Fixat till att läsa kundens egna
`ss_mailboxes`-rader och prata kundens språk.

`6469eaf`: "Hämta testmail" tog 60,3 sekunder och webbappens proxy dödar vid
60 — knappen kunde alltså aldrig lyckas. Klassificering flyttad till en
bakgrundsuppgift, svaret kommer direkt.

`99bd490` + `276b76a`: urvalet gav tomma fack (sex slumpade ur tjugofem utan
hänsyn till fack) och två fack saknade kunskapsbastäckning helt (garanti,
utbildning, orderstatus hade en artikel var). Sex nya KB-artiklar, seedningen
garanterar nu ett ärende per fack plus minst en eskalering.

### 2.6 PWA — appen går att installera (`fb545d2`, `fb9592b`, `faee48b`)

Manifest, ikoner (genererade ur logotypen med korrekta säkerhetszoner per
plattform — 8/12/20 % marginal för webb/iOS/Android maskerbar), service
worker (kunddata cachas **aldrig**, bara statiska byggartefakter och
appskalet), och slutligen skärmbilder + `id` + `launch_handler` för att Chrome
ska visa en riktig installationsdialog i stället för "Skapa genväg". Se 1.5
för vad som återstår.

### 2.7 Rebranding: fågeln → S:et (`efb57ab`, `a8e245c`)

Ny logotyp, vektoriserad med potrace (skarp i alla storlekar, 18px till
512px). Marknadssidornas hjältebild fick ett eget stort `hjalte`-läge i
`Logo.tsx` med `clamp()`-skalning (28px mobil → 88px stor skärm); arbetsytans
header är **medvetet orörd** — där är loggan en navigationsdetalj, inte
husets märke. Alla butiksbilder till installationsdialogen regenererade.

### 2.8 Supabase-grenen `development`: SQL:en var aldrig felet (`63b00e0`)

Grenen har stått i `MIGRATIONS_FAILED` sedan 15 augusti. Halva orsaken
(fjärrversioner utan lokal fil) är åtgärdad. Andra halvan testades genom att
köra alla fjorton väntande migrationer i en transaktion mot grenens egen
databas — allihop gick igenom utan fel, sen rullades det tillbaka. En
`rebase_branch` kördes och landade ändå i `MIGRATIONS_FAILED`. **Beslut:
grenen lämnas som den är** — den hör till den gamla Vercel/Render-stacken,
produkten kör på Railway där allt är grönt, och nästa steg (`reset_branch`)
raderar otrackad data på en gren skapad `--with-data` (spegel av riktig
kunddata). Inte värt risken för en miljö ingen använder. Fullständig tabell
över vilka migrationsnummer som är dubblerade och vilken variant som aldrig
körts: se `MIGRATIONS-PENDING.md`.

### 2.9 Diverse fixar värda att känna till

- `d858d40` — branching-checken föll på bokföring, inte SQL: Management-API:t
  registrerar egna 14-siffriga versioner för migrationer körda utanför
  filkedjan. Fem tomma "spegel"-filer löser det, samma mönster som en gång
  tidigare.
- `e929288` — trendstaplar som inte ritades ut och en kolumnkrock ("84RESEARCH
  PÅGÅR") — hittades bara genom att faktiskt läsa en skärmbild, inte genom
  DOM-frågor.
- `cadbfad` — `background-attachment: fixed` på fullbreddsbilder fick sidan
  att frysa i skurar under scroll; kompositorn kan inte scrolla en fäst
  bakgrund utan att måla om hela bandet varje bildruta.
- `0327687` — flikraden dolde sig bakom Admin/Demo-växeln vid ~820px,
  motstridiga `min-w-0`/`shrink-0`.
- `fd40746`, `736506f`, `5be591c`, `48dd717` — genomgående textgranskning:
  produktnamn ("Kundservice" vs "Kundtjänst"), plural på agenterna (70 par i
  28 filer, mening för mening, inte sök-och-ersätt), ny meny och "Vilka är
  vi"-sektion på marknadssidan, `Sverige · GDPR · RLS` bortplockat ur
  hjältebilden (två av tre var interna förkortningar).

---

## 3. Verifierat i drift (senaste mätningen, `de4c300`)

- Kundtjänstagenten: klassificerar rätt fack, svarar grundat på 24 s.
- Leads-agenten: research på 42 s, åtta steg loggade.
- "Hämta testmail": svarar på 0,4 s, bakgrundskedjan fyller alla sex fack på
  ~72 s utan tomma.
- Registreringstriggern skapar arbetsyta + profil (provad transaktionellt).
- 745 backend-tester, tsc rent, alla 23 routes utan konsollfel.

---

## 4. Öppna trådar som INTE blockerar

1. **En väntande kund utan slug syns inte i `/admin/kunder`** (§2.3) — kräver
   en migration som utökar `tenants_for_admin`.
2. **Migration 042 inte applicerad på Supabase development** — ofarligt
   eftersom den grenen är avstädd (§2.8) och Railway redan har den.
3. **`SNAJP_SUPPORT_URL` på Vercel** pekar fortfarande på gamla backenden
   (§1.6).
4. **IMAP saknas och ingen riktig sändväg** — sant i alla miljöer sedan innan
   denna period, oförändrat. Blockerar fortfarande skarp drift för en kund.
5. **`www.snajp.se`** väntar på CNAME + LoopiaAPI-nyckel (§1.4); apex förblir
   manuell.
6. **PR #9** (§1.1) och **skärmdumparna i historiken** (§1.3).
7. Ett otracked-filfynd i arbetsträdet just nu:
   `snajp-support/FUNGERANDE DEMO SNAJP.txt` — ser ut som ett gammalt
   kravdokument, ligger okommitterat i arbetsträdet. Inte skapat av mig under
   den här perioden; flaggar det bara så det inte kommer som en överraskning.

---

## 5. Commits, kronologiskt

```
5b26fc0  fix: embeddings mot rätt dimension, och två ord som eskalerade fel ärenden
a48dccf  feat: efterfyllnad av vektorer för artiklar som skrevs medan embeddings var trasiga
95a15fd  fix: hälsokontrollen kunde inte se en trasig embeddings-kedja
2284248  feat: tre förslag på färgat toppband
7c3a163  feat: exempelbolagen bär en pitch som går att öppna, skriva om och prova
deec205  revert: inget färgat toppband
810c1af  fix: pitchen sa "Vi säljer Vad vi säljer:", och Uppdatera gav samma bolag
fac3899  feat: förhandsvisning av menyraden
d03cdc5  feat: menyraden centrerad, Kundtjänst tillbaka, större logotyp
8baf698  feat: två demolänkar i hjältebilden, dataskyddet till sidfoten
fd40746  fix: produkten hette två saker, och tre språkfel
44d658b  feat: migrera en kunds agentprofil till Railway
ca57bd6  doc: Livrustnings profil är i Railway — main kör kod från 16 augusti
48dd717  feat: meny i sidhuvudet, "Vilka är vi"
83665ae  doc: handoff — pitcher, menyn, och två cutovers
736506f  feat: marknadssidorna skrivs om, demoknapparna fungerar
5be591c  feat: arbetsytans texter i plural
faf5098  fix: inkorgen — knapp som alltid misslyckades, två sidor som ljög
b5277d1  fix: Email Studio visade ett annat bolags säljmejl
f99fb17  doc: cutovern till railway-main är gjord
6469eaf  fix: "Hämta testmail" snurrade i en minut
99bd490  feat: testmailen fyller varje inkorg
276b76a  fix: två inkorgar stod tomma
cadbfad  fix: sidan frös i scroll (fäst bakgrund)
2a454af  fix: analysvyn visade påhittade siffror
b50a44b  feat: admin kan öppna vilken kunds arbetsyta som helst
fb545d2  feat: appen går att installera på hemskärmen
9519e8e  fix: kundens bolagslista var fem påhittade bolag
2f5b502  fix: Svar och Kontakter visade påhittade personer
1c8cf85  fix: assistentfliken är märkt som exempel
d858d40  fix: fem fjärrversioner saknade fil i repot
e929288  fix: trendstaplarna ritades inte, Score/Status-kollaps
fb9592b  feat: appen installerbar på alla tre plattformar
faee48b  fix: Chrome erbjöd "Skapa genväg" i stället för "Installera"
0327687  fix: flikraden hamnade under Admin/Demo-växeln
efb57ab  feat: nytt märke — S:et ersätter fågeln
a8e245c  feat: logotypen som husets märke i hjältebilden
63b00e0  doc: Supabase-grenens fel är inte SQL:en
de4c300  fix: Email Studio körde aldrig mot en modell + tre 500:or
34731e3  fix: en ny kund möttes av en databasinstruktion
4a89818  feat: DNS hos Loopia är ett kommando
```

128 filer, +9233/-1680.
