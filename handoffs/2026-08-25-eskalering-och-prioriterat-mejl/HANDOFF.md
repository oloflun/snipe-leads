# Bokföringschatten, det prioriterade mejlet och tre agenter som ger upp senare

2026-08-25. Allt nedan ligger på `development`. **Ingenting är deployat** — se
projektregeln i `CLAUDE.md`: `git push origin development:railway-development`
krävs också, och två av posterna här kräver dessutom en människas hand innan de
gör någon nytta.

---

## 1. 500:an i bokföringschatten — lagad, och den var inte en gissning

Hypotesen i uppdraget stämde. Bekräftad genom att köra SDK:ns egen konverterare,
inte genom att läsa traceback:

```
agents.exceptions.UserError: Unknown content: {'type': 'output_text', 'text': ...}
```

Historikens assistentrader byggdes som
`{"role": "assistant", "content": [{"type": "output_text", ...}]}` — alltså
Responses-API:ts **utdatatyp**, skickad in som indata. Den formen har bara två
nycklar, så `Converter.maybe_easy_input_message` fångar den som ett
EasyInputMessage och skickar innehållet till `extract_all_content`, som bara
känner `input_text`/`input_image`/`input_audio`/`input_file`.

Felet kunde **aldrig** slå på första turen — då finns ingen assistentrad. Det är
därför det såg ut att bero på att någon skrev, och inte på att chatten öppnades.
`run_onboarding_turn` undgick det bara genom att aldrig skicka någon historik.

Rättningen ger assistentraden `"type": "message"`, vilket flyttar den till
`maybe_response_output_message` — den gren som faktiskt kan `output_text`. Det är
samma form som `RunResult.to_input_list()` själv producerar; vi kan inte anropa
den (historiken kommer ur databasen mellan två HTTP-anrop), så vi speglar den.

**Testerna mockar nätverksgränsen, inte `Runner.run`.** Det är hela poängen:
buggen satt inne i Runner.run, och `tests/agent/test_leads_agent_wiring.py`
mockar bort just den — ett sådant test hade varit grönt genom hela incidenten.

---

## 2. Två saker som kräver din hand

### 2a. App-lösenordet till det prioriterade mejlet ▸ Anton

Sändvägen är byggd och testad men **av** tills två variabler finns på `api` i
Railway. Fullständig beskrivning i [`DEPLOY.md`](../../DEPLOY.md) under
"Prioriterat mejl vid eskalering".

Det är ett MEJL, inte ett larmsystem: ingen sida övervakas, inget tröskelvärde
bevakas, ingen jour väcks. Ämnesraden bär `[PRIORITERAT]` så att den går att
sortera på, och där slutar mekaniken.

```
INTERNLARM_SMTP_ANVANDARE=snajpsupport@gmail.com
INTERNLARM_SMTP_LOSENORD=<app-lösenord, 16 tecken>
```

Lösenordet är **inte** kontolösenordet — ett Gmail med tvåstegsverifiering kan
inte logga in på SMTP med det. Skapas under Google-kontots
säkerhetsinställningar → *Appspecifika lösenord*.

Sätt samtidigt `PUBLIC_BASE_URL`, som ändå redan står som en post i
`docs/JURIDIK_ATGARDER.md`. Utan den bygger mejlet ingen länk in i adminvyn.

Variabelnamnen bär fortfarande `INTERNLARM_` trots att modulen heter
`prioriterat_mejl.py`. De behålls med flit: de står i Railway och i DEPLOY.md,
så att döpa om dem är en driftändring och inte en omdöpning i koden. Säg till om
du vill ha dem bytta också — det är gjort på två minuter så länge ingen hunnit
sätta dem.

Saknas variablerna skickas ingenting, tyst. `har_konfiguration()` svarar på om
steget är gjort, utan att skicka ett provmejl.

### 2b. Två beslut jag inte tog åt dig

**Var går gränsen för "tunn KB"?** Jag satte `TUNN_KB_GRANS = 5` artiklar i
`app/agent/support_agent.py`. Det är ett **förslag**, inte ett mätt tal.

Resonemanget: en tenant med färre artiklar än så har inte ett bibliotek utan ett
par anteckningar, och att eskalera varje fråga som inte träffar dem är att lämna
över hela supportflödet till en människa under de första veckorna — alltså precis
den period då kunden bedömer om produkten fungerar.

Alternativet vore en konfidenströskel (`research.confidence`) i stället för ett
artikelantal. Den är i teorin bättre och i praktiken svårare: det är modellens
självskattning, alltså samma sorts tal som `should_escalate` redan bär, och att
bygga en andra grind på samma osäkra signal ger inte två oberoende villkor.
Artikelantalet är åtminstone ett faktum. **Mät det mot riktig data innan det
stelnar.**

**Ska leads följdfråga gå automatiskt eller läggas som utkast?** Den frågan
besvarades av kodbasen, inte av mig: leads har ingen automatisk sändväg alls.
`_queue_outreach_draft_impl` är enda vägen in i `send_queue`, autonominivån
avgör om posten blir `queued` eller `awaiting_review`, och
`scheduler.process_due_item` är enda vägen till `sent`. En följdfråga från leads
skulle alltså **redan** hamna i samma kö och lyda samma grindar som allt annat
utgående.

Det gör frågan mindre skarp än den såg ut — men den är inte borta: vill du att en
följdfråga ALLTID ska granskas av en människa oavsett autonominivå, är det en
rad i `autonomy.py`, inte i agenten. Säg till så bygger jag den.

---

## 3. Det jag inte kunde bygga: leads har ingen hantering av prospektsvar

Uppdraget bad om `abuse_gate` i "leads-agentens hantering av inkommande svar från
prospekt". **Den hanteringen finns inte.** Läst ur koden, inte antaget:

| Vad | Läge |
|---|---|
| Något som skriver ett inkommande `outreach_messages`-radslag | Finns inte. Endast `queue_outreach_message` skriver, och den sätter `direction="outbound"` hårdkodat |
| `storage.list_replies()` | Läser en tabell inget fyller. Arbetsytans Svar-flik är därför alltid tom i drift |
| `leads/handoff.py::route_handoff()` | Ingen produktionsanropare. `leads/autonomy.py` säger det rakt ut och stänger av autonominivån `meeting` just därför |
| `language_gate.InboundReplySignal` | Datatypen finns, ingen kodväg konstruerar den — så `en_confirmed` kan aldrig uppnås i drift |

Fyra oberoende halvfärdiga ändar som alla pekar på samma lucka: **kedjan slutar
när mejlet skickats.** Det är ett eget uppdrag, inte något jag skulle bygga
under en punkt om tonläge.

Vad jag gjorde i stället: kopplade in grinden på leads **enda** live-yta som tar
emot ett skrivet meddelande i dag — `run_onboarding_turn`, samtalet med vår kund
under onboarding. Repliken sätts EFTER körningen, samma ordning som i support, så
att modellen inte kan skriva om ett kontrollerat säkerhetssvar.

**Mejlet kopplades till `leads_tools._request_human_handoff_impl`, inte till
`handoff.py`.** Filen bär namnet men funktionen är död. `_request_human_handoff_impl`
är den som faktiskt körs: både modellens verktyg och fyra kodvägar i
`run_outreach_draft` går genom den.

---

## 4. Vad som blev svårare att utlösa, och vad som inte rördes

### Ändrat

| Var | Förut | Nu |
|---|---|---|
| support, KB-sökning | Ett försök: hela meddelandet | Tre: hela meddelandet → ämnesraden/nyckelord → `research.missing_info` |
| support, `not articles` | Fällde ensamt | Vägs mot `kb_supports_answer`, som förut bara var kontext åt nästa steg |
| support, tunn KB + ofarlig fråga | Eskalering | EN följdfråga, bara i första turen |
| bokföringschatt, `FALLT_SVAR` | Direkt | Ett omförsök med uttrycklig tillsägelse att hämta talet |
| leads, tomt utkast | Överlämning | Ett omförsök på utkaststeget |

### Orört, med flit

`abuse.ska_eskalera`, uppsägningsrisk, triageflaggan, lågt sentiment, modellens
egen `should_escalate`, hela `verifieringsgrind.py`, och INV-GROUND-001 (den enda
utgången för ett kvarstående ostött påstående är fortfarande en människa).

Dessutom en **ny** kodkontroll som gör följdfrågevägen stängd: `_ar_kansligt`
fångar ARN, Konsumentverket, GDPR, dataskydd, advokat, återbetalning,
kompensation, inkasso och reklamation. Den ligger i kod och inte bara hos
`cs:customer-escalation` av två skäl — beslutet ska inte kunna pratas bort av
innehållet i meddelandet, och steget som bär juridiken kommer EFTER utkastet, så
dess svar finns inte att läsa när frågan "fråga eller lämna över?" avgörs.

`INV-BOOK-003` är oförändrad. Omförsöket ger modellen en chans att HÄMTA talet,
inte rätt att behålla ett den hittat på — det finns ett test för just den
gränsen.

Hälften av de nya testerna prövar att agenten INTE eskalerar. Den andra hälften
prövar att de säkerhetskritiska vägarna gör det precis som förut.

---

## 5. Två saker att veta om koden

**Poleringen i bokföringschatten grindas OM.** Humaniseraren skriver om text, och
en omskrivning av "1 250 kr" till "cirka 1 200 kr" hade gjort vårt eget sista
steg till vägen förbi INV-BOOK-003. Faller det polerade svaret behålls det
opolerade: sant och stelt slår ledigt och fel.

**Humaniseraren på leads utskick var redan verkställd** — frågan i uppdraget var
om den faktiskt körs eller bara står i en prompt. Svaret: en GRIND, på två
oberoende ställen (vid köning i `leads_tools`, vid utskick i `send_decision`),
med varianten persisterad på meddelanderaden så att den andra kontrollen läser
ett lagrat värde. Ett test pinnar båda, eftersom den ena kan tas bort utan att
något beteendetest märker det.

---

## 6. Något annat pågick i arbetsträdet

Under sessionen rullades spårade filer tillbaka till HEAD två gånger av något
utanför min session, och sex filer med annat pågående arbete dök upp som
ändrade — `components/bookkeeping/BokforingPanel.tsx`,
`app/api/snajp-support/bookkeeping/[...path]/route.ts`,
`snajp-support/app/api/bookkeeping.py`, `app/storage/{base,memory,postgres}.py`
och `tests/api/test_bookkeeping_api.py`.

De råkade komma med i ett commit och plockades ut igen med `git reset --soft` —
innehållet är orört och ligger kvar som ostagade ändringar i arbetsträdet. Men
**kontrollera dem innan du commitar**, och kör inte två agenter mot samma
checkout samtidigt.

---

## Testläge

`1243 passed, 4 skipped`. Nya filer:
`tests/notifications/test_prioriterat_mejl.py`, `tests/bookkeeping/test_chatt_flertur.py`,
`tests/moderation/` (flyttad från `tests/leads/`).

---

## 7. Tillagt efter granskning: det heter inte "larm"

Modulen hette `internlarm.py` och funktionen `larma()`. Det var fel ord — det
här är ett mejl, inte ett larmsystem, och vokabulären antydde en apparat som
inte finns. Omdöpt till `app/notifications/prioriterat_mejl.py` och
`skicka_prioriterat()`.

**Beteendet är oförändrat.** Samma dubblettspärr, samma tidstak, samma
tystnad vid osatt konfiguration, samma `[PRIORITERAT]` i ämnesraden. Bara namn
och prosa.

Miljövariablerna behåller sina namn (`INTERNLARM_SMTP_*`) — se 2a.
