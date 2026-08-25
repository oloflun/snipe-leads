# Fältkartan: vilket fält ändrar vad

Varje ifyllbart fält i produkten, var det lagras, vem som läser det, och **var i
prompten det hamnar**. Läget per 2026-08-24, efter migration 049.

Kartan finns för att frågan "jag ändrade X, varför hände ingenting?" hade fyra
olika svar och inget ställe att slå upp dem på. Tre av svaren var buggar.

## Varför positionen är kartans viktigaste kolumn

Två textrutor som ser likadana ut i ett formulär gör helt olika saker:

- **system** — agenten läser texten som **regler** och följer dem. Bara vi kan
  skriva här.
- **user** — agenten läser texten som **uppgifter** och följer den inte. Kundens
  text ligger här, inramad som opålitligt innehåll.

Gränsen går vid **vem som skrev texten**, inte vid vad den handlar om. En kund
ska kunna be om en ton och ska inte kunna be om att reglerna ignoreras, och den
enda robusta skillnaden mellan de två är positionen i meddelandekedjan
(INV-SEC-009, `snajp-support/app/leads/soul.py`).

Flyttas ett fält från admin till kundens yta **måste** det samtidigt flyttas
till user-position. De två besluten är ett beslut.

---

## Instruktionslagren — vår text, system-position

| Fält | Yta | Lagras i | Läses av | Position |
|---|---|---|---|---|
| Globala agentinstruktioner | `/admin/installningar/agentinstruktioner` | `agent_global_instructions.strukturerad_md` | `agentcore/instruktioner.py:las_instruktioner` | system, **först** |
| — fallback när inget sparats | (git) | `agent-core/AGENTS.md` | `agentcore/overlays.py:load_global_instructions` | system, först |
| Kundinstruktioner | `/admin/kunder/<id>` | `agent_configs.instructions_md` | samma | system, **efter overlayen** |
| Steg-overlay | git (PR) | `agent-core/overlays/*.md` | `agentcore/overlays.py:load_overlay` | system, efter skillen |
| Vendorad skill | git (låst) | `agent-core/skills/<ns>/<id>/` | `agentcore/registry.py:load_full_skill` | system |
| Utdatakontrakt | kod | `agent/step_runner.py:_CONTRACT_INSTRUCTION` | — | system, **sist och ovillkorligt** |

Ordningen i systemprompten är `global → skill → overlay → kund → kontrakt`.
Senare vinner vid konflikt, och avgränsartexten säger det uttryckligen. Kontraktet
ligger sist därför att inget tuninglager ska kunna försvaga det.

**Råtexten** (`agent_global_instructions.ravtext`,
`agent_configs.instructions_rav`) når **aldrig** prompten. Den sparas för att
struktureringen ska gå att köra om, och för att frågan "vad bad vi om?" ska ha
ett svar som inte är modellens omskrivning.

---

## Kundens egna fält — user-position

| Fält | Yta | Lagras i | Läses av | Position |
|---|---|---|---|---|
| Röstdokument (SOUL) | `/settings/soul` · `/admin/kunder/<id>` | `agent_context_docs` kind=`soul` | `leads/soul.py:load_soul` | user, wrappad |
| Affärskontext | `/settings/affarskontext` · `/admin/kunder/<id>` | `agent_context_docs` kind=`product_marketing` | `leads/context_pack.py` (leads), `agent/support_agent.py` (support) | user, wrappad |
| Kunskapsbas | `/settings/kunskapsbas` | `ss_knowledge_base` | `storage.search_kb` | user, **enda faktakällan** |
| Tonläge | `/admin/kunder/<id>` | `agent_configs.tone` | `agent/support_agent.py` | user (ärendekontext) |
| Kanalton (default) | — (seed) | `ss_channel_configs.tone` | samma | user (ärendekontext) |

Tonen har två källor med en tydlig ordning: kundens egen `agent_configs.tone`
vinner, kanalens `ss_channel_configs.tone` gäller när den är tom.

**Affärskontexten har två lagringsplatser och de är inte synkade.** Dashboardens
formulär skriver `business_contexts` (per **arbetsyta**, i Next-appens databas)
och skickar dessutom vidare till `agent_context_docs`. Agenten läser **bara**
det senare. Se `lib/actions/affarskontext.ts` och
`snajp-support/app/leads/business_context.py`; avvikelsen är noterad med flit,
inte hopjämkad.

---

## Fält som styr KODEN, inte prompten

De här ändrar vad som händer, inte vad modellen läser. Ett vanligt
missförstånd — man ändrar dem och letar sedan efter en skillnad i texten.

| Fält | Yta | Lagras i | Vad det gör |
|---|---|---|---|
| Autonominivå | `/settings/leads` | `agent_configs.settings.autonomy` | `draft` / `first_contact` / `meeting` — om ett utkast får skickas utan människa (`leads/autonomy.py`) |
| ICP (målgrupp) | `/settings/leads` | `agent_configs.settings.icp` | urvalet av prospekt (`leads/icp.py`). SOUL styr ton, ICP styr urval |
| Fackregler | `/settings/regler` | `ss_category_rules` | `auto` / `draft` / `escalate` per fack (`api/rules.py`) |
| Ärendetaxonomi | — | `agent_configs.taxonomy` | vilka fack som är giltiga; hamnar även i ärendekontexten |
| Inkorgar | `/settings/mailboxes` | `ss_inboxes` | vilka adresser som läses |
| Notiser | `/settings/notiser` | `notification_preferences` | per **användare**, inte per arbetsyta |
| Tema | `/settings/tema` | cookie | bara den här webbläsaren |
| Plan och tillägg | `/settings/billing`, `/settings/addons` | `workspaces.products`, `.addons` | vilka vyer och produkter som finns |
| Spårningsnivå | — | `agent_configs.settings.trace_verbose` | om `agent_runs.step_log` bär hela prompttexten |

---

## Hur du kontrollerar att ett fält faktiskt når fram

```bash
python scripts/verifiera_instruktioner.py
```

Fyller varje fält med en unik markör, kör en riktig agentkörning och rapporterar
vilken position varje markör hamnade i. `--skarp` lägger till ett riktigt
modellanrop och kontrollerar att modellen faktiskt lydde instruktionen.

I efterhand: `agent_runs.step_log` bär `global_chars`, `kund_chars`,
`overlay_chars` och `instruktionshash` per steg — noll tecken betyder att lagret
var tomt, inte att det gick fel. `pack_version` bär samma hash, så två körningar
med olika regler aldrig ser ut att ha samma version (INV-AUDIT-001).

---

## Vad som var trasigt före 2026-08-24

Kartan hade tre osanningar, och alla tre visade sig som "jag ändrar något och
ingenting händer":

1. `agent_configs.instructions_md` och `.tone` fanns sedan migration 010. Ingen
   kodväg läste dem, ingen yta skrev dem.
2. Affärskontexten lästes **bara** av leads-agenten. En supportkund kunde
   beskriva hela sin verksamhet utan att ett enda supportsvar visste om det.
3. Vektorsökningen i kunskapsbasen hade ingen fallback till fulltext när den kom
   tom tillbaka. Tom träfflista är ett hårt eskaleringsvillkor, så en
   retrievalmiss blev ett ärende hos en människa i stället för ett sämre svar.

Och en fjärde, som inte är en kartfråga men som gör hela kartan overksam medan
den gäller: **når ingen LLM-provider fram kör tjänsten sin deterministiska
regelmotor**, och då spelar det ingen roll vad som står i något fält.
`GET /health/ready` svarar `"mode": "simulation"` när det är läget. Kontrollera
den först.
