# Handoff till Sebbes agent — 2026-08-30

**Uppföljning 2026-08-31:** se [HANDOFF-2026-08-31-TESTLAGER-OCH-UI.md](HANDOFF-2026-08-31-TESTLAGER-OCH-UI.md)
(exempelkörningar, inkorg, testchatt, impersonation). `oauth.ts` orörd.

Två saker: en ändring jag gjort i en fil du ägde igår, och ett rött
invarianttest i din Skatteverket-kod som jag inte rört.

## 1. `_kb_block` wrappar nu KB-text som opålitlig (min ändring)

**Commit:** `sec: KB-artiklarnas text wrappas som opålitlig, inte bara placeras rätt`
**Filer:** `snajp-support/app/agent/support_agent.py` (en funktion, rad ~176),
`tests/invariants/test_inv_sec_012.py`, `ARCHITECTURE_INVARIANTS.md` (INV-SEC-012).

### Varför

Fas 5 gav kunskapsbasen två nya inmatningsvägar — textfilsuppladdning och
PDF-extraktion (`POST /api/kb/extrahera`) — som landar i samma skrivväg som
textrutan alltid gjort: `POST /api/kb` → `storage.add_kb_article`. Skillnaden är
inte kodvägen utan kontrollen: en vidarebefordrad PDF kan bära en
instruktionsattack utan att kunden läst varje rad.

När INV-SEC-012 skrevs igår upptäcktes att `_kb_block` konkatenerade
artikeltexten rakt in i `case_context` utan `wrap_untrusted_content`. Positionen
var säker — `step_runner.run_step` lägger alltid `case_context` i
användarposition, aldrig i `messages[0]` — men den explicita ramen saknades,
den som SOUL (INV-SEC-009) och produktmarknadsföringstexten redan hade.
`support_agent.py` ägdes då av din session, så gapet dokumenterades i stället
för att lagas. Det är nu lagat.

### Vad som ändrades

```python
def _kb_block(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return "(inga träffar)"
    return wrap_untrusted_content(
        "\n\n".join(f"### {a['title']}\n{a['content']}" for a in articles),
        source="tenant:kb_article",
    )
```

Tre saker att veta om du bygger vidare i samma funktion:

- **Tomfallet är owrappat med flit.** `"(inga träffar)"` är vår egen text, inte
  kundens — att rama in den vore att kalla vår egen prompt opålitlig.
- **Grundningsgrinden är orörd.** Den läser `articles`, inte `kb_block`, så den
  tillåtna faktamängden ser exakt likadan ut som förut. Ramen syns bara i
  prompten (rad ~552, ~619, ~724).
- **`wrap_untrusted_content` var redan importerad** (rad 36) — ingen ny
  beroendekant.

### Invarianten är skärpt, inte bara uppdaterad

INV-SEC-012 kräver nu **två lager**, inte ett: positionen OCH ramen. Rubriken
bytte namn därefter (`… är opålitlig text i användarposition`). Testet mäter
båda: `test_kb_article_reaches_user_position_never_system` för lager 1,
`test_kb_article_is_wrapped_as_untrusted` för lager 2 — det senare kräver att
sentinelen ligger *inuti* ett `<untrusted-data-… source='tenant:kb_article'>`-block,
inte bara att markören finns någonstans i meddelandet. Ett regex som bara letar
efter strängen `untrusted-data-` hade passerat även om ramen låg runt SOUL och
KB-texten låg utanför.

**Verifierat:** `tests/invariants/test_inv_sec_012.py` 3 passed;
snajp-supports fulla svit 1586 passed, 4 skipped. Rebasen mot din
`origin/development` gick rent — ingen av dina 25 commits rörde
`support_agent.py`.

## 2. Rött invarianttest i Skatteverket-koden — din, inte min

`tests/invariants/test_inv_api_001.py::test_svar_tolkas_aldrig_som_json_utan_kontroll[lib/skatteverket/oauth.ts]`
failar på `development` just nu. Den fanns före min ändring och kommer från
`345667b Montera Skatteverket-knappen och koppla in de request-skopade agenterna`.

```
lib/skatteverket/oauth.ts:158: await svar.json()
```

Raden ligger efter `if (!svar.ok)`, så 4xx/5xx är redan avhandlat — men
invarianten fäller på något smalare: ett **200 med tom eller icke-JSON-kropp**.
Funktionen dödas vid `maxDuration`, en tjänst vaknar ur viloläge och svarar
HTML, eller svaret är 204. I alla tre fallen kastar `.json()` `Unexpected end of
JSON input`, och det meddelandet är det kunden ser.

Fixen är en rad — `readJson` eller `readJsonBody` från `lib/http/json.ts` — men
`data` typas som `TokenSvar` och båda hjälparna returnerar `T | null`, så
null-fallet behöver ett eget kast med en läsbar text. Jag lämnar den åt dig
eftersom `!data.access_token`-grenen strax under redan är din formulering av
"Skatteverket svarade fel", och de två bör låta likadant.

Övriga 329 invarianttester gröna.

## 3. Tillägg 2026-08-30: NameError i din Skatteverket-trådning — lagad

`_gather_registered_sources` i `snajp-support/app/agent/leads_agent.py` byggde
`ResearchContext(..., skatteverket=skatteverket)` utan att ta emot parametern
(kom med trådningen av Skatteverket-verktyget). Följd i live dev: **varje**
jobb ur `/api/leads/runs/batch` dog med `name 'skatteverket' is not defined`
före första LLM-anropet — kunden såg bara exempelbolagens deterministiska
utkast. Sviten var grön eftersom alla batchscenarier monkeypatchar
`run_research_step`.

Lagad (parametern tillagd + trådad, omockat regressionstest i
`tests/leads/test_batch_markering.py`, verifierat rött→grönt), deployad och
verifierad med en riktig batchkörning mot live dev som gick till completed.
Punkt 2 (oauth.ts `.json()`) står kvar hos dig.

## 4. Deploytriggern för development har slutat fira

Inget deployades automatiskt efter 2026-08-29 22:42Z trots ~30 pushar —
dina nattcommits och dagens gick aldrig live förrän jag deployade manuellt
via `railway_provision.deploy()`. Triggrarna står rätt i Railway
(development→development för web+api), så felet ligger troligen i
GitHub-App-kopplingen eller trial-planen. Tills det är löst:

```bash
python -c "import sys;sys.path.insert(0,'scripts');from railway_provision import deploy;EID='02c39616-1b8e-47b7-beea-d8c6cfba1acd';print(deploy('5828c279-ad8f-429b-b5e1-969372db8a0a',EID));print(deploy('0261f633-1247-4d92-b5ab-40c2a1828b90',EID))"
```
