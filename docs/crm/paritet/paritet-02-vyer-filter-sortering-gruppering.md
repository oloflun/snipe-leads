# Paritet 02: Vyer, filter, sortering och gruppering

Området gäller hur en användare tittar på ett objekts poster: sparade vyer, vytyper (tabell, tavla, kalender, lista), filter, sortering, gruppering, summeringar och själva postlistan med kolumner, markering och redigering. Varje rad i underlaget `docs/crm/underlag/twenty-02-vyer-filter-sortering-gruppering.md` (VY-001 till VY-208) har här fått ett läge mot det som finns i Snajp CRM i arbetskatalogen 2026-11-26.

Antal per läge: verifierad 3, byggd 2, delvis 54, inte gjord 147, avstår 2 (totalt 208).

Läget i korthet: Snajp CRM har fasta listor för Bolag och Personer (vyrad med fasta vyer per relation, sökfält, tre fasta sorteringar, papperskorg som vy, markering med åtgärdsrad, panel för posten) och ett API med likhetsfilter, fritext, sidindelning med markör och en tavla för affärer som bara finns i API:t. Begreppet vy som något användaren sparar och formar finns inte alls.

## De största luckorna

1. Sparade vyer saknas helt: användaren kan inte skapa, byta namn på, radera, dela eller göra en vy privat, och ändringar i filter och sortering försvinner vid omladdning.
2. Det finns ingen filterbyggare: man kan inte välja fält och villkor (innehåller, är, är inte, tom, större än, före, efter, idag, relativt datum) och ser inga filterchips. Det enda som finns är fritextsökning, relationsvyerna på Bolag och bolagsväljaren på Personer.
3. Inget avancerat filter med OCH- och ELLER-grupper, och inget filter på en relaterad posts fält.
4. Sortering går bara på tre fasta ordningar (senast ändrad, ändringsordning, namn A till Ö). Ingen sortering på valfritt fält, ingen omvänd namnordning och inga flera sorteringsnivåer.
5. Kolumnerna är fasta i koden: de går inte att dölja, visa, flytta, göra bredare eller döpa om, och det finns ingen "+"-knapp för att lägga till en kolumn.
6. Tavlan för affärer finns bara i API:t: inga kolumner per steg i gränssnittet, inget att dra kort mellan, ingen summering i kolumnhuvudet, inga kort.
7. Ingen redigering direkt i cellen och ingen tangentbordsnavigering mellan rader och celler; allt ändras via dialogen.
8. Ingen gruppering av tabellen (sektioner eller flikar per värde) utöver de fasta relationsvyerna på Bolag, och inga dolda eller omordnade grupper.
9. Inga summeringar per kolumn i tabellens sidfot (antal, summa, medel, min, max, procent tomma); bara en räknerad med antal och andel kunder.
10. Ingen kalendervy och ingen export av vyns poster till CSV.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| VY-001 | Varje objekt har minst en vy som listar dess poster, och ett nytt objekt får en första tabellvy "Alla". | delvis | Bolag och Personer har en fast lista med vyn "Alla" (`components/crm/app/BolagVy.tsx` `ALLTID`, `PersonerVy.tsx`). Ingen lagrad vy, och affärer, uppgifter, anteckningar, aktiviteter och bilagor har ingen lista i gränssnittet. | 4 |
| VY-002 | Objektets huvudvy är standardvyn, alltid delad och går inte att radera. | delvis | "Alla" är alltid första och förvalda vyn i vyraden (`BolagVy.tsx` `useState<Filter>("alla")`). Den är fast i koden, inte en lagrad vy med nyckel. | 4 |
| VY-003 | Användaren skapar en ny vy med namn, ikon och layout från vyväljaren. | inte gjord | Inga sparade vyer i CRM:et. Sparade vyer är planerade med Leads (LR-035 i `MIGRERING-FUNKTIONSLISTA.md`). | 4 |
| VY-004 | Användaren sparar den aktuella vyn med sina ändringar som en ny vy. | inte gjord | Inga sparade vyer. | 4 |
| VY-005 | Användaren byter namn och ikon på en vy. | inte gjord | Inga sparade vyer. | 4 |
| VY-006 | Användaren ordnar om vyerna genom att dra dem. | inte gjord | Vyraden har en fast ordning i koden (`BolagVy.tsx` `ALLTID`, `IBLAND`). | 4 |
| VY-007 | Användaren lägger en vy bland favoriterna i navigeringen. | inte gjord | Favoriter finns inte i CRM:et. | senare |
| VY-008 | Användaren raderar en vy, och vyns delar raderas med den; objektets sista vy kan inte raderas. | inte gjord | Inga sparade vyer. | 4 |
| VY-009 | En vy kan vara privat (bara skaparen ser den) eller delad med alla. | inte gjord | Inga sparade vyer. | 4 |
| VY-010 | Behörighet styr vem som får skapa och ändra delade vyer; egen privat vy ändras fritt. | inte gjord | Inga vyer och inga roller per användare i CRM:et; API-nycklarnas omfång (`snajp-support/app/crm/nycklar.py`) gäller poster, inte vyer. | 4 |
| VY-011 | En borttagen användares privata vyer flyttas till en efterträdare. | inte gjord | Inga privata vyer. | 4 |
| VY-012 | Vytyperna tabell, tavla, kalender och lista (plus widgetvarianter). | delvis | Tabell på bred skärm och lista på mobil (`BolagVy.tsx`, `PersonerVy.tsx`), tavla för affärer bara i API:t (`GET /v1/deals/board`, `snajp-support/app/api/crm_v1_objekt.py` `tavla`). Kalender och val av vytyp saknas. | 3 |
| VY-013 | En tavla måste ha ett grupperingsfält (valfält eller många-till-en-relation). | delvis | Affärernas tavla grupperar alltid på steget (`snajp-support/app/crm/objekt.py` `tavla`, steg i `crm_affarssteg`, migration 164). Användaren kan inte välja annat grupperingsfält. | 3 |
| VY-014 | En kalendervy kräver ett datumfält och en layout (dag, vecka, månad). | inte gjord | Ingen kalendervy. Kalender står bland Astryx förhandsutgåvor i fas 3 (`PLAN-MIGRERING.md`). | 3 |
| VY-015 | Tavlans kolumnsummering (operation och fält) sparas på vyn. | delvis | Tavlan i API:t ger alltid antal och beloppssumma per steg, även per valuta (`crm_v1_objekt.py` `tavla`; prövas i `test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa`, `snajp-support/tests/crm/test_objekt.py`). Operationen går inte att välja eller spara. | 3 |
| VY-016 | Kompakt läge där tavlans kort bara visar postens namn. | inte gjord | Tavlan finns inte i gränssnittet. | 3 |
| VY-017 | Tavlans kolumnbredd sparas per vy (150 till 400 px). | inte gjord | Tavlan finns inte i gränssnittet. | 3 |
| VY-018 | Hur många poster som laddas per grupp (8, 25, 50 eller 100). | inte gjord | Ingen gruppering i tabellen. | senare |
| VY-019 | Grupper utan poster kan döljas. | delvis | På Bolag visas vyerna Partner, Leverantör och Övrigt bara när de har bolag (`BolagVy.tsx` `IBLAND`). Det är fast, inte ett val i en vy. | senare |
| VY-020 | Grupperna kan visas som flikar i stället för sektioner. | delvis | Bolagens relationer visas som flikar med antal i vyraden (`BolagVy.tsx` `Vyval`; bilden `docs/crm/bilder/app/bolag-1440.png`). Fast på relationen, inget val av grupperingsfält eller visning som sektioner. | senare |
| VY-021 | Vyn kan spara en fritextsökning. | inte gjord | Sökfältet finns men sparas inte (`BolagVy.tsx` `sok`); inga sparade vyer. | 4 |
| VY-022 | Förinställda filter för inkorgsvyer över AI-chattrådar. | inte gjord | CRM:et har inga AI-chattrådar eller inkorgsvyer. | ej planerad |
| VY-023 | Vyfältet för var en post öppnas (sidopanel eller helsida), föråldrat i förlagan. | avstår | Föråldrat fält som förlagan bara behåller för API-kompatibilitet. Ersätts av det Snajp redan har: posten öppnas alltid i panelen och följer adressen (`BolagVy.tsx` `?bolag=`, `PersonerVy.tsx` `?person=`). | |
| VY-024 | Vydelar som motorn skapat själv eller som ägs av en app. | inte gjord | CRM:et har inga appar från tredje part och inga lagrade vyer. | ej planerad |
| VY-025 | Vyer läses och skrivs via API:t och av AI-agenten. | inte gjord | Inga vyer i API:t (`docs/crm/API.md`) och ingen AI-agent i CRM:et. | senare |
| VY-026 | Servern översätter en vy till parametrar för att hämta dess poster. | inte gjord | Inga lagrade vyer att översätta; gränssnittet bygger frågan själv (`BolagVy.tsx` `hamta`). | senare |
| VY-027 | Vyfält bestämmer vilka fält som syns som kolumner, med synlighet, bredd och position. | inte gjord | Kolumnerna är fasta i koden (`BolagVy.tsx` och `PersonerVy.tsx` `kolumner`). | senare |
| VY-028 | Postens namnfält ligger alltid först, är alltid synligt och kan inte tas bort. | delvis | Namnkolumnen står alltid först och öppnar posten (`BolagVy.tsx` kolumnen `name`, bilden `docs/crm/bilder/app/bolag-1440.png`). Det följer av fasta kolumner, inte av en regel i en vy som går att ändra. | senare |
| VY-029 | En kolumn kan få en egen rubrik (högst 63 tecken). | inte gjord | Rubrikerna är fasta i koden. | senare |
| VY-030 | Extra kolumner som visar ett fält på en relaterad post, till exempel bolagets ort på en person. | inte gjord | Personer visar bolagets namn som chip (`PersonerVy.tsx`), men inga andra fält från bolaget. | senare |
| VY-031 | En kolumn för en en-till-många-relation kan bära eget omfång med filter, sortering och gräns. | inte gjord | Inga omfångade kolumner. | senare |
| VY-032 | En kolumn kan summera relaterade poster (antal, summa, medel, min, max). | inte gjord | Bolagspanelens flik Personer visar antalet personer (`BolagPanel.tsx`), men ingen kolumn i listan summerar relaterade poster. | senare |
| VY-033 | Fältgrupper samlar fält i namngivna sektioner, främst på postsidan. | delvis | Bolagspanelen visar fälten i fasta grupper Allmänt, Affär, Kontakt och System (`components/crm/app/BolagPanel.tsx` `MetadataList`, bilden `docs/crm/bilder/app/bolag-panel-1440.png`). Grupperna går inte att skapa, döpa om eller dölja. | senare |
| VY-034 | En fältwidget uppdateras med antingen grupper eller lösa fält, aldrig båda. | inte gjord | Inga fältwidgetar eller sidlayouter i CRM:et. | ej planerad |
| VY-035 | Ett sparat vyfilter består av fält, villkor och värde, med valfritt delfält och relaterat fält. | inte gjord | Filter lagras aldrig; de är frågeparametrar per anrop (`snajp-support/app/api/crm_v1.py` `lista_bolag`). | 4 |
| VY-036 | Villkoren: är, är inte, större eller lika, mindre eller lika, före, efter, innehåller, innehåller inte, tom, inte tom, relativt datum, i det förflutna, i framtiden, idag. | delvis | API:t har likhet (`relation`, `org_number`, `company_id`, `stage_id`, `status`, `owner`), innehåller via `q` (ILIKE), före via `due_before` och vid eller efter via `updated_since` (`snajp-support/app/crm/lagring.py` `lista_poster`). Övriga villkor saknas, och användaren kan inte välja villkor. | senare |
| VY-037 | Vilka fälttyper som går att filtrera på (text, telefon, e-post, datum, tal, valuta, namn, länkar, relation, adress, val m.fl.). | delvis | Filtrerbart i dag: relation (valfält), organisationsnummer, kopplat bolag, person, affär, steg, status, ansvarig, förfallodag, ändringstid och fritext (`crm_v1.py`, `crm_v1_objekt.py`). Tal, valuta, telefon, adress, boolean och egna fält går inte att filtrera på. | senare |
| VY-038 | Varje fälttyp har sin egen lista av villkor. | inte gjord | Det finns inga villkor att välja per fälttyp; varje parameter har ett fast villkor. | senare |
| VY-039 | Ett filter utan värde ignoreras tyst i stället för att ge fel. | byggd | `lagring.py` `lista_poster` tar bort filter vars värde är `None` och hoppar över en tom fritext (`if q:`). | |
| VY-040 | Text: innehåller (skiftlägesokänsligt), innehåller inte, är exakt, är inte. | delvis | Innehåller finns som fritext över fasta kolumner (`lagring.py` `_LISTA`, ILIKE; prövas i `test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr`, `snajp-support/tests/crm/test_api.py`), och exakt likhet på organisationsnummer. Innehåller inte och är inte saknas, och man kan inte välja vilket textfält. | senare |
| VY-041 | Tom och inte tom per fälttyp. | inte gjord | Inga tomhetsvillkor i API:t. | senare |
| VY-042 | Tal: är, är inte, större eller lika, mindre eller lika. | inte gjord | Inga talfilter (antal anställda, omsättning, belopp går inte att filtrera). | senare |
| VY-043 | Betyg (ett till fem) filtreras som en mängd betyg. | inte gjord | CRM:et har inget betygsfält. | ej planerad |
| VY-044 | Valuta: filter på belopp och på valutakod. | inte gjord | Affärens belopp och valuta går inte att filtrera. | senare |
| VY-045 | Valfält: är eller är inte något av flera valda värden, med "inget värde" som val. | delvis | Ett enda värde med "är": relation på bolag (`crm_v1.py` `lista_bolag`, vyraden i `BolagVy.tsx`), status på uppgifter och steg på affärer (prövas i `test_uppgifter_sorteras_pa_forfallodag_och_filtreras`, `snajp-support/tests/crm/test_objekt_ovriga.py`, och `test_affarer_sorteras_sidindelas_och_filtreras`, `test_objekt.py`). Flera värden, "är inte" och "inget värde" saknas. | senare |
| VY-046 | Flerval: innehåller eller innehåller inte något av de valda. | inte gjord | Inga flervalsfält att filtrera på. | senare |
| VY-047 | Relation: är eller är inte valda poster, med "jag" och "aktuell post" som specialval. | delvis | Ett enda kopplat bolag: `company_id` på personer, affärer, uppgifter, anteckningar och aktiviteter, och `deal_id` (`crm_v1.py`, `crm_v1_objekt.py`; prövas i `test_personer_knyts_till_bolag_och_uppdateras_pa_epost`, `test_api.py`). Bolagsväljaren på Personer (`PersonerVy.tsx` `bolagsvaljare`, bilden `docs/crm/bilder/app/personer-1440.png`). Flera poster, "är inte" och "jag" saknas. | senare |
| VY-048 | Filter på ett fält i en relaterad post, till exempel bolagets namn på en person. | inte gjord | Ingen filtrering genom relationer. | senare |
| VY-049 | Datum: är (samma dag), före, efter, med tidszon för datum och tid. | delvis | Före via `due_before` på uppgifter och vid eller efter via `updated_since` (`lagring.py` `lista_poster`; prövas i `test_uppgifter_sorteras_pa_forfallodag_och_filtreras`, `test_objekt_ovriga.py`, och `test_sidindelning_med_markor`, `test_api.py`). "Är samma dag" och tidszon per användare saknas, och bara två datumfält går att filtrera. | senare |
| VY-050 | Datum: idag, i det förflutna, i framtiden, utan värde. | inte gjord | Inga sådana villkor. | senare |
| VY-051 | Relativt datum: senaste, denna eller nästa period i sekunder till år, med veckostart. | inte gjord | Inga relativa datumfilter. | senare |
| VY-052 | Telefon: innehåller, där värdet rensas till siffror. | inte gjord | Fritexten söker inte i telefonnummer (`lagring.py` `_LISTA`). | senare |
| VY-053 | Adress: innehåller i gata, ort, region, postnummer eller land. | delvis | Fritexten på bolag söker i ort (`postort` i `lagring.py` `_LISTA`). Gata, postnummer och land saknas, liksom val av delfält. | senare |
| VY-054 | Fullt namn: innehåller i förnamn eller efternamn. | delvis | Fritexten på personer söker i förnamn och efternamn (och e-post, titel) (`lagring.py` `_LISTA`). Inget eget filter på namnet och inget val av delfält. | senare |
| VY-055 | E-post och länkar: innehåller i primär och övriga adresser. | delvis | Fritexten söker i personens e-post och bolagets domän (`lagring.py` `_LISTA`). Bolagets e-post och webbadress ingår inte, och inget val av delfält. | senare |
| VY-056 | Aktör (Skapad av): innehåller, och filter på källa eller medlem. | inte gjord | Källan (`kalla`) lagras men går inte att filtrera på. | senare |
| VY-057 | Lista, JSON och filer: innehåller i något element, JSON-texten eller filnamnen. | inte gjord | Egna fält (`extra`) och listfält går inte att filtrera på. | senare |
| VY-058 | Sant eller falskt, och UUID är eller är inte en lista id:n. | delvis | Id-filter med "är" ett id finns (`company_id`, `deal_id`, `stage_id` i `crm_v1_objekt.py`). Inget filter på sant eller falskt (till exempel Kontakta inte), och inga listor av id:n. | senare |
| VY-059 | Filtergrupper med OCH och ELLER, nästlade i två nivåer. | inte gjord | API:ts filter kombineras alltid med OCH (`lagring.py` `lista_poster`); inga grupper och inget ELLER. | senare |
| VY-060 | Snabbsökning över alla sökbara fält, där posten träffas om något fält matchar. | delvis | Fritext `q` över ett fast urval kolumner per objekt (`lagring.py` `_LISTA`; prövas i `test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr`, `test_api.py`, och `test_affarer_sorteras_sidindelas_och_filtreras`, `test_objekt.py`). Inte alla fält, inte tal, valuta eller valalternativ. | senare |
| VY-061 | En sparad sortering är fält plus riktning, valfritt delfält eller relaterat fält; ett fält en gång per vy. | delvis | Sorteringen är en frågeparameter med riktning för ändringstid (`sort=updated` eller `-updated`) och stigande namn eller förfallodag (`crm_v1.py` `_LISTPARAMETRAR`; prövas i `test_senast_andrad_forst_med_sidindelning`, `snajp-support/tests/crm/test_handelser_webhooks.py`). Den sparas inte och går inte att lägga på valfritt fält. | 4 |
| VY-062 | En vygrupp är ett värde i grupperingsfältet med synlighet och position. | delvis | Affärernas steg har namn och position och är tavlans grupper (`crm_affarssteg` i migration 164, `objekt.py` `lista_steg`). Synlighet per grupp och grupper för andra fält saknas. | 3 |
| VY-063 | Summeringsoperationer: min, max, medel, summa, antal, antal unika, antal tomma och ifyllda, antal sant och falskt, procent tomma och ifyllda. | delvis | Antal och summa finns: antal och beloppssumma per steg på tavlan (`crm_v1_objekt.py` `tavla`; prövas i `test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa`, `test_objekt.py`) och antal bolag per relation (`lagring.py` `rakna_poster`). Övriga operationer saknas. | senare |
| VY-064 | Gruppering och summering per dag, vecka, månad, kvartal, år och liknande. | inte gjord | Ingen datumgruppering. | senare |
| VY-065 | Vyväljaren listar delade vyer och egna privata vyer i två sektioner som går att ordna. | inte gjord | Vyraden visar fasta vyer (`BolagVy.tsx` `Vyval`), ingen vyväljare med sektioner. | 4 |
| VY-066 | Meny per vy: välj, favorit, redigera, radera. | inte gjord | Inga sparade vyer. | 4 |
| VY-067 | Skapa-läget i vyväljaren med ikon, namn, vytyp, synlighet och grupperings- eller datumfält. | inte gjord | Inga sparade vyer. | 4 |
| VY-068 | Vad som följer med till en ny vy: fält, filter, sorteringar och tavlans inställningar. | inte gjord | Inga sparade vyer. | 4 |
| VY-069 | Vilka fält som kan väljas att gruppera på (valfält och många-till-en-relationer). | inte gjord | Inget val av grupperingsfält. | senare |
| VY-070 | Vilka datumfält som kan väljas för kalendern. | inte gjord | Ingen kalendervy. | 3 |
| VY-071 | Redigera-läget i vyväljaren: byt namn och ikon. | inte gjord | Inga sparade vyer. | 4 |
| VY-072 | Osparade ändringar ligger ovanpå den sparade vyn med knapparna Uppdatera vy och Återställ. | inte gjord | Sökning, vy och sortering hålls bara i komponentens tillstånd (`BolagVy.tsx`) och försvinner vid omladdning; inget att spara till. | 4 |
| VY-073 | Spara ändrade filter, sorteringar och sökning i vyn. | inte gjord | Inga sparade vyer. | 4 |
| VY-074 | Återställ vyn till det sparade. | inte gjord | Inga sparade vyer. | 4 |
| VY-075 | En detaljrad med filter- och sorteringschips visas när det behövs. | inte gjord | Ingen chiprad i vyraden. | 4 |
| VY-076 | Varje filter och sortering visas som chip med fält, villkor och värde, klick redigerar och X tar bort. | inte gjord | Inga chips; sorteringen visas som ett valt alternativ i väljaren Sortera (`BolagVy.tsx`). | senare |
| VY-077 | Visa raderade poster (papperskorgen) i stället för de aktiva. | verifierad | Papperskorgen är en egen vy i vyraden på Bolag och Personer (`BolagVy.tsx` vyn `papperskorg`, `components/crm/app/Papperskorg.tsx`) och hämtar `only_deleted=true` (`lagring.py` `lista_poster` med `ordning="raderad"`). Prövas i `test_papperskorgen_visar_det_som_gar_att_aterstalla`, `snajp-support/tests/crm/test_handelser_webhooks.py`. Visas som vy, inte som chip. | |
| VY-078 | Snabbsökning från vyfältet som filtrerar direkt och kan sparas i vyn. | delvis | Sökfältet i vyraden filtrerar medan man skriver (`BolagVy.tsx` och `PersonerVy.tsx` `sok`, 250 ms fördröjning; bilden `docs/crm/bilder/app/bolag-1440.png`). Det söker i ett fast urval fält och sparas inte. | 4 |
| VY-079 | Filter och sortering kan bäras i adressen och blir osparade ändringar på vyn. | inte gjord | Adressen bär bara den öppna posten och `?ny=1` (`BolagVy.tsx` `sattPost`, `useBestallning`), inga filter eller sorteringar. | senare |
| VY-080 | Fältlistan i Alternativ: synliga och dolda fält, sök, dra för ordning, öga för att dölja. | inte gjord | Inga inställningar för kolumner. | senare |
| VY-081 | Vilken vy som öppnas: den i adressen, annars senast besökta, annars huvudvyn. | inte gjord | Listan öppnar alltid "Alla", senast ändrad först (`BolagVy.tsx`). | 4 |
| VY-082 | Vyns grupper byts ut när grupperingen ändras på servern. | inte gjord | Ingen gruppering i vyer. | senare |
| VY-083 | Lägga till ett filter från menyn Filter med sökbara synliga och dolda fält. | inte gjord | Ingen filtermeny. | senare |
| VY-084 | Ett fält har bara ett enkelt filter åt gången, och enkla filter kombineras med OCH. | inte gjord | Ingen filtermeny att lägga filter i. | senare |
| VY-085 | Ett nytt filter får typens första villkor och ett startvärde (dagens datum, falskt, denna dag). | inte gjord | Ingen filtermeny. | senare |
| VY-086 | Byta villkor i ett filter via en väljare. | inte gjord | Ingen filtermeny. | senare |
| VY-087 | Kort villkorstext i chipet, till exempel "Senaste 3 dagarna". | inte gjord | Inga filterchips. | senare |
| VY-088 | Värdeinmatning anpassad efter fälttypen (text, tal, datum, val, relation, boolean, valuta, land, aktör). | inte gjord | Ingen filtermeny. | senare |
| VY-089 | Filter på delfält av sammansatta fält (namn, adress, valuta, telefon, e-post, länkar). | inte gjord | Ingen filtermeny. | senare |
| VY-090 | Öppna det avancerade filtret, som läggs till vyns filter med OCH och visas som ett chip. | inte gjord | Inget avancerat filter. | senare |
| VY-091 | Regelrader i det avancerade filtret med Where, And eller Or, fält, villkor och värde. | inte gjord | Inget avancerat filter. | senare |
| VY-092 | Lägga till regel och regelgrupp i det avancerade filtret. | inte gjord | Inget avancerat filter. | senare |
| VY-093 | Avancerat filter på relaterade poster och delfält. | inte gjord | Inget avancerat filter. | senare |
| VY-094 | En post som efter redigering inte längre matchar filtret försvinner ur listan utan omladdning. | delvis | Efter en ändring hämtar listan om sin första sida från servern (`BolagVy.tsx` `hamta(null)` efter relationsbyte, radering och sparat formulär), så ett bolag som byter relation lämnar vyn. Det sker genom omhämtning, inte genom lokal prövning mot filtret. | senare |
| VY-095 | Vilka fält som går att filtrera på i gränssnittet. | delvis | I gränssnittet: relation (vyraden på Bolag), kopplat bolag (Personer) och fritext (`BolagVy.tsx`, `PersonerVy.tsx`). Inga andra fält går att filtrera på. | senare |
| VY-096 | Lägga till en sortering från menyn Sort med riktning och sökbar fältlista. | delvis | Väljaren Sortera i vyraden har tre fasta ordningar: senast ändrad, ändringsordning och namn (`components/crm/app/kit.tsx` `ORDNINGAR`; bilden `docs/crm/bilder/app/bolag-1440.png`). Ingen riktningsväljare och inget val av fält. | senare |
| VY-097 | Flera sorteringsnivåer i den ordning de lades till. | inte gjord | En sortering åt gången; lika värden avgörs av postens id (`lagring.py` `lista_poster`). | senare |
| VY-098 | Tomma värden hamnar sist i båda riktningarna. | delvis | Uppgifter utan förfallodag hamnar sist (`lagring.py` `_ALDRIG`; prövas i `test_uppgifter_sorteras_pa_forfallodag_och_filtreras`, `test_objekt_ovriga.py`). I namnordningen sorteras ett tomt namn som tom sträng, alltså först (`lagring.py` `_sorteringsnyckel`). | senare |
| VY-099 | Postens manuella position är sista sorteringsnyckel, så att ordningen är stabil och kan dras. | delvis | Affärerna på tavlan ordnas på sin position (`objekt.py` `tavla`). Listorna har id som sista nyckel för stabil ordning, men ingen manuell position. | senare |
| VY-100 | Hur sammansatta fält och relationer sorteras (namn, adress, valuta, e-post, relation). | delvis | Personer sorteras i namnordning på efternamnet (`lagring.py` `_LISTA`, `"person": ("efternamn", ...)`). Sortering på adress, belopp, e-post eller relaterad post saknas. | senare |
| VY-101 | Vilka fälttyper som går att sortera på. | delvis | Bara namn, ändringstid och (för uppgifter) förfallodag (`crm_v1.py` `_LISTPARAMETRAR`, `crm_v1_objekt.py` `lista_uppgifter`). | senare |
| VY-102 | Sortera från kolumnens rubrik: först stigande, sedan växlar riktningen. | delvis | Rubrikerna Bolag och Ändrad (Namn och Ändrad på Personer) sorterar (`kit.tsx` `useKolumnsortering`). Ändrad växlar riktning; namnet står alltid A till Ö eftersom API:t saknar omvänd namnordning. Övriga kolumner sorterar inte. | senare |
| VY-103 | Alternativ-menyn på huvudvyn med fält, kopiera länk och skapa egen vy. | inte gjord | Ingen Alternativ-meny. | 4 |
| VY-104 | Alternativ-menyn på egna vyer med namn, layout, synlighet, fält, gruppering, länk och radering. | inte gjord | Ingen Alternativ-meny och inga egna vyer. | 4 |
| VY-105 | Byta layout på en vy mellan tabell, lista, kalender och tavla. | inte gjord | Tabell eller lista väljs av skärmbredden (`kit.tsx` `useSmal`), inte av användaren. | senare |
| VY-106 | Synlighetsmenyn (alla eller bara jag) och "Kopiera länk till vyn". | inte gjord | Inga vyer att dela eller länka till. | 4 |
| VY-107 | Gruppera tabellen från Alternativ: fält, sektioner eller flikar, ordning, laddningsgräns, dölj tomma. | inte gjord | Ingen gruppering att välja. | senare |
| VY-108 | Gruppernas ordning: manuell, A till Ö eller Ö till A. | delvis | Affärernas steg har manuell ordning som går att ändra via API:t (`POST /v1/deal-stages/reorder`, `objekt.py` `ordna_steg`; prövas i `test_steg_byter_namn_ordnas_om_laggs_till_och_tas_bort`, `test_objekt.py`). Bokstavsordning och val i gränssnittet saknas. | 3 |
| VY-109 | Dolda grupper listas och kan visas igen. | inte gjord | Inga dolda grupper. | senare |
| VY-110 | Lägga till en grupp genom att välja en relaterad post vid gruppering på relation. | inte gjord | Ingen gruppering på relation. | senare |
| VY-111 | Välja laddningsgräns per grupp (8, 25, 50 eller 100). | inte gjord | Ingen gruppering i tabellen. | senare |
| VY-112 | Kalenderns inställningar: datumfält och dag, vecka eller månad. | inte gjord | Ingen kalendervy. | 3 |
| VY-113 | Fältinställningar i Alternativ: sök, ordna, dolda fält och länk till fältinställningarna. | inte gjord | Inga kolumninställningar. | senare |
| VY-115 | Byta eller ta bort grupperingsfält från Alternativ, varvid grupperna skapas för fältets värden. | inte gjord | Inget val av grupperingsfält. | senare |
| VY-114 | Exportera vyns data, 200 poster per sida, efter vyns filter, sortering och kolumner. | inte gjord | Ingen export från CRM:ets listor. CSV-export av listor ligger i fas 4 (LR-129 i `MIGRERING-FUNKTIONSLISTA.md`). | 4 |
| VY-116 | Tabellens grundlayout: fasta radhöjder, dra-handtag, kryssruta, fast namnkolumn, plus-kolumn, fast rubrikrad och sidfot. | delvis | Astryx `Table` med kryssruta per rad, namnkolumnen först, rubrikrad och räknefot, rader på cirka 44 px (`BolagVy.tsx`, `PersonerVy.tsx`; bilden `docs/crm/bilder/app/bolag-1440.png`). Dra-handtag, plus-kolumn och namnkolumn som står kvar vid sidledsrullning saknas. | senare |
| VY-117 | Ändra kolumnbredd genom att dra i rubrikens kant; bredden sparas. | inte gjord | Bredderna är fasta i koden (`pixel(126)` med flera i `BolagVy.tsx`). | senare |
| VY-118 | Flytta kolumner genom att dra eller med Flytta vänster och höger. | inte gjord | Fast kolumnordning. | senare |
| VY-119 | Kolumnrubrikens meny: flytta, dölj, filtrera, sortera, ta bort kolumn. | inte gjord | Rubrikerna har ingen meny; två av dem sorterar vid klick (`kit.tsx` `useKolumnsortering`). | senare |
| VY-120 | Sortera från kolumnrubriken: stigande första gången, sedan växla riktning. | delvis | Klick på rubriken Bolag (Namn) eller Ändrad byter ordning (`kit.tsx` `useKolumnsortering`, `sortable: true` i `BolagVy.tsx` och `PersonerVy.tsx`). Bara två kolumner, och namnet kan inte vändas till Ö till A. | senare |
| VY-121 | Filtrera från kolumnrubriken. | inte gjord | Ingen rubrikmeny och ingen filtermeny. | senare |
| VY-122 | Lägga till en kolumn direkt i tabellen med "+" bland dolda fält och relationer. | inte gjord | Ingen plus-kolumn. | senare |
| VY-123 | Redigera ett fält direkt i cellen genom klick, Enter eller att börja skriva. | inte gjord | Fälten ändras i dialogen (`BolagFormular.tsx`, `PersonFormular.tsx`), som panelens "Lägg till" öppnar på rätt fält. Redigerbara celler är planerade med Leads (`MIGRERING-FUNKTIONSLISTA.md`, mönstret Redigerbara celler). | 4 |
| VY-124 | Spara eller avbryta en cellredigering med Enter, Tab, Shift+Tab, klick utanför och Escape. | inte gjord | Ingen redigering i cellen. | 4 |
| VY-125 | Tömma en cell med Backspace eller Delete. | inte gjord | Ingen redigering i cellen. | 4 |
| VY-126 | Piltangenterna flyttar fokus mellan celler. | inte gjord | Ingen cellnavigering. | senare |
| VY-127 | Kortkommandon för rader: upp, ned, j, k, x för markering, Ctrl+Enter för att öppna, Escape. | inte gjord | Inga kortkommandon i listan; Ctrl/Cmd+K öppnar kommandopaletten (`Kommandopalett.tsx`), som är något annat. | senare |
| VY-128 | Markera rader med kryssruta och Shift-klick för ett intervall; antalet styr åtgärderna. | delvis | Kryssruta per rad, antal markerade och åtgärdsraden med Ändra relation och Ta bort (`BolagVy.tsx` `useTableSelection`, `TableSelectionToolbar`; kryssrutorna syns i `docs/crm/bilder/app/bolag-1440.png`), och markeringsläget Välj på mobil. Intervall med Shift har jag inte sett i koden. | senare |
| VY-129 | Markera alla rader, och därefter gäller markeringen hela träffmängden även ej inlästa poster. | delvis | Kryssrutan i rubriken markerar de inlästa raderna (Astryx `useTableSelectionState` i `BolagVy.tsx`). Markering av hela träffmängden utöver inlästa rader och Ctrl/Cmd+A saknas. | senare |
| VY-130 | Högerklick på en rad öppnar en kontextmeny. | inte gjord | Ingen kontextmeny. | senare |
| VY-131 | Dra rader för att ordna dem manuellt, även mellan grupper; kräver att sorteringen tas bort. | delvis | Positionen mitt emellan grannarna räknas redan för affärer som flyttas på tavlan (`objekt.py` `flytta`; prövas i `test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa` och `test_luckan_mellan_tva_kort_jamnas_ut`, `test_objekt.py`). Rader i tabellen går inte att dra. | senare |
| VY-132 | Oändlig rullning med virtualisering och sidor om 10 rader. | delvis | Sidindelning med markör, 50 rader per sida och knappen "Visa fler" i foten (`BolagVy.tsx` `SIDSTORLEK`, `hamta(nasta)`; API:t prövas i `test_sidindelning_med_markor`, `test_api.py`). Ingen automatisk laddning vid rullning och ingen virtualisering. | senare |
| VY-133 | Liveuppdatering när andra ändrar poster. | inte gjord | Listan hämtas om bara efter egna ändringar. Webhooks ut finns (`webhooks.py`) men ingen ström till gränssnittet. | senare |
| VY-134 | Lägga till en ny post från tabellen: raden under tabellen och knappen i sidhuvudet. | verifierad | Knappen "Nytt bolag" i sidhuvudet och raden "Lägg till bolag" under tabellen öppnar samma dialog (`BolagVy.tsx` `nyttBolag`, `laggTill`; samma på Personer). Knappen syns i `docs/crm/bilder/app/bolag-1440.png`. Förifyllnad från filter och grupper saknas. | |
| VY-135 | Förifyllnad av fält utifrån radnivåbehörighet när en post skapas. | avstår | Enterprise-fil i förlagan (`useBuildRecordInputFromRLSPredicates.ts` med flera). | |
| VY-136 | Grupperad tabell med en sektion per grupp, hopfällbar, med "Ladda fler". | inte gjord | Ingen gruppering i tabellen. | senare |
| VY-137 | Tomlägen: inga poster än, inga träffar med filter, tom papperskorg, saknad rätt att skapa. | byggd | `EmptyState` för inga bolag än, ingen träff på sökningen, tom relationsvy och tom papperskorg (`BolagVy.tsx` `tomt`, `PersonerVy.tsx`, `Papperskorg.tsx`). Läget för saknad rätt och för fjärrobjekt har ingen motsvarighet eftersom CRM:et saknar sådana. | |
| VY-138 | Vy eller objekt som inte delats med användaren, och vy som använder fält användaren inte får läsa. | inte gjord | Inga behörigheter per objekt eller fält i CRM:et. | senare |
| VY-139 | Öppna en post från listan i sidopanel eller på egen sida. | verifierad | Klick på postchipet öppnar postens panel till höger och adressen får `?bolag=` (`BolagVy.tsx` `oppna`, `BolagPanel.tsx`; samma på Personer). Panelen syns i `docs/crm/bilder/app/bolag-panel-1440.png`. Egen postsida finns inte. | |
| VY-140 | Summering i tabellens sidfot per kolumn, vald i en meny och sparad på vyfältet. | delvis | Räknefoten visar antal visade av totalt och, på Bolag, antal och andel kunder; på Personer antal utan bolag (`BolagVy.tsx` och `PersonerVy.tsx` `crm-raknefot`). Ingen summering per kolumn och inget val. | senare |
| VY-141 | Vilka summeringar som finns per fälttyp. | inte gjord | Inga valbara summeringar. | senare |
| VY-142 | Hur summeringsvärden visas: tal, procent, valuta, datum och korta etiketter. | delvis | Räknefoten formaterar antal med lokalens tusentalsavgränsare och andelen kunder i procent (`BolagVy.tsx` `tal`, `fot`). Valuta och datum i summeringar saknas. | senare |
| VY-143 | En kolumn med en summering av relaterade poster per rad. | inte gjord | Inga summeringskolumner. | senare |
| VY-144 | Tavlans kolumner är grupperingsfältets värden i gruppernas ordning, med en kolumn för poster utan värde. | delvis | `GET /v1/deals/board` ger stegen i ordning med sina affärer (`crm_v1_objekt.py` `tavla`, `objekt.py` `tavla`; prövas i `test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa`, `test_objekt.py`). Tavlan ritas inte i gränssnittet, och det finns ingen kolumn för affärer utan steg. | 3 |
| VY-145 | Dra kort mellan kolumner så att grupperingsfältet och positionen ändras. | delvis | `POST /v1/deals/{id}/move` byter steg och position före eller efter en annan affär (`objekt.py` `flytta`; prövas i `test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa`, `test_objekt.py`). Inget att dra i gränssnittet, och flera kort åt gången saknas. | 3 |
| VY-146 | Ny post direkt i en kolumn, först eller sist, med kolumnens värde. | delvis | En affär som skapas med `stage_id` hamnar sist i steget (`crm_v1_objekt.py` `skapa_affar`, `objekt.py` `_sist`). Knapparna i kolumnen och "först i kolumnen" saknas. | 3 |
| VY-147 | Kolumnens meny: redigera, flytta höger eller vänster, dölj. | delvis | Steget kan döpas om och stegen ordnas om via API:t (`PATCH /v1/deal-stages/{id}`, `POST /v1/deal-stages/reorder`; prövas i `test_steg_byter_namn_ordnas_om_laggs_till_och_tas_bort`, `test_objekt.py`). Menyn i gränssnittet och att dölja en kolumn saknas. | 3 |
| VY-148 | Summering i kolumnhuvudet, valbar och sparad på vyn, till exempel summa av belopp per steg. | delvis | Antal och beloppssumma per steg, även uppdelat per valuta (`crm_v1_objekt.py` `tavla`; prövas i `test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa`, `test_objekt.py`). Fast, inte valbar, och inte visad i gränssnittet. | 3 |
| VY-149 | Tavlans kolumnbredd kan dras mellan 150 och 400 px. | inte gjord | Tavlan finns inte i gränssnittet. | 3 |
| VY-150 | Kortets innehåll: namn, kryssruta och vyns synliga fält, redigerbara på kortet. | inte gjord | Tavlan finns inte i gränssnittet. | 3 |
| VY-151 | Kompakt läge på tavlan och fälla ut ett enskilt kort. | inte gjord | Tavlan finns inte i gränssnittet. | 3 |
| VY-152 | Tavlan laddar 10 kort per kolumn och fler vid rullning, med skelettkort. | inte gjord | API:t lämnar alla affärer per steg i ett svar (`objekt.py` `tavla`); ingen tavla i gränssnittet. | 3 |
| VY-153 | Tangentbord och markering på tavlan, även rektangelmarkering. | inte gjord | Tavlan finns inte i gränssnittet. | senare |
| VY-154 | Liveuppdatering på tavlan. | inte gjord | Ingen liveuppdatering. | senare |
| VY-155 | Lägga till en kolumn på tavlan vid gruppering på relation. | inte gjord | Tavlan grupperar bara på steg. | senare |
| VY-156 | Lägga till och ta bort steg. | delvis | Steg skapas, döps om, ordnas och tas bort via API:t, med spärr för steg som har affärer och för det sista av sin typ (`objekt.py` `skapa_steg`, `ta_bort_steg`; prövas i `test_steg_byter_namn_ordnas_om_laggs_till_och_tas_bort` och `test_steg_med_affarer_och_det_sista_av_sin_typ_star_kvar`, `test_objekt.py`). Inget gränssnitt för stegen. | 3 |
| VY-157 | Varje grupp hämtar poster med gruppens värde, och flikläget har en flik "Alla". | delvis | Bolag har fliken "Alla" och en flik per relation som hämtar `relation=<värde>` (`BolagVy.tsx` `hamta`; bilden `docs/crm/bilder/app/bolag-1440.png`), och affärer går att hämta per steg (`stage_id`, prövas i `test_affarer_sorteras_sidindelas_och_filtreras`, `test_objekt.py`). Fast på relationen, inte för valfritt grupperingsfält. | senare |
| VY-158 | Vilka vytyper som stöder flikar, laddningsgräns och valfri gruppering. | inte gjord | Inga vytyper att välja. | senare |
| VY-159 | Bekräftelse när grupper dras medan gruppordningen är alfabetisk. | inte gjord | Inga grupper att dra. | senare |
| VY-160 | Visa eller dölja en enskild grupp, och fälla ihop en sektion. | inte gjord | Användaren kan inte dölja en vy eller grupp; de sällsynta relationerna döljs automatiskt när de är tomma (se VY-019). | senare |
| VY-161 | Kalendervyn placerar varje post som ett kort på dagen för ett datumfält. | inte gjord | Ingen kalendervy. Uppgifternas förfallodag och aktiviteternas tid finns i API:t men visas inte i en kalender. | 3 |
| VY-162 | Kalenderns layouter dag, vecka och månad med veckostart, helger och dagens datum markerade. | inte gjord | Ingen kalendervy. | 3 |
| VY-163 | Navigera i kalendern: layoutväljare, datumväljare, föregående, nästa och Idag. | inte gjord | Ingen kalendervy. | 3 |
| VY-164 | Kalendern hämtar poster i den visade perioden, kombinerat med vyns filter. | inte gjord | Ingen kalendervy. | 3 |
| VY-165 | Högst fem kort per dag i kalendern. | inte gjord | Ingen kalendervy. | 3 |
| VY-166 | Dra ett kort till en annan dag så att datumet flyttas. | inte gjord | Ingen kalendervy. | 3 |
| VY-167 | Skapa en ny post på en viss dag i kalendern. | inte gjord | Ingen kalendervy. | 3 |
| VY-168 | Redigera fälten direkt på kalenderkortet, med liveuppdatering. | inte gjord | Ingen kalendervy. | 3 |
| VY-169 | Listvy: en rad per post med namn och små fält, "+N" för dolda fält, dra, lägg till och gruppering. | delvis | På smal skärm visas Bolag och Personer som lista med avatar, namn, en dämpad andra rad (ort, ansvarig) och relationen (`BolagVy.tsx` `List`/`ListItem`; bilden `docs/crm/bilder/app/bolag-390.png`). Den väljs av skärmbredden, inte av användaren, och saknar "+N", dra och gruppering. | senare |
| VY-170 | Adressförslag (autokomplettering) i adressfält via Google Places eller den franska adresstjänsten. | inte gjord | Ingen adresstjänst i CRM:et; förlagans franska drivrutin har ingen svensk motsvarighet här. | ej planerad |
| VY-171 | Postväljare för flera poster med fördröjd sökning, valda först, laddning vid rullning och "Lägg till ny". | inte gjord | Ingen väljare för flera poster. | senare |
| VY-172 | Postväljare för en post, som kan utesluta vissa poster. | delvis | Bolagsväljaren på Personer och i personformuläret är en `Selector` med sökning bland de första 500 bolagen i namnordning (`PersonerVy.tsx` `bolagsvaljare`, `PersonFormular.tsx`; bilden `docs/crm/bilder/app/personer-1440.png`). Sökningen går i webbläsaren, inte mot servern, och "Lägg till ny" saknas. | senare |
| VY-173 | API:ts filteroperatorer: eq, neq, gt, gte, lt, lte, in, is, like, ilike, startsWith, contains, search, and, or, not med flera. | delvis | API:t har likhet per parameter, ILIKE via `q`, mindre än via `due_before` och större eller lika via `updated_since`, kombinerat med OCH (`lagring.py` `lista_poster`; ett ogiltigt värde ger 422, prövas i `test_uppgifter_sorteras_pa_forfallodag_och_filtreras`, `test_objekt_ovriga.py`). Övriga operatorer och ELLER saknas. | senare |
| VY-174 | Tomma värden likställs med null när servern filtrerar. | inte gjord | Inga tomhetsvillkor i API:t att likställa. | senare |
| VY-175 | Tidsstämplar jämförs med millisekundsprecision. | inte gjord | Tider jämförs som Postgres `timestamptz` (`lagring.py` `lista_poster`) utan förlagans regler för likhet inom samma millisekund. | senare |
| VY-176 | Fulltextsökning som är okänslig för accent och skiftläge. | delvis | Fritexten är skiftlägesokänslig (ILIKE i `lagring.py` `lista_poster`). Den är inte okänslig för accenter och använder inget fulltextindex. | senare |
| VY-177 | Ett nytt objekt får automatiskt sin huvudvy med systemfälten som kolumner. | inte gjord | CRM:et har inga egna objekt. | ej planerad |
| VY-178 | Ett nytt fält läggs automatiskt till som kolumn sist i huvudvyn. | inte gjord | Egna fält (`extra`, `falt.py`) visas inte som kolumner. | senare |
| VY-179 | När objektets namnfält byts flyttas dess kolumn först. | inte gjord | Namnfältet går inte att byta; inga egna objekt. | ej planerad |
| VY-180 | Ett raderat fält städas bort ur vyernas kolumner, filter och sorteringar. | inte gjord | Inga lagrade vyer att städa. | senare |
| VY-181 | En tabell kan visas som widget på en postsida eller instrumentpanel, med begränsningar. | inte gjord | CRM:et har inga sidlayouter eller instrumentpaneler med egna widgetar; översikten har fasta nyckeltal (`OversiktVy.tsx`). | ej planerad |
| VY-182 | Ändringar i en widgetvy sparas bara med sidlayouten. | inte gjord | Inga widgetar. | ej planerad |
| VY-183 | Summeringen i en tabellwidgets sidfot är låst utanför redigeringsläget. | inte gjord | Inga widgetar. | ej planerad |
| VY-184 | Lägga till en relaterad post från en tabellwidget på postsidan, även via kopplingsobjekt. | inte gjord | Bolagspanelens flik Personer har ingen knapp för att lägga till en person; personen kopplas i personformuläret. | senare |
| VY-185 | En tavla kan visas som widget. | inte gjord | Inga widgetar. | ej planerad |
| VY-186 | En kalender kan visas som widget. | inte gjord | Inga widgetar. | ej planerad |
| VY-187 | En lista kan visas som widget. | delvis | Bolagspanelens flik Personer visar bolagets personer som lista med avatar, namn, titel och kontaktpiller (`BolagPanel.tsx`). Den är fast, inte en konfigurerbar vy. | senare |
| VY-188 | En kolumn är ett av fem slag: fält, uppslag, omfångade poster, omfångat uppslag eller summering. | inte gjord | Bara fältkolumner, fasta i koden. | senare |
| VY-189 | Uppslagskolumner slås på med en funktionsflagga per arbetsyta. | inte gjord | Inga uppslagskolumner. | senare |
| VY-190 | Välja fält för en uppslagskolumn bland målobjektets fält. | inte gjord | Inga uppslagskolumner. | senare |
| VY-191 | Kolumnrubrikens form för de olika kolumnslagen. | inte gjord | Bara fältkolumner. | senare |
| VY-192 | Omfångade kolumner kan inte sorteras eller filtreras. | inte gjord | Inga omfångade kolumner. | senare |
| VY-193 | Lägga till en summeringskolumn från plus-menyn. | inte gjord | Ingen plus-meny och inga summeringskolumner. | senare |
| VY-194 | Omfång genom ett kopplingsobjekt (många-till-många). | inte gjord | Inga omfångade kolumner. | senare |
| VY-195 | Omfångade kolumner hålls aktuella när relaterade poster ändras. | inte gjord | Inga omfångade kolumner. | senare |
| VY-196 | Exportera vyns eller markeringens poster till CSV med vyns sortering och kolumner. | inte gjord | Ingen export från CRM:ets listor (LR-129 i `MIGRERING-FUNKTIONSLISTA.md`). | 4 |
| VY-197 | Exportens förlopp i knappen och en asynkron export på servern. | inte gjord | Ingen export. | 4 |
| VY-198 | Ladda fler i en grupp i den grupperade tabellen. | inte gjord | Ingen grupperad tabell. | senare |
| VY-199 | Fälla ihop en grupp och lägga till en grupp i tabellen. | inte gjord | Ingen grupperad tabell. | senare |
| VY-200 | En tom rotgrupp i det avancerade filtret tas bort automatiskt. | inte gjord | Inget avancerat filter. | senare |
| VY-201 | Tomma filtergrupper städas bort och lösa filter samlas i rotgruppen. | inte gjord | Inga filtergrupper. | senare |
| VY-202 | Sorteringschipets meny: växla riktning, välj delfält, ta bort. | inte gjord | Inga sorteringschips. | senare |
| VY-203 | Hur ett relativt datumfilter och ett relationsfilter skrivs som värde. | inte gjord | Inga relativa datumfilter och inga lagrade filtervärden. | senare |
| VY-204 | När ett objekt är skrivskyddat stängs cellredigering, dra och ny post av. | delvis | Servern nekar skrivning med en läsnyckel och utan registrerat avtal (`crm_v1.py` `kraev` och `_avtal`; prövas i `test_en_lasnyckel_laser_men_skriver_inte`, `test_objekt_ovriga.py`, och `test_utan_registrerat_avtal_gar_det_att_lasa_men_inte_skriva`, `test_api.py`). Gränssnittet stänger inte av knapparna i förväg. | senare |
| VY-205 | När ett fält eller en post är skrivskyddad, även genom behörighet på målobjektet. | inte gjord | Inga behörigheter per fält eller objekt i CRM:et. | senare |
| VY-206 | REST-API för vyer och deras delar (lista, hämta, skapa, ändra, radera). | inte gjord | Inga vyer i API:t (`docs/crm/API.md`). | senare |
| VY-207 | GraphQL-operationer för vyer. | inte gjord | CRM:et har inget GraphQL-API, bara REST. | ej planerad |
| VY-208 | En app kan leverera färdiga vyer för sina eller standardobjekt. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
