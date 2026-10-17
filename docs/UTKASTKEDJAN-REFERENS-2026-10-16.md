# Utkastkedjan: referens för Iris första mejl (låst 2026-10-16)

> **Läs den här filen först för varje fråga om utkastens output, skrivstil,
> ämnesrad, hälsning eller kvalitet.** Den ersätter
> [`UTKASTKEDJAN-REFERENS.md`](UTKASTKEDJAN-REFERENS.md) (2026-10-12) som
> gällande nivå. Den äldre filen står kvar som historik över hur kedjan
> byggdes. Facit i kod:
> `snajp-support/tests/leads/fixtures/utkastfacit_2026-10-16.json`, låst av
> INV-LEADS-UTKAST-002 (`tests/leads/test_utkastfacit_2026_10_16.py`).
> Förbättra vidare enligt avsnitt 8, aldrig genom att ändra facit först.

Antons beställning 2026-10-17: "Lås in detta på samma sätt som tidigare i
projektdokumentationen, i en separat fil med exempel på outputen och exakt vad
som ändrades från den tidigare versionen och varför."

Underlaget är Antons granskning 2026-10-15 och nattens körningar 2026-10-15/16:
fyra körningar á 50 Iris-leads (två för Norrland, två för Göteborg och Mölndal)
med påfyllnad, totalt 100 + 100 kompletta leads med utkast i Snajps
granskningskö i development.

## 1. Nivån

Antons ord 2026-10-15: "Det första utkastet med Christoffer var det bästa
(även om ämnesraden var ren smörja) och det är den nivån och anpassningen jag
förväntar mig … det kan vara bättre och det måste vara det HELA tiden."

Ett utkast på nivån har tre korta stycken efter hälsningen:

| Stycke | Vad det gör |
|---|---|
| **Ingången** (1–2 meningar) | Tar det bolaget **självt lovar sina kunder eller står för**, med deras egna ord ur sajten, och ställer det mot **det moment produkten löser**. Konkret i deras vardag: vad kunderna frågar om, vad som ska hittas eller bokföras. Aldrig en uppräkning av sortimentet, aldrig en slentrianöppning och aldrig ett benämnt "löfte". |
| **Erbjudandet** (2–3 meningar) | Produkten namnges **först** och vad den gör åt dem, sedan villkorens innehåll och siffror. Knyter gärna tillbaka till ingången ("lämnar över till en människa när den inte säkert kan svara"). |
| **Handlingen** (1 mening) | Villkorens handling, aldrig en fråga. |

**Ämnesraden** är två till fem ord om deras löfte eller momentet. Den bär
**aldrig bolagets namn** och aldrig vår produkt, och börjar inte som ett annat
mejls ämnesrad.

**Hälsningen** bär mottagarens riktiga förnamn bara när det är styrkt. Då
skrivs hela mejlet i du-form, även villkoren. Annars "Hej," och ni-form rakt
igenom.

## 2. Exempel på outputen (facit, verkliga utkast ur kön)

Signatur och lagstadgad fot läggs på i kod och är borttagna här.

**Båtladan i Gästrikland**, pilot, Supportagenten (Antons förebild; ämnesraden
var "ren smörja" och visas inte):

> Hej Christoffer,
>
> Hur hinner du med att ge personlig rådgivning och service genom hela processen, från köp till underhåll, när kundfrågorna om båtar, motorer och trailers blir många?
>
> Vår Supportagent kan svara på återkommande kundfrågor i chatt och mejl dygnet runt, utifrån er egen information. Den lämnar över till en människa när den inte säkert kan svara. Vi tar just nu in 20 företag i en pilot för Supportagenten, eftersom vi sätter upp varje företag personligen. Pilotföretagen får 50 % rabatt första året om de vill fortsätta, och 25 % så länge de stannar.
>
> Svara "pilot" på mejlet, så håller vi en plats åt dig.

**Nudie Jeans Retail**, pilot, Supportagenten. Ämne: *Frågorna om skötsel och reparationer*

> Hej,
>
> Ett par jeans som ska hålla en livstid väcker frågor om skötsel och reparationer, ofta långt efter att er kundtjänst har stängt för dagen.
>
> Vår Supportagent svarar på de frågorna dygnet runt, direkt på er webbplats, och lämnar över till en människa när det behövs. Vi tar just nu in 20 företag i en pilot där vi sätter upp allt personligen. Som ett av dem får ni 50 % rabatt första året och 25 % därefter.
>
> Svara "pilot" på det här mejlet så håller vi en plats åt er.

**Skellefteå El & Diesel**, gratis prov, Kvittohanteraren. Ämne: *Service på de flesta bilmärken*

> Hej Fredrik,
>
> Dina kunder kommer till dig för service och delar till de flesta bilmärken. Det förtroendet bygger på att du är i verkstaden, inte på jakt efter kvitton till bokföringen.
>
> Vår Kvittohanterare hämtar kvittona ur din e-post och gör dem klara att ladda ner. Du får prova den på fem av dina kvitton, med belopp, moms och konto, helt utan kostnad.
>
> Svara på mejlet med fem bifogade kvitton, så får du tillbaka dem färdiga inom en arbetsdag.

**Krohn Byggekonomen**, pilot, Kvittohanteraren. Ämne: *Byggekonomin och kvittona*

> Hej,
>
> Ni hjälper era kunder att styra ekonomin i byggprojekt, inte jaga kvitton till den egna bokföringen.
>
> Vår Kvittohanterare hämtar kvittona från er e-post och gör dem klara för bokföring. Just nu tar vi in 20 företag i en pilot och sätter upp varje företag personligen. Som pilotföretag får ni 50 % rabatt första året och 25 % så länge ni stannar.
>
> Svara "pilot" så reserverar vi en plats åt er.

**Ö-Logistik**, garanti, Iris. Ämne: *Nya kunder utanför gruppen*

> Hej,
>
> Ni sköter logistiken åt era systerbolag, men för att växa behöver ni även hitta kunder utanför den egna gruppen.
>
> Vår agent Iris hittar nya företagskunder åt er. Vi lovar minst 10 nya kunddialoger inom 90 dagar, och blir det färre förlänger vi provperioden utan kostnad tills ni har fått dem.
>
> Svara på det här mejlet så bokar vi 20 minuter där vi visar vilka företag Iris redan har hittat som passar er.

**Whitelip**, garanti, Supportagenten. Ämne: *Snabba svar om snuset*

> Hej,
>
> Ett brett sortiment av vitt snus och nikotinpåsar är en sak. Att hinna med alla frågor om innehåll, styrka och leverans är en annan, särskilt när de kommer efter stängning.
>
> Vår Supportagent svarar på de frågorna åt er, dygnet runt. Vi lovar att ni lägger minst 50 % mindre tid på kundmejl inom 60 dagar, annars förlänger vi provperioden utan kostnad tills ni når dit.
>
> Svara på det här mejlet, så bokar vi 20 minuter och sätter upp agenten för era vanligaste frågor.

**Vindshem Bygg**, pilot, Iris. Ämne: *Relationen med föreningen*

> Hej Daniel,
>
> Att bygga en stark relation med en bostadsrättsförening tar tid. Samtidigt måste nästa outnyttjade yta att utveckla hittas.
>
> Vår agent Iris hittar och kvalificerar nya bostadsrättsföreningar åt dig. Vi tar just nu in 20 företag i en pilot där vi sätter upp varje deltagare personligen. Som pilotföretag får du 50 % rabatt första året och 25 % så länge du stannar.
>
> Svara "pilot" på det här mejlet, så reserverar vi en plats åt dig.

## 3. Fel och rätt (verkliga utkast, oktober 2026)

| Fel | Varför | Rätt riktning |
|---|---|---|
| Ämne "Åkes Motor och era kundfrågor", "Pilot för Iris, Törnqvist Etc.", "Båtladan i Gästrikland och livet på sjön" | Bolagsnamn, produkt eller reklamslogan i ämnesraden | "Frågorna om skötsel och reparationer" |
| "Hej Delsbo," till Magnus på Åkes Motor | Orten före namnet på sajten blev förnamnet | Förnamnet väljs mot adressen (magnus@ → Magnus) |
| "Hej Scandinavia,", "Hej Polarhandlare,", "Hej Hising,", "Hej Brobergs," | Bolagsord, yrkesord eller efternamn + roll som förnamn | "Hej," när namnet inte kan styrkas |
| "Med ert breda utbud av fordon, utrustning och service för snöskotrar, motorcyklar och ATV uppstår många återkommande kundfrågor." | Slentrianöppning och uppräkning av sortimentet | Ett löfte ur deras ord, ställt mot momentet (Nudie, Båtladan) |
| "När ni säljer snöskotrar, ATV och båtar …" / "Ni som prioriterar …" | De nya mallorden efter "för företag som ert" | Se ovan |
| "Att hjälpa kunder att hitta rätt båt för deras behov är ert löfte, men att svara på … tar tid från det arbetet." | Löftet benämns och svansen är allmän (fem av elva mejl i en omkörning) | Visa löftet med deras ord; konkret moment |
| "… kräver fullt fokus på bygget, inte på att hitta nästa uppdrag." / "det är svårt att …" | Mall i 5–9 av 189 ingångar | Variera rörelsen, inte bara orden |
| "Hej Per," och sedan "ni" rakt igenom, eller "du lägger … åt er" | Du och ni om samma person | Namngiven → du; annars ni |
| "Vi lovar att du lägger minst 50 % mindre tid …" före att agenten nämnts | Löfte om ingenting | Produkten först, sedan siffrorna |
| Christoffer-meningen ordagrant i ett mejl till Yngvessons Maskin | Förebilden stod ordagrant i prompten och kopierades | Förebilden beskrivs i prompten, citeras aldrig |

## 4. Vad som ändrades från versionen 2026-10-12, och varför

| Ändring | Var | Varför |
|---|---|---|
| **Ingången bygger på bolagets löfte**, inte på "en detalj ur citaten"; ingångsformerna utan "Med er …", "Ni …", "Era …" och utan exempelfraser | `leads-skrivstil.md` (omgång 6), grundmallen § 10.2, `_INGANGSUPPGIFT`, `_INGANGSFORMER` i `leads_research_v2.py` | Anton: "nu har du bytt ut 'för företag som ert' … till 'med er/ert/era', 'när ni', till en generisk upprabbling". Formernas exempelfraser kopierades ordagrant ("Nästa uppdrag ska hittas medan ni …"). |
| **Ämnesraden utan bolagsnamn och produkt**, 2–5 ord; namnet lyfts ut i kod som sista nät | skrivstilen, grundmallen, hårda reglerna, `stilkontroll.amne_fynd`, `tilltal.amne_utan_namn` | Anton: "nämn INTE företagens namn i ämnesraden". Före: varje ämnesrad bar namnet (även facit 2026-10-12, vars ämnesrader därför är borttagna). |
| **Nya fynd i stilgrinden**: `slentrian_ingang`, `uppraknad_ingang`, `mallord_i_ingangen`, `kopierat_exempel`, `du_och_ni`, `ni_till_person`, `agent_efter_loftet`, `samma_fras`, `namn_i_amnet`, `produkt_i_amnet`, `samma_amne`, `langt_amne` | `app/leads/stilkontroll.py` | Varje fel i avsnitt 3 som går att känna igen i kod. En regel som bara står i en prompt är en riktning, inte en garanti. |
| **Grinden körs även efter humanizern**, med omskrivning och ny humanisering, högst två varv | `run_outreach_draft_v2` | Humanizern förde tillbaka det grinden fällt (mallord, tankstreck), och grinden gav bara en omskrivning före den. |
| **Utkast och humanizer på `gemini-2.5-pro`** (Vertex `europe-west1`), "lite tänkande" i stället för inget | `LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL` på api i development; `step_runner.py` | Flash föll tillbaka i mallord även efter två grindvarv; pro skrev på nivån. Pro tål inte tankebudget 0 (400). |
| **Tilltalet bestäms i kod före modellen**: mottagarens förnamn och du/ni står i ärendet och humanizerns bas | `tilltalsblock` i `run_outreach_draft_v2` | Koden satte förut in förnamnet efter att modellen skrivit "Hej," i ni-form: "Hej Per," + ni i 10 av 60. |
| **Förnamnet styrks**: väljs mot mejladressen; ord som inte liknar förnamn och bolagets första ord ger "Hej," | `halsning.fornamn`, `_ar_bolagstilltal`, `discovery.person_kontakt_i_text` | "Hej Delsbo", "Hej Scandinavia", "Hej Polarhandlare", "Hej Hising", "Hej Brobergs". |
| **Facit reviderat**: 2026-10-12 års facit har fyra kvar (Svensk Rivtjänst, Tingstad, ÅW, Båtladan); nio ligger under `ersatta` | `utkastfacit_2026-10-12.json` | De började "Med er …", räknade upp eller bar mallord som Anton nu underkänt. Det nya facit är `utkastfacit_2026-10-16.json`. |

Commits: `5561c4d`, `fb2f1da`, `b6474bd`, `edf07e5`, `8dc31db`, `3a0fc6e`, `ad7737f`
och låsningen. Beslut med resonemang: `docs/BESLUT.md` (2026-10-15 och 2026-10-16).

### Det som ändrades i körningen och påverkar outputen

Inte utkastets text, men vilka bolag som får ett utkast:

- **Registret läses från allabolag.se**, eftersom ScrapeGraph-krediten tagit slut
  och merinfo-sidorna föll (`sources/allabolag.py`).
- **Iris kräver webbplats.** En kedjas sajt räknas inte som bolagets egen.
  Utan sajt finns inget underlag för ingången.
- **Ett lead räknas som levererat först när utkastet står i kön.** Körningen
  letar vidare tills beställt antal har underlag och utkast.
- **Inget fast tak på sökrundor.** Körningen slutar först efter fyra tomma
  rundor i rad. Bortval står sig 30 dagar och blandas sedan in igen.

## 5. Kedjan, steg för steg (gällande)

Allt i `app/agent/leads_research_v2.py:run_outreach_draft_v2`.

| # | Steg | Vad som händer |
|---|---|---|
| 0 | Ärendet | Uppdrag, skrivregler, skrivstil, brief, erbjudandeblock, ingångsform (fyra, roterade per prospekt), ingångar som redan används i kön, **tilltal i det här mejlet**, språkläge, kontextpaket, SOUL, researchvy. |
| 1 | Utkastet (`sa:draft-outreach` + `mk:cold-email`, pro) | Skriv, skärp, granska i ett svar. |
| 1a | Personalisera ingången (alltid) | Enbart första stycket skrivs om mot deras löfte; ämnesraden 2–5 ord utan namn. |
| 1b | Stilgrinden | Fynden ger en omskrivning av hela mejlet. |
| 2 | Humanizern (pro, alltid sist, INV-LANG-002) | Med tilltalsblocket och ämnesregeln. |
| 2b | Stilgrinden igen | Kvarstår fynd: omskrivning + humanizer, högst två varv. |
| 3 | Kod | Signoff, hälsning (`ratta_tilltal` med adressen), namnet ur ämnet, bolagsnamnet en gång. |
| 4 | Faktagrinden | Ostött påstående → reparation, annars stopp. |
| 5 | Köningen | Hälsningspass, stilkontroll (flaggar på köposten som "Stil: …"), signatur, fot. |

Undantagna från omskrivning (villkoren orsakar dem): `lang_mening`,
`samma_uppmaning`, `for_langt`.

## 6. Mätt utfall 2026-10-16

- 200 kompletta leads (100 Norrland, 100 Göteborg och Mölndal), alla nivå A med utkast i kön.
- 0 av 200 ämnesrader med bolagsnamn eller produkt.
- 22 av 200 med ett kvarvarande stilfynd vid låsningen, de flesta skrivna före
  de sista rättningarna (tilltalsblocket, mallorden ur 189 utkast). De syns för
  granskaren som "Stil: …" på köposten.
- Kostnad och tid: ett utkast tar 5–8 minuter med pro, research 4–5 minuter.

## 7. Så verifierar du

```bash
cd snajp-support && python -m pytest -q tests/leads/test_utkastfacit_2026_10_16.py tests/leads/test_utkastfacit_2026_10_12.py tests/leads/test_stilkontroll_2026_10_12.py tests/agent/test_leads_v2_wiring.py
```

```bash
python scripts/granska_utkast.py --slug snajp --visa 5
```

Noll `slentrian_ingang`, `uppraknad_ingang`, `mallord_i_ingangen`,
`kopierat_exempel`, `du_och_ni`, `ni_till_person`, `agent_efter_loftet` och
`namn_i_amnet` är målet.

## 8. Så förbättrar du vidare utan att tappa nivån

1. Skriv ned felet som en ny feedbackrunda i `leads-skrivstil.md`, med verkliga
   exempel (fel/rätt). Citera inga rätt-meningar i prompterna som modellen kan
   kopiera; beskriv rörelsen.
2. Lägg till ett fynd i stilgrinden när felet går att känna igen i kod.
3. Kör testerna i avsnitt 7. Fäller facit den nya regeln är regeln fel, eller
   så ska Anton godkänna ett nytt facit. Facit ändras aldrig tyst.
4. Prova på fem leads (`scripts/omskriv_utkast.py --slug snajp --prospekt …
   --apply`) och läs dem själv.
5. "Skapa om utkast" skriver sedan 2026-10-17 bara utkastet, ur leadets
   sparade research (`scope="utkast"`, `app/leads/sparad_research.py`), så
   bedömningen står kvar. Före det researchade den om, och 23 leads föll till
   nivå C när 104 skrevs om 2026-10-16. Processa om i registret kör
   fortfarande full research och ska inte användas för att skriva om mejl.
6. Dokumentera i `docs/BESLUT.md` och här (ny rad i avsnitt 4).

## 9. Öppet

- ~~**"Skapa om bara utkast"** utan ny research (se 8.5).~~ Byggd 2026-10-17.
- **Iris-ingångarna** konvergerar mot "hitta nästa företagskund": ett Iris-mejl
  har bara ett moment. Grinden fäller frasen när den upprepas, men rörelsen
  behöver fler varianter ur bolagets egna affärer (nya orter, nya tjänster,
  rekryteringar).
- **Koncernbolag med få anställda** (Kappahl, Continental Däck) passerar
  storleksfiltret. Antons beslut om de ska uteslutas.
- **Gemini 3** finns bara på Vertex globala endpoint. Att flytta behandlingen
  ut ur EU-regionen är Antons dataskyddsbeslut.
