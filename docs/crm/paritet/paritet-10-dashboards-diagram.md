# Paritet 10: Dashboards och diagram

I Twenty är en dashboard en vanlig post som bär en sidlayout med flikar och widgetar i ett rutnät om tolv kolumner: diagram (nyckeltal, stapel, linje, cirkel) som användaren själv konfigurerar med datakälla, mått, gruppering, filter, sortering och stil, plus tabell-, iframe-, rik text- och appwidgetar, med redigeringsläge, duplicering, nedborrning och ett grupperings-API på servern. Snajp CRM har ingen dashboardmotor alls, bara en fast översikt (`components/crm/app/OversiktVy.tsx`) med fyra nyckeltal, en ring över bolag per relation, liggande staplar för de största orterna och två listor, räknade ur `/api/crm/oversikt` (`snajp-support/app/api/crm.py`) och bolagslistan.

Antal per läge (räknat i tabellen nedan, 192 rader): verifierad 1, byggd 0, delvis 32, inte gjord 154, avstår 5.

Underlag: `docs/crm/underlag/twenty-10-dashboards-diagram.md`. Läget gäller arbetskatalogen 2026-11-26. `docs/crm/PLAN-MIGRERING.md` har ingen fas för egna dashboards eller en diagrambyggare (fas 3 nämner bara Astryx diagram som utgångspunkt, och `docs/BESLUT.md` 2026-11-26 säger att diagrammen ritas med `recharts`), så "ej planerad" i kolumnen Fas betyder att planen inte har någon fas för raden. Godkända bilder: `docs/crm/bilder/app/oversikt-1440.png`, `oversikt-390.png` och `oversikt-morkt-1440.png`. Backendens fasta grupperingar är antal bolag per relation (`snajp-support/app/crm/lagring.py:rakna_poster`) och affärer per steg med antal och summa (`GET /v1/deals/board`, `snajp-support/app/api/crm_v1_objekt.py:tavla`, ocommittat).

## De största luckorna

1. Det går inte att skapa en egen dashboard: ingen ny översikt, ingen namngivning, inga flikar, ingen duplicering och ingen lista över dashboards. Det finns en enda fast översikt per kund.
2. Inga egna diagram: användaren kan inte välja diagramtyp, datakälla, mått (summa, medel, min, max, andel) eller vad som ska grupperas.
3. Inget filter på ett diagram, till exempel "bara affärer stängda senaste 30 dagarna" eller "bara kunder i Västra Götaland".
4. Inga tidsserier: inget linje- eller stapeldiagram per dag, vecka, månad, kvartal eller år, och ingen kumulativ kurva. API:t har ingen historik att rita.
5. Inga affärsdiagram i gränssnittet: pipelinevärde per steg, affärer per ansvarig och intäkt över tid. API:t räknar summa per steg på tavlan men ingen yta visar den.
6. Inget redigeringsläge: widgetar kan inte läggas till, flyttas, storleksändras, dupliceras eller tas bort, och översikten har ingen layout att spara.
7. Ingen nedborrning: ett klick på en sektor eller stapel öppnar inte posterna bakom. Nyckeltalskorten länkar till listan, men utan filter.
8. Inga tabell-, iframe- eller rik text-widgetar på översikten, bara fasta listor över senaste synkar och senast ändrade bolag.
9. Inget grupperings- och aggregat-API (`groupBy` över REST eller GraphQL) som en integratör kan bygga egna rapporter på.
10. Ingen styrning av utseendet: färgschema, staplat eller sida vid sida, axelnamn, datavärden, förklaring av och på, talformat och fast Y-skala.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| DB-001 | Skapa en ny dashboard från dashboardlistan i sidomenyn och namnge den. | inte gjord | Finns inte: Översikten är en fast sida (`app/crm/oversikt/page.tsx`, `OversiktVy.tsx`), det går inte att skapa fler. | ej planerad |
| DB-002 | Dashboards är gemensamma för alla i arbetsytan, utan privata dashboards och utan export. | delvis | Den fasta översikten är densamma för alla i kundens arbetsyta (kundisolering och tillägget som grind, `snajp-support/app/crm/tillgang.py`). Egna dashboards att dela finns inte. | ej planerad |
| DB-003 | Favoritmarkera en dashboard med en personlig stjärna. | inte gjord | CRM:et har inga favoriter alls. | ej planerad |
| DB-004 | Duplicera en dashboard från kommandomenyn. | inte gjord | Finns inte: inga dashboardposter, och kommandopaletten (`Kommandopalett.tsx`) har bara navigering och sökning. | ej planerad |
| DB-005 | Visa diagramdata i betraktarens tidszon och med vald veckostart. | inte gjord | Finns inte: översikten har inga datumgrupperingar och ingen tidszonsinställning. | ej planerad |
| DB-006 | Filter sätts per widget, inte för hela dashboarden. | inte gjord | Finns inte: översiktens kort har inga filter alls. (Filter för hela dashboarden saknas i förlagan också.) | ej planerad |
| DB-007 | Mätare (gauge) finns inte som widgettyp. | inte gjord | Finns inte i Snajp, och inte i förlagan heller; raden beskriver en lucka hos Twenty. | ej planerad |
| DB-008 | Widgetarna uppdateras när datan ändras och kan uppdateras för hand. | delvis | Synkkörningarna på översikten följs var tredje sekund (`components/crm/app/synklage.tsx`, `SYNKPULS`). Övriga tal hämtas bara när sidan laddas, och en uppdateringsknapp finns bara vid fel ("Försök igen" i `OversiktVy.tsx`). | ej planerad |
| DB-009 | Skapa, döpa, flytta, ta bort och duplicera flikar på en dashboard. | inte gjord | Finns inte: översikten har inga flikar. | ej planerad |
| DB-010 | Placera widgetar och ändra deras storlek i rutnätet genom att dra. | inte gjord | Finns inte: korten ligger på fasta platser i `OversiktVy.tsx`. | ej planerad |
| DB-011 | En flik har layoutläge rutnät, vertikal lista eller canvas. | inte gjord | Finns inte: inga flikar eller layoutlägen. | ej planerad |
| DB-012 | Sidlayouter finns i fem typer (postlista, postsida, dashboard, fristående sida, formulär). | inte gjord | Finns inte: Snajp CRM har ingen sidlayoutmotor; varje vy är en egen komponent i `components/crm/app/`. | ej planerad |
| DB-013 | Duplicera en widget. | inte gjord | Finns inte: inga widgetar att duplicera. | ej planerad |
| DB-014 | Diagrammets inställningspanel med avsnitten Data, X-axel, Y-axel och Stil. | inte gjord | Finns inte: diagrammen på översikten har inga inställningar. | ej planerad |
| DB-015 | Välja vilket objekt ett diagram räknar på. | inte gjord | Finns inte: ringen räknar alltid bolag per relation och staplarna alltid bolag per ort. | ej planerad |
| DB-016 | Filtrera vilka poster ett diagram räknar, med filtergrupper, OCH/ELLER och relativa datum. | inte gjord | Finns inte: inga diagramfilter, och CRM:et har ingen filterbyggare. | ej planerad |
| DB-017 | Välja mått som fält plus aggregatoperation (antal, summa, medel, min, max, procent med flera). | delvis | Fasta mått finns: antal per relation (`lagring.py:rakna_poster`) och antal och summa av belopp per affärssteg (`crm_v1_objekt.py:tavla`, prövat i `test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa` i `snajp-support/tests/crm/test_objekt.py`). Inget val av fält eller operation. | ej planerad |
| DB-018 | Visa andelen poster med ett visst värde (Ratio), till exempel vunna av alla. | delvis | Kortet Kunder visar andelen kunder av alla bolag ("63 % av bolagen", `OversiktVy.tsx`, syns i `oversikt-1440.png`). Det är fast; andel för valfritt fält och värde saknas. | ej planerad |
| DB-019 | Välja datumupplösning (dag, vecka, månad, kvartal, år och cykliska) för ett datumfält. | inte gjord | Finns inte: inga datumgrupperingar. | ej planerad |
| DB-020 | Sortera diagrammets kategorier på position, alfabetiskt, efter värde eller manuellt. | delvis | Fasta ordningar: orterna efter antal, högst först, och ringen i relationsordning (`OversiktVy.tsx`, `Orter`, `RING`). Användaren kan inte välja. | ej planerad |
| DB-021 | Dölja kategorier utan poster. | delvis | Ringen visar bara relationer som har bolag (`Ring`, filtret `antal > 0`). Det är fast, inget val. | ej planerad |
| DB-022 | Lägga till en andra gruppering som ger flera serier med förklaring. | inte gjord | Finns inte: varje diagram har en enda serie. | ej planerad |
| DB-023 | Visa kumulativa värden. | inte gjord | Finns inte. | ej planerad |
| DB-024 | Låsa Y-axelns min och max. | inte gjord | Finns inte: inga axlar att låsa. | ej planerad |
| DB-025 | Välja färgschema för ett diagram; grupperas på ett valfält används alternativens färger. | delvis | Ringen färgas efter relationens egna färger ur paletten (`RING` i `OversiktVy.tsx`), som Twenty gör med valfältets färger. Användaren kan inte välja färg. | ej planerad |
| DB-026 | Välja vilka axelnamn som visas. | inte gjord | Finns inte: inga axlar eller axelnamn. | ej planerad |
| DB-027 | Välja staplat eller grupperat för stapel och linje. | inte gjord | Finns inte. | ej planerad |
| DB-028 | Visa värden på diagrammets staplar, punkter eller sektorer. | delvis | Ortstaplarna visar alltid antalet bredvid stapeln (`Orter`, syns i `oversikt-1440.png`). Ingen av/på-inställning. | ej planerad |
| DB-029 | Visa eller dölja förklaringen, med hovring och tillfällig döljning av serier. | delvis | Ringens förklaring står alltid under eller bredvid med antal och andel (`Ring`). Den går inte att stänga av och är inte interaktiv. | ej planerad |
| DB-030 | Cirkeldiagrammets egna inställningar: vad varje sektor är, dölj tom kategori, mittvärde, sortering. | delvis | Ringen finns med totalen i mitten (`Ring`), men grupperingen är fast på relation och inget går att ställa in. | ej planerad |
| DB-031 | Nyckeltalet har prefix, suffix, etikett och talformat. | delvis | `Nyckeltalskort` (`components/crm/app/kit.tsx`) har etikett och en dämpad rad under talet. Prefix, suffix och val av talformat saknas. | ej planerad |
| DB-032 | Visningsgränser per diagramtyp med varning när data inte visas. | delvis | Orterna visar de sex största och räknas ur högst 500 bolag, med en rad i kortets fot när registret är större (`Orter`, `ORTSURVAL`). Gränser per diagramtyp saknas. | ej planerad |
| DB-033 | Egna lägen för diagram utan data och för ogiltig konfiguration. | delvis | Tomlägen finns ("Inga bolag än" i ringen, "Inget bolag har en ort ifylld än", "Ingen synk har körts än"). Läget för ogiltig konfiguration saknas, eftersom inget går att konfigurera. | ej planerad |
| DB-034 | Ett diagram kan ha en beskrivning. | inte gjord | Finns inte. | ej planerad |
| DB-035 | Dela upp flervärdesfält så att varje värde räknas i sin egen grupp. | inte gjord | Finns inte. | ej planerad |
| DB-036 | Iframe-widget som bäddar in en extern webbsida, med styrd mikrofon- och kameraåtkomst. | inte gjord | Finns inte. | ej planerad |
| DB-037 | Tabellwidget som visar filtrerade poster ur en vy, skrivskyddad eller redigerbar. | delvis | Översikten har två fasta listor: senast ändrade bolag (fem, öppnar panelen) och senaste synkarna (`OversiktVy.tsx`). Val av vy, filter, gräns och redigering saknas. | ej planerad |
| DB-038 | Rik text-widget för fritext med formatering, bilder och filer. | inte gjord | Finns inte. | ej planerad |
| DB-039 | Dashboarden lagras som en vanlig post som går att söka, lista och få tidslinje för. | inte gjord | Finns inte: inget dashboardobjekt i `snajp-support/app/crm/` eller migrationerna. | ej planerad |
| DB-040 | En ny dashboard får automatiskt en sidlayout med en första flik. | inte gjord | Finns inte. | ej planerad |
| DB-041 | När en dashboard raderas permanent raderas dess layout också. | inte gjord | Finns inte. | ej planerad |
| DB-042 | Dashboards kan inte slås ihop. | inte gjord | Finns inte: inga dashboardposter och ingen sammanslagning. | ej planerad |
| DB-043 | Duplicera en dashboard via API (GraphQL och REST). | inte gjord | Finns inte. | ej planerad |
| DB-044 | Dupliceringen kopierar hela layouten och ger kopian titeln plus " (Copy)". | inte gjord | Finns inte. | ej planerad |
| DB-045 | Duplicering ger tydliga felkoder (hittas inte, saknar layout, misslyckades, behörighet). | inte gjord | Finns inte. | ej planerad |
| DB-046 | Dashboardens "senast ändrad" uppdateras när layouten ändras. | inte gjord | Finns inte. | ej planerad |
| DB-047 | AI-agenten skapar en komplett dashboard med widgetar i ett steg. | inte gjord | Finns inte: CRM:et har ingen AI-agent. | ej planerad |
| DB-048 | AI-agenten får vägledning om widgetstorlekar och tabellwidgetarnas vyer. | inte gjord | Finns inte. | ej planerad |
| DB-049 | AI-agenten kan lista och hämta dashboards. | inte gjord | Finns inte. | ej planerad |
| DB-050 | Diagramfilter i AI-verktyget följer ett fast värdeformat för relativa datum, val och valuta. | inte gjord | Finns inte. | ej planerad |
| DB-051 | Servern levererar färdiga diagramdata för stapel, linje och cirkel utifrån en konfiguration. | delvis | Servern ger fasta tal: `/api/crm/oversikt` (`snajp-support/app/api/crm.py:oversikt`, bolag per relation, personer, körningar) och `/v1/deals/board` (antal och summa per steg). Inga diagramfrågor med konfiguration. | ej planerad |
| DB-052 | Stapeldiagrammets svar med tabelldata, serier, axeletiketter, visningsflaggor och uppslagstabell. | inte gjord | Finns inte: orternas staplar räknas i webbläsaren ur bolagslistan (`Orter`). | ej planerad |
| DB-053 | Linjediagrammets svar med serier av punkter. | inte gjord | Finns inte. | ej planerad |
| DB-054 | Cirkeldiagrammets svar med sektorer (nyckel och värde). | delvis | `/api/crm/oversikt` ger antal per relation som nyckel och värde, prövat i `test_appens_nyckelhantering_och_oversikt` (`snajp-support/tests/crm/test_api.py`). Visningsflaggor, gränsflagga och uppslagstabell saknas. | ej planerad |
| DB-055 | Standardvärden för förklaring, datavärden, mittvärde och stapelriktning. | inte gjord | Finns inte: inga visningsflaggor. | ej planerad |
| DB-056 | Tidszon och veckostart styr datumgrupperingen, med UTC och måndag som standard. | inte gjord | Finns inte. | ej planerad |
| DB-057 | Standarddatumupplösning dag och standardsortering fältvärde stigande. | inte gjord | Finns inte. | ej planerad |
| DB-058 | Sju sorteringsval för diagram (fält, position, värde, manuell). | inte gjord | Finns inte. | ej planerad |
| DB-059 | Sortering på fältvärde jämför efter fälttyp (datum, valuta, tal, text). | inte gjord | Finns inte. | ej planerad |
| DB-060 | Positionssortering följer valfältets alternativordning, med tomt sist. | inte gjord | Finns inte. | ej planerad |
| DB-061 | Manuell sortering följer användarens lista. | inte gjord | Finns inte. | ej planerad |
| DB-062 | Värdesortering i diagram med serier använder summan över serierna. | inte gjord | Finns inte. | ej planerad |
| DB-063 | Tomma datumperioder fylls i med noll. | inte gjord | Finns inte: inga tidsserier (`docs/BESLUT.md` 2026-11-26: API:t har ingen historik att rita). | ej planerad |
| DB-064 | Valfältets alternativ utan poster visas med noll. | inte gjord | Finns inte: ringen gör tvärtom och döljer relationer utan bolag. | ej planerad |
| DB-065 | "Dölj tomma" tar bort grupper utan värde eller med måttet noll. | delvis | Ringen tar bort relationer med noll bolag (`Ring`). Fast regel, gäller bara ringen. | ej planerad |
| DB-066 | Aggregatvärden normaliseras före visning (saknat blir 0, procent gånger 100, valuta ur mikroenheter). | inte gjord | Finns inte: tavlan summerar belopp som de är lagrade, utan normalisering för visning. | ej planerad |
| DB-067 | Grupperingsvärden visas med läsbara etiketter (val, ja/nej, datum per upplösning, tal, relationens namn). | delvis | Relationernas nycklar visas med svenska och engelska namn (`RING` i `OversiktVy.tsx`). Etiketter för datum, tal, ja/nej och relationer saknas. | ej planerad |
| DB-068 | Gruppering på en relation visar den relaterade postens namn, med löpnummer vid lika namn. | inte gjord | Finns inte. | ej planerad |
| DB-069 | Gruppering på ett fält i en relaterad post, även ett datum. | inte gjord | Finns inte. | ej planerad |
| DB-070 | Flervärdesfält delas upp som standard, men bara i en av två grupperingar. | inte gjord | Finns inte. | ej planerad |
| DB-071 | Diagramfiltret översätts till samma filter som vyerna, med tidszon och "mig". | inte gjord | Finns inte: inga diagramfilter och inga sparade vyer. | ej planerad |
| DB-072 | Stapeldiagrammets gränser (100 kategorier, 50 serier) upprätthålls på servern. | inte gjord | Finns inte. | ej planerad |
| DB-073 | Linjediagrammets gränser (100 punkter, 50 serier) upprätthålls på servern. | inte gjord | Finns inte. | ej planerad |
| DB-074 | Cirkeldiagrammets gräns är 100 sektorer. | inte gjord | Finns inte. | ej planerad |
| DB-075 | Kumulativt läge räknar löpande summa efter sortering och avkortning. | inte gjord | Finns inte. | ej planerad |
| DB-076 | Axeletiketterna sätts automatiskt efter fält och operation. | inte gjord | Finns inte: inga axlar. | ej planerad |
| DB-077 | Diagramfrågor ger klassade fel (widget saknas, ogiltig konfiguration, behörighet med flera). | inte gjord | Finns inte. | ej planerad |
| DB-078 | Lista, läsa, skapa, ändra och radera widgetar via API. | inte gjord | Finns inte. | ej planerad |
| DB-079 | En widget har titel, typ, flik, objekt, position, konfiguration och villkorlig tillgänglighet. | inte gjord | Finns inte. | ej planerad |
| DB-080 | Rutnätet är 12 kolumner brett och 100 rader högt, med kontroll av positionen. | inte gjord | Finns inte. | ej planerad |
| DB-081 | Vertikal lista placerar widgetar efter index med höjdbeteende. | inte gjord | Finns inte. | ej planerad |
| DB-082 | Diagramkonfigurationen valideras per typ (obligatoriska fält per diagram). | inte gjord | Finns inte. | ej planerad |
| DB-083 | Fälten i ett diagram måste finnas och höra till widgetens objekt. | inte gjord | Finns inte. | ej planerad |
| DB-084 | Ett filter med valvärden som inte finns underkänns med lista över tillåtna värden. | inte gjord | Finns inte. | ej planerad |
| DB-085 | Diagramfiltrets operand och värde valideras mot fälttypen. | inte gjord | Finns inte. | ej planerad |
| DB-086 | Konfigurationsfälten typkontrolleras (tidszon, veckostart, min och max, talformat med flera). | inte gjord | Finns inte. | ej planerad |
| DB-087 | Iframe-widgetens adress måste vara en giltig URL. | inte gjord | Finns inte. | ej planerad |
| DB-088 | Tabellwidgetens radgräns är ett heltal minst 1. | inte gjord | Finns inte. | ej planerad |
| DB-089 | Rik text-widgeten kräver en kropp och normaliserar formatet vid sparning. | inte gjord | Finns inte. | ej planerad |
| DB-090 | Widgettypen VIEW kan inte skapas, och okända typer nekas. | inte gjord | Finns inte: inga widgettyper. | ej planerad |
| DB-091 | Widgetfel har egna koder, och flera valideringsfel samlas i ett svar. | inte gjord | Finns inte. | ej planerad |
| DB-092 | En widget kan visas villkorligt utifrån ett uttryck. | inte gjord | Finns inte. | ej planerad |
| DB-093 | Lista, läsa, skapa, ändra, radera och spara hela sidlayouter i ett svep, och återställa till standard. | inte gjord | Finns inte. | ej planerad |
| DB-094 | Spara i ett svep räknar ut skillnaden och skapar, ändrar och raderar flikar och widgetar som en enhet. | inte gjord | Finns inte. | ej planerad |
| DB-095 | Sidlayouten har namn, typ, objekt, flikar och visningsinställningar. | inte gjord | Finns inte. | ej planerad |
| DB-096 | Att radera en dashboards sidlayout raderar också dashboardposten. | inte gjord | Finns inte. | ej planerad |
| DB-097 | Duplicering av sidlayout kopierar flikar och widgetar med samma titlar. | inte gjord | Finns inte. | ej planerad |
| DB-098 | Lista, läsa, skapa, ändra och radera flikar via API. | inte gjord | Finns inte. | ej planerad |
| DB-099 | En flik har titel, position, ikon och layoutläge. | inte gjord | Finns inte. | ej planerad |
| DB-100 | Ett generellt grupperings-API grupperar poster i ett objekt och räknar aggregat per grupp. | delvis | Två fasta grupperingar finns i backend: bolag per relation (`lagring.py:rakna_poster`, SQL `group by`) och affärer per steg med antal och summa (`objekt.tavla` via `GET /v1/deals/board`, prövat i `test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa`). Inget generellt API med valfritt fält, filter och aggregat. | ej planerad |
| DB-101 | Antal grupper är som standard 50, med högst 10 poster per grupp. | inte gjord | Finns inte. | ej planerad |
| DB-102 | Datumgruppering bildar perioder i vald tidszon och veckostart. | inte gjord | Finns inte. | ej planerad |
| DB-103 | Flervärdesfält kan grupperas per värde. | inte gjord | Finns inte. | ej planerad |
| DB-104 | Regler för vilka fält och relationer som kan grupperas. | inte gjord | Finns inte. | ej planerad |
| DB-105 | Grupperingsargumenten valideras med tydliga fel. | inte gjord | Finns inte. | ej planerad |
| DB-106 | En sparad vys filter och sökfras kan styra grupperingen. | inte gjord | Finns inte: inga sparade vyer. | ej planerad |
| DB-107 | Appar kan deklarera dashboards, flikar och widgetar som kod. | inte gjord | Finns inte: CRM:et har inga appar från tredje part. | ej planerad |
| DB-108 | Tabellwidgetens redigerbarhet har olika standard per layouttyp. | inte gjord | Finns inte. | ej planerad |
| DB-109 | En appwidget kan ha kommandoknappar i widgetens rubrik. | inte gjord | Finns inte. | ej planerad |
| DB-110 | Standardinstallationen har dashboardobjektet, listan "Alla dashboards" och en menypost. | delvis | Menyposten Översikt finns i sidofältet och i kommandopaletten (`CrmRam.tsx`, `Kommandopalett.tsx`). Dashboardobjektet och listan över dashboards saknas. | ej planerad |
| DB-111 | Nya arbetsytor får en färdig exempeldashboard med affärsdiagram, nyckeltal, rik text och iframe. | delvis | Varje kund får samma fasta översikt med nyckeltal, ring, staplar och listor (`OversiktVy.tsx`, bild `oversikt-1440.png`). Affärsdiagrammen saknas; `/v1/deals/board` räknar summa per steg men ingen yta visar den. | ej planerad |
| DB-112 | Kommandomenyn har Redigera, Spara, Avbryt och Duplicera dashboard. | inte gjord | Finns inte: kommandopaletten har bara navigering och sökning. | ej planerad |
| DB-113 | Redigeringsläget startas och avslutas uttryckligen, och Spara skickar hela layouten i ett anrop. | inte gjord | Finns inte: inget redigeringsläge. | ej planerad |
| DB-114 | Duplicering i gränssnittet visar kvittens och öppnar kopian. | inte gjord | Finns inte. | ej planerad |
| DB-115 | Antalet dashboards är obegränsat i alla planer. | avstår | Gäller Twentys planer och prissättning. Ersätts av Snajps egen modell, CRM:et som tillägg (`snajp-support/app/crm/tillgang.py`, migration 161). | |
| DB-116 | Rutnätet har fasta mått och går till en kolumn på mobil. | delvis | Översiktens kort ligger i Astryx `Grid` som går till en kolumn på mobil (`OversiktVy.tsx`, bilder `oversikt-1440.png` och `oversikt-390.png`). Ett rutnät med rader, radhöjd och tomma buffertrader saknas. | ej planerad |
| DB-117 | Standard- och minsta storlek per widgettyp. | inte gjord | Finns inte. | ej planerad |
| DB-118 | Rita upp en yta i rutnätet för att skapa en widget just där. | inte gjord | Finns inte. | ej planerad |
| DB-119 | Flytta widgetar mellan flikar genom att dra. | inte gjord | Finns inte. | ej planerad |
| DB-120 | Dra om flikar, fästa första fliken och visa överskottet i en mer-meny. | inte gjord | Finns inte. | ej planerad |
| DB-121 | Nya diagram får standardinställningar och numrerade titlar. | inte gjord | Finns inte. | ej planerad |
| DB-122 | Diagram över affärer förväljer steg som gruppering och belopp som mått. | inte gjord | Finns inte: affärer finns i API:t (`crm_v1_objekt.py`) men inga diagram över dem. | ej planerad |
| DB-123 | Widgetväljaren med grupperna Diagram, Vyer och Övrigt. | inte gjord | Finns inte. | ej planerad |
| DB-124 | Byta diagramtyp i efterhand utan att tappa inställningar. | inte gjord | Finns inte. | ej planerad |
| DB-125 | Inställningslistan för varje diagramtyp (stapel, linje, cirkel, nyckeltal). | inte gjord | Finns inte. | ej planerad |
| DB-126 | Inställningar döljs tills deras förutsättning finns. | inte gjord | Finns inte. | ej planerad |
| DB-127 | Sorteringsvalen beror på fälttyp. | inte gjord | Finns inte. | ej planerad |
| DB-128 | Min och max för Y-axeln måste vara förenliga. | inte gjord | Finns inte. | ej planerad |
| DB-129 | Datummått byts till antal när diagramtypen inte stöder tidigast och senast. | inte gjord | Finns inte. | ej planerad |
| DB-130 | Gruppera på ett underfält i en relation. | inte gjord | Finns inte. | ej planerad |
| DB-131 | Varning när diagrammet inte visar all data. | delvis | Kortet Största orterna säger i foten när bara de första 500 bolagen räknats (`Orter`, `ORTSURVAL` i `OversiktVy.tsx`). Någon varning per diagramtyp och gräns finns inte. | ej planerad |
| DB-132 | Nyckeltalets mått räknas med en aggregatfråga med widgetens filter, och "-" utan data. | delvis | Nyckeltalen är fasta antal ur `/api/crm/oversikt` och visar skelett medan de hämtas (`Nyckeltalskort` i `kit.tsx`). Valbart mått, filter och tecknet för saknad data saknas. | ej planerad |
| DB-133 | Andel räknas som täljare delat med nämnare och visas med en decimal. | delvis | Kortet Kunder räknar kunder delat med alla bolag och visar hela procent ("63 % av bolagen", `OversiktVy.tsx`, `oversikt-1440.png`). Andel för valfritt fält och decimalvisning saknas. | ej planerad |
| DB-134 | Nyckeltalet kan visa en trendprocent med pil upp eller ned. | inte gjord | Finns inte: ingen historik att räkna en trend ur. | ej planerad |
| DB-135 | Vilka mått som erbjuds beror på fälttyp. | inte gjord | Finns inte: inga valbara mått. | ej planerad |
| DB-136 | Talformat kort (1,3 mn) eller fullt, med decimaler efter fältet. | delvis | Talen visas i fullt format med svensk tusentalsavgränsning (`toLocaleString("sv-SE")` i `OversiktVy.tsx`). Kort format och val saknas. | ej planerad |
| DB-137 | Färgläget väljs automatiskt: vald färg, valfältets färger eller en palett. | delvis | Ringen färgas alltid efter relationens fasta färg och orterna i Bolags blå (`RING`, `Orter`). Enfärgsläge och automatisk palett saknas. | ej planerad |
| DB-138 | Klick på stapel, punkt eller sektor öppnar postlistan filtrerad på gruppen. | delvis | Nyckeltalskorten länkar vidare (Bolag och Kunder till Bolag, Personer till Personer, Att rätta till körningen i Synk, `OversiktVy.tsx`). Sektorer och staplar går inte att klicka, och länkarna bär inget filter. | ej planerad |
| DB-139 | Förklaringen är interaktiv: hovring markerar och klick döljer en serie. | inte gjord | Finns inte: ringens förklaring är statisk. | ej planerad |
| DB-140 | Staplat eller grupperat avgörs när serier finns, med totalsumma och nollinje. | inte gjord | Finns inte. | ej planerad |
| DB-141 | Linjediagram med fylld yta, stapling, hårkors och verktygstips. | inte gjord | Finns inte: inga linjediagram. | ej planerad |
| DB-142 | Cirkeldiagrammet ritas som ring med mittvärde, och verktygstipset visar värde och andel. | verifierad | `Ring` i `components/crm/app/OversiktVy.tsx` (recharts `PieChart`, totalen i mitten, andel per relation i förklaring och verktygstips). Bilderna `docs/crm/bilder/app/oversikt-1440.png` och `oversikt-390.png` visar ringen med mittvärde och andelar. | |
| DB-143 | Axlar och etiketter anpassar sig till utrymmet (ellips, rotation, skalsteg). | delvis | Ortnamnen kortas med ellips i en fast kolumn (`Orter`, `truncate`). Axlar, rotation och skalsteg saknas. | ej planerad |
| DB-144 | Widgeten har lägen för laddning, tom data, ogiltig konfiguration, fel och saknad behörighet. | delvis | Skelett vid laddning, tomlägen per kort och en felruta med "Försök igen" (`Felruta` i `Sida.tsx`, `OversiktVy.tsx`). Lägen för ogiltig konfiguration och saknad behörighet per widget saknas. | ej planerad |
| DB-145 | Widgetens hantering i redigeringsläge: inställningar, duplicera, ta bort, dra och ändra storlek. | inte gjord | Finns inte: inget redigeringsläge. | ej planerad |
| DB-146 | Tabellwidgetens inställningar (källa, layout, fält, filter, gruppering, gräns, redigering). | inte gjord | Finns inte. | ej planerad |
| DB-147 | Iframe-widgeten visar sidan i en sandlåda med säkrad adress. | inte gjord | Finns inte. | ej planerad |
| DB-148 | Rik text redigeras direkt i widgeten med snedstreckskommandon. | inte gjord | Finns inte. | ej planerad |
| DB-149 | Analysmodulen i Twentys front är produktstatistik, inte rapportering. | avstår | Skickar användningsstatistik till Twenty och hör inte till dashboards; serverns användningsanalys är en Enterprise-fil i förlagan. | |
| DB-150 | Gruppera och aggregera poster över REST med parametrar för gruppering, aggregat, filter, sortering och gräns. | inte gjord | Finns inte: REST-API:t (`crm_v1.py`, `crm_v1_objekt.py`) har inget `groupBy`; bara den fasta tavlan `/v1/deals/board`. | ej planerad |
| DB-151 | GraphQL-vägens grupperingsgräns och frågekostnad. | inte gjord | Finns inte: CRM:et har inget GraphQL-API. | ej planerad |
| DB-152 | Bläddra bland posterna i varje grupp. | inte gjord | Finns inte. | ej planerad |
| DB-153 | Vyns sökfras i grupperingen tar bara hänsyn till fält användaren får läsa. | inte gjord | Finns inte. | ej planerad |
| DB-154 | Datumgruppering kräver tidszon för perioder men inte för cykliska grupper. | inte gjord | Finns inte. | ej planerad |
| DB-155 | Sortering sker delvis i databasen och delvis efteråt, med regler för relationer. | inte gjord | Finns inte. | ej planerad |
| DB-156 | Resultat med två grupperingar rensas innan de visas. | inte gjord | Finns inte. | ej planerad |
| DB-157 | Linjediagrammets serier får nycklar som är unika per diagram. | inte gjord | Finns inte. | ej planerad |
| DB-158 | En widget som rör data användaren inte får läsa visas inte, och spärren namnger fälten. | inte gjord | Finns inte: CRM:et har ingen behörighet per objekt eller fält; hela ytan grindas av tillägget och nyckelns omfång (`nycklar.py`). | ej planerad |
| DB-159 | En ny tabellwidget får en egen standardvy med de sex viktigaste fälten. | inte gjord | Finns inte. | ej planerad |
| DB-160 | Flikens inställningspanel: fäst, flytta, duplicera, återställ och ta bort. | inte gjord | Finns inte. | ej planerad |
| DB-161 | Återställning till standard gäller bara levererade layouter. | inte gjord | Finns inte. | ej planerad |
| DB-162 | AI-agenten kan lägga till och ändra flikar och widgetar i befintliga dashboards. | inte gjord | Finns inte: ingen AI-agent i CRM:et. | ej planerad |
| DB-163 | Sidlayout- och flikfel har egna koder. | inte gjord | Finns inte. | ej planerad |
| DB-164 | Färgskalan i enfärgsläge och för grupper, med nedtoning vid hovring. | inte gjord | Finns inte. | ej planerad |
| DB-165 | Flytta widgetar med tangentbordet. | inte gjord | Finns inte: inga flyttbara widgetar. | ej planerad |
| DB-166 | En exempeldashboard med påhittade företag, personer och affärer skapas när en ny arbetsyta aktiveras. | avstår | Strider mot `docs/BESLUT.md` 2026-11-26 (Snajp CRM får en egen form): "ett påhittat diagram är värre än inget", och mot `docs/crm/DESIGN-CRM.md`: inga påhittade tal i appen. Påhittad data finns bara i förhandsvisningen (`app/forhandsvisning/crm/`). | |
| DB-167 | Redigering i tabellwidgeten gäller bara tabell och kanban, inte lista och kalender. | inte gjord | Finns inte. | ej planerad |
| DB-168 | Staplarna ritas med fasta mått och luft, och värdeaxeln får 2 till 6 skalsteg. | inte gjord | Finns inte: orternas staplar är fasta rundade band utan värdeaxel (`Orter`). | ej planerad |
| DB-169 | Värdeaxelns automatiska skala utgår från noll med tio procents luft. | inte gjord | Finns inte: ingen värdeaxel. | ej planerad |
| DB-170 | Staplade staplar visar totalsumman per kategori. | inte gjord | Finns inte. | ej planerad |
| DB-171 | Verktygstipset på en stapel visar alla serier i kategorin. | delvis | Varje ortstapel har ett verktygstips med ort, antal och andel av bolagen med ort, nåbart med tangentbordet (`Orter`, Astryx `Tooltip`). Bara en serie, ingen lista över serier. | ej planerad |
| DB-172 | Linjediagram med serier är staplade som standard. | inte gjord | Finns inte. | ej planerad |
| DB-173 | Verktygstipset i linjediagrammet sorteras efter läge, med hårkors. | inte gjord | Finns inte. | ej planerad |
| DB-174 | Datavärden i linjediagrammet glesas ut så att de inte krockar. | inte gjord | Finns inte. | ej planerad |
| DB-175 | Linjediagrammets yta tonar ut nedåt. | inte gjord | Finns inte. | ej planerad |
| DB-176 | Cirkeldiagrammets verktygstips visar "värde (andel %)", och hovrad sektor mörknar. | delvis | Ringens verktygstips visar antal bolag och andel i hela procent (`Ring`, `DiagramTips` i `OversiktVy.tsx`). En decimal i andelen och mörkning av hovrad sektor saknas. | ej planerad |
| DB-177 | Axeletiketter kortas och roteras efter utrymme inom fasta marginaler. | inte gjord | Finns inte: inga axlar. | ej planerad |
| DB-178 | Diagramvärden formateras som tal utan valutasymbol, med prefix och suffix som väg till symbol. | inte gjord | Finns inte: översikten visar inga belopp. | ej planerad |
| DB-179 | En appwidget visar en installerad apps komponent. | inte gjord | Finns inte: inga appar. | ej planerad |
| DB-180 | En app väljer om dess komponent erbjuds i dashboardens widgetväljare. | inte gjord | Finns inte. | ej planerad |
| DB-181 | En tom dashboard visar ett kort som uppmanar till första widgeten. | inte gjord | Finns inte: översikten är aldrig tom på widgetar, bara korten har tomlägen. | ej planerad |
| DB-182 | Kanbanlayouten i tabellwidgeten kräver ett valfält, kalendern ett datumfält. | inte gjord | Finns inte. | ej planerad |
| DB-183 | Tabellwidgetens fält ordnas efter relevans med namnfältet först. | inte gjord | Finns inte. | ej planerad |
| DB-184 | En duplicerad widget hamnar under de befintliga med " (Copy)" i titeln. | inte gjord | Finns inte. | ej planerad |
| DB-185 | En duplicerad flik läggs direkt efter originalet. | inte gjord | Finns inte. | ej planerad |
| DB-186 | AI-verktygen för flikar och widgetar har fasta parametrar. | inte gjord | Finns inte: ingen AI-agent i CRM:et. | ej planerad |
| DB-187 | AI-placering av en appkomponent kontrolleras mot flik och layout. | inte gjord | Finns inte. | ej planerad |
| DB-188 | Appwidgetens konfiguration och rubrikknappar valideras. | inte gjord | Finns inte. | ej planerad |
| DB-189 | Posterna i en grupp hämtas för exakt de grupper som returnerats. | inte gjord | Finns inte. | ej planerad |
| DB-190 | Utvecklingsmiljöns exempeldata har tre dashboards till. | avstår | Gäller bara Twentys egen utvecklingsmiljö, inte kundernas arbetsytor. | |
| DB-191 | Twentys standardapp får skapa VIEW-widgetar, andra inte. | avstår | Gäller bara Twentys interna standardapp och dess appsystem. | |
| DB-192 | Sidlayouten bestämmer om första fliken är fäst. | inte gjord | Finns inte: inga flikar. | ej planerad |
