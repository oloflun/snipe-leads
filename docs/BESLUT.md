# Beslutslogg

Varje nytt beslut om produkten skrivs här med beslutsfattarens eget resonemang,
så att skälet går att följa efteråt (Antons regel 2026-10-10). Nyaste överst.
Ett beslut som ersätts stryks inte: det får en rad om vad som ersatte det.

Format: datum, vem, beslutet, resonemanget (så nära beslutsfattarens ord som
möjligt), vad det betyder i koden.

---

## 2026-10-10 (Anton) — Org.nr stoppar inte utskick; utskick går från development

**Beslut.** Tvåvägssynken gäller bara körningar och ärenden i databasen;
funktioner och andra ändringar stannar i development tills de pushas. Syftet är
att pålitligt kunna testa nya funktioner mot samma data. Org.nr-regeln får inte
blockera utskick, och det måste gå att skicka utskick från development också.

**I koden.** Regel 1 kräver bara företagsnamnet i sidfoten; org.nr och
postadress tas med när kundregistret har dem (`leads_tools.lagstadgad_fot`,
`utskicksfot.bygg_fot`). Varje godkänt utkast bär miljön där det godkändes
(`gate_checks.godkand_i`) och skickas bara därifrån (`scheduler.skickas_har`),
så att synken aldrig ger ett dubbelutskick. Äldre godkännanden utan miljö och
autonoma utskick skickas av main. Uppföljningssvepet, inkorgsläsningen och
autopiloten körs bara i main.

*Att veta (agenten):* e-handelslagen kräver organisationsnummer i
information från en näringsidkare. Ett utskick utan org.nr går nu ut; regeln
kräver det inte längre.

## 2026-10-10 (Anton) — Tvåvägssynk mellan development och main

**Beslut.** Slå på och testa utskicken även i main. Allt speglas utom
specifika testkörningar, markerade som Provkörningar, som går att flytta över
till main. Alla övriga körningar och supportärenden speglas åt båda hållen med
det senaste tillägget som sanning. Vid första synken ska development vara
sanningen.

**Resonemang (Anton).** Det är en ändring från tidigare men en nödvändig sådan
för att kunna testa pålitligt.

**Fynd när beslutet genomfördes.** Den nattliga envägsspeglingen hade inte
speglat något sedan 2026-10-04: development låg på migration 110 och main på
102, skriptet avbröt, och GitHub visade grönt eftersom `tee` dolde felkoden.
Miljöerna hade glidit isär i sex dygn. Main hade under tiden fått produktions-
data som development saknade (15 kundmejl, 6 ärenden, 7 prospekt).

**I koden.** `scripts/railway_synk.py` (var tionde minut, `.github/workflows/
synk.yml`), migration 111 (`synk_andrad_at` och `synk_raderingar`).
*Agentens tolkning av "development är sanningen":* vid första synken vinner
development varje rad som finns i båda och skiljer sig, och allt som bara finns
i development kopieras till main. Det som bara finns i main raderas inte utan
kopieras till development, eftersom det är kundmejl och ärenden som annars
hade gått förlorade. En kopia av varje synkad tabell sparas före första synken.
Uppföljningar, inkorgsläsning och autopilot sker bara i main; utskick i den
miljö där utkastet godkändes (se beslutet ovan).

## 2026-10-10 (Anton) — Listornas leads stannar i listan; Flytta till Iris tas bort

**Beslut.** Alla leads från listor stannar i sina listor. Varje rad går att
klicka på och öppnar samma information och utkast som ett Iris-lead, med exakt
samma upplevelse. Knappen Flytta till Iris tas bort helt; kvar finns Processa om
och Skapa utkast, och båda går att köra på enskilda markerade rader eller alla.

**Resonemang (Anton).** Vår styrka är att alltid leverera högkvalitativa leads
och utkast. Även om listformatet låter användaren generera utkast för flera
hundra leads på en gång ska alla anpassas på exakt samma sätt som vanliga
Iris-leads. Flytta till Iris skulle göra Iris överfull och svårnavigerad, och
fungerade bara som ett stopp mellan ännu en utkastgranskning och utskicket.

**I koden.** Migration 110: `lead_list_items.prospect_id` kopplar raden till ett
bakgrundsprospekt (detaljvyn, researchen och utkastet går genom det), och
Iris-tabellen visar inte listkopplade prospekt (`GET /api/leads/prospects`).
`POST /api/leads/listor/{id}/utkast` kör samma research och utkast som Iris
(en körning med `kalla='lista'`, syns i Körningar). `till-iris` är borttagen.
De generella listutkasten (Sebbe 2026-10-07, `app/leads/listutkast.py`)
ersätts av detta.

## 2026-10-10 (Anton) — Processa om är en noggrannare omsökning

**Beslut.** Processa om anpassar en färdig lista, från en misslyckad körning
eller en annan användare, där leadsen ofta har bristfällig information. Den gör
om informationshämtningen i en noggrannare sökning och sveper bara källor som
förra agenten inte använde, så att så många källor som möjligt täcks. Hos
Alunix och Umeå Webbdesign hämtar Processa om även webbplatsinformationen på
nytt och förbereder underlag för utkast med erbjudande om hemsidor.

**Resonemang (Anton).** Det finns alltid kontaktinformation, det gäller bara
att leta tillräckligt. 200 bolag i dag blev ej kvalificerade och lämnades på
bordet för att de saknade hemsida eller lättillgänglig kontaktinformation.

**I koden.** `app/leads/omprova.py:sok` med källorna register, katalog
(hitta.se), webbplats och webbuppslag; prövade källor sparas i
`lead_list_items.kallor` (migration 110). Webbyråerna: `webbpool.bedom_en`.
Raderna uppdateras på plats, inget flyttas.

## 2026-10-10 (Anton) — Varje funktion har ett sätt att följa flödet

**Beslut.** Bygg alltid ett sätt att följa flödet för varje funktion. Fråga
alltid om det ska vara synligt för kund när det är tveksamt.

**Resonemang (Anton).** Processa om visade bara ett meddelande om att listan
processades, men det fanns inget sätt att följa aktiviteten eller veta om det
lyckades. Det ska lösas enkelt och tydligt i den befintliga miljön, inte i
ytterligare en flik om det inte är absolut nödvändigt.

**I koden.** `lead_lists.processering` (migration 110) bär förloppet för
Processa om och Skapa utkast och visas i listan, även efter en omladdning.
Regeln står i projektets CLAUDE.md.

## 2026-10-10 (Anton) — Kontaktuppgifter ur företagskatalogerna

**Beslut.** Leta i fler källor innan ett bolag blir ej kvalificerat. Hitta.se
och Eniro är där de flesta bolag fyller i sina uppgifter.

**Resonemang (Anton).** Norrtech i Skellefteå AB och Örnbergs Plåtslageri blev
"Inget kontaktsätt" respektive "Ingen namngiven VD" fast telefon, e-post och
webbplats stod öppet i katalogen och i Googles sammanfattning.

**I koden.** `app/leads/katalog.py`: hitta.se slås upp på org.nr (gratis, en
förfrågan per bolag) före webbplatsvalet i körningen och i Processa om.
Katalogens e-post är bolagsnivå (regel 13) och ger också webbplatsen via
domänen. Katalogens telefon räknas som bolagets publicerade nummer, som
sajtens, och kräver därför ingen VD i registret (`merinfo.fordela`).

*Bekräftat av Anton 2026-10-10:* regel 15 krävde en namngiven VD för
registrets nummer. Ett nummer bolaget själv publicerar i katalogen räknas som
sajtens nummer och kräver ingen VD. Så hamnar Örnbergs (070-numret, ingen VD i
registret) på ringlistan.

*Eniro:* inte inkopplad. Eniro svarar 403 på en ärlig bot-identitet och visar
numret först efter ett klick ("Visa nummer"); via ScrapeGraph kom varken
telefon eller e-post med. Vi maskerar oss inte som webbläsare.

*Gemini med Google-sökning och URL-kontext* provades för kontaktuppgifter
(Vertex, EU-regioner): 2.5-flash bytte till ett annat bolag när det sökta inte
hittades, 2.5-pro och 3.6-flash (3.6 finns bara på Vertex globala ändpunkt,
utanför EU-regionerna) gav inga träffar. För bolagshändelser och nyheter gav
2.5-flash användbara svar med länkar på bolagets egen sajt, men utan
sökkällor och med gissade datum: varje händelse måste styrkas genom att länken
hämtas innan den används.

## 2026-10-10 (Anton) — Iris sköter leads helt automatiskt inom kontots spärr

**Beslut.** Automatiseringen av leadskörningar, utkast, uppföljning och svar på
mejl ska slås på och skötas helt automatiskt av Iris, utifrån spärren som är
satt i kontot (första utkast, första mejl eller till bokat möte).

**Läget när beslutet togs (uppmätt i Railway och databasen 2026-10-10).**
Svaren hanteras redan automatiskt (inkorgen läses var femte minut i båda
miljöerna). Uppföljningar skrivs automatiskt men alltid som utkast till
granskning. Inget skickades av sig självt: `SEND_QUEUE_POLL_SECONDS` var inte
satt i någon miljö, så spärren avgjorde ingenting. Schemalagda leadskörningar
fanns inte. Bara kontot Snajp hade en spärr satt (`meeting`, till bokat möte,
som i koden beter sig som första mejl eftersom ett bokat möte kräver
överlämning); övriga stod på standard (utkast).

**I koden.** `app/leads/autopilot.py`: en Iris-körning per vardag från 06:00
med kundens `automation.autopilot.leads_per_dag` (standard 10, tak 50), när
både miljöns `LEADS_AUTOPILOT=1` och kundens `automation.autopilot.pa` är på.

*Väntar på Antons ja (agentens avgränsning):* att slå på `LEADS_AUTOPILOT`
och `SEND_QUEUE_POLL_SECONDS` i main. Development är en spegel med riktiga
kunders data och ska inte skicka mejl på egen hand till riktiga bolag; där
slås bara körningarna på, så att flödet går att följa utan utskick.

## 2026-10-10 (Anton) — Köade mejl kan skickas tidigare eller flyttas

**Beslut.** Det ska gå att markera och manuellt skicka mejl tidigare, eller
ändra den schemalagda tiden för ett eller flera mejl i kön utan att ändra
standarden.

**I koden.** Skicka nu går samma väg som Godkänn och skicka. Ändra tid:
`POST /api/leads/queue/schemalagg`; en vald tid utanför sändfönstret (vardagar
08–16) går ut när fönstret öppnar.

*Antons svar 2026-10-10:* "Gå direkt. Vanliga funktionen för att skicka
utkasten går via kön, men från kön kan man välja att skicka direkt." Skicka nu
(`POST /api/leads/queue/{id}/skicka-nu`) går därför förbi tidsgrinden och
regel 5a (kontorstid). Språkgrinden, suppression, karens, volymtak och
avsändaruppgifterna gäller fortfarande. Godkänn och skicka följer fönstret.
