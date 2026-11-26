# Paritet 09: Import, export, dubbletter och berikning

Området handlar om hur data kommer in i och ut ur CRM:et utan att man skriver poster en och en: importguiden för kalkylblad, upsert på unika fält, export till CSV av en vy eller en hel arbetsyta, dubblettkriterier och sammanslagning av poster, och berikning av bolag och personer. I Snajp CRM finns i dag bara vägen in över API:t (kundsynken med tolv källsystem, CSV eller JSON i satser om högst 500, upsert på källans id, organisationsnummer och e-post); det finns ingen importguide i gränssnittet, ingen export till fil, ingen sammanslagning och ingen berikning.

Antal per läge (räknat i tabellen nedan, 203 rader): verifierad 25, byggd 15, delvis 41, inte gjord 117, avstår 5.

Underlag: `docs/crm/underlag/twenty-09-import-export-dubbletter-berikning.md`. Läget gäller arbetskatalogen 2026-11-26. Koden som prövats: `snajp-support/app/crm/synk.py` (matchning och upsert), `snajp-support/app/crm/adaptrar.py` (mappning och CSV), `snajp-support/app/crm/falt.py` (svenska fältformat), `snajp-support/app/api/crm_v1.py` (synkvägarna, förhandsgranskningen, taken) och `components/crm/app/SynkVy.tsx` (körningarna i gränssnittet). Testerna ligger i `snajp-support/tests/crm/test_api.py` och `test_falt_och_adaptrar.py`. En importguide med fil, kolumnkoppling och granskning finns i Leads (`lib/leads/importfil.ts`, `importmallar.ts`, `importrader.ts`, `components/leads/ImportLista.tsx`), men den skriver till leadslistor, inte till CRM:ets bolag, och går inte att nå från CRM:et. Fasen för importen i gränssnittet är 3, efter `docs/crm/MIGRERING-FUNKTIONSLISTA.md` LR-133 och LK-147 (befintliga kunder laddas upp till CRM:ets bolag i fas 3). Export av poster, sammanslagning, dubblettsökning och berikning har ingen fas i `docs/crm/PLAN-MIGRERING.md` och står som "ej planerad"; sammanslagning och berikning ur SCB är öppna frågor i `docs/crm/SVENSK-STANDARD.md` § 3 och § 4.

## De största luckorna

1. Ingen import i gränssnittet: den som har en CSV- eller Excelfil med kunder kan inte ladda upp den i CRM:et, koppla kolumner och granska raderna. Det går bara över API:t, med en anslutning och en API-nyckel.
2. Ingen export: varken en vy, markerade poster eller en enskild post går att ladda ned som CSV. Det enda sättet ut är API:ts listning med markör (JSON).
3. Ingen sammanslagning av dubbletter: två poster för samma bolag eller person kan inte slås ihop, varken från listan eller från posten, och relaterade personer, affärer och anteckningar flyttas aldrig över.
4. Ingen dubblettsökning: CRM:et kan inte visa troliga dubbletter för en post. Dubblettskyddet finns bara som matchning när en post skrivs (organisationsnummer, e-post, källans id, entydig domän eller entydigt namn).
5. Ingen Excelfil (.xlsx eller .xls) in i CRM:et, bara CSV i UTF-8 och JSON.
6. Ingen granskning före import där raderna rättas eller tas bort i en tabell. Förhandsgranskningen över API:t tar högst 50 poster och visar bara vad som skulle hända.
7. Ingen export av hela arbetsytan som zip-arkiv för administratören, och ingen säkerhetskopia att ta före en massuppdatering.
8. Ingen bolagslogotyp ur domänen: bolagen visas med initialer.
9. Ingen berikning av bolag eller personer från en extern tjänst. Berikning av bolag ur SCB:s register är en öppen fråga till Anton.
10. Bara personer går att koppla till bolag vid import. Affärer, uppgifter, anteckningar och aktiviteter går inte att importera alls, och ansvarig säljare är fri text, inte en användare.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| IE-001 | Användaren startar en import av poster från ett objekts listvy. | inte gjord | Bolag och Personer (`BolagVy.tsx`, `PersonerVy.tsx`) har ingen importhandling; synken startas bara av källan över API:t (SynkVy: "Källan startar den över API:t"). | 3 |
| IE-002 | Det finns två vägar in: kalkylblad i gränssnittet och API. | delvis | API-vägen finns: `POST /v1/sync/companies`, `/v1/sync/people` och körningar i satser (`crm_v1.py`), prövad i `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting` (`test_api.py`). Kalkylbladsvägen i gränssnittet saknas. | 3 |
| IE-003 | Importen skapar poster men aldrig nya fält eller valalternativ. | delvis | Nya valvärden skapas aldrig: en okänd relation ger fältfelet `relation_okand` (`adaptrar._relation`). Men egna fält i `extra` uppstår av importen när mappningen räknar upp dem (`adaptrar.mappa`, högst 50), så kravet att fältet ska finnas först gäller inte. | 3 |
| IE-004 | Import och export kräver var sin behörighet. | delvis | Synken kräver nyckelns omfång `crm:synk` (`kraev("crm:synk")` i `crm_v1.py`), prövat i `test_varje_omfang_oppnar_bara_sitt` (`test_api.py`). Någon export att skydda finns inte, och ingen behörighet per användare i appen. | 3 |
| IE-005 | Importen tar CSV, xlsx och xls, med komma eller semikolon som avgränsare. | delvis | CSV i UTF-8 (BOM tas bort), semikolon, komma eller tabb gissas, `sep=;` respekteras, och JSON (`adaptrar.tolka_csv`, `crm_v1._las_sats`), prövat i `test_csv_med_semikolon_och_svenska_rubriker` och `test_csv_med_komma_och_for_manga_rader`. Excel (.xlsx, .xls) saknas i CRM:et. | 3 |
| IE-006 | En fil får ha högst ett visst antal rader. | verifierad | Högst 500 poster per sats (`crm_v1.MAX_SATS`) och 8 MB kropp, annars `too_many_items` eller `body_too_large`; fler poster skickas i flera satser i samma körning. `test_satsens_granser` (`test_api.py`). | |
| IE-007 | Användaren hämtar en exempelfil som visar kolumner och format. | delvis | `GET /v1/connections/systems` (`crm_v1.py`) visar varje systems standardmappning, alltså vilka kolumnrubriker som känns igen, och `docs/crm/API.md` visar ett CSV-exempel. Ingen nedladdningsbar exempelfil. | 3 |
| IE-008 | Adress importeras som en kolumn per del. | verifierad | Gatuadress, c/o, postnummer, ort och land är egna fält (`adaptrar.BOLAGSFALT`); postnummer tolkas till `NNN NN`. `test_csv_in_med_anslutningen_i_fragan` och `test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr` (`test_api.py`). | |
| IE-009 | Listfält importeras som en JSON-lista av strängar. | inte gjord | Snajp CRM har inga listfält; `extra` tar bara skalära värden (`synk._tolka`). | ej planerad |
| IE-010 | Sant och falskt skrivs på ett bestämt sätt. | byggd | `adaptrar._sann` tolkar allt utom tomt, false, 0, nej, no, n, f, null och none som sant (kontakta inte, privatperson, raderad). | |
| IE-011 | Valuta importeras som belopp och valutakod. | delvis | Omsättning tolkas som heltal kronor i svenska och engelska skrivsätt (`falt.heltal`, `test_heltal_svenska_och_engelska_skrivsatt` i `test_falt_och_adaptrar.py`). Ingen valutakod: allt är SEK. | ej planerad |
| IE-012 | Datum importeras i ett tolkbart format. | verifierad | `falt.datum` tar ÅÅÅÅ-MM-DD, ISO-tid, DD/MM/ÅÅÅÅ, DD.MM.ÅÅÅÅ, ÅÅÅÅMMDD och millisekunder och sparar ISO-datum. `test_datum_blir_iso` (`test_falt_och_adaptrar.py`). | |
| IE-013 | Bolagets domän importeras i ett rekommenderat format och är unik. | delvis | Webbplatsen normaliseras och domänen härleds utan www (`falt.webbplats`, `test_webbplats_och_privata_domaner`). Domänen är inte unik (bara ett vanligt index i migration 160) och används för matchning bara när den pekar ut exakt en post. | |
| IE-014 | E-post importeras som giltig adress, unik per person, med fler adresser i en egen kolumn. | delvis | Primär adress valideras och sparas med gemener (`falt.epost`, `test_epost`) och är unik per kund bland levande personer (`crm_personer_epost_uq`, migration 160). Ytterligare adresser finns inte. | ej planerad |
| IE-015 | Användaren kan importera postens id för att skapa med eget id eller uppdatera en befintlig post. | delvis | Källans id sparas som externt id per anslutning och används för att hitta posten igen (`crm_externa_id`, `synk.synka_sats`, `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting`). Snajps eget id kan inte sättas vid import; en befintlig post uppdateras på sitt id bara med `PATCH`. | |
| IE-016 | JSON-fält importeras som giltig JSON. | inte gjord | Inga JSON-fält; `extra` tar bara skalära värden. | ej planerad |
| IE-017 | Länkfält importeras med URL, etikett och sekundära länkar. | delvis | En webbplats per bolag (`falt.webbplats`). Etikett och sekundära länkar saknas, och personer har inga länkfält. | ej planerad |
| IE-018 | Flervalsfält importeras som lista och skriver över tidigare värden. | inte gjord | Inga flervalsfält i Snajp CRM. | ej planerad |
| IE-019 | Tal importeras utan tusentalsavgränsare och valutatecken. | verifierad | `falt.heltal` är generösare: tar mellanslag, punkt och komma som avgränsare, "kr" och typografiskt minus. `test_heltal_svenska_och_engelska_skrivsatt` och `test_felen_ur_researchens_prov_ar_rattade` (`test_falt_och_adaptrar.py`). | |
| IE-020 | Telefon importeras med nummer, landskod och riktnummer. | verifierad | Ett fält per nummer, sparat som E.164; landet tas från bolaget (`falt.telefon`). `test_telefon_blir_e164` (`test_falt_och_adaptrar.py`). | |
| IE-021 | Betyg importeras som RATING_1 till RATING_5. | inte gjord | Inga betygsfält i Snajp CRM. | ej planerad |
| IE-022 | Enkelval importeras med alternativets API-namn, och nya alternativ skapas inte. | byggd | Relation och rättslig grund slås upp mot kända värden på svenska och engelska utan hänsyn till skiftläge (`adaptrar._relation`, `_rattslig_grund`, `_RELATION_ALLMAN`); okänt värde blir fältfel, aldrig nytt alternativ. Mappningens `uppslag` låter kunden översätta egna värden. | |
| IE-023 | Text importeras utan inledande och avslutande blanksteg. | byggd | `falt.text` trimmar och slår ihop blanksteg och kortar till fältets längd. | |
| IE-024 | Användaren hittar valfältens API-namn i inställningarna. | delvis | Tillåtna värden står i `docs/crm/API.md` och i specifikationen (`docs/crm/openapi.json`). Ingen inställningssida för datamodellen. | ej planerad |
| IE-025 | Relationer importeras genom att referera föräldern med ett unikt fält. | delvis | En person kopplas till sitt bolag via källans bolags-id eller bolagets organisationsnummer (`synk.synka_sats`, `bolag_externt_id`, `bolag_orgnr`), prövat i `test_personer_synkas_och_knyts_via_kallans_bolags_id`. Andra relationer går inte att importera, och ansvarig är fri text. | 3 |
| IE-026 | Polymorfa relationer och många-till-många går inte att importera. | inte gjord | Anteckningar, uppgifter, aktiviteter och affärer (`objekt.py`) går inte att importera alls, så inte heller deras kopplingar. | ej planerad |
| IE-027 | Relaterade objekt importeras i ordning: bolag före personer före affärer. | byggd | API:t säger att bolagen skickas först (`crm_v1.sats_personer`, `docs/crm/API.md`); en person utan bolag i satsen får ingen koppling. Affärer och medlemmar importeras inte. | |
| IE-028 | En relation som inte hittas upptäcks först när importen körs. | delvis | Kopplingen avgörs vid skrivningen (`synk.synka_sats`), men en person vars bolag inte hittas skapas utan bolag, utan fel eller meddelande. | 3 |
| IE-029 | Import med unik nyckel uppdaterar en befintlig post i stället för att skapa en ny. | verifierad | Bolag matchas på källans id, sedan organisationsnummer, sedan entydig domän eller namn; personer på källans id och sedan e-post. Skapande och uppdatering blandas, och fält som inte skickas rörs inte; en tom cell tömmer inte fältet. `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting`, `test_ett_falt_kallan_inte_skickar_roers_inte`, `test_personer_knyts_till_bolag_och_uppdateras_pa_epost` (`test_api.py`). | |
| IE-030 | Ett unikt fält kan ändras via import när ett annat unikt fält matchar. | byggd | När källans id matchar skrivs ett nytt organisationsnummer eller en ny adress över (`synk._andringar`); pekar numret på ett annat bolag blir raden en konflikt (`test_orgnr_som_tillhor_ett_annat_bolag_ar_en_konflikt`). | |
| IE-031 | En importerad rad med samma unika värde som en raderad post återställer posten. | delvis | Bara via källans id: en raderad post återställs med de nya uppgifterna (`test_raderad_i_kallan_blir_gravsten_och_kan_komma_tillbaka`). Via organisationsnummer eller e-post söks bara levande poster (`lagring.hitta_poster`), så en ny post skapas i stället. | 3 |
| IE-032 | Standardobjektens unika fält är id och e-post för personer, id och domän för bolag. | verifierad | Bolag: organisationsnummer (inte domän) är unikt per kund bland levande rader (`crm_bolag_orgnr_uq`); personer: e-post (`crm_personer_epost_uq`), migration 160. `test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr` och `test_personer_knyts_till_bolag_och_uppdateras_pa_epost`. Egna fält kan inte göras unika. | |
| IE-033 | Dubbletter inom filen markeras före import. | delvis | Två rader för samma bolag eller adress i en sats blir en post (`synk.synka_sats`, "Senare poster i samma sats ska se den här"). Ingen markering, ingen granskning. | 3 |
| IE-034 | Granskningen anger hur många rader som uppdaterar respektive skapar. | delvis | `POST /v1/connections/{connection}/preview` visar status per post (skapad, uppdaterad, hoppad) utan att skriva, högst 50 poster; `test_forhandsgranskning_skriver_ingenting`. Ingen granskning i gränssnittet. | 3 |
| IE-035 | Det finns ingen ångra för massuppdatering; export rekommenderas som säkerhetskopia. | inte gjord | Ingen export att ta som säkerhetskopia. Händelseloggen (`handelser.py`) visar vilka fält som ändrats, men inte värdena, och kan inte återställa. | ej planerad |
| IE-036 | Användaren exporterar en vy till CSV. | inte gjord | Ingen export i `BolagVy.tsx` eller `PersonerVy.tsx` och ingen exportväg i `crm_v1.py`. Ut går bara listning med markör över API:t (JSON). | ej planerad |
| IE-037 | Exporten tar med synliga kolumner, egna fält, id och relations-id. | inte gjord | Ingen export. | ej planerad |
| IE-038 | Vissa delar (arbetsflöden, inställningar, logg) går inte att exportera eller flytta. | inte gjord | Ingen export av något slag i CRM:et. | ej planerad |
| IE-039 | Migrering från ett annat CRM steg för steg. | delvis | Bolag och personer kan flyttas in från tolv system med färdig mappning (`adaptrar.SYSTEM`, `adaptrar.STANDARD`), prövat i `test_standardmappningen_for_varje_system` (`test_falt_och_adaptrar.py`). Affärer, aktiviteter, anteckningar, uppgifter och användare går inte att flytta in. | 3 |
| IE-040 | Byte från egen drift av Twenty till molnet via export och import. | avstår | Gäller bara egen drift av Twenty. | |
| IE-041 | Massimport över API i satser med hastighetsgräns. | verifierad | Satser om högst 500 poster, 600 anrop per minut och kund med `Retry-After` vid 429, och idempotensnyckel (`crm_v1.py`). `test_satsens_granser`, `test_taket_ger_429_med_retry_after`, `test_idempotency_key_ger_samma_svar_en_gang` (`test_api.py`). | |
| IE-042 | Importen öppnas som ett kommando i objektets meny och visas bara på listsidan, utanför papperskorgen och med behörighet. | inte gjord | Ingen importhandling i Bolag, Personer eller kommandopaletten (`Kommandopalett.tsx`). | 3 |
| IE-043 | Importguiden har fasta steg med en stegrad högst upp. | inte gjord | Ingen importguide i CRM:et. Leads har en guide i fyra steg (`components/leads/ImportLista.tsx`) som inte går att nå från CRM:et. | 3 |
| IE-044 | Användaren stänger guiden och bekräftar att informationen inte sparas. | inte gjord | Ingen importguide. | 3 |
| IE-045 | Användaren laddar upp en fil genom att dra in den eller välja den. | inte gjord | Ingen filuppladdning i CRM:ets gränssnitt; filen skickas som kropp till `POST /v1/sync/companies` med `text/csv`. | 3 |
| IE-046 | Uppladdningsytan visar hur många poster som får importeras. | inte gjord | Ingen uppladdningsyta. Taket (500 per sats) står i `docs/crm/API.md`. | 3 |
| IE-047 | Filen tolkas med UTF-8, tomma rader tas bort och exportens skyddstecken tas bort. | delvis | `adaptrar.tolka_csv` läser UTF-8 och tar bort BOM, hoppar över tomma rader och trimmar celler, på servern. Ingen xlsx och inget skyddstecken mot formler att ta bort (ingen export). | 3 |
| IE-048 | Radtaket kontrolleras när filen läses. | verifierad | `adaptrar.tolka_csv(max_rader=...)` stoppar med "Filen har fler än N rader. Dela upp den." och API:t svarar `too_many_items`. `test_csv_med_komma_och_for_manga_rader` (`test_falt_och_adaptrar.py`) och `test_satsens_granser` (`test_api.py`). | |
| IE-049 | Användaren hämtar en exempelfil med objektets fält och tre exempelrader. | inte gjord | Ingen exempelfil; `GET /v1/connections/systems` visar bara vilka rubriker som känns igen. | 3 |
| IE-050 | I en arbetsbok med flera blad väljer användaren blad. | inte gjord | Excel stöds inte i CRM:et. | 3 |
| IE-051 | Användaren väljer vilken rad som är rubrikrad. | delvis | Första raden är alltid rubrikrad, och en `sep=`-rad före den hoppas över (`adaptrar.tolka_csv`). Inget val av rubrikrad. | 3 |
| IE-052 | Bara vissa fält går att importera till. | verifierad | Målen är de fält som räknas upp i `adaptrar.BOLAGSFALT` och `PERSONFALT` plus egna fält i `extra`; en mappning mot något annat avvisas. `test_varje_system_har_en_mappning_och_bara_kanda_falt` och `test_ogiltig_mappning_avvisas` (`test_falt_och_adaptrar.py`). | |
| IE-053 | Sammansatta fält importeras som en kolumn per delfält med etiketten "Fält / Delfält". | delvis | Snajps fält är platta: adressen är fem egna fält och ett helt namn delas i förnamn och efternamn (`adaptrar.mappa`). Inga etiketter av formen "Fält / Delfält" och ingen engelsk reservetikett i ett gränssnitt. | 3 |
| IE-054 | Relationsfält importeras via målobjektets unika fält. | verifierad | Personens bolag kopplas via källans bolags-id eller bolagets organisationsnummer; tomma värden hoppas över. `test_personer_synkas_och_knyts_via_kallans_bolags_id` (`test_api.py`). | |
| IE-055 | Kolumner matchas automatiskt mot fält. | delvis | Rubriker normaliseras (`adaptrar._rubrik`) och matchas mot standardmappningens kända namn på svenska och engelska, utan hänsyn till skiftläge. `test_csv_med_semikolon_och_svenska_rubriker`. Ingen luddig matchning och inget gränssnitt. | 3 |
| IE-056 | Användaren ser föreslagna fält per kolumn. | inte gjord | Ingen kolumnmatchning i gränssnittet. | 3 |
| IE-057 | Användaren matchar en kolumn mot ett fält för hand, med sökning och exempelvärde. | delvis | Egen mappning per fält går att sätta på anslutningen över API:t och läggs ovanpå standarden (`adaptrar.validera_mappning`, `gallande_mappning`); `test_kundens_mappning_laggs_ovanpa_standarden`. SynkVy väljer bara system, ingen fältväljare. | 3 |
| IE-058 | Ett fält kan bara matchas av en kolumn. | byggd | Mappningen går från målfält till källa (dokumentationen i `adaptrar.py`), så varje fält har en källa, eller en lista där den första med värde gäller. | |
| IE-059 | Användaren hoppar över en kolumn. | verifierad | Bara kolumner som mappas följer med; egna fält bara om de räknas upp (dataminimering, `docs/BESLUT.md` 2026-11-23). `test_kundens_mappning_laggs_ovanpa_standarden` (`test_falt_och_adaptrar.py`). | |
| IE-060 | Valfältens värden matchas mot alternativ, och omatchade blir tomma. | byggd | Mappningens `uppslag` översätter källans värden, och relationens kända värden slås upp utan hänsyn till skiftläge (`adaptrar._los`, `_relation`); ett omatchat värde blir fältfel och fältet lämnas tomt. Inget gränssnitt per värde. | |
| IE-061 | Flervalsfältens värden matchas per enskilt värde. | inte gjord | Inga flervalsfält. | ej planerad |
| IE-062 | Sant och falskt normaliseras utan hänsyn till skiftläge. | verifierad | `adaptrar._sann`; `test_inaktiv_i_kallan_ar_raderad` (`test_falt_och_adaptrar.py`) prövar falskt, 0 och en tidpunkt. | |
| IE-063 | Tomma celler blir "inget värde" och skickas inte. | byggd | `adaptrar._tomt` och `mappa.satt` hoppar över tomma värden, så att en tom cell aldrig skriver över ett fält. | |
| IE-064 | Användaren varnas när obligatoriska fält saknar kolumn. | delvis | En rad utan namn (bolag) eller utan namn och e-post (person) hoppas över med skälet `saknar_namn` eller `saknar_namn_och_epost`; `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting`. Ingen varning före importen. | 3 |
| IE-065 | Nästa steg kräver minst en matchad kolumn. | inte gjord | Ingen guide. | 3 |
| IE-066 | Användaren börjar om matchningen efter bekräftelse. | inte gjord | Ingen guide. | 3 |
| IE-067 | Tal valideras. | byggd | `falt.heltal` ger fältfel när värdet inte går att tolka; fältet hoppas över och posten skrivs ändå (`adaptrar.mappa`). | |
| IE-068 | id och relationer som refereras med id måste vara giltiga UUID. | delvis | Id i API:ts sökvägar kontrolleras (`kraev_uuid`), `test_felformat_id_ger_404_aldrig_500`. Vid import är källans id fri text och ingen UUID krävs. | |
| IE-069 | E-post valideras, primär adress sparas med gemener, och ytterligare adresser kontrolleras. | delvis | Primär adress valideras och görs till gemener (`falt.epost`, `test_epost`). Ytterligare adresser finns inte. | ej planerad |
| IE-070 | Länkar och domäner valideras och normaliseras. | delvis | Webbplatsen normaliseras och domänen härleds; privata domäner som gmail.com räknas aldrig som bolagets (`falt.webbplats`, `test_webbplats_och_privata_domaner`). Sekundära länkar finns inte. | ej planerad |
| IE-071 | Datum och tidpunkt valideras och sparas som datum respektive ISO-tid. | verifierad | `falt.datum` och `falt.tidpunkt`; `test_datum_blir_iso` (`test_falt_och_adaptrar.py`). | |
| IE-072 | Telefon valideras: nummer, riktnummer och landskod. | verifierad | `falt.telefon` tolkar och ger E.164 eller fältfel; `test_telefon_blir_e164`, `test_telefon_utan_riktnummer_sparas_inte`. Ytterligare nummer som lista finns inte; personer har telefon och mobil. | |
| IE-073 | Telefon utan landsnummer kompletteras. | verifierad | Svenska nummer får +46 och ett mobilnummer där Excel tappat nollan räddas (`falt.telefon`). `test_telefon_blir_e164`, `test_felen_ur_researchens_prov_ar_rattade`. | |
| IE-074 | JSON, listor och betyg valideras. | inte gjord | Inga sådana fälttyper. | ej planerad |
| IE-075 | Valutabelopp skrivs om till mikroenheter. | delvis | Belopp tolkas till hela kronor (`falt.heltal`). Ingen valutakod och inga mikroenheter. | ej planerad |
| IE-076 | Adress och text skrivs som text, och ett sammansatt fält utan värden skickas inte. | byggd | `adaptrar.mappa` skriver adressens delar som text via `falt.text` och hoppar över tomma delar. Formaterad text finns inte. | |
| IE-077 | Importerade poster märks med källan import. | verifierad | `kalla` blir `synk` vid synk och `api` vid skapande över API:t. `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting` och `test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr` (`test_api.py`). | |
| IE-078 | Dubbletter inom filen markeras på varje unikt villkor. | delvis | Samma bolag eller adress två gånger i en sats blir en post (`synk.synka_sats`). Inget markeras, och ingen granskning. | 3 |
| IE-079 | Granskningen har en regelmotor med nivåerna fel, varning och info. | delvis | Fältfel med kod per fält samlas i `adaptrar.Mappad.fel` och visas på körningen. En nivå, ingen regelmotor. | 3 |
| IE-080 | Användaren granskar och rättar raderna i en tabell före import. | inte gjord | Ingen granskning före import. Efteråt visar SynkVy raderna som inte kom in, utan att de går att rätta där. | 3 |
| IE-081 | Användaren filtrerar fram rader med fel. | inte gjord | Ingen granskningstabell. Körningens fel visas i SynkVy efter importen. | 3 |
| IE-082 | Användaren tar bort rader före import. | inte gjord | Ingen granskningstabell. | 3 |
| IE-083 | Användaren bekräftar importen även när rader har fel. | inte gjord | Ingen bekräftelse. Synken skriver raderna och hoppar över fält som inte går att tolka (`synk.py`). | 3 |
| IE-084 | Posterna skrivs in i omgångar med upsert. | verifierad | En körning tar flera satser om högst 500 och avslutas för sig (`/v1/sync/runs`, `/v1/sync/runs/{id}/companies`, `/complete`). `test_full_synk_i_satser_tar_hand_om_det_som_saknas` (`test_api.py`). | |
| IE-085 | Användaren ser importens förlopp som "X av Y poster". | byggd | SynkVy visar en pågående körning som "X av Y poster" och hämtar om var tredje sekund medan något pågår (`SynkVy.tsx`, `SYNKPULS`); utfallet ligger kvar efter omladdning. Gäller körningar som källan startat, inte en import i gränssnittet. | |
| IE-086 | Användaren avbryter en pågående import. | inte gjord | Ingen väg att avbryta en körning i `crm_v1.py` eller SynkVy. | 3 |
| IE-087 | En misslyckad import kan skickas igen utan dubbelimport. | verifierad | Samma sats igen ändrar ingenting (källans id och innehållshash), och idempotensnyckeln ger samma svar. `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting`, `test_idempotency_key_ger_samma_svar_en_gang` (`test_api.py`). | |
| IE-088 | Guiden har utbyggnadspunkter och inställningar för anroparen. | avstår | Intern inställning i förlagans guidekomponent. Ersätts av något Snajp redan har: anslutningens mappning, konfliktregel och regel för saknade poster (`adaptrar.py`, `synk.py`). | |
| IE-089 | Användaren exporterar markerade poster eller hela vyn med kommandot Exportera. | inte gjord | Åtgärdsraden i `BolagVy.tsx` och `PersonerVy.tsx` har bara Ändra relation och Ta bort; ingen export. | ej planerad |
| IE-090 | Exportens urval följer vyns filter och sortering, eller markeringen. | inte gjord | Ingen export. | ej planerad |
| IE-091 | Exportens kolumner följer vyns synliga fält i vyns ordning. | inte gjord | Ingen export och inget kolumnval. | ej planerad |
| IE-092 | Exportens första kolumn är alltid postens id. | inte gjord | Ingen export. | ej planerad |
| IE-093 | Relationer exporteras som den relaterade postens id. | inte gjord | Ingen export. | ej planerad |
| IE-094 | Sammansatta fält exporteras som en kolumn per delfält. | inte gjord | Ingen export. | ej planerad |
| IE-095 | Värdena formateras för CSV: datum, belopp, listor och citattecken. | inte gjord | Ingen export. | ej planerad |
| IE-096 | Exportfilen börjar med UTF-8 BOM så att Excel läser tecknen rätt. | inte gjord | Ingen export. Importen tar däremot bort en BOM (`adaptrar.tolka_csv`). | ej planerad |
| IE-097 | Exporten skyddar mot formelinjektion i kalkylprogram. | inte gjord | Ingen export. | ej planerad |
| IE-098 | En liten export byggs direkt i webbläsaren. | inte gjord | Ingen export. | ej planerad |
| IE-099 | En stor export körs som bakgrundsjobb på servern med förlopp och tillfällig länk. | inte gjord | Ingen export. | ej planerad |
| IE-100 | Exportbegäran valideras (objekt, fält, sortering). | inte gjord | Ingen export. | ej planerad |
| IE-101 | Export kräver behörighet och tillåts för användare, API-nyckel och app. | inte gjord | Ingen export. | ej planerad |
| IE-102 | Bara en export åt gången per arbetsyta. | inte gjord | Ingen export. | ej planerad |
| IE-103 | Exportjobbet läser i sidor och rapporterar förlopp i procent. | inte gjord | Ingen export. | ej planerad |
| IE-104 | En export har tak för tid och filstorlek. | inte gjord | Ingen export. | ej planerad |
| IE-105 | Behörigheterna kontrolleras under hela exporten. | inte gjord | Ingen export. | ej planerad |
| IE-106 | Exportens kolumnrubriker översätts till beställarens språk. | inte gjord | Ingen export. | ej planerad |
| IE-107 | Nedladdningslänken gäller en gång och bara för beställarens session. | inte gjord | Ingen export. | ej planerad |
| IE-108 | Exportfilen är tillfällig och tas bort efter nedladdning eller fel. | inte gjord | Ingen export. | ej planerad |
| IE-109 | Användaren ser exportens förlopp på kommandot och kan avbryta. | inte gjord | Ingen export. | ej planerad |
| IE-110 | Generiska fel vid export ger ett gemensamt meddelande. | inte gjord | Ingen export. | ej planerad |
| IE-111 | Användaren exporterar en enskild post till CSV. | inte gjord | Postpanelerna (`BolagPanel.tsx`, `PersonPanel.tsx`) har ingen export. Registerutdrag per person enligt GDPR står som IN-143 i fas 5 i `docs/crm/MIGRERING-FUNKTIONSLISTA.md`, men det är inte samma sak. | ej planerad |
| IE-112 | Gränssnittet följer ett serverjobb via dess id. | delvis | SynkVy följer körningar och en vald körning via id (`GET /v1/sync/runs/{run_id}`) med hämtning var tredje sekund, inte via en realtidsström (`SynkVy.tsx`). Ingen gemensam jobbmekanism. | ej planerad |
| IE-113 | Jobbets tillstånd når ett sluttillstånd, och då slutar gränssnittet följa det. | byggd | Körningen har status pågår, klar eller misslyckad, och hämtningen var tredje sekund slutar när ingen körning pågår (`SynkVy.tsx`, effekten med `nagotPagar`). | |
| IE-114 | Förloppet visas i procent med fast bredd så att siffran inte hoppar. | delvis | Förloppet visas som antal ("X av Y poster") med tabellsiffror (`tabular-nums`) i `SynkVy.tsx`. Ingen procent. | ej planerad |
| IE-115 | Jobbstatus hämtas om efter återanslutning. | avstår | Ersätts av något Snajp redan har: SynkVy hämtar körningarna på nytt var tredje sekund (`SynkVy.tsx`), så det finns ingen ström att återansluta. | |
| IE-116 | Jobbmekanismen används för appinstallation och utskickslistor. | inte gjord | CRM:et har ingen appmarknad och inga utskickslistor, och därmed ingen sådan användning. | ej planerad |
| IE-117 | Serveradministratören exporterar en hel arbetsyta som CSV-filer i ett zip-arkiv. | inte gjord | Ingen export av en hel kunds CRM i adminytan eller i CRM:et. | ej planerad |
| IE-118 | Bara en arbetsyteexport åt gången. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-119 | Arbetsyteexporten tar med alla objekt och fält, också raderade poster. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-120 | Arbetsyteexporten körs i steg med delfiler om högst 20 MB. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-121 | Ett felande exportsteg försöks om tre gånger. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-122 | Arkivet packas med en manifestfil. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-123 | Administratören ser exportens status och förlopp i en tabell. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-124 | Administratören laddar ned arkivet. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-125 | Gamla exporter rensas automatiskt varje timme. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-126 | En begärd arbetsyteexport loggas som händelse. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-127 | Varje objekt kan ha egna dubblettkriterier i form av fältkombinationer. | delvis | En fast ordning för att känna igen en post när den skrivs: källans id, organisationsnummer, entydig domän, entydigt namn, och för personer e-post (`synk.py`, modulens dokumentation). Inga kriterier per objekt och ingen dubblettsökning. | ej planerad |
| IE-128 | Bolag räknas som dubbletter vid samma namn eller samma domän. | delvis | Domän och namn används bara för bolag utan organisationsnummer och bara när exakt en post matchar; namnet jämförs utan bolagsform och skiftläge (`falt.namnnyckel`). `test_utan_orgnr_matchas_bara_pa_entydig_doman_eller_entydigt_namn` (`test_api.py`). Används vid skrivning, inte som dubblettlista. | ej planerad |
| IE-129 | Personer räknas som dubbletter vid samma namn, LinkedIn eller e-post. | delvis | Bara e-post (och källans id) känner igen en person; `test_personer_knyts_till_bolag_och_uppdateras_pa_epost`. Namn och LinkedIn används inte, och LinkedIn finns inte som fält. | ej planerad |
| IE-130 | Värden kortare än tre tecken räknas inte vid dubblettjämförelse. | inte gjord | Ingen sådan regel; namnnyckeln normaliserar i stället namnet (`falt.namnnyckel`). | ej planerad |
| IE-131 | Integratören söker dubbletter via API. | inte gjord | Ingen dubblettväg i `crm_v1.py`. | ej planerad |
| IE-132 | Dubblettkontrollen körs bara på begäran, inte när en post skapas. | verifierad | Snajp gör tvärtom: kontrollen körs vid varje skapande över API:t (`synk.skapa`: samma organisationsnummer eller e-post uppdaterar den befintliga posten) och i varje synksats. `test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr`, `test_tva_kallor_om_samma_bolag_blir_en_post` (`test_api.py`). | |
| IE-133 | Användaren slår ihop 2 till 9 markerade poster från listvyn. | inte gjord | Åtgärdsraden har ingen sammanslagning. `docs/BESLUT.md` (CRM-grunden 2026-11-26) säger "hellre en dubblett som en människa slår ihop", men verktyget för det finns inte; frågan är öppen i `docs/crm/SVENSK-STANDARD.md` § 3 (SuperOffice). | ej planerad |
| IE-134 | Användaren slår ihop en post med en annan som väljs i en sökbar lista. | inte gjord | Ingen sammanslagning i postpanelerna. | ej planerad |
| IE-135 | Sammanslagningsvyn har flikar för förhandsvisning, varje post och inställningar. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-136 | Användaren väljer vilken post som vinner vid konflikt. | inte gjord | Ingen sammanslagning. Synkens konfliktregel (källan, Snajp eller nyast) gäller källa mot Snajp, inte post mot post. | ej planerad |
| IE-137 | Användaren förhandsgranskar den sammanslagna posten utan att spara. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-138 | Användaren genomför sammanslagningen och förs till den kvarvarande posten. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-139 | Fältvärdena slås ihop: prioritetspostens värde vinner, annars första ifyllda. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-140 | Listor och flerval får unionen av alla posters värden. | inte gjord | Ingen sammanslagning och inga listfält. | ej planerad |
| IE-141 | E-post, telefon och länkar förenas med primärvärde och ytterligare värden. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-142 | Relaterade poster flyttas till den kvarvarande posten. | inte gjord | Ingen sammanslagning; personer, affärer, uppgifter och anteckningar flyttas aldrig mellan bolag. | ej planerad |
| IE-143 | De andra posterna raderas permanent i samma transaktion. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-144 | Sammanslagningen valideras och har egna felmeddelanden. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-145 | Integratören slår ihop poster via API, med torrkörning. | inte gjord | Ingen sammanslagningsväg i `crm_v1.py`. `docs/crm/API.md` ("Det som inte finns än") nämner att sammanslagningar i källan inte följs. | ej planerad |
| IE-146 | Vyerna uppdateras efter en sammanslagning. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-147 | Många poster skapas i ett anrop med valfri upsert. | verifierad | En synksats tar högst 500 poster och gör alltid upsert (`crm_v1.MAX_SATS`, `synk.synka_sats`). Satsen är inte en transaktion: varje post avgörs för sig. `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting`, `test_satsens_granser` (`test_api.py`). | |
| IE-148 | Upsert matchar mot objektets unika fält, också mot raderade poster. | delvis | Matchningen mot källans id, organisationsnummer och e-post finns (`synk.synka_sats`, prövad i `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting`). Raderade poster hittas bara via källans id; organisationsnummer och e-post söks bland levande poster (`lagring.hitta_poster`). | 3 |
| IE-149 | En matchad post uppdateras och återställs ur papperskorgen. | verifierad | Skickade fält skrivs, raderingstiden nollställs och källan (`kalla`) skrivs inte över (`synk.synka_sats`). `test_raderad_i_kallan_blir_gravsten_och_kan_komma_tillbaka`, `test_ett_falt_kallan_inte_skickar_roers_inte` (`test_api.py`). | |
| IE-150 | En tvetydig matchning avvisas. | verifierad | Pekar källans id på en post och organisationsnumret på en annan blir raden en konflikt med `orgnr_tillhor_annat_bolag` och `conflicting_id`; domän och namn som pekar på flera poster används inte alls. `test_orgnr_som_tillhor_ett_annat_bolag_ar_en_konflikt`, `test_utan_orgnr_matchas_bara_pa_entydig_doman_eller_entydigt_namn` (`test_api.py`). | |
| IE-151 | Relationer kan kopplas eller skapas nästlat i samma anrop. | delvis | En person kopplas till ett befintligt bolag i samma sats (`bolag_externt_id`, `bolag_orgnr`, eller `company_id` i `POST /v1/people`). Nästlat skapande av bolaget finns inte. | ej planerad |
| IE-152 | Bolagets logotyp hämtas från domänen och visas på posten. | delvis | Domänen härleds och sparas (`falt.webbplats`, kolumnen `doman`), men ingen logotyp hämtas: bolagen visas med initialer i en färgad avatar (`BolagVy.tsx`, `BolagPanel.tsx`). | ej planerad |
| IE-153 | Arbetsytans bolag berikas under introduktionen. | inte gjord | Ingen berikning i CRM:et. | ej planerad |
| IE-154 | Bolagsberikningen körs bara under vissa villkor (skaparen, arbetsdomän, nyckel finns). | inte gjord | Ingen berikning. | ej planerad |
| IE-155 | Bolagsuppgifter hämtas från en extern tjänst (People Data Labs) på domänen. | inte gjord | Ingen extern berikningstjänst. Berikning ur SCB:s register på bolagsnivå är fråga 4 i `docs/crm/SVENSK-STANDARD.md`. | ej planerad |
| IE-156 | Berikningen hämtar namn, bransch, storlek, ort och liknande och sanerar texten. | inte gjord | Ingen berikning. | ej planerad |
| IE-157 | Arbetsytans skapare berikas som person på sin e-post. | inte gjord | Ingen personberikning. | ej planerad |
| IE-158 | Berikningsanropen stryps till tio per timme och arbetsyta. | inte gjord | Ingen berikning. | ej planerad |
| IE-159 | Berikningens utfall klassas som matchad, ej tillgänglig eller tillfälligt fel. | inte gjord | Ingen berikning. | ej planerad |
| IE-160 | Berikningens resultat och varje försök sparas per arbetsyta. | inte gjord | Ingen berikning. | ej planerad |
| IE-161 | Berikningen avgör om introduktionen erbjuder ett säljsamtal. | inte gjord | Ingen berikning och inget sådant introduktionssteg i CRM:et. | ej planerad |
| IE-162 | Bolaget har standardfält som domän, LinkedIn, årsomsättning, adress och kontoansvarig. | delvis | `crm_bolag` (migration 160) har namn, organisationsnummer, momsnummer, bolagsform, SNI, webbplats och domän, e-post, telefon, adress, anställda, omsättning, relation, kund sedan, avtalsslut och ansvarig. LinkedIn saknas, och ansvarig är fri text, inte en användare. | 3 |
| IE-163 | Personen har standardfält som namn, e-post, LinkedIn, titel, telefon och bild. | delvis | `crm_personer` (migration 160) har förnamn, efternamn, titel, e-post, telefon, mobil, rättslig grund, kontakta inte och bolag. LinkedIn, ytterligare adresser och nummer, och bild saknas. | 3 |
| IE-164 | En användare i arbetsytan refereras med sin e-post vid import, t.ex. som kontoansvarig. | inte gjord | Ansvarig är fri text (`adaptrar.BOLAGSFALT`, `ansvarig`), inte en koppling till en användare. | ej planerad |
| IE-165 | Användaren startar importen från den globala kommandomenyn. | inte gjord | Kommandopaletten (`Kommandopalett.tsx`) har navigering och sökning men ingen import. | 3 |
| IE-166 | Användaren väljer rubrikrad i en tabell med en radioknapp per rad. | inte gjord | Ingen guide; första raden är alltid rubrikrad (`adaptrar.tolka_csv`). | 3 |
| IE-167 | Matchningssteget visar filens kolumner och målfälten sida vid sida. | inte gjord | Ingen guide. | 3 |
| IE-168 | Användaren väljer delfält för sammansatta fält och relationer i en undermeny. | inte gjord | Ingen guide. | 3 |
| IE-169 | Användaren väljer alternativ för ett enskilt valvärde i en rullista. | inte gjord | Ingen guide. Värdeöversättning går bara att skriva som `uppslag` i mappningen över API:t. | 3 |
| IE-170 | Nya valalternativ kan inte skapas i guiden. | inte gjord | Ingen guide. Synken skapar heller aldrig nya valvärden (`adaptrar._relation`). | 3 |
| IE-171 | Relationsreferensen ska matcha föräldern exakt, och en relation kan ändras via import. | byggd | Snajp matchar i stället bolagets organisationsnummer oavsett skrivsätt (`falt.orgnr` ger samma nyckel, `test_orgnr_alla_skrivsatt_ger_samma_nyckel`), och en ny bolagskoppling på en befintlig person skrivs vid nästa synk (`synk.synka_sats` sätter `bolag_id`). | |
| IE-172 | Exempelfilens relationsrubrik skiljer sig från importens mål. | inte gjord | Ingen exempelfil. | 3 |
| IE-173 | Radtaket gäller när det är satt, och felet anger taket. | verifierad | Taket är alltid satt och felet säger det: "En sats tar högst 500 poster." (`crm_v1._las_sats`). `test_satsens_granser` (`test_api.py`). | |
| IE-174 | Automationer och AI kan upserta poster och få antal skapade och uppdaterade. | inte gjord | Inga automationer eller AI-verktyg i CRM:et. Synkens svar räknar skapade och uppdaterade, men bara för API-anrop. | ej planerad |
| IE-175 | Automationer och AI kan slå ihop poster. | inte gjord | Ingen sammanslagning och inga automationer. | ej planerad |
| IE-176 | Den stora exportens fil hämtas via en egen engångsadress. | inte gjord | Ingen export. | ej planerad |
| IE-177 | Exportjobbets fel klassas med egna koder. | inte gjord | Ingen export. | ej planerad |
| IE-178 | Arbetsyteexportens fel har egna koder och meddelanden. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-179 | Arbetsyteexporten går att återuppta steg för steg ur ett sparat tillstånd. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-180 | Sammanslagningsvyns postflikar visar postens egen sidlayout. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-181 | Dubblettsökning via id matchar på alla läsbara fält, högst 200 träffar. | inte gjord | Ingen dubblettsökning. | ej planerad |
| IE-182 | Integratören importerar i omgångar via REST med upsert. | verifierad | `POST /v1/sync/companies` och `/v1/sync/people` (en sats, en körning) och `POST /v1/companies` eller `/v1/people`, som uppdaterar på organisationsnummer eller e-post. `test_synk_i_ett_anrop_och_omsynk_andrar_ingenting`, `test_csv_in_med_anslutningen_i_fragan`, `test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr` (`test_api.py`). Dubblett- och sammanslagningsvägarna saknas (IE-131, IE-145). | |
| IE-183 | Vid sammanslagning tas telefonnumret från prioritetsposten och övriga samlas. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-184 | Fältväljaren visar bara fält som går att importera. | delvis | En mappning mot ett okänt fält avvisas (`adaptrar.validera_mappning`, `test_ogiltig_mappning_avvisas`). Ingen fältväljare. | 3 |
| IE-185 | Granskningstabellen har fasta mått, färger per felnivå och tomlägen. | inte gjord | Ingen granskningstabell. | 3 |
| IE-186 | Varje steg har knapparna Tillbaka och Fortsätt med laddningsläge. | inte gjord | Ingen guide. | 3 |
| IE-187 | Rader med fel skickas aldrig. | avstår | Strider mot `docs/BESLUT.md` 2026-11-23 (listimporten): ett värde som inte håller lämnas tomt och raden importeras ändå. Synken följer samma regel (`synk.py`: "Synken hoppar över fält som inte går att tolka, inte posten"), prövad i `test_ett_fel_falt_faller_inte_posten`. | |
| IE-188 | Flervalsceller och andra fält redigeras som fri text i granskningen. | inte gjord | Ingen granskningstabell. | 3 |
| IE-189 | Användaren kan ändra värdematchningen även när alla värden kopplats automatiskt. | inte gjord | Ingen guide. | 3 |
| IE-190 | Arbetsyteexportens lista uppdateras av sig själv medan en export pågår. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-191 | Driften registrerar rensningen av arbetsyteexporter med ett kommando. | avstår | Gäller bara egen drift av Twenty (driftkommando som lägger rensningsjobbet i Twentys cron-kö). | |
| IE-192 | Arbetsyteexportens fel får API-felklasser. | inte gjord | Ingen arbetsyteexport. | ej planerad |
| IE-193 | Förhandsvisningen räknas om när användaren går tillbaka till den. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-194 | Förhandsvisningen visar alla relaterade poster samlade. | inte gjord | Ingen sammanslagning. | ej planerad |
| IE-195 | Sammanslagningen stoppas om dolda fält skulle ändras. | inte gjord | Ingen sammanslagning och inga fältbehörigheter. | ej planerad |
| IE-196 | Upsertens unika grupper byggs ur id och objektets unika index. | byggd | Fast ordning i `synk.synka_sats`: källans id, organisationsnummer, sedan domän och namn för bolag utan nummer; e-post för personer. De unika indexen gäller bara levande rader (`crm_bolag_orgnr_uq`, `crm_personer_epost_uq`, migration 160). Uppslagen görs med en fråga per sats (`lagring.hitta_poster`). | |
| IE-197 | Dubblettsökning utan tillämpligt kriterium ger ett tomt svar. | inte gjord | Ingen dubblettsökning. | ej planerad |
| IE-198 | Berikningens felmeddelande tas ur tjänstens svar, och strypningen är en token bucket. | inte gjord | Ingen berikning. | ej planerad |
| IE-199 | Personberikningens resultat saneras och kortas. | inte gjord | Ingen berikning. | ej planerad |
| IE-200 | Handbokens bild av granskningen (sammanfattning, obligatoriska fält, nya alternativ) avviker från koden. | inte gjord | Ingen granskning i gränssnittet; förhandsgranskningen över API:t (IE-034) är det närmaste. | 3 |
| IE-201 | Bolagets domän importeras som två kolumner, etikett och URL. | delvis | En kolumn, webbplatsen, och domänen härleds ur den (`falt.webbplats`, `test_webbplats_och_privata_domaner`). Ingen etikett. | ej planerad |
| IE-202 | Handboken har en felsökningstabell för vanliga importfel. | byggd | `docs/crm/API.md` listar skälen till att en post hoppas över eller krockar, och gränssnittet översätter dem till klartext (`lib/crm/felkoder.ts`, t.ex. `dubblett`). Personer utan e-post tas emot om de har namn, och källans id ligger i ett eget register (`crm_externa_id`). | |
| IE-203 | Exporten har fler kolumner för sammansatta fält än importen tar emot. | inte gjord | Ingen export. | ej planerad |
