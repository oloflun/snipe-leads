# Handoff: instruktionslagren, adminkontrollen och vad som INTE följer med en push

Skriven 2026-08-25 till Sebbe. Läs § "Det du behöver göra" först om du har bråttom.

---

## Vad som var fel, och varför ingen såg det

`agent_configs.instructions_md` och `.tone` har funnits i schemat sedan
migration 010. **Ingen kodväg har någonsin läst dem.** Ingen yta skrev dem
heller. En kund kunde alltså fylla i sina instruktioner, spara, och få exakt
samma svar som förut — texten lämnade aldrig databasen.

Affärskontexten hade samma form av fel, fast halvvägs: den lästes av
leads-agenten och aldrig av supportagenten. En supportkund kunde beskriva hela
sin verksamhet utan att ett enda supportsvar visste om det.

Det som gjorde det osynligt är att allt annat såg rätt ut. Fältet fanns,
sparningen returnerade 200, agenten svarade. Symptomet hos användaren var
"jag ändrar instruktionerna och ingenting händer", vilket låter som en
modellkvalitetsfråga och inte som en saknad `select`.

---

## Vad som byggdes

### Migration 049

Två saker:

- `agent_global_instructions` — plattformens egna regler, admin-redigerade.
  Ersätter `agent-core/AGENTS.md` i drift; **filen är kvar som fallback** när
  ingen rad är aktiv, alltså exakt beteendet före 049.
- `agent_configs.instructions_rav` — råtexten bakom den strukturerade.

Versionerad genom insert, en aktiv rad i taget (partiellt unikt index). Historik
gratis, och `agent_runs.pack_version` kan peka ut vilken text en körning läste.

### Skiktordningen i systemprompten

```
global  ->  skill  ->  overlay  ->  KUND  ->  kontrakt
```

Kundlagret ligger sist av instruktionerna för att det är mest specifikt: en
overlay gäller ett steg för alla kunder, kundinstruktionen gäller alla steg för
en kund. Kontraktet ligger under allt och kan inte nås av något tuninglager.

### Positionen är säkerhetsgränsen, inte en rollfråga

Instruktionsfälten är **admin-only** och går i **systemposition**. Kundskriven
text (SOUL, affärskontext, kunskapsbas) ligger kvar i **användarposition**,
wrappad som opålitligt innehåll.

Gränsen går vid **vem som skrev texten**, inte vid vad den handlar om. En kund
ska kunna be om en ton och ska inte kunna be om att reglerna ignoreras, och den
enda robusta skillnaden mellan de två är positionen i meddelandekedjan.

> **Flyttar du ett instruktionsfält till kundens egen yta måste det samtidigt
> flyttas till användarposition. De två besluten är ETT beslut.** (INV-SEC-009)

### Struktureringen

Admin skriver löpande text och feedback. Modellen gör om det till imperativa
regler under fasta rubriker. Råtexten sparas orört och når aldrig prompten.

En kodgrind efter modellen städar bort ```-staket, inledande artigheter och
avslutande frågor, och underkänner okända rubriker. Misslyckas den sparas
råtexten som den är (`kalla='manuell'`) i stället för att kastas — att förlora
någons anteckningar för att en endpoint svajade är dyrare än en instruktion som
inte blev snyggt formaterad.

### Adminytan

- `/admin/installningar/agentinstruktioner` — globala reglerna. Två rutor: vad
  du skriver, och vad agenten läser. Plus versionshistorik.
- `/admin/kunder/<id>` — kundprofilen som saknades. Instruktioner, ton,
  röstdokument och affärskontext per kund och agenttyp, **med positionen
  utskriven vid varje fält**, och en sparknapp per sektion.

Din vidareutveckling av båda komponenterna (facketiketter, skelettillstånd,
sparning per fält i stället för delad `isPending`, exempeltexter) ligger kvar
och är med i commiten. Tack för den.

### KB-sökningen

Vektorvägen filtrerade på `embedding is not null` och hade ingen fallback när
den kom tom. Tom träfflista är ett hårt eskaleringsvillkor, så en retrievalmiss
blev ett ärende hos en människa i stället för ett sämre svar. Vektor och
fulltext kedjas nu i `storage.search_kb`.

Det är alltså en tredje sak utöver dina två i `c983dd9`: du lagade
anropsnivån (tre sökförsök, `kb_supports_answer` i kod, följdfråga vid tunt
bibliotek), det här lagar källan.

---

## Konflikterna i rebasen, och hur de löstes

Två, båda i `support_agent.py`, båda kommentarer eller importer.

1. **Importblocket.** Din `prioriterat_mejl` mot min `wrap_untrusted_content`.
   Båda behölls.
2. **Kommentaren över `escalated`.** Din version beskriver den nuvarande
   logiken (du tog bort `not articles` och införde `kb_saknar_svar`); min
   beskrev ett villkor som inte finns kvar. **Din text vann**, plus ett stycke
   om kedjningen i lagringslagret, som din kommentar inte täckte.

`abuse_gate`-flytten till `app/moderation/` löstes automatiskt.

### En bugg rebasen införde, och som är lagad

`_fanga_kunskap` (ditt nya steg 9, `sa:call-summary`) anropade `run_step` utan
`instruktioner`. Steget hade alltså läst filens `AGENTS.md` medan de åtta
stegen omkring det läste kundens — det körs, det loggas, och ingenting felar.
Lagret tråds nu igenom som i `_run_grounding_cycle`.

**Regeln att hålla:** varje `await run_step(` ska bära `instruktioner=`.
Support-sidan har garantin genom att alla anrop går via
`partial(run_step, instruktioner=lager)`. Lägger du ett nytt steg i leads,
skicka lagret.

---

## Hur du kontrollerar att ett fält faktiskt når fram

```bash
python scripts/verifiera_instruktioner.py           # utan LLM, bara positionerna
python scripts/verifiera_instruktioner.py --skarp   # + ett riktigt modellanrop
```

Fyller varje fält med en unik markör, kör en riktig agentkörning och rapporterar
var varje markör hamnade. Sex av sex ska stå i rätt kolumn, och den globala
regeln ska finnas i **alla** steg — inte bara det första.

Fältkartan över vilket fält som ändrar vad: [`docs/FALTKARTA.md`](docs/FALTKARTA.md).

---

## Det du behöver göra

### 1. Migration 049 är INTE körd i main

```bash
python scripts/railway_migrate.py --env main --apply
```

Main saknar **043 till 049**. Den nya koden träffar en tabell som inte finns om
den deployas dit först. Development har hela kedjan.

### 2. Två miljövariabler saknas i main

| Variabel | Tjänst | Utan den |
|---|---|---|
| `SNAJP_KEY_LIVRUSTNING`, `SNAJP_KEY_SNAJP`, `SNAJP_KEY_TESTKUND` | web | registrerad kund utan nyckel avvisas (`MissingTenantKeyError`) |
| `PUBLIC_BASE_URL` | api | `send_guard` blockerar varje utskick, avregistreringslänken går inte att bygga |

### 3. Gemini-nyckeln ligger på FREE TIER

Uppmätt i kväll: `429 RESOURCE_EXHAUSTED`, kvot **20 anrop per dygn** för
`gemini-3.6-flash`. Ett supportärende kostar sex till sju anrop, alltså ungefär
tre ärenden per dygn för hela plattformen.

Nyckeln fungerar (403-spärren är borta sedan Cloud-kontot aktiverades), men den
räcker inte till drift. Det är en betalningsfråga och kräver Anton.

**Och en fälla:** repots `.env` bar ett tag en ANNAN nyckel än Railway, från ett
projekt som aldrig aktiverades. Båda var 53 tecken, vilket dolde skillnaden.
Jämför sista sex tecken, inte längden, om något beter sig olika lokalt och i
drift. Rätt nyckel slutar på `P-A2Mw`.

---

## Orphans utanför Railway

Ingen Railway-variabel pekar på Render, Supabase eller Vercel — den betjänande
vägen är alltså Railway-ren. Men tre saker lever kvar:

1. **Render-backenden svarar.** `snajp-support.onrender.com/health/ready` ger
   200 med `storage: postgres`. En andra levande backend med databaskoppling.
   Värd att stänga, och den korsar dataskyddsarbetet.
2. **`keep-backend-awake.yml`** pingar den var tionde minut, vardagar 06–17.
   Håller orphanen varm.
3. **Supabase är fortfarande fyllt**: 5 användare, 4 tenants, 48 KB-artiklar,
   26 ärenden, 52 meddelanden, 18 körningar.

Konfigurationen är flyttad. `scripts/flytta_fran_supabase.py` tog 10
KB-artiklar och 2 kontextdokument till både main och development, och den är
idempotent.

### Importen som sänkte Nordlys Handel, och grinden som stoppar den nu

Den första versionen av det skriptet skrev importerade dokument som
`max(version) + 1`, alltså som **senaste**. `get_latest_context_doc` plockar
just den. Följden i development: affärskontexten gick från kundens 726 tecken
till en 43 teckens stubbe ur Supabase, och röstdokumentet från 1024 till 39.
Agenten bytte underlag mitt i drift och ingenting felade.

Det är återställt (kundens versioner är senaste igen, ingen historik raderad)
och `far_importeras()` gör om det omöjligt: **ett dokument från Supabase får
bara fylla ett tomt fack.** Ingen jämförelse på tidsstämpel eller längd — båda
kan ljuga, riktningen mellan systemen kan inte. Supabase är den avvecklade
stacken.

```bash
python scripts/flytta_fran_supabase.py --demo    # självkontrollen
```

---

## Läget just nu

- 1317 backendtester gröna (`pypdf` saknades lokalt, står i requirements.txt).
- TypeScript rent.
- `detect.mjs` rent mot adminkomponenterna.
- Sex av sex fält når agenten i rätt position, globala regeln i alla steg.
- Migration 048 och 049 körda i **development**. Main väntar.
- `development` deployar numera till Railway via speglingen till
  `railway-development` — den pushen behöver alltså inte längre göras för hand.

Öppet och inte mitt att avgöra: **main ligger 37 commits efter och kör
regelmotorn, inte AI.** `/health/ready` på main säger `mode: simulation`. Varje
riktigt kundärende i produktion får ett konserverat svar tills koden deployas
dit.
