# Handoff — hela sessionen 2026-08-30, till Grok

Den här filen sammanfattar ALLT som gjordes i den här sessionen, i ordning,
plus ett nytt fynd i slutet som förklarar varför Anton fortfarande ser
"färdiga exempel direkt" i leads-flödet trots att backend-buggen är lagad.
Den kompletterar (ersätter inte) [`HANDOFF-2026-08-30-KB-WRAP.md`](HANDOFF-2026-08-30-KB-WRAP.md),
som är riktad till Sebbes agent om KB-wrappen och oauth.ts.

## 0. Vad sessionen faktiskt löste, i ordning

1. **KB-artikeltext wrappas nu som opålitlig text** (`_kb_block`,
   `snajp-support/app/agent/support_agent.py`). Se punkt 1 i KB-WRAP-handoffen.
2. **INV-SEC-012 skärpt** till att kräva två lager (position + ram), inte
   bara position. Se samma fil, punkt 1.
3. **NameError i leads-batchen lagad**: `_gather_registered_sources` i
   `snajp-support/app/agent/leads_agent.py` byggde `ResearchContext(...,
   skatteverket=skatteverket)` utan att funktionen tog emot parametern.
   Varje jobb ur `/api/leads/runs/batch` dog med `name 'skatteverket' is not
   defined` FÖRE första LLM-anropet. Parametern tillagd och trådad, ett
   omockat regressionstest verifierat rött→grönt, deployat.
4. **Deploytriggern för `development` var död** — inget hade deployats
   automatiskt sedan 2026-08-29 22:42Z trots ~30 pushar. Deployade manuellt
   via `railway_provision.deploy()` (api + web), båda SUCCESS. Grundorsaken
   (GitHub-App-koppling eller trial-plan) är INTE löst — bara symptomet.
5. **Live-verifiering, riktigt konto:** en batchkörning mot
   `web-development-6c85.up.railway.app` som admin-tenanten (`snajp`) gick
   hela vägen till `status: completed` med 9 riktiga skill-steg och Gemini-
   anrop. Job-id `9141d801-2ef4-45a1-899e-04cc24ec85f8`.

Punkt 3+4+5 är varför jag rapporterade till Anton att leadskörningar
"fungerar" — och det stämde för BACKENDEN. Punkt 6 nedan är vad jag missade:
frontendens formulär visar aldrig det riktiga resultatet, så Anton såg exakt
samma sak som innan trots att backend-buggen var borta.

## 1. Feedback till Grok: leads-formuläret visar aldrig den riktiga körningen

**Fil:** `components/leads/LeadsRunForm.tsx`
**Rader:** checkboxen `exempelbolag` initieras till `true` (rad ~158,
`useState(true)`), och `kör()`-funktionen (rad ~250-303) postar batchen men
pollar ALDRIG jobbens status och visar ALDRIG deras resultat.

### Mekaniken

Varje körning gör två helt separata saker, och bara den ena syns i UI:t:

1. **Exempelbolag** (`POST /api/leads/prospects/exempel` →
   `bygg_exempelbolag` i `snajp-support/app/leads/exempelbolag.py`).
   Deterministisk, noll LLM-anrop, svarar på millisekunder. Varje bolag
   kommer redan med `pitch_subject` och `pitch_body` — ett komplett,
   färdigskrivet säljmejl (se `exempelbolag.py` rad ~284-293). Detta är
   texten Anton ser direkt.

2. **Den riktiga batchkörningen** (`POST /api/leads/runs/batch` →
   `run_research_step`, 9 riktiga skill-steg, sekunder till minuter per
   bolag). `kör()` sparar svaret i `setSvar(resultat)`, men `resultat`
   innehåller bara `{jobs: [{job_id, prospect_id}], count, scope,
   overrides}` — INGEN forskningstext. Ingenstans i komponenten pollas
   `job_id` mot `/api/jobs/{id}` för att hämta det färdiga resultatet. Sök
   själv: `grep -n "job_id" components/leads/LeadsRunForm.tsx` ger bara
   typdeklarationen, ingen polling-loop.

Eftersom `exempelbolag` är true som DEFAULT, och `Exempelbolagslista`
renderas direkt när `bolag.length > 0` (rad ~458), är det FÖRSTA och ENDA
Anton ser efter klick: exempelbolagens färdigskrivna pitchar. Den riktiga
körningen pågår i bakgrunden, avslutas, och resultatet hamnar ingenstans i
det här formuläret. Det ser exakt ut som "genererar färdiga exempel direkt"
— för att det bokstavligen är vad som renderas, oavsett om backend-buggen
finns eller ej.

### Vad jag INTE gjorde

Jag rörde inte `LeadsRunForm.tsx` denna session — Sebbes/Groks yta enligt
tidigare uppdelning, och en UI-ändring mitt i en pågående annan session
kändes fel att göra oanmält. Det här är alltså ett FYND, inte en fix.

### Rekommenderad fix, för den som tar den

Två rimliga vägar, inte ömsesidigt uteslutande:

- **Minimalt:** lägg till en pollingloop i `kör()` efter
  `runs/batch`-anropet, samma mönster som testchattens `jobb/[jobId]`-route
  redan använder (se `app/api/snajp-support/testchatt/jobb/[jobId]/route.ts`
  för referensimplementationen). Visa "Körningen pågår… (N/M klara)" tills
  alla job_id är `completed`/`failed`, sedan resultatet.
- **Tydligare för användaren:** separera visuellt "exempelbolag" (märkt
  `Exempel`, kan aldrig mejlas — märkningen finns redan i
  `Exempelbolagslista`, se dess docstring) från "riktig körning pågår" så de
  aldrig kan förväxlas, ens innan polling är klar.

Verifiera fixen mot `https://web-development-6c85.up.railway.app` inloggad
som `snajpsupport@gmail.com` (lösenord i `scripts/qa_vyer.mjs`), inte bara
mot testsviten — det här är precis den klassen bugg (UI:t ljuger om vad som
hände) som en grön svit inte fångar, för att sviten aldrig renderar
komponenten och läser vad som faktiskt visas.

## 2. Verifieringskommandon som användes (för att reproducera)

```bash
# Trigga en manuell deploy när Railway-triggern inte fyrar:
python -c "import sys;sys.path.insert(0,'scripts');from railway_provision import deploy;EID='02c39616-1b8e-47b7-beea-d8c6cfba1acd';print(deploy('5828c279-ad8f-429b-b5e1-969372db8a0a',EID));print(deploy('0261f633-1247-4d92-b5ab-40c2a1828b90',EID))"

# Läs senaste deployloggen för api-tjänsten i development:
python scripts/railway.py q 'query($eid:String!,$sid:String!){deployments(first:1,input:{environmentId:$eid,serviceId:$sid}){edges{node{id createdAt status}}}}' '{"eid":"02c39616-1b8e-47b7-beea-d8c6cfba1acd","sid":"5828c279-ad8f-429b-b5e1-969372db8a0a"}'
```

`scripts/railway.py` läser token ur `.env.deploy`, skriver aldrig ut den.
Miljö-id:n för `development`: `02c39616-1b8e-47b7-beea-d8c6cfba1acd`.
Tjänste-id:n: `web=0261f633-1247-4d92-b5ab-40c2a1828b90`,
`api=5828c279-ad8f-429b-b5e1-969372db8a0a`.
