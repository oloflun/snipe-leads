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

## Avtal och dataskydd före första trafik

Stegen tas i den här ordningen. Ingen riktig kundtrafik (chatt, inkommande
mejl, kanaler, utskick) innan alla sju är gjorda.

> **Varning:** `scripts/onboard_tenant.py` pekar fortfarande på den gamla
> infrastrukturen: Vercel-nycklar (`vercel_env_set`) och Supabase
> (`NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`). Vercel är
> avvecklat och Supabase får inte skrivas till (se CLAUDE.md). Använd inte
> skriptet för en ny kund förrän det är omskrivet för Railway.

1. **Personuppgiftsbiträdesavtalet undertecknat.**
   Gör: `docs/pub-avtal.md` är ett ogranskat utkast. Det granskas av jurist,
   Bilaga 3 (underbiträden) fylls i med de underbiträden kunden faktiskt
   berörs av, och båda parter skriver under.
   Klart när: ett undertecknat exemplar med ifylld Bilaga 3 finns arkiverat.
2. **Företagsnamn, organisationsnummer och postadress i kundregistret.**
   Gör: admin, fliken Kunder & Data, kundens datavy (`app/admin/kunder/[id]/data`), fälten
   Organisationsnummer och Företagets adress; företagsnamnet är tenantens namn.
   Alternativt `python scripts/fyll_kundregister.py --slug <slug> --orgnr ...
   --foretagsadress ... --apply` (går via admin-API:t, standardmiljö
   development; mot main krävs `--env main --jag-menar-produktion`).
   Klart när: samma skript utan `--apply` listar fälten som ifyllda, och ett
   utkasts sidfot bär "<namn>, org.nr <nummer>" och adressen
   (`app/leads/utskicksfot.py`).
3. **Avtalsgrinden på och avtalsdatumet registrerat.**
   Gör: det finns ingen admin-yta eller API som sätter `ss_tenants.kraver_avtal`;
   den sätts med SQL, som migration 070 gjorde för Livrustning:
   `update ss_tenants set kraver_avtal = true where slug = '<slug>';`
   Lägg den helst som en ny additiv migration i `db/migrations/` så att
   `.github/workflows/migrera.yml` kör den mot Railway, aldrig mot Supabase.
   Avtalsdatumet sätts av en människa som sett avtalet: samma datavy i
   Kunder & Data, fältet Avtal signerat (`ss_customer_details.avtal_signerat`).
   `fyll_kundregister.py` kan med flit inte sätta det.
   Klart när: `select kraver_avtal from ss_tenants where slug = '<slug>'` ger
   `true` och fältet Avtal signerat har ett datum. Utan datum svarar chatten
   med spärrtexten i `snajp-support/app/avtalsgrind.py` (`KUNDTEXT_AVTAL`);
   ändringen slår igenom inom en minut (grindens cache).
4. **Art. 13-texten till kunden och kundens integritetspolicy länkad.**
   Gör: skicka `docs/kundmall_informationstext.md` till kunden, som lägger in
   texten på sin kontaktsida och i sin integritetspolicy. Sätt sedan
   `policy_url` i samma datavy i Kunder & Data, fältet Integritetspolicy (URL),
   eller med `scripts/fyll_kundregister.py --policy-url ...`.
   Klart när: fältet är ifyllt, och ett utkast till en personlig adress bär
   raden "Hur <kund> behandlar personuppgifter: <url>". Utan den blockerar
   `send_guard.py` (regel 2) utskick till personliga adresser.
5. **Gallringsperiod beslutad och satt.**
   Gör: perioden beslutas med kunden och ska stå i integritetspolicyn
   (`docs/JURIDIK_ATGARDER.md`, P1.1). Sätt den med
   `python scripts/gallra.py --env railway-main --tenant <slug> --satt-policy <dagar> --beslutad-av "<namn>"`.
   Klart när: torrkörningen `python scripts/gallra.py --env railway-main --tenant <slug>`
   skriver "(policy: <dagar> dagar)" för kunden och inte "kunder saknar beslutad policy".
6. **Autonominivån per ärendekategori genomgången med kunden.**
   Gör: gå igenom Inställningar › Kundtjänst › När agenten får svara själv
   (`/settings/regler`, lägena Utkast, Auto och Eskalera per kategori).
   Standard är Utkast. Varje kategori som kunden ställer på Auto betyder att
   den mänskliga granskningen upphör där, och enligt villkoren (`/villkor`,
   avsnittet om autonomi) är bedömningen enligt art. 22 kundens ansvar.
   Klart när: kunden har bekräftat valet per kategori skriftligt; varje ändring
   loggas som händelsen `rule_changed` (`snajp-support/app/api/rules.py`).
7. **Kanaler och integrationer som kunden slår på står i avtalet.**
   Gör: stäm av vilka inkorgar (`/settings/mailboxes`), tillägg
   (`/settings/addons`, tilläggsväljaren på kundens sida i admin (`app/admin/kunder/[id]`)) och
   kanaler kunden ska använda mot punkt 15 och Bilaga 1 i biträdesavtalet.
   Klart när: varje påslagen kanal och integration finns uppräknad i det
   undertecknade avtalet, och inget är påslaget som inte står där.
