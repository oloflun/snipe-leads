# Systemblad: Jev (TypeSafe `jev-1.13.0`)

Datum 2026-11-18. Claude (agent), på Antons uppdrag. Underlag, inte godkänt av
ägaren. Läsanvisning: `README.md` i samma mapp. "Bevis" =
`docs/compliance/bevis/railway-konfiguration-2026-11-18.txt`. "Lev." =
`docs/compliance/leverantorsgranskning.md`. Sökvägar under `app/` avser
`snajp-support/app/`.

## 1. Syfte och avsedd användning

**Vad den är.** En extern beslutsmodell hos TypeSafe AI, Inc. (USA). Typade
frågor in, sannolikheter ut, ungefär 0,3 s per anrop. Den skriver ingen
motivering och ersätter aldrig Iris kvalificering; den sitter runt den som ett
billigt förfilter (`app/leads/jev.py:1-20`).

**Vad den används till.**

1. **Leads, triage före research.** Fäller i läge `pa` bara uppenbara missar
   med hög säkerhet; godkänner aldrig något (`jev.py:13-17, 58-62, 192-219`).
   Anropas från körningen (`app/leads/korning.py:186-203`) och från
   registerkällan (`app/leads/sources/merinfo.py:814`).
2. **Leads, klassning efter research.** En sannolikhet för "bra lead" och en
   nivå hög, mellan eller låg. Sparas bredvid kodens nivå för jämförelse och
   ändrar den aldrig (`jev.py:18-20, 222-252`; anrop i
   `app/agent/leads_research_v2.py:609`).
3. **Inkorgen (avstängd).** Klassning av kundmejl som support, lead eller ej
   relaterat (`app/email_pipeline/klassning.py:157-189`). Av i båda miljöerna
   sedan 2026-11-17 genom Antons beslut (`docs/BESLUT.md:572-599`; bevis rad
   95, 248).

**För vem.** Snajps kunder som kör Iris. Jev har ingen kontakt med någon
människa.

**Användning som inte är avsedd** (Snajps beskrivning, inte en beslutad policy):

- Läsa kundernas kundmejl. Antons beslut 2026-09-30, citerat i koden
  (`jev.py:22-28`), och beslutet 2026-11-17 (`docs/BESLUT.md:572-585`). Slås
  inkorgsklassningen på igen ska underbiträdeslistan ändras först (samma, rad
  598-599).
- Godkänna ett bolag eller sätta Iris nivå (`jev.py:6-9, 226-227`).
- Bedöma fysiska personer, eller ta emot personnamn och kontaktuppgifter
  (`jev.py:24-27, 77-80`).

## 2. Design

| Del | Kod | Beteende |
|---|---|---|
| Läge | `jev.py:68-74`; `config.py:447-450` | `IRIS_JEV`: `off` (inga anrop), `skugga` (anrop loggas, inget fälls), `pa` (triagen fäller). Okänt värde blir `off`. Utan `TYPESAFE_API_KEY` görs inga anrop |
| Inkorgens läge | `klassning.py:104-110`; `config.py:451-454` | `INKORG_JEV`: `off`, `prov` (bara knappen Provsortera), `auto`. Standard `off` |
| Rensning före anrop | `jev.py:77-80` | E-post och telefon byts ut; personnummer maskeras före telefonmönstret |
| Frågorna | `jev.py:128-164` | En `score` för passform, en `noul` per måste-kriterium och per uteslutning, en `choice` för stödraden i utdraget |
| Fällningsgräns | `jev.py:58-62, 167-189` | Måste-kriterium med sannolikhet högst 0,08, eller uteslutning med minst 0,92 |
| Kundens val | `jev.py:212-218` | `jev_bortval=False`: Jev bedömer men fäller aldrig |
| Inkorgens gräns | `klassning.py:44, 184-186` | Styr bort ett mejl bara vid konfidens minst 0,9 |
| Fel | `jev.py:33-34, 203-205, 242-246`; `klassning.py:187-188` | Fail open: kandidaten går vidare till research, mejlet går supportvägen. Jev är en besparing, inte en grind |
| Loggning | `jev.py:101-109` | Varje anrop till `agent_runs` via `logga_anrop` |
| Mätning mot Iris | `jev.py:255-285` | `statistik`: antal falska bortval (Jev skulle fälla, Iris gav A eller B) och överensstämmelse mellan nivåerna |

Endpoint: `https://api.typesafe.ai/v1/systemone`, tidsgräns 20 s
(`jev.py:52-54`).

## 3. Modeller och resurser

| | |
|---|---|
| Modell | `jev-1.13.0`, hårdkodad (`jev.py:53`). Ingen konfigvariabel för modellversion |
| Leverantör | TypeSafe AI, Inc., San Francisco (Lev. rad 119) |
| Plats | USA, ingen EU-region. Underbiträden bland andra AWS, Modal, Nebius, CoreWeave (Lev. rad 18, 131-140) |
| Avtal | DPA inkorporerad i Master Customer Agreement; vilka villkor kontot accepterade är inte belagt (Lev. rad 121-122) |
| Överföring | SCC; TypeSafe finns inte i DPF-listan (Lev. rad 138) |
| Telemetri | MCA §4.1(c) ger en tidsobegränsad rätt att härleda telemetri ur kunddata (Lev. rad 125) |
| Leverantörsbedömning | Röd (Lev. rad 18) |
| Var anropet görs | Railway-tjänsten `api` |

**I drift 2026-11-18:**

| Miljö | `IRIS_JEV` | `INKORG_JEV` | `TYPESAFE_API_KEY` | Följd |
|---|---|---|---|---|
| `main` | Osatt, alltså `off` (bevis rad 237-280) | `off` (rad 248) | satt (rad 280) | Jev gör inga anrop i produktionen |
| `development` | satt, värdet syns inte (rad 97) | `off` (rad 95) | satt (rad 130) | Jev kan anropas för leads; om i läge `skugga` eller `pa` är inte belagt |

Maskeringen av personnummer före Jev (`jev.py:47, 80`) finns i `development`
men inte i `main` enligt den lokala referensen `origin/main`. I `main` görs
inga anrop, så skillnaden har ingen följd där i dag.

## 4. Data in och ut

**Leads (triage och klassning)** skickar (`jev.py:113-125, 231-241`):

- kundens erbjudande och målgrupp i fritext,
- bolagets namn, ort, webbplats, antal anställda och uppmätta webbsignaler,
- ett utdrag ur bolagets publika sida eller researchens sammanfattning, upp
  till 255 rader, efter rensning av e-post, telefon och personnummer,
- kundens kriterier och uteslutningar som frågetext.

Namn på personer i utdraget tas inte bort; rensningen gäller bara e-post,
telefon och personnummer (`jev.py:77-80`).

**Inkorgen (av sedan 2026-11-17)** skickade avsändarens domän, ämnesraden (200
tecken) och de första 1 500 tecknen av mejltexten (`klassning.py:162-167`).
Det som skickades före avstängningen ligger kvar hos TypeSafe; radering är
inte begärd (`docs/BESLUT.md:594-596`).

**Ut:** sannolikheter, en nivå och en stödrad. Sparas på prospektet under
`jev` (`jev.py:261-274`).

**Loggat:** varje anrop med fråga och svar i `agent_runs` (`jev.py:101-109`).
Lagringstiden är inte beslutad (se `supportagent.md` avsnitt 4).

## 5. Mänsklig översyn

- Jev fattar inget beslut som når en människa direkt. En fällning i läge `pa`
  tar bort en kandidat innan research; den syns i körningens tratt med skäl
  och stödrad (`korning.py:189-202`).
- Kunden kan stänga av Jevs bortval och bara se bedömningen (`jev.py:212-218`;
  `app/leads/automation.py:13`).
- Klassningen ändrar aldrig Iris nivå (`jev.py:226-227`).
- Vem som får slå på `IRIS_JEV=pa` eller `INKORG_JEV` är inte bestämt.
  `INKORG_JEV` sattes till `auto` mot ett uttryckligt beslut; vem som gjorde
  det är okänt (`matris.md:49, 208`).

## 6. Utvärdering

- **Ingen svit.** Jev saknar evalsvit i `snajp-support/evals/`
  (`snajp-support/evals/README.md:7-11`) och mättes inte vid modellbytet
  (`docs/compliance/modellbyte-underlag.md:758-760`).
- `jev.py:20` hänvisar till `scripts/iris_jev_eval.py`. Skriptet finns inte i
  repot (sökt 2026-11-18). Inte belagt att mätningen gjorts.
- `statistik` (`jev.py:255-285`) räknar falska bortval ur sparade prospekt.
  Inga resultat finns i repot.
- Antons mätning 2026-09-27, "förfilter i kaskad, inte ersättare", citeras i
  koden (`jev.py:8-9`); mätunderlaget ligger i valvet och är inte läst här.

**Inte mätt:** andelen falska bortval i läge `pa`, kalibreringen av
sannolikheterna, och om svenska bolagstexter bedöms lika väl som engelska
(frågorna är på engelska, `jev.py:131-163`).

## 7. Kända begränsningar

- Modellversionen är hårdkodad; byter TypeSafe beteende syns det inte i
  konfigurationen.
- Ingen motivering, bara sannolikheter (`jev.py:6-7`).
- Personnamn i bolagets sidutdrag skickas.
- Leverantören är röd: USA utan DPF, telemetrilicens, ingen raderingsregel i
  DPA:n (Lev. rad 18, 123-125, 138).

## 8. Risker per AI-steg (bedömningsutkast)

Utkast av agenten. Inga riskkriterier finns, så ingen restrisk är accepterad.

| Steg | Risk | Följd | Befintlig kontroll | Restrisk (utkast) | Behandling beslutad |
|---|---|---|---|---|---|
| Leads-triage, läge `pa` | Falskt bortval | Kunden går miste om ett bra lead, utan att någon ser det i listan | Bara uppenbara missar vid 0,08 och 0,92; skäl i tratten; kunden kan stänga av bortval | Inte mätt | nej (ägarens beslut) |
| Leads, alla lägen | Personnamn i sidutdrag till USA | Överföring utan DPF, med telemetrilicens | Rensning av e-post, telefon och personnummer | Medel | nej (ägarens beslut) |
| Leads, alla lägen | Kundens erbjudande och kriterier blir TypeSafes telemetri | Kundens affärsinformation används av leverantören | Ingen | Inte bedömd | nej (ägarens beslut) |
| Inkorgen | Slås på igen utan beslut | Kundmejl till USA | `INKORG_JEV=off` i båda miljöerna; standard `off` i kod | Medel så länge ingen godkännandeprocess finns (`matris.md:67`) | nej (ägarens beslut) |
| Inkorgen, historiskt | Kundmejltext ligger kvar hos TypeSafe | Personuppgifter hos ett ej godkänt underbiträde | Ingen; radering inte begärd | Kvarstår | nej (ägarens beslut) |
| Anropsfel | Jev svarar inte | Ingen; kandidaten går vidare | Fail open | Låg | nej (ägarens beslut) |

## 9. Påverkan på individer och grupper (A.5.4)

Utkast av agenten. Det här är den bedömning som saknades för Jev
(`matris.md:123`).

**Vilka berörs.**

| Grupp | Hur | Belägg |
|---|---|---|
| Kundernas kunder (de som skrivit till kundtjänst) | Deras mejl gick till Jev fram till 2026-11-17 när `INKORG_JEV` var `auto`. Ämne och 1 500 tecken text, med e-post och telefon borttagna; namn, personnummer (i `main`) och hälsouppgifter i texten passerade | `klassning.py:162-167`; DPIA rad 160-162 |
| Personer som nämns på prospektets webbplats | Namn i sidutdraget kan nå Jev | `jev.py:77-80, 124` |
| Prospektbolagen | Kan väljas bort före research; bolaget får inget mejl | `jev.py:192-219` |
| Små bolag och bolag med sparsam webbplats | Får korta utdrag och få webbsignaler. Om Jev oftare fäller dem är **inte mätt** | – |
| Bolag med svensk text | Frågorna är på engelska och utdraget på svenska. Om det påverkar sannolikheterna är **inte mätt** | `jev.py:131-163` |

**Bedömning (agentens).**

- För individer är följden i dag liten i drift: Jev gör inga anrop i `main`,
  och den får inte kundmejl i någon miljö. Den största kvarvarande följden är
  historisk: kundmejl som redan ligger hos TypeSafe under en telemetrilicens
  utan tidsgräns. Om anmälningsplikt och underrättelse gäller är Antons
  bedömning (`docs/BESLUT.md:596-597`).
- För bolag är följden ett uteblivet säljmejl. Det har ingen rättslig verkan
  och påverkar inte bolaget i betydande grad. Ett falskt bortval drabbar
  främst kunden, som går miste om ett lead.
- För grupper finns en möjlig skevhet mot små bolag och bolag med lite text,
  men den går inte att bedöma utan mätning av falska bortval per grupp.
- AI-förordningen: trolig minimal risk; inga särskilda skyldigheter utöver
  art. 4 (`docs/compliance/ramverk/iso42001/ai-forordningen.md:71-75`).

**Det som behövs för att bedömningen ska bli beslutbar:** mätning av falska
bortval i läge `skugga` per bolagsstorlek, ett beslut om leverantören ska
behållas för leads (`docs/BESLUT.md:597-598`), och ett beslut om radering hos
TypeSafe. Alla tre är ägarens.
