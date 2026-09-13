# Pilotonboarding på en timme

Kunskapsbasen fylls i dag helt för hand. Onboardingen sparar orgnr och webbplats
som text och slår inte upp något. `scripts/pilot_kb_utkast.py` gör grovjobbet:
kundens egen sajt blir artikelutkast plus en lista med luckor att gå igenom på
pilotmötet. Skriptets docstring är specifikationen för det automatiska flödet.

## Kommandot

Kör med backendens venv, eftersom skriptet importerar `app.leads`, `app.config`
och `app.api.schemas`:

```bash
PY=snajp-support/.venv/Scripts/python

# 1. Torrkörning (standard). Hämtar högst 15 sidor och gör högst 4 Gemini-anrop.
$PY scripts/pilot_kb_utkast.py --orgnr 556824-9022 --webbplats https://bolaget.se

# 1b. Samma kedja utan nät och LLM, mot tests/fixtures/pilot_kb/
$PY scripts/pilot_kb_utkast.py --orgnr 556824-9022 \
    --webbplats https://www.lingonkudden-exempel.se --simulera --ut var/pilot/sim

# 2. Granska kb-utkast.md och sätt "godkand": true i kb-utkast.json (se nedan).
# 3. Skicka in de godkända artiklarna. Nyckeln läses ur SNAJP_PILOT_TENANT_KEY
#    (miljön eller .env.deploy), aldrig från argv.
$PY scripts/pilot_kb_utkast.py --orgnr 556824-9022 --apply \
    --api-base https://<backend> --tenant-namn "Bolaget AB"
```

Utfilerna hamnar i `var/pilot/<orgnr>/` (gitignorerad):
`kb-utkast.md` är till för granskningen och `kb-utkast.json` används av `--apply`.

LLM-steget kräver `LLM_PROVIDER=gemini` i `snajp-support/.env`. Autentiseringen
sker via Vertex AI när `GOOGLE_SERVICE_ACCOUNT_JSON` finns, annars via
`GEMINI_API_KEY`. Med alla andra providrar avbryter skriptet, DeepSeek inräknat.

## Vad du granskar (ungefär 40 minuter, gärna med kunden)

1. **Varje artikel mot källsidan.** Varje artikel har en källänk och ett
   confidence-värde. En varning betyder att artikeln innehåller en siffra som
   inte står i källan, eller att modellen föreslog en kategori som inte finns.
   Rätta texten i JSON-filen och sätt `"godkand": true` på de artiklar som ska in.
2. **Luckorna.** Sju punkter kommer alltid med och markeras hittad, delvis
   eller saknas: villkorstexter, garantier, prislista, de tio vanligaste
   kundfrågorna, målgrupp (3 drömkunder och 3 nej-bolag), avsändaradress och
   ärenden som alltid ska till en människa. Tre av dem kan aldrig bli
   "hittad" utifrån en sajt. Där är de listade frågorna själva mötesagendan.
3. **Genomsökningen.** Längst ned i md-filen står det som inte blev läst:
   - PDF:er, som läses in via Kunskapsbas och sedan PDF (förhandsvisas och godkänns).
   - Sidor som robots.txt blockerade. Be kunden om texten i stället.
   - Sidor över sidtaket.
4. **Bransch/SNI** står som "ej uppslaget". Slå upp den manuellt tills
   uppslaget byggs. Kroken heter `sla_upp_bransch`.

## Hur det här blir det automatiska flödet

| Skriptet i dag | Produkten sedan |
|---|---|
| `validera_orgnr` | Finns redan i `lib/orgnr.ts` och `app/leads/orgnr.py` |
| `sla_upp_bransch` (stub) | Registeruppslag mot ett avtalat API (se `app/leads/sources/registry.py`), klartext ur `app/leads/sni.py` |
| `genomsok` + `utkast_med_llm`, körs för hand | Engångsjobb som startas av `saveBusinessContext` när onboardingen sparas |
| `kb-utkast.md` + `"godkand": true` | Förslagslista i Kunskapsbas-vyn med en kryssruta per artikel, samma mönster som PDF-förhandsvisningen |
| `bedom_luckor` | Checklista i onboardingen som kunden fyller i |
| `--apply` till `POST /api/kb` | Samma endpoint, anropad när kunden godkänner |

**Engångsskrapningen är ingen synkning.** Att hämta om sajten löpande och hålla
KB:n uppdaterad när kunden ändrar något är tillägget **Synkad kunskapsbas**
(`kb_autoingest` i `lib/addons.ts`). Det är drift, inte uppsättning. Det
automatiska onboardingflödet ska därför aldrig schemalägga en ny hämtning. Det
föreslår en gång, och resten ingår i tillägget.
