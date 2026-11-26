# Twenty 13: handboken som facit (ID-prefix HB)

Källa: Twentys engelska användarhandbok (`packages/twenty-docs/user-guide/**`) och
kom-igång-sidorna (`packages/twenty-docs/getting-started/**`), commit 1da6d55
(2026-11-24). Innehållsförteckningen följer `packages/twenty-docs/navigation/navigation.template.json`
och `docs.json`. Allt är återgivet med egna ord; inga kodstycken eller längre
citat. Licens: dokumentationen ligger i AGPL-repot; kolumnen "Licens" anger
AGPL om inget annat sägs, och "Enterprise" där handboken uttryckligen säger att
funktionen kräver Enterprise-plan (handboken markerar inte filernas
licenshuvuden; den kontrollen görs av kodläsarna). Ett stickprov med Grep i
`twenty-server/src` gav "Enterprise" för valideringsregler (HB-077) och
radnivåbehörigheter (HB-323). Där handboken säger att en funktion kräver
Organization- eller Premiumplan står det inom parentes i licenskolumnen.

Raderna ska användas som facit: varje HB-rad ska motsvaras av minst en rad i
kodläsarnas underlag (twenty-01 till twenty-12). Saknas en motsvarighet där har
kodläsningen missat något, eller så finns funktionen bara i handboken.

## Översikt

Handboken är ordnad i flikar: Getting Started (introduktion, nyckelfunktioner,
snabbstart och "Core Concepts") och User Guide med sektionerna Data Model, Data
Migration, Calendar & Emails, Email Campaigns, Workflows, AI, Layout (med Views
& Pipelines), Dashboards, Permissions & Access, Billing, Settings och Legal.
Varje sektion har en översiktssida, "Reference/Capabilities" (vad funktionen
är) och "How-Tos" (recept och FAQ).

Begreppen hänger ihop så här: en arbetsyta (workspace) har en datamodell av
objekt (objects) med fält (fields) och relationer; poster (records) visas i
vyer (views: tabell, kanban, kalender) med filter, sortering och gruppering;
varje post har en postsida (record page) med tidslinje, anteckningar, uppgifter,
mejl och kalenderhändelser som synkas från anslutna konton. Arbetsflöden
(workflows) reagerar på händelser och kör steg; AI (agenter, chatt, MCP) läser
och skriver samma data; dashboards sammanfattar datan i widgetar. Behörigheter
(roller) styr allt, och plan/krediter (billing) sätter gränser.

## Avprickningslista

| Katalog | Status |
|---|---|
| getting-started (docs-roten) | läst |
| user-guide/introduction.mdx + user-guide/getting-started | läst |
| user-guide/data-model | läst |
| user-guide/data-migration | läst |
| user-guide/calendar-emails | läst |
| user-guide/email-campaigns | läst |
| user-guide/workflows | läst |
| user-guide/ai | läst |
| user-guide/layout | läst |
| user-guide/views-pipelines | läst |
| user-guide/dashboards | läst |
| user-guide/permissions-access | läst |
| user-guide/billing | läst |
| user-guide/settings | läst |
| user-guide/legal | läst |
| navigation (docs.json, navigation/) | läst (navigation.template.json; docs.json jämförd sida för sida mot filerna vid kontrolläsningen, se HB-393) |
| Kontrolläsning 2026-11-26 | Alla 141 engelska .mdx under user-guide/ och getting-started/ jämförda mot raderna: fem sidor saknade hänvisning (två ordlistor, what-is-twenty, customize-your-data-model, professional-services) och har fått HB-389–HB-392. Uppräkningar och stickprov tillagda. |

## Funktionstabell

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| **Getting Started (kom igång)** | | | | |
| HB-001 | Registrera konto via Google, Microsoft eller e-post. | Tre inloggningsvägar vid registrering i molnet. | getting-started/quickstart.mdx; user-guide/getting-started/how-tos/create-workspace.mdx | AGPL |
| HB-002 | Välja provperiod vid registrering. | 30 dagar med kort eller 7 dagar utan kort; båda ger full åtkomst (obegränsat antal kontakter, mejlintegration, egna objekt, API och webhooks). Plan och faktureringsintervall kan bytas när som helst ("Change plan"). | getting-started/quickstart.mdx; user-guide/getting-started/how-tos/create-workspace.mdx | AGPL |
| HB-003 | Skapa arbetsyta och användarprofil efter betalbekräftelse. | Betalning bekräftas via Stripe, därefter anges arbetsytans namn och användarprofil. Prenumerationen kan sägas upp när som helst. | getting-started/quickstart.mdx; create-workspace.mdx | AGPL |
| HB-004 | Ansluta brevlåda och kalender som första steg. | Settings → Accounts; Google eller Microsoft. Importerar mejl och möten och kan (valfritt) skapa kontakter automatiskt utifrån interaktioner. Annan leverantör: brevlåda via SMTP, kalender via CalDAV. Rekommenderas som första steg ("quick win"). | getting-started/quickstart.mdx; user-guide/getting-started/how-tos/configure-your-workspace.mdx | AGPL |
| HB-005 | Forma datamodellen med egna objekt och fält. | Settings → Data Model. Egna objekt och fält är obegränsade på alla planer och kräver aldrig uppgradering. | quickstart.mdx; configure-your-workspace.mdx | AGPL |
| HB-006 | Rekommendation: använd People, Companies, Opportunities som bas. | Bara dessa tre objekt visar synkade mejl och möten. Kategorisera med ett fält (t.ex. personens typ) och separata vyer hellre än ett eget objekt (som saknar mejlhistorik). | quickstart.mdx; configure-your-workspace.mdx | AGPL |
| HB-007 | Unikhet för personer och bolag. | Två personer kan inte ha samma e-postadress; två bolag kan inte ha samma domän. | quickstart.mdx; configure-your-workspace.mdx | AGPL |
| HB-008 | Avaktivera standardfält och standardobjekt; dölja fält i vyer. | Standardobjekt/-fält som inte behövs kan avaktiveras; fält kan döljas i vyer utan att raderas. | quickstart.mdx; configure-your-workspace.mdx | AGPL |
| HB-009 | Importera CSV via kommandomenyn. | Cmd/Ctrl+K → import för People, Companies, Opportunities eller valfritt eget objekt. Ladda ner exempelfil först. Högst 10 000 poster per fil (rekommendation). Dubbletter av e-post/domän ska tas bort före import. Fel markeras gult och ska rättas före import. | quickstart.mdx; configure-your-workspace.mdx | AGPL |
| HB-010 | Skapa första vyn: visa/dölja och ordna kolumner. | Options → Fields uppe till höger; visa/dölj och dra för att ordna om. | configure-your-workspace.mdx | AGPL |
| HB-011 | Filtrera och sortera i vyn; sortera genom klick på kolumnrubrik. | Filter och Sort uppe till höger; klick på kolumnnamn sorterar. | configure-your-workspace.mdx | AGPL |
| HB-012 | Byta till kanban eller grupperad lista. | Kräver att objektet har ett fält av typen Select (t.ex. Stage). | configure-your-workspace.mdx | AGPL |
| HB-013 | Spara vy som favorit. | Via rullgardinen med vyerna. Favoriter är personliga (unika per användare). | configure-your-workspace.mdx; navigate-around-twenty.mdx | AGPL |
| HB-014 | Huvudytan: visa, redigera och radera poster och skapa vyer. | Mitten av skärmen visar poster för People, Companies, Opportunities, Tasks, Notes, Dashboards, Workflows och egna objekt. | getting-started/core-concepts/layout.mdx; navigate-around-twenty.mdx | AGPL |
| HB-015 | Sidofältet: växla arbetsyta eller skapa ny. | Rullgardin överst i sidofältet listar användarens arbetsytor och låter skapa en ny. | core-concepts/layout.mdx; navigate-around-twenty.mdx | AGPL |
| HB-016 | Sök från sidofältet; snabbtangent `/`. | Sökningen går över alla objekt; nås även via kommandomenyn. | core-concepts/layout.mdx; navigate-around-twenty.mdx | AGPL |
| HB-017 | Sidofältet: Settings, favoriter, objektgenvägar, Workflows. | Settings överst till vänster; favoriter (fästa vyer) per användare; genvägar till objekt; ingång till arbetsflöden. | core-concepts/layout.mdx | AGPL |
| HB-018 | Ordna sidofältet: dra för att sortera, skapa mappar, dölja objekt. | Mappar grupperar relaterade objekt; oanvända objekt kan döljas. | core-concepts/layout.mdx | AGPL |
| HB-019 | Fälla ihop och fälla ut sidofältet. | Knapp överst i sidofältet, eller kommandona "Collapse sidebar"/"Expand sidebar" i kommandomenyn. | core-concepts/layout.mdx; navigate-around-twenty.mdx | AGPL |
| HB-020 | Kommandomenyn: skapa poster, import/export CSV, skapa vyer, se raderade poster, se kortkommandon. | Öppnas med Cmd+K/Ctrl+K eller trepunktsmenyn uppe till höger. Raderade poster nås här; systemet har både mjuk och hård radering. | core-concepts/layout.mdx; navigate-around-twenty.mdx | AGPL |
| HB-021 | Sidopanel för snabbtitt på post. | Klick på en post öppnar en panel till höger med nyckeluppgifter utan sidbyte; "Open" går till hela postsidan. | core-concepts/layout.mdx; navigate-around-twenty.mdx | AGPL |
| HB-022 | Obegränsat antal vyer per objekt; växla via rullgardin uppe till vänster. | Vytyper: tabell (gruppering, redigering i cellen, kolumnanpassning), kanban (dra-och-släpp efter Select-fält), kalender (efter datumfält). Varje vy sparar egna filter, sortering och fältsynlighet; kan delas med arbetsytan eller vara privat; kan favoritmarkeras. | core-concepts/layout.mdx; navigate-around-twenty.mdx | AGPL |
| HB-023 | Postsidor byggda av flikar och widgetar. | Widgetar kan läggas till, tas bort, ordnas om och storleksändras i ett rutnät: fält, relaterade poster, mejl, tidslinje, uppgifter, anteckningar, filer, diagram, iframes m.m. Varje objekttyp har egen layout. | core-concepts/layout.mdx | AGPL |
| HB-024 | Inställningar: översikt över vad som finns. | Konton för mejl/kalender, datamodell, API-lekplats och webhooks, behörigheter, inbjudan av medlemmar och roller, profil- och arbetsytepreferenser, fakturering och arbetsflödeskrediter, Updates → Early Access (kommande funktioner), Support (livechatt), Dokumentation. Sektioner kan vara dolda beroende på behörighet. | navigate-around-twenty.mdx | AGPL |
| HB-025 | Standardobjekt: Companies, People, Opportunities, Tasks, Notes. | Egna objekt för allt annat (projekt, ärenden, produkter, avtal). Egna objekt får samma behandling: API-ändpunkter, vyer, behörigheter, arbetsflödestriggers. | getting-started/core-concepts/data-model.mdx | AGPL |
| HB-026 | Fälttyper i kategorier. | Grundläggande: Text, Number, Boolean, Date, Currency, Rating, Select. Sammansatta: Address, Full Name, Links, Phones, Emails. Speciella: Relation, File/Attachment, JSON, Actor. "20+ fälttyper". | core-concepts/data-model.mdx; getting-started/key-features.mdx | AGPL |
| HB-027 | Automatiska systemfält på varje objekt. | `id`, `createdAt`, `updatedAt`, `createdBy`, `position`. | core-concepts/data-model.mdx | AGPL |
| HB-028 | Relationer mellan valfria objekt, även många-till-många. | Ett bolag har många personer, en affärsmöjlighet tillhör ett bolag osv. | core-concepts/data-model.mdx | AGPL |
| HB-029 | Filter med AND/OR-logik, sortering på flera fält, gruppering, sparade vyer. | Nämnt som nyckelfunktion. | key-features.mdx | AGPL |
| HB-030 | Arbetsflöden: triggers och steg utan kod. | Triggers: posthändelse (skapad, uppdaterad, raderad, upsert), manuell (en post, flera poster eller global), schema (cron), webhook (HTTP POST in). Steg: postoperationer (create/update/find/delete/upsert), skicka/skapa utkast till mejl, HTTP-anrop, kod (JavaScript), förgreningar (if/else), iterator, AI-agent, fördröjning, formulär. Variabler flödar mellan steg. | getting-started/core-concepts/workflows.mdx | AGPL |
| HB-031 | Mejl- och kalendersynk. | Google Workspace eller Microsoft 365. Mejl kopplas till matchande bolag och personer; hela trådar på tidslinjen; skicka mejl från systemet; flera brevlådor per användare; filtrera importen på datum eller avsändare. Kalenderhändelser synkas automatiskt till relevanta poster. | getting-started/core-concepts/calendar-and-email.mdx | AGPL |
| HB-032 | Integrationsvägar. | API (GraphQL och REST), webhooks vid poständringar, Zapier ("5 000+ appar"), HTTP-steg i arbetsflöden, egna appar (publika eller privata). | core-concepts/calendar-and-email.mdx | AGPL |
| HB-033 | Dashboards med widgetar. | Widget = ett diagram eller nyckeltal. Diagramtyp (stapel, linje, cirkel, tal m.fl.), datakälla (valfritt objekt), filter, aggregering (count, sum, average, min, max), gruppering (Select, datum, relation). Dashboards är på arbetsytenivå (alla ser dem); widgetar i rutnät med storleksändring. | getting-started/core-concepts/dashboards.mdx | AGPL |
| HB-034 | AI-chatt om datan. | Frågor på naturligt språk; sammanfattar och hittar poster utan att bygga filter. | getting-started/core-concepts/ai.mdx | AGPL |
| HB-035 | AI-agenter för flerstegsuppgifter. | Exempel: berika poster, skriva och skicka uppföljningsmejl, analysera pipeline, routa inkommande data. Kan kombineras med manuella godkännanden, villkor och API-anrop i arbetsflöden. Agenter ser bara det användaren/rollen får se. | core-concepts/ai.mdx | AGPL |
| HB-036 | Appar: kodade tillägg (TypeScript-paket). | Kan definiera objekt och fält, logikfunktioner (HTTP-route, cron, databashändelse), frontkomponenter (sandlådade, i sidopanel, widgetar, kommandomeny), skills och agenter, vyer och navigationsposter. Logikfunktioner körs isolerat och når data via rollbegränsad klient; frontkomponenter körs i Web Worker. Publiceras privat eller via npm/marknadsplats. | getting-started/core-concepts/apps.mdx | AGPL |
| HB-037 | Behörigheter på objekt-, fält- och postnivå; SSO (SAML/OIDC); revisionslogg. | Nämnt som nyckelfunktion ("audit logs track who did what"). | key-features.mdx | AGPL |
| HB-038 | API som anpassar sig efter datamodellen. | GraphQL och REST; automatiskt genererad dokumentation per arbetsyta ("schema-per-tenant"). | key-features.mdx; quickstart.mdx | AGPL |
| HB-039 | Import/export med fältmappning, dubblettdetektering och felhantering; export när som helst. | Nämnt som nyckelfunktion ("no lock-in"). | key-features.mdx; getting-started/introduction.mdx | AGPL |
| HB-040 | Självhosting via en Docker Compose-körning. | Full kontroll över data och uppdateringstakt. | key-features.mdx | AGPL |
| HB-041 | Implementeringspartner. | Certifierade partner kan sökas (region, språk, expertis) eller förmedlas av Twenty. | user-guide/getting-started/capabilities/implementation-services.mdx | AGPL |
| HB-042 | Support. | E-post och Discord; livechatt via Settings → Support. | create-workspace.mdx; navigate-around-twenty.mdx | AGPL |
| **Data Model (datamodell)** | | | | |
| HB-043 | Öppna datamodellen. | Settings → Data Model visar alla standard- och egna objekt (aktiva och avaktiverade); klick på objekt visar dess fält. Åtkomsten är normalt begränsad till administratörer. | user-guide/data-model/overview.mdx | AGPL |
| HB-044 | Standardobjekten People, Companies, Opportunities, Notes, Tasks. | People: kontakter med interaktionshistorik. Companies: konton (bransch, storlek, plats), kopplade till People och Opportunities. Opportunities: affärer med steg, storlek, konto, förväntat stängningsdatum; kan visas som kanban. Notes: fritext kopplad till People/Companies/Opportunities m.fl. Tasks: att-göra med förfallodatum, tilldelad och status. Standardobjekt kan användas som de är, anpassas eller avaktiveras. | data-model/capabilities/objects.mdx | AGPL |
| HB-045 | Skapa eget objekt. | Settings → Data Model → "+ New object"/"+ Add object". Namn i singular och plural (måste skilja sig), ikon, valfri beskrivning, Save. Objektet syns direkt i sidofältet och kan få poster direkt. Nya objekt startar med grundfält. | data-model/capabilities/objects.mdx; how-tos/create-custom-objects.mdx | AGPL |
| HB-046 | Hoppa över namnfältet vid skapande av objekt. | Reglaget "Skip creating a Name field" vid skapande (används för kopplingsobjekt). | how-tos/create-many-to-many-relations.mdx | AGPL |
| HB-047 | Avaktivera objekt. | Data Model → objekt → fliken Settings → Deactivate. Objektet döljs; data bevaras. | capabilities/objects.mdx; how-tos/create-custom-objects.mdx | AGPL |
| HB-048 | Återaktivera objekt. | Data Model → filtret "Deactivated" → ⋮ → Activate. Objekt och all data återställs. Avaktiverade objekt märks "Deactivated". | capabilities/objects.mdx | AGPL |
| HB-049 | Radera eget objekt permanent. | Egna objekt kan raderas (gärna avaktiveras först). Standardobjekt kan aldrig raderas, bara avaktiveras. | how-tos/data-model-faq.mdx; create-custom-objects.mdx | AGPL |
| HB-050 | Byta etikett och ikon på objekt. | Etiketten för standardobjekt kan bytas men inte API-namnet (fast för alla arbetsytor). Ikon kan bytas för standard- och egna objekt. | data-model-faq.mdx | AGPL |
| HB-051 | Obegränsat antal egna objekt och fält utan prisändring. | Gäller alla planer. | data-model-faq.mdx; overview.mdx | AGPL |
| HB-052 | Standardfält: kan inte raderas men avaktiveras; Select-alternativ kan anpassas. | Exempel: alternativen för Stage på Opportunities. | capabilities/fields.mdx | AGPL |
| HB-053 | Fälttyper i datamodellen. | Address (gata, ort, delstat, land, postnummer), Array (lista av textvärden), Boolean, Currency (belopp + valutakod), Date, Date & Time, Domain (för bolag), Email (primär + ytterligare), JSON, Links (URL med etikett, primär + sekundära), Long Text, Multi-Select, Number (heltal eller decimal), Phone (med landskod), Rating (1–5 stjärnor), Relation, Select, Text. | capabilities/fields.mdx | AGPL |
| HB-054 | Skapa eget fält. | Data Model → objekt → "+ New Field": namn, typ, valfri beskrivning, typspecifika inställningar, Save. Genväg: "+" längst till höger i tabellhuvudet → "Customize fields". | capabilities/fields.mdx; how-tos/create-custom-fields.mdx | AGPL |
| HB-055 | Nya fält syns inte automatiskt i vyer. | Visas via Options → Fields → ögonikonen; dra för att ordna. | how-tos/create-custom-fields.mdx | AGPL |
| HB-056 | Select/Multi-Select: alternativ, ordning och standardval. | "+ Add option", dra för att ordna, välj standardalternativ för nya poster. Menyn ⋮ vid Options → "Show API values" visar alternativens API-namn (används vid import). | how-tos/create-custom-fields.mdx; capabilities/fields.mdx | AGPL |
| HB-057 | Standardvaluta för Currency-fält. | Ställs in per fält (USD, EUR osv.) och förifylls i nya poster. | how-tos/create-custom-fields.mdx; capabilities/fields.mdx | AGPL |
| HB-058 | Standardlandskod för Phone-fält. | Förifylls för nya nummer. | how-tos/create-custom-fields.mdx | AGPL |
| HB-059 | Standardvärde för kryssruta (Boolean). | Markerad eller omarkerad som standard. | how-tos/create-custom-fields.mdx | AGPL |
| HB-060 | Göra fält unikt. | Reglaget "Unique" hindrar dubbletter mellan poster. Fel om dubbletter redan finns, även bland raderade poster; rensa först. | capabilities/fields.mdx; how-tos/create-custom-fields.mdx | AGPL |
| HB-061 | Avaktivera fält. | ⋮ → Deactivate. Fältet försvinner i appen och nya värden kan inte anges; data bevaras; befintliga relationer kvarstår men nya kan inte skapas; fältet nås fortfarande via API. Kan återaktiveras eller raderas permanent. | capabilities/fields.mdx; data-model-faq.mdx | AGPL |
| HB-062 | Hantera index (avancerat). | Data Model → objekt → Settings → Advanced → "Manage indexes". Index sköts annars automatiskt. | capabilities/fields.mdx | AGPL |
| HB-063 | Namnregler för fält och objekt. | Singular och plural måste skilja sig (API:t använder båda formerna för enkel- resp. massoperation). Vissa namn är reserverade för systemet (t.ex. Type, Application). | capabilities/fields.mdx; data-model-faq.mdx | AGPL |
| HB-064 | Huvudvisningsfält per objekt. | Varje objekt har ett visningsfält av texttyp som står i kolumnen längst till vänster och representerar posten i relationer (People: Name). | capabilities/fields.mdx | AGPL |
| HB-065 | Fälttyp kan inte bytas efter skapande. | Lösning: nytt fält, migrera data, avaktivera det gamla. | data-model-faq.mdx | AGPL |
| HB-066 | Obligatoriska fält stöds inte för egna fält (enligt FAQ). | Alla fält accepterar tomt; arbetsflöden kan användas för att larma. (Se HB-076 om valideringsregler, som motsäger detta.) | data-model-faq.mdx | AGPL |
| HB-067 | Formelfält och nästlade fält: "kommer H2 2026". | Under tiden: arbetsflöden räknar ut och synkar värden (t.ex. bolagets bransch på personen). | data-model-faq.mdx | AGPL |
| HB-068 | Ordna fält på objektet (postsidan). | Data Model → objekt → Layout → "Customize record page". Knappen är inaktiv tills minst en post finns. | data-model-faq.mdx | AGPL |
| HB-069 | Ordna och dölja objekt i sidofältet. | Med behörigheten Layouts: anpassningsläge för sidofältet, dra i sektionen Workspace (ordningen delas av alla). Favoriter är personliga och ordnas utan anpassningsläge. Dolda objekt visas igen från Data Model. | data-model-faq.mdx | AGPL |
| HB-070 | Relationstyper: en-till-många och många-till-en. | Ex.: ett bolag har många personer; många personer tillhör ett bolag. | capabilities/relation-fields.mdx | AGPL |
| HB-071 | Relationer till flera objekttyper (morph). | Ett fält kan peka mot flera objekttyper; t.ex. en anteckning kopplad samtidigt till en person, ett bolag och en affär. Begränsning: stöds ännu inte i CSV-import/export ("på färdplanen"). | capabilities/relation-fields.mdx; data-model-faq.mdx | AGPL |
| HB-072 | Skapa relationsfält. | Data Model → objekt (oftast "många"-sidan) → New field → Relation → målobjekt → typ → fältnamn på båda sidor → Save. Relationsnamn kan inte ändras efter skapande (påverkar API). | capabilities/relation-fields.mdx; how-tos/create-relation-fields.mdx | AGPL |
| HB-073 | Standardrelationer. | People→Companies (många-till-en), Opportunities→Companies (många-till-en), Opportunities→People (många-till-en; kontaktperson). | capabilities/relation-fields.mdx | AGPL |
| HB-074 | Avaktivera eller radera relation. | Avaktivering döljer länkarna (bevaras, kan återställas). Radering bara för egna relationer; standardrelationer kan bara avaktiveras. Poster raderas aldrig av detta. Radering av en post tar bort länken men inte de relaterade posterna. | how-tos/create-relation-fields.mdx; relation-fields.mdx; data-model-faq.mdx | AGPL |
| HB-075 | Många-till-många via kopplingsobjekt (junction). | Skapa kopplingsobjekt (utan namnfält), två en-till-många-relationer till det, aktivera "This is a relation to a Junction Object" och välj målrelation. Då visas slutposterna direkt (t.ex. personens projekt) och kopplingsobjektet döljs i UI. Reglaget visas bara på en en-till-många-relation med ett målobjekt som ser ut som ett kopplingsobjekt (alla dess icke-systemrelationer är många-till-en) och har en annan relation att peka genom. Kopplingsobjektet kan bära egna fält (roll, startdatum, timmar). Begränsningar: kan inte importeras direkt via CSV (importera till kopplingsobjektet); begränsade filtermöjligheter. FAQ säger samtidigt "kommer H2 2026". | capabilities/relation-fields.mdx; how-tos/create-many-to-many-relations.mdx; data-model-faq.mdx | AGPL |
| HB-076 | Självrefererande relationer och flera relationer mellan samma objekt. | Ex.: moder-/dotterbolag (Companies→Companies); "Primary Contact" och "Billing Contact" mot People. Cirkulära relationer avråds. För många relationer kan göra arbetsytan långsam. | data-model-faq.mdx; relation-fields.mdx | AGPL |
| HB-077 | Valideringsregler per objekt. | Kräver Organization-planen och behörighet att redigera datamodellen. Data Model → objekt → Settings → Validation rules → Add rule: namn, valfri beskrivning, villkor (det som ska vara sant för att spara), felmeddelande och var det visas ("Show on": ett fält eller hela posten). Nya regler är inaktiva tills "Activate"; kräver namn, giltigt villkor och felmeddelande. | data-model/capabilities/validation-rules.mdx | Enterprise (stickprov: serverns hanterare för valideringsregler bär Enterprise-huvud; handboken: Organization-plan) |
| HB-078 | Förhandsgranska valideringsregel. | Använder upp till tre senaste poster; pilar bläddrar. Status: Valid, Blocked (visar felmeddelandet), Error (villkoret kunde inte beräknas). Ändrar inga poster; kräver att objektet har poster. | validation-rules.mdx | AGPL |
| HB-079 | Villkorsspråk i valideringsregler. | Fältnamn (API-namn, inte etiketter); jämförelser (==, !=, <, <=, >, >=); and/or/not; aritmetik; "in"-lista; true/false; `now` (sparögonblicket); text i enkla/dubbla citattecken; parenteser. `||` sammanfogar text (som concat) och ska inte användas som logiskt eller. | validation-rules.mdx | AGPL |
| HB-080 | Funktioner för tomma värden. | isEmpty (saknat, tom text, tom lista, tomt sammansatt fält), isDefined (tom text räknas som definierad), isNonEmptyString, includes (lista eller delsträng, skiftlägeskänslig), arrayLength. Obligatoriskt fält = `not isEmpty(fält)`, fungerar även för sammansatta fält. | validation-rules.mdx | AGPL |
| HB-081 | Datumfunktioner. | dateDiff (hela enheter; minuter/timmar som förfluten tid, dagar–år som kalenderdagar/-månader i UTC; negativ om "till" är tidigare), dateAdd (månad på den 31:a hamnar på månadens sista dag), dateTrunc (veckor börjar måndag), datePart (YEAR, QUARTER, MONTH, WEEK, DAY, DAY_OF_WEEK med 1 = måndag, HOUR, MINUTE), isInRelativeDateRange (PAST/NEXT/THIS; enheter DAY–YEAR; PAST och NEXT utesluter innevarande period). Allt i UTC. Enheter: MINUTE, HOUR, DAY, WEEK, MONTH, QUARTER, YEAR. daysSince är borttagen. Datum utan tid jämförs som UTC-kalenderdag; datum-tider som ögonblick. | validation-rules.mdx | AGPL |
| HB-082 | Beräkningsfunktioner. | if, coalesce, concat (hoppar över osatta), lower/upper, min/max (ignorerar icke-tal), roundTo. | validation-rules.mdx | AGPL |
| HB-083 | Läsa delar av sammansatta fält och relaterade fält. | Punktnotation (namnets förnamn, beloppets mikrobelopp); genom många-till-en-relation (personens bolags namn). Valutabelopp lagras i mikroenheter (1 enhet = 1 000 000). Select jämförs mot lagrat värde, inte etiketten. | validation-rules.mdx | AGPL |
| HB-084 | När regler kontrolleras. | Vid skapa och uppdatera, även via API, import och arbetsflöden. Posten måste klara alla aktiva regler. Aktivering ändrar inte befintliga poster (rättas vid nästa sparning). Regel som läser relaterad post kontrolleras bara när den egna posten sparas. | validation-rules.mdx | AGPL |
| HB-085 | Redigera, stänga av, radera valideringsregel. | Edit (Save; inaktiv regel: Activate). Danger zone: Disable/Enable (behåller konfigurationen), Delete (permanent, efter bekräftelse; poster påverkas inte). Avaktiveras eller raderas ett fält som villkoret läser avaktiveras regeln. Regler kan också definieras i appar. | validation-rules.mdx | AGPL |
| HB-086 | Antal poster och fält. | Ingen hård gräns för antal poster (stora mängder kan göra vyer långsamma). Högst 1 600 fält per objekt (Postgres-gräns, inklusive raderade fält); att nå gränsen åtgärdas inte (fair use). | data-model-faq.mdx | AGPL |
| HB-087 | Import till egna objekt; ingen export av datamodellens konfiguration. | CSV-import fungerar för alla objekt med fältmappning. Datamodellen kan inte exporteras inbyggt (kontakta support för flytt mellan arbetsytor). | data-model-faq.mdx | AGPL |
| HB-088 | Råd för modellering. | Fält för egenskaper/kategorier/status; objekt när något har egen livscykel, egna relationer eller ett okänt antal per post (inte "Produkt 1, Produkt 2"). Fält som inte gäller alla poster är okej och kan döljas i vyer. Mejl/kalendersynk bara för People, Companies, Opportunities. | data-model/overview.mdx | AGPL |
| **Data Migration (import och export)** | | | | |
| HB-089 | Två importvägar: fil och API. | Fil: 10 000 poster per fil. API: obegränsat. Rekommendation: under 10 000 en fil; 10 000–50 000 delade filer; över 50 000, återkommande import, realtidssynk och integrationer via API. | data-migration/overview.mdx; how-tos/import-data-via-api.mdx; how-tos/migrating-from-other-crms.mdx | AGPL |
| HB-090 | Starta filimport. | Från objektets vy: ⋮ uppe till höger → "Import records"; eller kommandomenyn → skriv "import" → Import records → välj objekt. Fungerar för alla objekt, även egna. | data-migration/overview.mdx; how-tos/import-companies-via-csv.mdx | AGPL |
| HB-091 | Filformat. | CSV (rekommenderas), XLSX, XLS. UTF-8 rekommenderas. Första raden = kolumnrubriker. En objekttyp per fil. CSV-avgränsare komma eller semikolon, dubbla citattecken som textavgränsare, CRLF eller LF. Tomma celler, inte "NULL"/"N/A". Excel: bara värden (inga formler), inga tomma slutrader, inga sammanslagna celler, bara första bladet. | capabilities/file-formats.mdx; how-tos/prepare-your-csv-files.mdx | AGPL |
| HB-092 | Gräns 10 000 poster per fil. | Fler blockerar uppladdningen helt med felet att för många poster (högst 10 000). Dela filen eller använd API. | file-formats.mdx; how-tos/fix-import-errors.mdx | AGPL |
| HB-093 | Ladda ner exempelfil. | "Download sample file" i importdialogen visar exakta kolumnnamn och syntax. Alternativ: exportera några befintliga poster (kolumnnamnen mappas då automatiskt). | how-tos/prepare-your-csv-files.mdx; capabilities/field-mapping.mdx | AGPL |
| HB-094 | Automatisk kolumnmappning. | Matchar på rubriknamn (exakt eller likt), datatyp (datum, tal, e-post) och vanliga mönster. | capabilities/field-mapping.mdx | AGPL |
| HB-095 | Manuell mappning eller "Do not map". | Rullgardin per kolumn; "Do not map" hoppar över kolumnen. Importen skapar poster, aldrig fält: fält måste finnas i datamodellen före import (annars "fältet känns inte igen"). | field-mapping.mdx; fix-import-errors.mdx | AGPL |
| HB-096 | Mappa Select-värden mot alternativ. | Eget steg: filens värden visas bredvid befintliga alternativ och matchas; nya alternativ kan skapas i steget (enligt import-guiderna). Fältmappningsguiden säger samtidigt att nya alternativ inte skapas automatiskt och måste läggas till i datamodellen först. Värden anges som API-namn, inte etiketter. | how-tos/import-companies-via-csv.mdx; import-contacts-via-csv.mdx; field-mapping.mdx | AGPL |
| HB-097 | Format per fälttyp vid import. | Address: delkolumner Address 1, Address 2, City, State, Country, Post Code (några kan vara tomma). Array: JSON-lista av strängar. Boolean: TRUE/FALSE versalt (inte true, yes, 1). Currency: belopp och valutakod, båda måste fyllas; punkt som decimal. Date: ÅÅÅÅ-MM-DD rekommenderas; även MM/DD/ÅÅÅÅ, DD/MM/ÅÅÅÅ och ISO 8601 (en guide säger att bara ÅÅÅÅ-MM-DD fungerar). Number: bara siffror, punkt som decimal, inga tusentalsavgränsare. Phone: nummer, landskod (t.ex. US) och riktnummer (+1). Rating: RATING_1–RATING_5. Text: inledande/avslutande blanksteg trimmas. JSON: giltig JSON. Multi-Select: JSON-lista av API-namn. | field-mapping.mdx; prepare-your-csv-files.mdx; fix-import-errors.mdx | AGPL |
| HB-098 | Domänformat. | Rekommenderat https://domän.se (samma format som bolag skapade av mejl-/kalendersynk; annat format kan ge dubbletter). Etikett "domän.se" och URL "https://domän.se". Domän måste vara unik i bolagsobjektet och i filen. | field-mapping.mdx; import-companies-via-csv.mdx; fix-import-errors.mdx | AGPL |
| HB-099 | E-postformat. | Giltig adress; unik i People och i filen. Primär e-post och "Additional Emails" som JSON-lista. | field-mapping.mdx; import-contacts-via-csv.mdx | AGPL |
| HB-100 | Länkformat. | Etikett och URL (full URL); sekundära länkar som JSON-lista av objekt med url och label. | field-mapping.mdx; prepare-your-csv-files.mdx | AGPL |
| HB-101 | Importera id. | Valfritt; måste vara UUID. Sätter id för nya poster eller matchar befintliga för uppdatering (mappa då helst inga andra unika fält). | field-mapping.mdx; prepare-your-csv-files.mdx | AGPL |
| HB-102 | Multi-Select vid import skriver över, slår inte ihop. | Befintliga val ersätts helt av filens lista. | field-mapping.mdx; update-existing-records-via-import.mdx | AGPL |
| HB-103 | Validering före import med gulmarkering. | Efter mappning ("Next Steps") granskas varje rad; fel markeras gult; hovra över cell för felmeddelande. Rätta direkt i cellen eller ta bort raden (X). Inget skrivs förrän "Confirm". | capabilities/error-handling.mdx; fix-import-errors.mdx | AGPL |
| HB-104 | Feltyper vid import. | Dubblettvärde (finns i systemet eller två gånger i filen); ogiltigt format ("fält är inte en giltig typ"); obligatoriskt fält tomt; relation hittades inte (upptäcks först när importen körs, importen avbryts); fil för stor (uppladdning blockeras); fält okänt; tom användarrelation. | error-handling.mdx; fix-import-errors.mdx | AGPL |
| HB-105 | Relation som inte finns stoppar importen under körning. | Felet nämner objektet och villkoret (id = …). Åtgärd: avbryt, importera föräldern först, rätta värdet eller töm cellen. | fix-import-errors.mdx; capabilities/import-relations.mdx | AGPL |
| HB-106 | Tom användarrelation (Owner, Assignee). | Användaren har inte accepterat inbjudan, id från gammalt system används, eller fel e-post. Referera medlemmar med e-post (inte namn); bjud in och vänta på accept före import. | fix-import-errors.mdx; migrating-from-other-crms.mdx | AGPL |
| HB-107 | Standardunika fält. | People: id, email. Companies: id, domain. Egna objekt: bara id som standard. Fler unika fält kan sättas (externa id, kundnummer, LinkedIn, telefon). Fältnamnet id är reserverat; använd t.ex. externalId. | capabilities/uniqueness-constraints.mdx | AGPL |
| HB-108 | Import skapar eller uppdaterar (upsert på unikt fält). | Unikt värde som saknas → ny post; som matchar → posten uppdateras; inget unikt värde i filen → ny post med genererat id. Matcha helst på ett enda unikt fält. Byte av e-post med behållet id (eller tvärtom) uppdaterar det unika fältet. | uniqueness-constraints.mdx; fix-import-errors.mdx; update-existing-records-via-import.mdx | AGPL |
| HB-109 | Mjukraderade poster räknas i unikhet. | Poster under kommandomenyn → "See deleted records" räknas; import med samma unika värde återställer den raderade posten med nya data. "Hittades inte"-fel kan bero på att föräldern är mjukraderad. | uniqueness-constraints.mdx; import-relations.mdx; data-migration/overview.mdx | AGPL |
| HB-110 | Dubbletter inom filen markeras före import. | Gula rader; redigera eller ta bort. | uniqueness-constraints.mdx | AGPL |
| HB-111 | Importera relationer. | Stöds för en-till-många mot en objekttyp per sida. Lägg en kolumn på "många"-sidan med förälderns unika värde (id, domän för bolag, e-post för personer och medlemmar, valfritt unikt fält för andra objekt) och mappa den mot relationsfältet. Exakt matchning, skiftlägeskänslig. Mappa bara en identifierare (inte både id och domän). Relationsfältet måste finnas. | capabilities/import-relations.mdx; how-tos/import-relations-between-objects-via-csv.mdx | AGPL |
| HB-112 | Importordning. | Companies → People → Opportunities → Tasks/Notes → egna objekt efter beroenden. Föräldern måste finnas. | import-relations.mdx; data-migration/overview.mdx | AGPL |
| HB-113 | Morph-relationer och många-till-många stöds inte i import/export. | Relationer mot flera objekttyper: importeras inte; exportkolumnerna lämnas tomma ("på färdplanen"). Många-till-många: "planerat H2 2026" respektive "H1 2026" på olika sidor; importera till kopplingsobjektet. | import-relations.mdx; import-relations-between-objects-via-csv.mdx | AGPL |
| HB-114 | Massuppdatering via import. | Exportera, ändra, importera med oförändrat unikt fält. Fält som inte finns i filen lämnas orörda; tom cell tömmer fältet. Relationer kan uppdateras. Uppdatering och nya poster kan blandas i samma fil. Granskningssteget visar hur många poster som uppdateras respektive skapas. Ingen ångra-funktion. | how-tos/update-existing-records-via-import.mdx | AGPL |
| HB-115 | Exportera vy. | ⋮ uppe till höger i tabellen → "Export view". Bara synliga kolumner och poster som matchar vyns filter; följer sorteringen. Högst 20 000 poster per export (dela med filter eller använd API). Kräver behörigheten "Export CSV". | how-tos/export-your-data.mdx; data-migration/overview.mdx | AGPL |
| HB-116 | Vad som ingår i export. | Med: synliga kolumner, filtrerade poster, egna fält, post-id, relations-id (bara på "många"-sidan, t.ex. personens bolags-id). Utan: dolda kolumner, filtrerade bort poster, bilagor, bilder. Ingen schemalagd export i UI. Format enligt exportguiden CSV; enligt export-FAQ Excel (oklart). | export-your-data.mdx; how-tos/export-faq.mdx | AGPL |
| HB-117 | Behörigheter för import och export. | "Import CSV" respektive "Export CSV". | data-migration/overview.mdx | AGPL |
| HB-118 | Vad som inte kan exporteras/migreras. | Dashboards, arbetsflöden, behörigheter och alla inställningar (API-nycklar, webhooks, revisionslogg, användarinställningar) flyttas för hand; revisionsloggen kan inte flyttas. Arbetsflödesversioner och -körningar går förlorade. App-skapade objekt flyttas genom att installera appen. Mejl- och kalenderobjekt synkas om vid ny anslutning (exportera dem för avslutade medarbetares konton). Created by, Updated by och tidslinjeaktiviteter skrivs över vid import. | how-tos/export-faq.mdx | AGPL |
| HB-119 | API-gränser enligt handboken. | Import-guiden: 100 anrop/minut, 60 poster per batchanrop, cirka 6 000 poster/minut (100 000 poster ≈ 17 min); minst 600 ms mellan anrop vid långa körningar, exponentiell backoff, bevaka 429. Export-FAQ: 50 anrop/min på Pro, 100 på Organization, upp till 200 poster per anrop (motstridigt). | how-tos/import-data-via-api.mdx; how-tos/export-faq.mdx | AGPL |
| HB-120 | API-nyckel för import. | Settings → Developers → "+ Create API key", namnge, kopiera direkt (visas bara en gång). | import-data-via-api.mdx | AGPL |
| HB-121 | API: GraphQL och REST med CRUD och batch. | Batch-upsert i GraphQL; uppdatera via mutation eller PUT/PATCH; radera via mutation eller DELETE. Inget officiellt Python/Node-SDK enligt importguiden. Objekt och fält kan bläddras under Settings → Developers → API (Metadata API). | import-data-via-api.mdx | AGPL |
| HB-122 | Migrering från annat CRM. | Rensa (inaktiva >2 år, dubbletter, testdata), mappa (Account→Company, Contact→People, Deal→Opportunity, Activity→Task/Note), skapa fält, bjud in medlemmar och vänta på accept, exportera, städa format, importera i ordning, återskapa vyer, arbetsflöden och roller, varje användare ansluter sitt konto. Bilagor följer inte med i filexport. | how-tos/migrating-from-other-crms.mdx | AGPL |
| HB-123 | Migrering från självhostat till moln. | Ingen officiell procedur. Skapa molnarbetsyta, återskapa datamodell, bjud in, exportera, ersätt användar-id med e-post, importera i ordning, återskapa vyer/arbetsflöden/roller, anslut mejl, nya API-nycklar. | how-tos/migrating-from-self-hosted-to-cloud.mdx; export-faq.mdx | AGPL |
| **Calendar & Emails (kalender och mejl)** | | | | |
| HB-124 | Ansluta Google-konto (Gmail + Google Calendar). | Settings → Accounts → Add account → Continue with Google → godkänn åtkomst → mejlinställningar (synlighet, autoskapande) → Next → kalenderinställningar → Add Account. Synken startar automatiskt. | calendar-emails/overview.mdx | AGPL |
| HB-125 | Ansluta Microsoft-konto (Outlook + kalender). | Samma flöde via Continue with Microsoft. | calendar-emails/overview.mdx | AGPL |
| HB-126 | Ansluta andra leverantörer via IMAP/SMTP/CalDAV. | IMAP för inkommande, SMTP för utgående, CalDAV för kalender; anslutningen testas. | calendar-emails/overview.mdx; how-tos/connect-several-mailboxes-per-user.mdx | AGPL |
| HB-127 | Självhosting: skydd mot anslutningar till interna adresser. | Som standard nekas utgående anslutningar till privata/interna IP (SSRF-skydd), även för mejl, kalender, SSO, HTTP-steg och webhooks. En miljövariabel listar tillåtna interna värdnamn/IP (bara värdnamn, inga jokertecken; `*` stänger av skyddet). Molnmetadata-adresser nås aldrig. En äldre variabel som stänger av säkert läge åsidosätter listan. | calendar-emails/overview.mdx | AGPL |
| HB-128 | Flera brevlådor per användare. | Obegränsat antal konton per användare; egna inställningar per brevlåda (synlighet, autoskapande, mappar); avsändarkonto väljs i Från-fältet när man skriver mejl. Bara riktiga brevlådor kan anslutas, inte alias som vidarebefordrar (de synkas via huvudbrevlådan). | overview.mdx; how-tos/connect-several-mailboxes-per-user.mdx; capabilities/mailbox.mdx | AGPL |
| HB-129 | Synlighet för mejl per brevlåda. | Tre nivåer: bara metadata (avsändare, mottagare, datum, tid); ämne och metadata; allt innehåll inklusive bilagor. | overview.mdx; capabilities/mailbox.mdx | AGPL |
| HB-130 | Autoskapande av kontakter från mejl. | Avaktiverat; för skickade och mottagna; bara skickade. Avaktiverat: mejl synkas ändå till befintliga kontakter. Skapade kontakter kopplas till bolag via e-postdomänen; saknas bolaget skapas det. | overview.mdx; how-tos/limit-emails-imported.mdx | AGPL |
| HB-131 | Synka interna mejl (samma domän). | Av som standard; mejl där alla deltagare har samma domän synkas inte. Kan slås på för hela arbetsytan med "Sync Internal Emails" (anges under Settings → Communication på en sida och Settings → General → Security på andra). En felsökningssida säger att interna mejl "aldrig" synkas. | overview.mdx; capabilities/mailbox.mdx; how-tos/limit-emails-imported.mdx; how-tos/i-dont-see-emails-on-records.mdx | AGPL |
| HB-132 | Välja mappar som synkas (Message Folder). | Settings → Accounts → kontot: inkludera Inbox, Sent, Archive, egna mappar; uteslut Spam, Trash, personliga. Ingen CC-adress för selektiv synk finns. | overview.mdx; how-tos/limit-emails-imported.mdx | AGPL |
| HB-133 | Det som aldrig synkas. | Gruppmejl och distributionslistor; uteslutna mappar; systemmappar (skräp/papperskorg) normalt. Bilagor synkas "H1 2026" (kommer). | capabilities/mailbox.mdx; limit-emails-imported.mdx; overview.mdx | AGPL |
| HB-134 | Synlighet för kalenderhändelser. | Allt (hela händelsen delas med teamet) eller metadata (bara datum och deltagare). Kalender följer samma synlighetsprincip som mejl. | overview.mdx; capabilities/calendar.mdx | AGPL |
| HB-135 | Autoskapande av kontakter från möten. | Ja (skapa kontakter för deltagare som saknas) eller Nej (bara koppla till befintliga). Bolag skapas/kopplas via domän. | overview.mdx | AGPL |
| HB-136 | Synkintervall och initial import. | Var 5:e minut efter första importen. Kalender klar på minuter; mejl cirka 400 meddelanden/minut (Gmail-API:ts gräns): 1 000 ≈ 2,5 min, 10 000 ≈ 25 min, 50 000 ≈ 2 h. Kontakter från kalendern kan dyka upp före mejlkontakter. "Nya mejl syns direkt" sägs på en sida. | overview.mdx; capabilities/mailbox.mdx; how-tos/i-dont-see-emails-on-records.mdx | AGPL |
| HB-137 | Fliken Messages (mejl) på poster. | Finns på People (mejl med kontakten), Companies (alla med bolagets domän/anställda) och Opportunities (mejl kopplade till affärens bolag; trådar från personerna på affären visas ännu inte). Klick öppnar hela tråden med deltagare och tidsstämplar. Mejl från flera adresser hamnar på samma kontakt. | capabilities/mailbox.mdx; how-tos/can-i-track-email-activity-on-all-objects.mdx | AGPL |
| HB-138 | Mejlaktivitet på egna objekt stöds inte. | Bara People, Companies, Opportunities. Matchning: e-postadress → person, domän → bolag, bolagsrelation → affär. Lösning: relation till person/bolag. Utvidgning "övervägs". | how-tos/can-i-track-email-activity-on-all-objects.mdx | AGPL |
| HB-139 | Fliken Calendar på poster. | Bredvid Messages på People, Companies, Opportunities; visar möteshistorik med deltagare, tider och ämne. Synkas: möten med externa deltagare, kopplade via deltagarnas e-post. Synkas inte: interna möten (bara kolleger) och händelser märkta privata. | capabilities/calendar.mdx | AGPL |
| HB-140 | Skapa kalenderhändelse från en post. | Kräver ansluten Google-, Microsoft- eller CalDAV-kalender. På person/bolag/affär: åtgärden "Create calendar event" → välj kalenderkonto → gäster, titel, plats, beskrivning → start/slut eller heldag, tidszon → reglage för inbjudningar och videomöte → Create event. Händelsen skapas i den anslutna kalendern och posten kopplas automatiskt (syns på tidslinjen). Åtgärden döljs utan behörigheten "Create calendar event" och är inaktiv om posten saknar e-postadress. | how-tos/can-i-book-meetings-from-twenty.mdx | AGPL |
| HB-141 | Skapa kalenderhändelse från arbetsflöde. | Steget "Create Calendar Event" med valfri trigger. | can-i-book-meetings-from-twenty.mdx | AGPL |
| HB-142 | Skriva och skicka mejl från systemet. | Kommandomenyn → "Compose email": mottagare, ämne, brödtext, bilagor, Send. Svara i en tråd på postsidan via Reply. Kräver anslutet konto som får skicka. Sidan nämner också "svara via omdirigering till brevlådan" och att inbyggd mejlskrivning är "på färdplanen" (motstridigt). Massutskick från egen brevlåda avråds (domänrykte). | how-tos/can-i-send-emails-from-twenty.mdx | AGPL |
| HB-143 | Felsökning: mejl syns inte på poster. | Initial synk pågår; kontakten finns inte (slå på autoskapande eller skapa personen); interna mejl; grupplista; mappen ej vald; fel e-post på personen. Sista utväg: koppla från och anslut brevlådan igen. | how-tos/i-dont-see-emails-on-records.mdx | AGPL |
| HB-144 | E-postkanal (delad inkorg) i tre steg. | Kräver behörigheten Workspace settings. Steg 1 Ta emot: vidarebefordringsregel hos mejlleverantören, inga DNS-ändringar. Steg 2 Svara: fem autentiseringsposter i DNS. Steg 3 Kampanjer: två avregistreringsposter i DNS (bygger på steg 2). Steg 1 är oberoende; kampanjer kräver inte vidarebefordran. | capabilities/email-channels.mdx | AGPL |
| HB-145 | Skapa e-postkanal. | Settings → Communication → "Add email channel": delad adress (Source Email Address) och visningsnamn → Save. En privat vidarebefordringsadress på en inkommande domän visas och kan kopieras. Varje kanal har egen adress; två brevlådor får aldrig peka på samma. Testmejl syns inom ett par minuter. Gäller bara ny post (inte historik). | email-channels.mdx; how-tos/forward-a-shared-inbox-from-any-mail-provider.mdx; forward-…-google-workspace.mdx | AGPL |
| HB-146 | Krav på vidarebefordringen. | Måste vara serverns automatiska vidarebefordran/omdirigering som behåller ursprunglig avsändare (From-huvudet avgör vem meddelandet kopplas till). Vidarebefordran som bilaga eller regler som skapar nytt meddelande gör att allt ser ut att komma från en själv och inget matchas. Undvik regler som tar bort bilagor eller gör om till ren text. Välj "behåll kopia". Fel tecken i adressen = posten försvinner tyst. | forward-a-shared-inbox-from-any-mail-provider.mdx | AGPL |
| HB-147 | Vidarebefordran från Google Workspace. | Lägg till kanalens adress som medlem i en Google-grupp: grupp måste tillåta externa medlemmar och "Anyone on the web" får posta (båda låsta som standard; admin låser upp), prenumeration "Each email", lägg till direkt. Säkerhetsmärkta grupper fungerar inte (ny grupp krävs). | how-tos/forward-a-shared-inbox-from-google-workspace.mdx | AGPL |
| HB-148 | Vidarebefordran från Microsoft 365. | Delad brevlåda i Exchange admin center → Email forwarding → till extern adress, leverera till både vidarebefordran och brevlåda. Extern vidarebefordran måste tillåtas i Defender (utgående skräppostpolicy, helst avgränsad till de delade brevlådorna), annars studsar posten med felkod 5.7.520. Ändringar kan ta 5 minuter. | how-tos/forward-a-shared-inbox-from-microsoft-365.mdx | AGPL |
| HB-149 | Vidarebefordran från andra leverantörer. | Lista med länkar till leverantörsguider (Amazon SES/WorkMail, Bluehost, cPanel, DreamHost, Exchange, GoDaddy, iCloud, Namecheap, OVHcloud, Rackspace, Zoho). Felsökning: studs om extern vidarebefordran förbjuds; post försvinner ur inkorgen om regeln flyttar i stället för kopierar. | forward-a-shared-inbox-from-any-mail-provider.mdx | AGPL |
| HB-150 | Svara från delad adress (avsändardomän). | Kanal → "Sending domain": tre CNAME för DKIM, MX och TXT på en bounce-underdomän, ev. DMARC. "Check verification" → Domain authentication = Verified, oftast inom en timme, högst 48 h. Mottagning och sändning är separata. | email-channels.mdx | AGPL |
| HB-151 | Avregistreringslänk på egen domän (för kampanjer). | Två CNAME (en på links-underdomänen, en för certifikatutmaning). Verified oftast inom en timme (certifikat utfärdas). Utan dem står raden Pending, vilket bara blockerar kampanjer. Cloudflare: "DNS only". Kampanj skickas bara när båda raderna är Verified. | email-channels.mdx | AGPL |
| HB-152 | En domän kan bara verifieras i en arbetsyta. | Systemet säger till om domänen används någon annanstans. | email-channels.mdx | AGPL |
| **Email Campaigns (e-postkampanjer)** | | | | |
| HB-153 | Kampanjer är betafunktion. | Måste slås på per arbetsyta via chatt med Twenty ("Beta"). Hittas inte Campaigns är funktionen inte påslagen. | email-campaigns/overview.mdx; how-tos/send-your-first-campaign.mdx | AGPL |
| HB-154 | En-till-många-kampanj. | Ett mejl (ett ämne, en brödtext) per lista, med variabler per mottagare; inte ett utkast per lead. | overview.mdx; how-tos/create-a-campaign-with-ai.mdx | AGPL |
| HB-155 | Förutsättningar för kampanj. | Verifierad avsändardomän; behörigheten Workspace settings för att testa, schemalägga och skicka; e-postkrediter i molnet (varje skickat mejl drar krediter). | send-your-first-campaign.mdx | AGPL |
| HB-156 | Listor och listmedlemmar (Lists, List Members). | Listor är poster. Kommandomenyn → "Go to Lists" → New List → namn → fältet Members lägger till personer. En person kan läggas i lista från sin post via fältet Lists. Arbetsflöden kan skapa och uppdatera listor och medlemmar. | send-your-first-campaign.mdx; overview.mdx; create-a-campaign-with-ai.mdx | AGPL |
| HB-157 | Mottagarregler. | Skickas till personens primära e-post. Hoppar över personer utan adress och de som avregistrerat sig, studsat eller anmält spam. Varje person får ett mejl även om hen står två gånger i listan. | send-your-first-campaign.mdx; how-tos/email-campaign-best-practices.mdx | AGPL |
| HB-158 | Skapa kampanj. | Kommandomenyn → "Compose Campaign", eller Campaigns → New Campaign. Internt namn. Fliken Email: From (väljs bland e-postkanaler), To (lista; ny lista kan skapas här), Unsubscribe topic (valfritt, syns först när ett ämne finns), Subject. | send-your-first-campaign.mdx | AGPL |
| HB-159 | Mejlredigerare. | Sparar utkastet löpande. `/` för kommandon, vänsterlist med Text, Image, Blocks och Variables. Block: Section, 2 Columns, 3 Columns, Button, Divider, Image, HTML (egen HTML). | send-your-first-campaign.mdx | AGPL |
| HB-160 | Variabler (personalisering). | Dubbla klammerparenteser: förnamn, efternamn, fullständigt namn, titel; dessutom text-, tal-, datum- och Select-fält på People inklusive egna. Fungerar i ämne, brödtext och länkadresser. Saknat värde blir tomt. En variabel som inte motsvarar ett fält på People blockerar utskicket (välj från Variables i stället för att skriva). | send-your-first-campaign.mdx | AGPL |
| HB-161 | Postadress läggs inte till automatiskt. | Ska skrivas in i mejlets fot (krav i USA, CAN-SPAM). | send-your-first-campaign.mdx; email-campaign-best-practices.mdx | AGPL |
| HB-162 | Testmejl. | "Test" eller kommandot "Send Test Email": mottagare → skicka. Variabler är tomma i test. Högst tre testmejl per dag och arbetsyta. | send-your-first-campaign.mdx | AGPL |
| HB-163 | Skicka nu eller schemalägg. | Send / "Send Campaign": sammanfattning med antal mottagare och skäl till att andra hoppas över. Delivery: Send now (kan inte ångras) eller Send later (datum/tid i framtiden). Knappen inaktiv utan From, lista, ämne, brödtext eller minst en möjlig mottagare. | send-your-first-campaign.mdx | AGPL |
| HB-164 | Schemalägg om. | Send igen → ny tid → "Reschedule campaign". Mottagare räknas om vid utskick. Vid utskickstid kontrolleras kampanjen igen; om ingen kan ta emot eller domänen inte längre är verifierad går den tillbaka till Draft. | send-your-first-campaign.mdx | AGPL |
| HB-165 | Dagsgräns för kampanjmejl. | Högst 1 000 kampanjmejl per dag och arbetsyta; höjning kan begäras via chatt (prövas fall för fall). | send-your-first-campaign.mdx; overview.mdx; email-campaign-best-practices.mdx | AGPL |
| HB-166 | Kampanjstatus. | Draft (redigerbar), Scheduled, Sending, Sent (alla lämnade till leverantören), Sent with errors (t.ex. slut på krediter), Canceled. | send-your-first-campaign.mdx | AGPL |
| HB-167 | Resultat efter utskick. | Fliken Home: skickade, levererade, studsade, klagomål, misslyckade, överhoppade. Recipients-listan visar mottagarna. | send-your-first-campaign.mdx; overview.mdx | AGPL |
| HB-168 | Duplicera kampanj. | Kopierar mejl, lista och inställningar till nytt utkast. | send-your-first-campaign.mdx | AGPL |
| HB-169 | Avbryta kampanj. | Cancel eller kommandot "Cancel Campaign". Schemalagd: "Unschedule Campaign", tillbaka till utkast. Pågående: väntande mejl stoppas; redan skickade kan inte återkallas. | send-your-first-campaign.mdx | AGPL |
| HB-170 | Felmeddelanden vid utskick. | From saknar adresser (ingen e-postkanal); ingen verifierad avsändardomän matchar From; kampanjen kan inte skickas (saknad From/lista/ämne eller ogiltig variabel). | send-your-first-campaign.mdx | AGPL |
| HB-171 | Avsändardomän: skapa adress. | Via e-postkanal (Settings → Communication → Add email channel); delen efter @ blir avsändardomän. Sektionen "Sending domain" listar DNS-poster med kopieringsknapp. | how-tos/set-up-a-sending-domain.mdx | AGPL |
| HB-172 | DNS-postgrupper. | Domain authentication (tre DKIM-CNAME, MX + TXT på bounce-värd; DKIM och SPF; studsrapporter), DMARC policy (en TXT; föreslås bara om ingen DMARC finns; kontrolleras aldrig och står alltid "Not set"), Unsubscribe link (två CNAME; avregistreringssida och spårade länkar på egen domän; krävs för kampanjer). Egen värdnamn påverkar inte vanlig mejl; två DMARC-poster ska undvikas. | set-up-a-sending-domain.mdx | AGPL |
| HB-173 | Verifiering av domän. | Kontrolleras automatiskt varje timme; "Check verification" kontrollerar direkt. Pending → Verified, normalt inom en timme, högst 48 h. Failed: kontrollen stoppas tills man rättat och klickat igen. Temporary Failure: DNS svarade inte; fortsätter varje timme. | set-up-a-sending-domain.mdx | AGPL |
| HB-174 | DNS-leverantörsguide. | Tabell med råd per leverantör (bl.a. bara värddelen i namnfältet, MX-prioritet 10 i eget fält, Cloudflare "DNS only", Gandi punkt i slutet, Route 53 citattecken). | set-up-a-sending-domain.mdx | AGPL |
| HB-175 | Avregistrering i varje kampanj. | Fotrad med avregistreringslänk plus envägs-avregistreringshuvuden (Gmail/Yahoo). Sidan ligger på egen domän. Utan publika ämnen: en Unsubscribe-knapp; med publika ämnen: kryssruta per ämne, Update eller Unsubscribe all. Gäller direkt. E-postappens egen knapp avregistrerar från allt. | how-tos/manage-unsubscribes-and-topics.mdx | AGPL |
| HB-176 | Avregistreringsämnen (topics). | Settings → Communication → Unsubscribe → Manage unsubscribe → Topics → Add topic: namn, beskrivning (för teamet), "Listed on the unsubscribe page". Publikt = syns på sidan; privat = syns inte men respekterar avregistreringar. Nya ämnen är privata. Kampanj med ämne hoppar över de som lämnat ämnet eller allt. | manage-unsubscribes-and-topics.mdx | AGPL |
| HB-177 | Lista över avregistrerade. | Fliken Unsubscribers: adress, omfattning (alla eller ämne), orsak (Unsubscribed, Bounce, Complaint), datum; sök och filter. Studsar och klagomål är permanenta och kan inte ångras. Den som vill tillbaka kan via länk i ett mejl från senaste 30 dagarna välja ämnen igen. | manage-unsubscribes-and-topics.mdx | AGPL |
| HB-178 | Förhandsvisa avregistreringssidan. | Fliken "Unsubscribe page" visar sidan med nuvarande publika ämnen; inget sparas. | manage-unsubscribes-and-topics.mdx | AGPL |
| HB-179 | AI för kampanjer. | Öppna AI med `@` eller kommandomenyn → Ask AI. Kan hitta personer, bygga lista, skriva utkast (namn, ämne, brödtext, knapp, variabler) och förbättra det. Kan inte skicka. Redigerar bara kampanjer i Draft. Ämnen och avregistreringslistan hanteras i Settings, inte av AI. Följer användarens behörigheter. | how-tos/create-a-campaign-with-ai.mdx | AGPL |
| HB-180 | Leveransråd och nyckeltal. | Systemet sköter DKIM/SPF, avregistrering, spärrlista och dubblettskydd. Användaren ansvarar för samtycke och postadress. Mål: klagomål under 0,1 % (aldrig 0,3 %), studs under 2 % (5 % utlöser granskning). För många studsar/klagomål kan pausa utskick från domänen. Uppvärmning av ny domän: vecka 1 50–100/dag, sedan fördubbling var några dagar, normalvolym vecka 4–6. Lagar: CAN-SPAM, GDPR/ePrivacy/PECR, CASL (allmän vägledning). | how-tos/email-campaign-best-practices.mdx | AGPL |
| **Workflows (arbetsflöden): referens** | | | | |
| HB-181 | Arbetsflöden på även systemobjekt. | Triggers och steg fungerar på standard- och egna objekt samt Workspace Members, Calendar Events, Messages (mejl), Tasks, Notes och andra systemobjekt. | workflows/capabilities/workflow-triggers.mdx | AGPL |
| HB-182 | Trigger "Record is Created". | Välj objekt. Lämplig för poster från CSV, synk och API. Avråds för manuellt skapade poster: UI:t sparar fält för fält (inget redigeringsläge), så flödet startar innan alla fält är ifyllda; använd då "created or updated". | workflow-triggers.mdx | AGPL |
| HB-183 | Trigger "Record is Updated". | Välj objekt; valfritt vilka fält som bevakas. | workflow-triggers.mdx | AGPL |
| HB-184 | Trigger "Record is Updated or Created". | Startar både vid skapande och senare uppdateringar; valfria bevakade fält. | workflow-triggers.mdx | AGPL |
| HB-185 | Trigger "Record is Deleted". | Välj objekt. | workflow-triggers.mdx | AGPL |
| HB-186 | Manuell trigger: Global, Single, Bulk. | Startas från kommandomenyn eller en knapp i övre listen när poster valts. Global: ingen post krävs, startas var som helst. Single: en körning per vald post; mjuk gräns 100 körningar/minut, överskott står "Not Started" och betas av gradvis. Bulk: en körning med hela listan som indata (kräver Iterator). Inställningar: målobjekt, kommandoikon, placering i listen (Pinned/Not Pinned). | workflow-triggers.mdx | AGPL |
| HB-187 | Schematrigger. | Tidsenhet (minuter, timmar, dagar) med värde, eller egen cron-uttryck. Körs i UTC. | workflow-triggers.mdx | AGPL |
| HB-188 | Webhook-trigger. | Unik URL per arbetsflöde; tar emot GET eller POST. För POST definieras förväntad kroppsstruktur (fälten som används senare). Autentisering "kommer snart". | workflow-triggers.mdx | AGPL |
| HB-189 | Variabelväljare. | Ikonen (x+) bläddrar data från tidigare steg; hovring visar vilket steg en variabel kommer från. Steg bör ges beskrivande namn. Variabelnotation med dubbla klammerparenteser; posthändelser exponerar värden före och efter ändring, manuell trigger exponerar vald post, webhook exponerar kroppens fält. Relationsfält exponerar bara relaterad posts id; övriga fält kräver ett sökningssteg. Stegnamn kan inte skrivas för hand; välj från väljaren. | workflow-actions.mdx; send-emails-from-workflows.mdx | AGPL |
| HB-190 | Steg "Create Record". | Välj objekt, fyll fält med fasta värden eller variabler. Utdata: skapad post. | workflow-actions.mdx | AGPL |
| HB-191 | Steg "Update Record". | Välj objekt och post: fast post (rullgardin) eller post från tidigare steg via variabel; posten kan inte sökas fram här (lägg Search Records före). Välj fält och nya värden. Utdata: uppdaterad post. | workflow-actions.mdx | AGPL |
| HB-192 | Steg "Delete Record". | Välj objekt och post; den raderade postens data finns kvar för senare steg. | workflow-actions.mdx | AGPL |
| HB-193 | Steg "Search Records". | Objekt, filter, sortering och gräns. Högst 200 poster. | workflow-actions.mdx; use-iterator.mdx | AGPL |
| HB-194 | Steg "Upsert Record". | Matchar på e-post (People), domän (Companies), id eller unikt fält; minst ett måste fyllas, helst bara ett. Hittas post uppdateras den, annars skapas ny. | workflow-actions.mdx | AGPL |
| HB-195 | Steg "Pick Record" (fördelning). | Väljer en post bland kandidater: Random, Round Robin (minns position mellan körningar), Load Balanced (kandidaten med minst antal länkade poster på valt objekt/fält; räknar alla oavsett status). Kandidater är en fast, manuellt vald mängd, inte en variabel. | workflow-actions.mdx | AGPL |
| HB-196 | Steg "Iterator". | Loopar över en lista (Search Records, Bulk-trigger, kodsteg, webhook-lista). Kod/logikfunktion som returnerar lista på toppnivå väljs med "Whole list". Flera steg kan ligga i loopen; grenar i loopen måste kopplas tillbaka till Iterator. Aktuellt element och index (0-baserat) nås via "Current item" eller "Use the whole item". Fel: "Iterator expects an array" om enskild post skickas; tom lista kör inget (filtrera på längd > 0 först). Varje varv drar krediter. | workflow-actions.mdx; use-iterator.mdx | AGPL |
| HB-197 | Steg "Filter". | Grind utan utdata: villkor uppfyllt → fortsätt, annars stoppar grenen. Operatorn IS fungerar som lika med på tal. | workflow-actions.mdx; use-branches-in-workflows.mdx | AGPL |
| HB-198 | Steg "Delay". | Varaktighet (dagar, timmar, minuter, sekunder, kombinerbart) eller till ett datum/tid (kan tas från tidigare steg). Datum i det förflutna får körningen att misslyckas. Ingen maxlängd. Kostar 0,0001 kredit vid körning; väntan är gratis. Kan inte konfigureras att vänta på att en annan gren blir klar. | workflow-actions.mdx; workflow-branches.mdx; workflow-credits.mdx | AGPL |
| HB-199 | Steg "Send Email". | Kräver anslutet konto som får skicka. Avsändare: bara brevlådor kopplade till det egna kontot (andras brevlådor "på färdplanen"). En mottagare åt gången. Ämne och brödtext med variabler; länkar, numrerade och punktlistor. Statiska bilagor (samma fil till alla; dynamiska via logikfunktion). HTML-signatur stöds inte. Ser ut som vanligt mejl; inte för nyhetsbrev eller sekvenser. | workflow-actions.mdx; send-emails-from-workflows.mdx | AGPL |
| HB-200 | Steg "Draft Email". | Samma fält som Send Email, men sparas i brevlådans utkastmapp för manuell granskning. | workflow-actions.mdx | AGPL |
| HB-201 | Steg "Create Calendar Event". | Kalenderkonto, titel, beskrivning, plats, start/slut eller heldag, valfri tidszon, deltagare, skicka inbjudningar ja/nej, konferenslänk ja/nej. Utdata: händelsen. | workflow-actions.mdx | AGPL |
| HB-202 | Steg "Form". | Bara för manuella triggers: visas i sidopanelen för den som startar flödet; Submit. Fälttyper: text, tal, datum, en post, Select-fält (fält från alla objekt). Etikett, platshållare som standardvärde, formulärtitel, instruktioner (med variabler). Fält kan inte göras obligatoriska. Med andra triggers nås formuläret bara via körningsvyn; för godkännanden i inkorg används "Send to Inbox". Exempelflödet "Quick Lead" finns i alla arbetsytor. | workflow-actions.mdx | AGPL |
| HB-203 | Steg "Code". | JavaScript i inbyggd editor; varje kodsteg backas av en egen logikfunktion. Variabler från tidigare steg som indata (namn kan ändras), returvärden till senare steg, testkörning i steget, helskärmsläge. API-nycklar måste skrivas direkt i koden. Listor från andra system kan komma som sträng och behöver tolkas; för att välja enskilda element returneras ett objekt. | workflow-actions.mdx; how-tos/advanced-configurations/handle-arrays-in-code-actions.mdx | AGPL |
| HB-204 | Återanvändbar logikfunktion som eget steg. | Definieras i en app och exponeras för arbetsflödesbyggaren; dyker upp som eget steg med deklarerade indatafält. Kodsteg kan senare flyttas till sådan funktion. | workflow-actions.mdx | AGPL |
| HB-205 | Steg "HTTP Request". | URL (med variabler), metod GET/POST/PUT/PATCH/DELETE, rubriker, exempelsvar för strukturförhandsvisning. Misslyckas efter 30 sekunder eller om kropp i anrop/svar överstiger 10 MB. | workflow-actions.mdx | AGPL |
| HB-206 | Steg "AI Agent". | Välj agent (eller standardagent) och prompt med variabler. Kan analysera, sammanfatta, klassa, generera text, fatta beslut och använda verktyg mot CRM-data. Strukturerad utdata om agenten har schema. Drar krediter efter modell. Respekterar roller (roller kan tilldelas agenter). | workflow-actions.mdx | AGPL |
| HB-207 | Steg "Classify". | En eller flera frågor om data från tidigare steg, var och en med namn, typ (boolean, choice, score), instruktioner och kriterier (alternativ eller poängnivåer). Returnerar alltid värde i definierad form (deterministiska grenar). Kräver att admin aktiverat en utvärderingsmodell med separat API-nyckel; annars misslyckas steget. | workflow-actions.mdx | AGPL |
| HB-208 | Grenar körs parallellt. | Flera utgångar från ett steg (+ flera gånger, eller högerklick på ytan → Add node och dra pil). Alla grenar körs samtidigt som standard; Filter först i varje gren styr vilka som fortsätter. Grenar kan ritas om utan att påverka körningen. | use-branches-in-workflows.mdx; workflow-branches.mdx | AGPL |
| HB-209 | Steg "If/else". | Första gren If med villkor; "Add route" lägger till Else if; sista Else utan villkor. Villkor prövas uppifrån; första matchande gren körs, övriga hoppas över. | workflow-branches.mdx | AGPL |
| HB-210 | Sammanfoga grenar. | Dra pilar från varje grens sista steg till ett gemensamt steg; det väntar på alla anslutna grenar. Grenar sammanfogas aldrig automatiskt. | use-branches-in-workflows.mdx; workflow-branches.mdx | AGPL |
| HB-211 | Krediter för arbetsflöden. | Pro: 1 kredit per användare och månad; Organization: 4; tidiga planer: 5/månad eller 50/år. En kredit ≈ 10 000 vanliga steg. Dras i realtid vid körning; utkast drar inget; misslyckade körningar betalar för genomförda steg. Billiga: sök/skapa/uppdatera/radera/formulär. Dyrare: kod, HTTP. AI efter modell och längd. Saldo och köp av paket under Settings → Billing. | workflows/capabilities/workflow-credits.mdx | AGPL |
| HB-212 | Körningar (runs). | Varje trigger skapar en körning. Visas i Runs-panelen i editorn och i vyn Workflow Runs (alla flöden; filter på status, flöde, datum). Status: Running, Completed, Failed, Waiting (Delay eller formulär); dessutom "Not Started" i kö. Detaljer: start, varaktighet, triggerdata, utdata per steg, felmeddelande. Gamla körningar "kan arkiveras automatiskt". Ingen inbyggd omkörning; manuella flöden startas igen. | workflows/capabilities/workflow-runs.mdx; workflow-triggers.mdx | AGPL |
| HB-213 | Versioner. | Varje aktivering skapar en version. Status: Draft, Active, Deactivated, Archived. Redigering av aktivt flöde sparas som utkast medan det aktiva fortsätter. Activate publicerar (föregående arkiveras); Discard kastar utkastet. Fliken Versions visar historik; "Use as draft" kopierar en gammal version till nytt utkast (återställning). | workflows/capabilities/workflow-versions.mdx | AGPL |
| HB-214 | Skapa arbetsflöde, testa och aktivera. | Workflows (i sidofältet under objekten) → "+ New Record"/"+ New Workflow" → namn → trigger → steg. "Test" kör med exempeldata; reglaget Active aktiverar. Steg kan döpas om. | workflows/overview.mdx | AGPL |
| HB-215 | Städa layouten på arbetsytan. | Högerklick på ytan → "Tidy up workflow" ordnar alla noder automatiskt. | how-tos/need-more-help/workflows-faq.mdx | AGPL |
| HB-216 | Hastighetsgränser för körningar. | Mjuk: 100 körningar/minut (kö "Not Started", betas av). Hård: 5 000 körningar/timme per arbetsyta; därutöver misslyckas körningar direkt och syns inte i körningslistan. | workflows-faq.mdx | AGPL |
| HB-217 | Tidsgräns för kodsteg. | Standard 5 minuter (300 s), max konfigurerbart 15 minuter (900 s); annars timeout-fel. | workflows-faq.mdx | AGPL |
| HB-218 | Ingen automatisk omkörning av misslyckade körningar. | Fel granskas under flödets Runs; åtgärda och starta om manuellt. Automatisk omkörning "på färdplanen". | workflows-faq.mdx | AGPL |
| HB-219 | Avaktivera flöden före massimport. | Import kan utlösa posthändelseflöden (gränsen 5 000/h, krediter, oväntade mejl, dubbletter). Avaktivera, importera, återaktivera, eller importera i mindre omgångar. | workflows-faq.mdx | AGPL |
| HB-220 | Manuell knapp syns i listen bara om flödet är aktivt, placering Pinned och man står på rätt objekt. | Alltid nåbar via kommandomenyn. | workflows-faq.mdx | AGPL |
| HB-221 | Arbetsflödesbehörighet. | Krävs för att skapa och aktivera; syns inte Workflows i sidofältet saknas behörigheten (Settings → Members → Roles). | workflows-faq.mdx; workflow-troubleshooting.mdx | AGPL |
| HB-222 | CC/BCC i mejlsteg stöds inte. | "På färdplanen". Lösning: flera mejlsteg eller HTTP mot extern tjänst. | workflows-faq.mdx | AGPL |
| HB-223 | In-Reply-To i mejlsteg (svar i tråd). | Under avancerade alternativ: "Add In-Reply-To" tar meddelandets header-id; tomt = fristående mejl. Gmail kräver även att ämnet börjar med "Re:" för att trådas. | how-tos/crm-automations/auto-reply-to-inbound-emails.mdx | AGPL |
| HB-224 | Systemobjekten Messages och Message Participants i flöden. | Messages har ämne, text och header-id; avsändaren finns på Message Participant (roll From, handle = e-post, displayName). Message Participant = en rad per meddelande och deltagare. Search Records ger även totalt antal träffar (totalCount) även när bara 200 poster returneras. | auto-reply-to-inbound-emails.mdx; display-number-of-emails-received.mdx | AGPL |
| HB-225 | Begränsning: relationer på Tasks och Notes. | Kopplingarna på uppgifter och anteckningar är hårdkodade som många-till-många och är inte tillgängliga i triggers eller steg; använd API. | how-tos/crm-automations/display-related-record-data.mdx | AGPL |
| HB-226 | @-omnämnanden i anteckningar och uppgifter stöds inte. | "Planerat andra halvåret 2026". Lösning: relationsfält Reviewer mot Workspace Member + flöde som mejlar länk till anteckningen. Postlänkar har formen arbetsytans underdomän + objekt + id. | how-tos/crm-automations/notify-teammates-of-note-to-review.mdx | AGPL |
| HB-227 | Recept: affär vunnen. | Uppdaterad-trigger på Opportunities med bevakat fält Stage → Filter vunnen → uppdatera bolagets typ → skapa onboardinguppgift → mejla CS och säljaren. Variabler pekar på stegets id, inte namn (välj i väljaren). Motsvarande för förlorad affär. | how-tos/crm-automations/closed-won-automations.mdx | AGPL |
| HB-228 | Recept: inaktuella affärer. | Daglig schematrigger → sök affärer ej uppdaterade på 7 dagar och inte stängda (gräns 100) → filter på antal → kodsteg sammanställer → mejl till chef. Varianter: per säljare, eskalering 7/14/21 dagar, Slack via HTTP. | how-tos/crm-automations/detect-stale-opportunities.mdx | AGPL |
| HB-229 | Recept: räkna mottagna mejl per person. | Eget talfält på People; trigger skapad Message Participant, filter roll From, sök alla med samma handle (gräns 200), upsert person med totalCount. | display-number-of-emails-received.mdx | AGPL |
| HB-230 | Recept: visa data från relaterad post. | Kopiera fält (t.ex. bolagets bransch till affär) via sök + uppdatera; vid ändring på bolaget loopa över dess affärer. Varning för oändliga loopar vid dubbelriktad synk. Lösning i väntan på nästlade fält. | display-related-record-data.mdx | AGPL |
| HB-231 | Recept: formelfält via arbetsflöde. | Inbyggda formelfält "kommer 2026". Kodsteg + uppdatera: fullständigt namn, förväntat belopp (belopp × sannolikhet), dagar till förfall, leadpoäng, domän ur e-post. | how-tos/crm-automations/formula-fields.mdx | AGPL |
| HB-232 | Recept: daglig påminnelse om uppgifter som förfaller. | Cron kl. 08 (UTC) → alla medlemmar → Iterator → sök uppgifter (tilldelad = medlem, förfaller i dag) → kodsteg formaterar med länkar → mejl till medlemmen. | how-tos/crm-automations/send-email-alerts-with-tasks-due.mdx | AGPL |
| HB-233 | Recept: AI-svar på inkommande mejl. | Trigger skapat meddelande → hitta avsändare → AI-agent triagerar (SKIP eller svarstext) → If/else → mejl med In-Reply-To. | auto-reply-to-inbound-emails.mdx | AGPL |
| HB-234 | Recept: webhook-trigger. | Kopiera URL, "Define expected body" med exempel-JSON (skapar variabler), mappa till Create Record, testa med POST, aktivera. Nästlade fält nås med punktnotation; listor via kodsteg + Iterator eller extraktion till namngivna fält. Exempel på källor: webbformulär, Stripe, Zapier/Make/n8n, Typeform (svar som lista). | how-tos/connect-to-other-tools/set-up-a-webhook-trigger.mdx; bring-typeform-submissions-in-twenty.mdx | AGPL |
| HB-235 | Recept: hämta produktdata enligt schema. | Schema → kodsteg hämtar ändrade poster från datalager → ev. formatering → Iterator → Upsert på externt id/SKU. | how-tos/connect-to-other-tools/bring-product-data-in-twenty.mdx | AGPL |
| HB-236 | Recept: skapa PDF och bifoga till post. | Manuell trigger på objekt → logikfunktion laddar ner PDF (från URL eller PDF-tjänst), laddar upp fil och skapar bilaga kopplad till posten (bilagan har målrelation per objekttyp). Kräver API-nyckel. Bilagor syns i postens Attachments. | how-tos/connect-to-other-tools/generate-pdf-from-twenty.mdx | AGPL |
| HB-237 | Recept: offert/faktura till externt system. | Uppdaterad affär → filter vunnen → hämta bolag → formatera → HTTP POST till faktureringssystem; spara externt id tillbaka. | how-tos/connect-to-other-tools/generate-quote-or-invoice-from-twenty.mdx | AGPL |
| HB-238 | Felsökning av arbetsflöden. | Inte aktiverat, villkor ej uppfyllt, fält ej bevakat, behörighet; triggern startar för tidigt vid manuellt skapande (använd skapad-eller-uppdaterad; filtrera "createdAt = updatedAt" eller kryssfält för att köra en gång); HTTP-felkoder 400–500; kodfel inklusive timeout; mejl skickas inte (konto, adress, gränser, spam). | how-tos/need-more-help/workflow-troubleshooting.mdx | AGPL |
| **AI** | | | | |
| HB-239 | AI-chatt (assistent). | Frågor på naturligt språk mot alla poster, relationer och mått (inom användarens behörighet). Sidkontext: "det här bolaget/den här affären" utifrån aktuell sida. Följdfrågor behåller kontext. Öppnas med `@` var som helst eller kommandomenyn → "Ask AI". | ai/overview.mdx; ai/capabilities/ai-chatbot.mdx; email-campaigns/how-tos/create-a-campaign-with-ai.mdx | AGPL |
| HB-240 | AI-agenter i arbetsflöden. | AI-steg för berikning, klassning, sammanfattning, egna promptar; autonoma flerstegsuppgifter. Exempel: leadpoäng, datarensning, utkast från mötesanteckningar, routning. | ai/overview.mdx; ai/capabilities/ai-agents.mdx | AGPL |
| HB-241 | Tilldela roll till AI-agent. | Settings → Members → Roles → roll → fliken Assignment → AI Agents → "+ Assign to AI agent". Agenten når inte data utanför rollen, även om arbetsflödet har bredare behörighet. Rollistan filtreras som standard till roller för medlemmar; roller bara för agenter visas efter filterbyte. | ai/capabilities/permissions-access-control.mdx; ai/how-tos/ai-faq.mdx | AGPL |
| HB-242 | AI-krediter och personlig AI-kvot. | Pro och Organization: AI-chatt och webbsökning använder först varje medlems personliga veckokvot; därefter, och alltid för agenter i flöden, dras arbetsytans krediter efter uppgiftens komplexitet och modell. | ai/how-tos/ai-faq.mdx | AGPL |
| HB-243 | Välja AI-modeller. | Moln: modeller på Twentys leverantörskonton, val under Settings → AI; egen API-nyckel går inte. Självhostat: inbyggda leverantörer (OpenAI, Anthropic, Google, Mistral, xAI) på alla planer inklusive Free via nyckel i Admin Panel → Configuration Variables eller miljöfil; modellerna visas under Admin Panel → AI. Egna leverantörer (egna ändpunkter, gateways, OpenAI-kompatibla/lokala modeller, regioner) under Admin Panel → AI → Custom Providers: gratis upp till 25 platser, därefter Organization-plan. | ai/how-tos/ai-faq.mdx | AGPL (handboken: Organization över 25 platser) |
| HB-244 | MCP-server för externa AI-assistenter. | Ändpunkt = arbetsytans URL + /mcp (moln och självhostat). Streamable HTTP; stöder MCP-protokollversioner från 2024-11-05 till 2026-07-28. Konfigurationssnutt kopieras från Settings → AI → MCP. | ai/capabilities/mcp.mdx | AGPL |
| HB-245 | MCP-autentisering med OAuth (rekommenderas). | Klienten upptäcker OAuth-metadata via well-known-adresser, registrerar sig dynamiskt (RFC 7591), öppnar webbläsare för inloggning; token förnyas automatiskt. Användarens roll gäller. | mcp.mdx | AGPL |
| HB-246 | MCP-autentisering med API-nyckel. | Bearer-nyckel i Authorization-huvudet; nyckeln skapas under Settings → Developers → API. Nyckelns tilldelade roll gäller. | mcp.mdx | AGPL |
| HB-247 | MCP-verktyg (standardläge). | Samma lista i alla arbetsytor (cirka hundra): postverktyg med objekt som argument (find_records, group_records, create_records, update_record, update_records, upsert_records, delete_records, merge_records), upptäckt (list_object_metadata_names, get_field_metadata), metadata (läs/ändra datamodellen), övriga inbyggda verktyg (arbetsflöden, dashboards, vyer, navigation, webhooks, roller, agenter, frontkomponenter, mejl, kalender, filer), samt list_skills, load_skills, search_help_center. Synliga verktyg beror på roll. Appars funktioner och anslutna MCP-servrar ingår inte här. | mcp.mdx | AGPL |
| HB-248 | MCP direktläge. | Parametern mode=direct: ett verktyg per objekt och operation (t.ex. find_many_companies, create_one_person; flera hundra), plus appfunktioner och anslutna MCP-servrar. Nya objekt syns efter återanslutning. Kräver klient som laddar verktyg vid behov. | mcp.mdx | AGPL |
| HB-249 | MCP metaläge. | Parametern mode=meta: bara learn_tools (hämta schema; okända namn rapporteras med närmaste träffar) och execute_tool, plus get_tool_catalog som reserv (bläddra per kategori). Operationsnamn följer en grammatik. | mcp.mdx | AGPL |
| HB-250 | MCP för självhostat. | Serverns publika URL-variabel måste stämma; OAuth-metadata och ändpunkter härleds från den. Felsökning: 401 (rensa token / ny nyckel), ingen webbläsare (klient saknar stöd), timeout. | mcp.mdx | AGPL |
| HB-251 | Inbox (labbfunktion, Early Access). | Slås på under Settings → Community → Features → Inbox. | ai/how-tos/inbox-notifications.mdx | AGPL |
| HB-252 | Skrivbordsnotiser för Inbox. | Settings → Experience → Notifications → Allow (webbläsarens fråga) → testnotis skickas. Nivå: alla följda chattar, direktmeddelanden och omnämnanden, eller av. "Show message preview" visar avsändare och text. Påslag per webbläsare och arbetsyta; nivå och förhandsvisning gäller alla enheter. Sektionen visas bara om Inbox är på och rollen har AI-åtkomst. "Send test" finns. Ingen notis när en flik med systemet är i fokus. Meddelanden när webbläsaren varit stängd mer än en timme ger ingen notis. Privata fönster stöds inte. | inbox-notifications.mdx | AGPL |
| **Layout (sidofält och postsidor)** | | | | |
| HB-253 | Fälla ihop sidofältet. | Knapp överst (verktygstips "Collapse sidebar"/"Expand sidebar"); kommandomenyn: sök "sidebar", kommandot speglar aktuellt läge och stänger menyn. | layout/capabilities/navigation.mdx | AGPL |
| HB-254 | Anpassningsläge för sidofältet. | Med behörigheten Layouts: hovra över sektionen Workspace → skiftnyckelikon → dra objekt → spara. Ordningen i Workspace delas av alla. | layout/capabilities/navigation.mdx | AGPL |
| HB-255 | Mappar i sidofältet. | Gruppera vyer och objekt (t.ex. Sälj, Support). Skapas med högerklick eller +. | navigation.mdx | AGPL |
| HB-256 | Dölja objekt i sidofältet. | Döljs utan radering; visas igen via Settings → Data Model. | navigation.mdx | AGPL |
| HB-257 | Favoriter: vyer, poster eller sökningar. | Fästs överst i sidofältet; personliga; ordnas med dra utan anpassningsläge. | navigation.mdx; layout/overview.mdx | AGPL |
| HB-258 | Egna länkar i sidofältet. | Länkar till externa verktyg (wiki, andra dashboards, valfri URL). | navigation.mdx | AGPL |
| HB-259 | Kommandomenyn: hoppa till post, vy eller åtgärd. | "Copy link to page" kopierar aktuell URL inklusive vy och flik. Sök "theme" för att byta ljust, mörkt eller system (bara de teman som inte är aktiva erbjuds; sparas i profilen). | navigation.mdx | AGPL |
| HB-260 | Postsidans flikar. | Per objekttyp: lägg till, ta bort, byt namn, ordna med dra, välj standardflik. | layout/capabilities/record-pages.mdx | AGPL |
| HB-261 | Widgettyper på postsidan. | Fields (grupperade eller enskilda), Related records (tabell, även kanban), Emails, Calendar, Timeline, Tasks, Notes (rik text), Files, Charts (data från relaterade poster), iFrame, Rich text (statiskt innehåll). | record-pages.mdx | AGPL |
| HB-262 | Redigerbarhet för relaterade poster. | Tabell- och kanbanwidgetar för relaterade poster är redigerbara som standard; "Allow editing" under Data and display stänger av redigering av celler, kort, flytt mellan kolumner och skapande. Rollbehörigheter gäller alltid. | record-pages.mdx | AGPL |
| HB-263 | Anpassa postsidan. | Kommandomenyn "Edit record page layout" eller Data Model → objekt → Layout → "Customize record page": lägg till widgetar, dra på rutnät, ändra storlek via kanter, konfigurera fält i widgetar, hantera flikar, spara (gäller alla poster av typen). Fältsynlighet och ordning per Fields-widget. | record-pages.mdx; layout/overview.mdx | AGPL |
| **Views & Pipelines (vyer och pipelines)** | | | | |
| HB-264 | Skapa vy från vyrullgardinen. | Klick på vynamnet uppe till vänster → "+ Add view" → namn → Create → layout under Options (Table, Kanban, Calendar) → filter, sortering, fält → Save. | views-pipelines/overview.mdx | AGPL |
| HB-265 | Skapa vy genom att ändra befintlig. | Ändra layout/filter/sortering → "Save as new view" → namn → Create → "Update view" sparar fler ändringar. Standardvyer ("All [objekt]") sparas alltid som ny vy. Pilen bredvid Update view ger "Create view". | overview.mdx; capabilities/filters-and-sorting.mdx | AGPL |
| HB-266 | Byta namn och ikon på vy. | Vyrullgardin → ⋮ → Edit → namn/ikon → Save. | overview.mdx; capabilities/view-settings.mdx | AGPL |
| HB-267 | Ordna vyer i rullgardinen. | Dra i handtaget; sparas automatiskt. | view-settings.mdx | AGPL |
| HB-268 | Lägga vy i favoriter. | ⋮ → "Add to favorites". | view-settings.mdx | AGPL |
| HB-269 | Radera vy. | ⋮ → Delete → bekräfta. Kan inte återställas. | view-settings.mdx; overview.mdx | AGPL |
| HB-270 | Vyns synlighet. | Options → Visibility: Workspace (alla medlemmar) eller Unlisted (bara jag; syns inte i andras rullgardin). Standardvyerna "All [objekt]" kan inte ändras. Kan växlas tillbaka. | view-settings.mdx; how-tos/restrict-access-to-your-view.mdx | AGPL |
| HB-271 | Visa/dölja och ordna fält per vy. | Options → Fields → ögonikon; dra för ordning; sparas automatiskt. Tabell: fält = kolumner, bredd ändras genom att dra kanten. Kanban: fält på kort. Kalender: fält på händelser. Dolda fält listas under "Hidden Fields". | capabilities/fields-and-columns.mdx; how-tos/create-a-kanban-view-for-projects.mdx | AGPL |
| HB-272 | Lägga till filter. | Filter → fält → operator → värde; gäller direkt (operatorer som Is empty eller Is in past gäller utan värde). Filter från Filter-knappen kombineras med AND; väljer man ett fält som redan har filter öppnas det för redigering. | capabilities/filters-and-sorting.mdx | AGPL |
| HB-273 | Filteroperatorer per fälttyp. | Text, Emails, Phones, Links, Address, Full Name: Contains, Doesn't contain, Is empty, Is not empty. Number, Currency, Rating: Is, Is not, Greater than or equal, Less than or equal, Is empty, Is not empty. Date, Date and Time: Is, Is relative, Is in past, Is in future, Is today, Is before, Is after or equal, Is empty, Is not empty. Select: Is, Is not, Is empty, Is not empty. Multi-select: Contains, Doesn't contain, Is empty, Is not empty. True/False: Is. Relation: Is, Is not, Is empty, Is not empty. Actor: Contains, Doesn't contain, Is empty, Is not empty. Array, JSON, Files: Contains, Doesn't contain, Is empty, Is not empty. Contains är skiftlägesokänslig delsträng. Select, Multi-select och Relation tar flera värden (matchar något av dem). Relationsfilter bara på fält som pekar på en post. | filters-and-sorting.mdx | AGPL |
| HB-274 | Avancerat filter (AND/OR och grupper). | Filter → Advanced filter → regler (fält, operator, värde), "Add filter rule → Add rule", växla And/Or; "Add rule group" för grupper med egen koppling. Kan filtrera på fält i relaterad post och på del av sammansatt fält. Visas som chip ("2 advanced rules") och kombineras med övriga filter med AND. | filters-and-sorting.mdx | AGPL |
| HB-275 | Ta bort filter och återställa. | X på chip; ⋮ → Remove rule / Remove rule group; "Reset" återgår till vyns sparade filter och sortering. | filters-and-sorting.mdx | AGPL |
| HB-276 | Sortering. | Sort → stigande/fallande → fält; gäller direkt. Flera nivåer (första primär). Från kolumnrubrik: Sort (först stigande, sedan växling). Ta bort via X på chip. | filters-and-sorting.mdx | AGPL |
| HB-277 | Spara filter och sortering i vyn. | "Update view" sparar till aktuell vy; "Create view" som ny. | filters-and-sorting.mdx | AGPL |
| HB-278 | Tabellvy med gruppering efter Select-fält. | Options → Group → Select-fält. Gruppordning under Options → Group → Sort: alfabetisk, omvänd, manuell (dra under "Visible groups"); ögonikon döljer grupp. Grupper är hopfällbara. Rekommendation: högst 10–15 synliga grupper (prestanda). | capabilities/table-views.mdx; how-tos/create-a-table-view-with-grouping.mdx | AGPL |
| HB-279 | Kanbanvy. | Kräver Select-fält (kolumner = alternativ; väljs automatiskt). Dra kort mellan kolumner uppdaterar värdet. "+" i kolumn skapar post i den. Rekommenderat 5–7 steg. | capabilities/kanban-views.mdx; how-tos/create-a-kanban-view-for-projects.mdx; how-tos/set-up-a-sales-pipeline.mdx | AGPL |
| HB-280 | Lägga till och ta bort kanbansteg. | Steg = alternativ i Select-fältet; läggs till i datamodellen. Ta bort: hovra kolumnnamn/⋮ → "Edit from settings" → Delete vid steget. | kanban-views.mdx | AGPL |
| HB-281 | Kompakt kanbanvy. | Options → "Compact view": korten visar bara postnamnet. | kanban-views.mdx | AGPL |
| HB-282 | Aggregeringar per kanbankolumn. | Klick på talet vid kolumnnamnet → Count, Sum, Average, Min, Max → fält. T.ex. summa belopp per steg. | kanban-views.mdx; set-up-a-sales-pipeline.mdx | AGPL |
| HB-283 | Kalendervy. | Kräver datumfält. "+ Add view" → Options → Calendar → välj datumfält → Update view/Save. Varje post visas som händelse på datumet; fält på händelser via Options → Fields. | capabilities/calendar-view.mdx; how-tos/create-a-calendar-view-for-tasks-due.mdx | AGPL |
| HB-284 | Säljpipeline. | Kanbanvy på Opportunities efter fältet Stage; stegen ändras i datamodellen. Förslag: New, Qualified, Meeting, Proposal, Negotiation, Closed Won, Closed Lost. Vyer: "Min pipeline" (ägare = jag, Unlisted), "Teamets pipeline" (Workspace), "Stänger denna månad" (tabell, filter på stängningsdatum och ej stängd). Filtervärdet "Me" för ägare. | how-tos/set-up-a-sales-pipeline.mdx | AGPL |
| HB-285 | Recept: förväntat belopp i pipelinen. | Egna fält Sannolikhet (tal) och Förväntat belopp (valuta), ev. skrivskyddade via roll; flöde sätter sannolikhet per steg och räknar belopp × sannolikhet; andra flöde räknar om vid beloppsändring; kanban-aggregering Sum på förväntat belopp. | how-tos/show-expected-amount-in-pipeline.mdx | AGPL |
| HB-286 | Recept: tid i varje steg. | Datum-tid-fält "senast in i steg X" och talfält "dagar i steg X"; flöde vid stegändring sätter tidsstämpel och räknar dagar i föregående steg; analys via sortering och Average-aggregering. | how-tos/track-time-in-stage.mdx | AGPL |
| **Dashboards** | | | | |
| HB-287 | Skapa dashboard. | Hierarki: dashboard → flikar → widgetar. Dashboards i sidofältet → "+ New Record"/"+ New Dashboard" → namn → flikar → widgetar → spara. | dashboards/capabilities/dashboards.mdx; dashboards/overview.mdx | AGPL |
| HB-288 | Redigeringsläge. | "Edit" uppe till höger; klick på widget öppnar inställningspanelen till höger. | capabilities/chart-settings.mdx | AGPL |
| HB-289 | Flikar på dashboard. | I redigeringsläge: + i flikraden (sidopanel för namn), dra för att ordna eller flytta vänster/höger via kommandomenyn, Delete via kommandomenyn, Duplicate i sidopanelen. | capabilities/dashboards.mdx | AGPL |
| HB-290 | Lägga till widget. | Flik → "+ Add Widget" → typ → datakälla → inställningar → spara. Widgetar dras och storleksändras i rutnät. Duplicera widget via Options → "Duplicate widget". | overview.mdx; capabilities/widgets.mdx; capabilities/dashboards.mdx | AGPL |
| HB-291 | Duplicera dashboard. | I visningsläge: kommandomenyn → "Duplicate dashboard". | dashboards.mdx; how-tos/dashboards-faq.mdx | AGPL |
| HB-292 | Synlighet och favoriter. | Alla med åtkomst till arbetsytan ser alla dashboards; privata dashboards finns inte. Stjärnikon lägger i personliga favoriter. Ingen export och ingen delning till externa användare ("på färdplanen"). | dashboards.mdx; dashboards-faq.mdx; overview.mdx | AGPL |
| HB-293 | Tidszon. | Data visas i betraktarens tidszon (kan ge olika siffror per region). Tidszon per dashboard "kommer snart". | dashboards.mdx; dashboards-faq.mdx | AGPL |
| HB-294 | Dashboardfilter för alla widgetar. | "Kommer snart"; i dag filter per widget. | dashboards.mdx; dashboards-faq.mdx | AGPL |
| HB-295 | Uppdatering. | Widgetar uppdateras automatiskt (i realtid för de flesta mått); manuell uppdateringsknapp finns. | dashboards-faq.mdx | AGPL |
| HB-296 | Widget: stapeldiagram. | Horisontellt eller vertikalt. Högst 100 staplar och 50 grupper per stapel med Group by; annars varningen "Undisplayed data" (filtrera eller grövre datumindelning). | capabilities/widgets.mdx | AGPL |
| HB-297 | Widget: cirkeldiagram. | Andelar av helhet. Inställningar: vad varje sektor representerar, dölj tom kategori, visa värde i mitten. Högst 100 sektorer. | widgets.mdx; chart-settings.mdx; how-tos/widget-faq.mdx | AGPL |
| HB-298 | Widget: linjediagram. | Trender över tid; högst 100 datapunkter. | widgets.mdx; widget-faq.mdx | AGPL |
| HB-299 | Widget: aggregat (nyckeltal). | Ett enskilt värde (KPI). Ratio för Select-fält; prefix och suffix (t.ex. $ och %). Datumfält ger Earliest/Latest. | widgets.mdx; chart-settings.mdx | AGPL |
| HB-300 | Widget: iFrame. | Bäddar in externt innehåll. Mikrofon/kamera för inbäddning kräver att en medlem med säkerhetsbehörighet lägger exakt HTTPS-ursprung under Settings → General → Security → Embedded website media access (inga sökvägar eller jokertecken). Appar deklarerar egna ursprung och godkänns vid installation; godkännanden gäller inte korsvis. Efter ändring laddas flikar om (avslutar samtal). Varje aktivering kräver webbläsarbekräftelse som visar widget/app, ursprung och begärd åtkomst; indikator "Media access enabled" med Disable/Enable. | widgets.mdx | AGPL |
| HB-301 | Widget: tabell (och kanban). | Visar filtrerade poster. Skrivskyddade som standard i dashboards; "Allow editing" möjliggör cellredigering, kortredigering, flytt och skapande. Rollbehörigheter gäller. | widgets.mdx | AGPL |
| HB-302 | Widget: rik text. | Formaterad text, bilder och filer, markdown-liknande redigering. | widgets.mdx | AGPL |
| HB-303 | Mätardiagram (gauge). | Finns inte än; "på färdplanen". | widgets.mdx; dashboards-faq.mdx | AGPL |
| HB-304 | Diagraminställning: källa. | Valfritt standard- eller eget objekt; byte av källa nollställer övriga inställningar. | chart-settings.mdx | AGPL |
| HB-305 | Diagraminställning: filter. | Samma filter som i tabellvyer, inklusive "Is relative" för datum och avancerade And/Or-regler. | chart-settings.mdx | AGPL |
| HB-306 | X-axel: fält och datumindelning. | Gruppering på fält. Datumindelning: Day, Week, Month, Quarter, Year, Day of week, Month of year, Quarter of year (de senare aggregerar över all tid). Visas bara när datumfält valts. | chart-settings.mdx | AGPL |
| HB-307 | X-axel: sortering och nollvärden. | Position (Select-fältets ordning), Alphabetical (kronologiskt för datum), By value, Manual (dra). Alternativen beror på fälttyp. "Omit zero values" döljer tomma kategorier. | chart-settings.mdx | AGPL |
| HB-308 | Y-axel: mått. | Count all, Count empty, Count not empty, Count unique values; Sum, Average, Min, Max (tal); Percent empty, Percent not empty; Count true/false (Boolean). | chart-settings.mdx; widget-faq.mdx | AGPL |
| HB-309 | Ratio. | För Select, Multi-select och Boolean: andel av ett valt värde (t.ex. vunna av alla). | chart-settings.mdx | AGPL |
| HB-310 | Group by (andra dimension). | Flera serier (färger och förklaring); egen datumindelning; sortering Position/Alphabetical/Manual (inte efter värde). Kräver att X-axeln valts. | chart-settings.mdx | AGPL |
| HB-311 | Kumulativt och axelgränser. | Cumulative visar löpande summa. Min/Max range fixerar Y-axeln (tomt = automatiskt). | chart-settings.mdx | AGPL |
| HB-312 | Stil. | Färgpaletter (Select-fält använder alternativens färger), axelnamn (None, X, Y, Both), staplade eller grupperade staplar/linjer, dataetiketter, förklaring (hovra framhäver, klick döljer tillfälligt). | chart-settings.mdx | AGPL |
| HB-313 | Diagrammeddelanden. | "No data" (inga matchande poster), "Invalid configuration" (obligatorisk inställning saknas), "Undisplayed data" (över 100 staplar/punkter/sektorer). Inställningar som kräver andra visas först när förutsättningen är satt. | widget-faq.mdx | AGPL |
| **Permissions & Access (behörigheter och åtkomst)** | | | | |
| HB-314 | Tre behörighetsområden. | Objekt och fält (se, redigera, radera poster och fält), Settings (konfiguration och administration), Actions (allmänna åtgärder som import och mejl). | permissions-access/capabilities/permissions.mdx | AGPL |
| HB-315 | Inbyggda roller Admin och Member. | Admins behörigheter är låsta; Members kan redigeras. Admin kan aldrig raderas och minst en medlem måste alltid ha Admin. | permissions-access/overview.mdx; permissions.mdx; how-tos/permissions-faq.mdx | AGPL |
| HB-316 | Egna roller: planregler. | Moln: skapa och tilldela egna roller till medlemmar eller API-nycklar kräver Organization-planen; Pro använder bara Admin/Member; Pro (Early) behåller egna roller; AI-agenter kan få egna roller på alla planer; självhostat har egna roller på alla planer. | permissions.mdx; permissions-faq.mdx; overview.mdx | AGPL (handboken: Organization) |
| HB-317 | Skapa roll. | Settings → Members → Roles → All Roles → "+ Create Role" → namn → fliken Permissions → Save. | permissions.mdx | AGPL |
| HB-318 | Radera roll. | Roll → fliken Settings → "Delete Role" → Confirm. Medlemmar med rollen flyttas till standardrollen. | permissions.mdx; permissions-faq.mdx | AGPL |
| HB-319 | Tilldela roll till medlem. | Roll → fliken Assignment → "+ Assign to member". Rollöversikten visar antal medlemmar per roll. Bara befintliga medlemmar; en roll per användare. | permissions.mdx; permissions-faq.mdx | AGPL |
| HB-320 | Standardroll för nya medlemmar. | Settings → Members → Roles → Options → Default Role. Används även vid JIT-provisionering via SSO och när roll raderas. | permissions.mdx; sso-configuration.mdx | AGPL |
| HB-321 | Objektbehörigheter: grundnivå för alla objekt. | See Records, Edit Records, Delete Records (mjuk radering, återställbar), Destroy Records (permanent) "on All Objects". | permissions.mdx | AGPL |
| HB-322 | Objektundantag. | "Object-Level" → "+ Add rule" → objekt: åsidosätter grundnivån per objekt (t.ex. dölja Opportunities helt, tillåta redigering av People). | permissions.mdx | AGPL |
| HB-323 | Radnivåbehörigheter. | "Premium", Organization-planen (moln och självhostat). Fliken Objects → sektionen Row-Level: filtervillkor per objekt som avgör vilka poster rollen ser/redigerar (t.ex. bara egna affärer, region, tilldelade ärenden). Varje post prövas för sig. | permissions.mdx; permissions-faq.mdx | Enterprise (stickprov: twenty-server/src/engine/permissions/internal och radnivåregelhanterarna bär Enterprise-huvud) |
| HB-324 | Fältbehörigheter. | Inom objektregel: See Field, Edit Field, No Access (helt dolt). Används t.ex. för skrivskyddade beräknade fält. | permissions.mdx; permissions-faq.mdx | AGPL |
| HB-325 | Arv av behörigheter. | Alla objekt → objektregel → fältregel; mest specifika vinner. Ärvd regel tas bort med X; orange ångra-ikon återställer; Finish och sedan Save. | permissions.mdx | AGPL |
| HB-326 | Inställningsbehörigheter. | "Settings All Access" eller enskilda: API-nycklar, arbetsytepreferenser, rolltilldelning, datamodell, säkerhet, arbetsflödeshantering. Begränsning: arbetsflödeshantering krävs för att starta manuella flöden. | permissions.mdx; permissions-faq.mdx | AGPL |
| HB-327 | Åtgärdsbehörigheter. | "Application All Access" eller enskilda: Send Email, Import CSV, Export CSV. (Andra sidor nämner även "Create calendar event" och "Layouts".) | permissions.mdx; permissions-faq.mdx; calendar-emails/how-tos/can-i-book-meetings-from-twenty.mdx; layout/capabilities/navigation.mdx | AGPL |
| HB-328 | Roll till API-nyckel. | Roll → Assignment → API Keys → "+ Assign to API key". Nyckel utan roll har standardbehörigheter. | permissions.mdx | AGPL |
| HB-329 | Roll till AI-agent. | Roll → Assignment → AI Agents → "+ Assign to AI agent" (se HB-241). | permissions.mdx | AGPL |
| HB-330 | SSO. | Organization-planen ("Premium"), moln och självhostat. Leverantörer: SAML 2.0, Google Workspace, Microsoft Entra ID. Settings → Security → SSO Configuration → Configure SSO → välj leverantör eller "Custom SAML" → i IdP: Entity ID, ACS URL, certifikat → i systemet: SSO URL, Entity ID, X.509-certifikat → "Test Configuration" → aktivera. (OIDC nämns som stöd på nyckelfunktionssidan.) | permissions-access/capabilities/sso-configuration.mdx; permissions-faq.mdx; getting-started/key-features.mdx | AGPL (handboken: Organization/Premium) |
| HB-331 | Provisionering via SSO. | JIT: användare skapas vid första inloggning med standardroll. Manuell: bjud in först och tilldela roll. Lösenordsinloggning kan stängas av för SSO-användare. Åtkomst återkallas i IdP eller genom att ta bort ur arbetsytan. Gruppmappning IdP→roll "om tillgängligt". Felsökning: certifikat utgånget, ACS-URL avviker, användare hittas inte (JIT). | sso-configuration.mdx; permissions-faq.mdx | AGPL (handboken: Organization/Premium) |
| **Billing (fakturering, planer, krediter, gränser)** | | | | |
| HB-332 | Planer i molnet: Pro. | Alla kärnfunktioner, mejl-/kalendersynk, arbetsflöden, rollerna Admin och Member, personlig AI cirka 100 uppgifter per medlem och vecka, 1 kredit per användare och månad, mejl- och chattsupport. Inga premiumfunktioner. | billing/capabilities/pricing-plans.mdx; billing/overview.mdx | AGPL |
| HB-333 | Planer i molnet: Organization. | Allt i Pro, cirka 500 AI-uppgifter per medlem och vecka, 4 krediter per användare och månad, premiumfunktioner, prioriterad support. | pricing-plans.mdx | AGPL |
| HB-334 | Tidiga planer (Early). | Äldre prenumerationer behåller pris och villkor så länge de inte byts (kan inte väljas igen). Pro (Early): egna roller med fältbehörigheter. Organization (Early): plus premiumfunktioner. Båda 5 krediter/månad (50/år), ingen personlig AI-kvot. | pricing-plans.mdx; credits.mdx | AGPL |
| HB-335 | Självhostat: Free. | Alla Pro-funktioner plus egna roller; AI på egna leverantörsnycklar (ingen personlig AI eller krediter); communitysupport via Discord. | pricing-plans.mdx; how-tos/billing-faq.mdx | AGPL |
| HB-336 | Självhostat: Organization. | Allt i Free plus premiumfunktioner (radnivå, SSO m.m.), support från Twenty, inget krav att publicera egen kod som öppen källkod före distribution. Kräver Organization-nyckel; molnprenumeration gäller inte för självhostat. | pricing-plans.mdx; billing-faq.mdx | AGPL (licensnyckel) |
| HB-337 | Premiumfunktioner (bara Organization). | Egna roller (utom Pro (Early) i molnet; alla planer självhostat), radnivåbehörigheter, SSO, revisionsloggar (vad varje medlem gjort), användningsgränser per medlem/API-nyckel/app, egen domän (även självhostat), obegränsat antal arbetsytor (självhostat), privat källkod (självhostat). | pricing-plans.mdx; billing-faq.mdx | AGPL (handboken: Organization/Premium) |
| HB-338 | Byta plan och intervall. | Settings → Billing → Plans → "Upgrade/Switch to Organization" eller "Switch to Pro"; Settings → Billing → "Switch to annual"/"Upgrade to yearly" eller "Downgrade to monthly". | pricing-plans.mdx; billing-faq.mdx | AGPL |
| HB-339 | Hämta Organization-nyckel (självhostat). | Settings → Admin Panel → Organization → "Get Organization Key" → betalning via Stripe → klistra in nyckeln och aktivera licensen. | pricing-plans.mdx | AGPL |
| HB-340 | Krediter: en gemensam saldopott. | Arbetsytans krediter driver arbetsflöden, AI-agenter och AI-chatt. 1 kredit = 1 USD. Standardsteg ≈ 0,0001 (10 000 per kredit); logikfunktion 0,0001 per anrop + 0,0001 per sekund (debiteras per millisekund; timeout debiteras full tid; 15-minuters timeout ≈ 0,09 extra); externt API/kod: liten bråkdel; AI-chatt: bråkdel av en cent; stor agentuppgift: ca 1 USD eller mer; webbsökning: fast pris per sökning. Vissa appar (samtalsinspelning m.fl.) debiterar inte körningar men väl mätt arbete. | billing/capabilities/credits.mdx | AGPL |
| HB-341 | AI-mätning. | Exakta tokens prissätts efter leverantörens publicerade priser och omvandlas till krediter; billigare modeller kostar mindre. Fördelning per åtgärd och modell syns i Settings → Billing. | credits.mdx | AGPL |
| HB-342 | Inkluderade krediter. | Pro 1/användare/månad; Organization 4; tidiga planer 5/månad eller 50/år. Årsbetalning: 12 resp. 48 per användare för året. | credits.mdx; workflows/capabilities/workflow-credits.mdx | AGPL |
| HB-343 | Personlig AI-kvot. | Pro ≈ 100, Organization ≈ 500 AI-uppgifter per medlem och vecka (en uppgift = en chattförfrågan med standardmodell; smartare modeller drar mer). Förnyas måndag 00:00 UTC. Används av chatt och webbsökning före krediter; agenter i flöden använder alltid krediter. När kvoten tar slut fortsätter chatt på krediter, om inte en medlem med Billing-behörighet slår av "Use workspace credits after a member reaches their limit". | credits.mdx; billing-faq.mdx | AGPL |
| HB-344 | Överföring av krediter. | Inkluderade krediter på Pro/Organization förnyas varje period och överförs inte. Krediter från paket och tidiga planers inkluderade krediter överförs, med tak på en periods tilldelning (aldrig mer än dubbelt). Sektionen Credits visar ursprung och vad som kan överföras. | credits.mdx | AGPL |
| HB-345 | Bevaka och köpa krediter. | Settings → Billing: kvarvarande saldo, periodens förbrukning, uppdelning per arbetsflöde och AI-åtgärd. Kreditpaket 1 USD per kredit, från 20 USD/månad, förnyas med prenumerationen; "Manage" eller genvägar "Increase to $…"; läggs till direkt. Engångsökning för en månad: höj och sänk sedan tillbaka (sänkningen gäller nästa period). | credits.mdx; billing-faq.mdx | AGPL |
| HB-346 | Användningsgränser. | Settings → Billing → Limits; kräver behörigheten Workspace settings. Användning: AI (chatt, agenter, webbsökning; arbetsyta, medlem, API-nyckel, app), arbetsflöden (arbetsyta, app), logikfunktioner (arbetsyta, app, enskild funktion), e-post (arbetsyta, medlem), all användning (app, bara krediter). Mäts i krediter eller antal operationer. Perioder: dag, vecka, månad (kalender) eller faktureringsperiod (kräver prenumeration). | billing/capabilities/usage-limits.mdx | AGPL |
| HB-347 | Planregel för gränser. | Hela arbetsytan: alla planer. Medlem, API-nyckel, app, logikfunktion: Organization. Utan planen kan omfånget inte väljas och sparade gränser visas "Deactivated" och tillämpas inte, men återaktiveras automatiskt vid rätt plan. | usage-limits.mdx | AGPL (handboken: Organization) |
| HB-348 | Skapa, ändra, radera gräns. | New limit → Scope → belopp, enhet, period → Save; gäller direkt och räknar redan registrerad användning i perioden. Klick på rad ändrar; "Delete limit" i danger zone. Tabellen visar förbrukning per gräns. | usage-limits.mdx | AGPL |
| HB-349 | När gränsen nås. | Arbetet nekas (köas inte) bara i det omfånget; resten fortsätter. Återupptas vid periodens nollställning, eller höj/radera gränsen. Kontroll före start och debitering efteråt, så pågående arbete kan gå något över (en batch vid kampanjutskick). | usage-limits.mdx | AGPL |
| HB-350 | Betalningsuppgifter och fakturor. | Settings → Billing → "View billing details": betalmetod, faktureringsinformation, fakturor längst ned. | billing-faq.mdx | AGPL |
| HB-351 | Platser och fakturering per användare. | Inga gratisplatser för läsanvändare; varje användare kräver licens. Platsantal synkas med betalsystemet var 6:e timme. Ny medlem ger faktura för mellanskillnaden; borttagen medlem justeras på nästa ordinarie faktura. | billing-faq.mdx | AGPL |
| **Settings (inställningar)** | | | | |
| HB-352 | Arbetsytans namn och logotyp. | Settings → General. Logotyp PNG, JPEG eller GIF under 10 MB; kan tas bort. Namn syns för alla; sparas automatiskt. | settings/capabilities/workspace-settings.mdx; settings/how-tos/settings-faq.mdx | AGPL |
| HB-353 | Radera arbetsyta. | Settings → General → Danger Zone → "Delete workspace" → bekräfta. Tar bort all data permanent och spärrar alla medlemmar direkt; bara administratörer. | workspace-settings.mdx; settings-faq.mdx | AGPL |
| HB-354 | Pausa arbetsyta utan radering. | Settings → Billing → "Cancel Plan"; data bevaras under en respitperiod (längd anges ej). | settings-faq.mdx | AGPL |
| HB-355 | Flera arbetsytor per användare. | Man kan skapa och vara medlem i flera; var och en har egen data, egna inställningar och egen prenumeration. Kontot är gemensamt för alla arbetsytor. | settings-faq.mdx | AGPL |
| HB-356 | Underdomän och egen domän för arbetsytan. | Settings → General → Workspace Domain → Customize Domain: underdomän (företag.twenty.com) eller egen domän (crm.företag.se, kräver DNS). Egen domän listas som premiumfunktion i molnet. | settings/capabilities/domains-settings.mdx; settings-faq.mdx; billing/capabilities/pricing-plans.mdx | AGPL (handboken: Organization för egen domän) |
| HB-357 | Godkända domäner för självregistrering. | Settings → Members → Invite → "Add Approved Access Domain": alla med e-post på domänen kan gå med utan inbjudan. | domains-settings.mdx; member-management.mdx | AGPL |
| HB-358 | Egen domän för en app. | Settings → Apps → appen → General → App URL (visas när appen har HTTP-triggade funktioner) → Custom Domain → DNS → verifiera. Bara appens routes nås där; SSL-certifikat skapas automatiskt. | domains-settings.mdx | AGPL |
| HB-359 | Utseende och språk. | Settings → Experience: tema Light, Dark eller System; språk ur lista. Sparas automatiskt. | settings/capabilities/experience-settings.mdx | AGPL |
| HB-360 | Format. | Tidszon, datumformat, tidsformat (12/24 h), talformat (decimal- och tusentalsavgränsare), veckans första dag (söndag eller måndag). Varje inställning kan följa systemet. | experience-settings.mdx | AGPL |
| HB-361 | Bjuda in medlem via e-post. | Settings → Members → Invite → "+ Invite" → e-post → roll → "Send invite"; e-post med länk. | settings/capabilities/member-management.mdx | AGPL |
| HB-362 | Inbjudningslänk. | Kopiera arbetsytans länk och dela; åtkomst efter registrering. | member-management.mdx | AGPL |
| HB-363 | Väntande inbjudningar. | Visas under Invite; Resend eller Cancel. | member-management.mdx | AGPL |
| HB-364 | Medlemslista och medlemsprofil. | Settings → Members → Team visar aktiva medlemmar. Administratör kan ändra namn och profilbild, logga in som medlemmen (impersonate, för felsökning) och radera kontot. | member-management.mdx | AGPL |
| HB-365 | Byta medlems roll. | Profil → fliken Permissions → välj roll; gäller direkt. | member-management.mdx | AGPL |
| HB-366 | Ta bort medlem. | Profil → "Delete account". Åtkomst upphör direkt; poster, anteckningar och uppgifter finns kvar; medlemmens mejl och kalenderhändelser arkiveras och är tillgängliga för andra. | member-management.mdx | AGPL |
| HB-367 | Återställningskod för tvåfaktor. | Kräver behörigheten Security och egen tvåfaktor. Profil → Two-factor authentication → "Generate recovery code" → bekräfta med egen kod → dela via säker kanal. Engångskod, giltig 1 timme som standard, visas en gång; ny kod ersätter gammal; "Revoke" avbryter; medlemmen får e-post. Användning tar bort medlemmens autentiserare i arbetsytan och loggar ut övriga sessioner; kräver arbetsytan tvåfaktor måste ny sättas upp direkt. Kan inte skapas för sig själv; bara serveradministratör kan skapa för annan serveradministratör. | member-management.mdx; profile-settings.mdx; settings-faq.mdx | AGPL |
| HB-368 | Profil: namn, e-post, bild. | Visningsnamn; byte av inloggnings-e-post kräver verifiering (FAQ: kontakta support); egen avatar eller initialer. | settings/capabilities/profile-settings.mdx; settings-faq.mdx | AGPL |
| HB-369 | Tvåfaktorautentisering (autentiseringsapp). | Settings → Profile → Authenticator app → skanna QR → ange kod. Förlorad app: "Lost your authenticator? Use a recovery code" på verifieringsskärmen. Arbetsytan kan kräva tvåfaktor. | profile-settings.mdx; member-management.mdx | AGPL |
| HB-370 | Byta lösenord. | Settings → Profile → nuvarande + nytt lösenord. Minst 8 tecken. | profile-settings.mdx; settings-faq.mdx | AGPL |
| HB-371 | Radera konto. | Settings → Profile → Danger Zone → Delete Account → skriv in e-postadressen. Tar bort åtkomst till alla arbetsytor och alla synkade mejl från anslutna konton; kan inte ångras. | profile-settings.mdx; settings-faq.mdx | AGPL |
| HB-372 | Koppla från e-postkonto. | Settings → Accounts → konto → Disconnect → bekräfta. | settings-faq.mdx | AGPL |
| HB-373 | Early Access-funktioner. | Settings → Community → Features → slå på; tillgänglig direkt; kan ändras. Just nu: Inbox (dela AI-chattrådar och triagera i delad inkorg) och nytt format för REST-metadata-API (objekt och fält utan omslag; standard för arbetsytor skapade sedan maj 2026; gamla formatet upphör 15 november 2026). Community-sektionen har även sök efter partner. | settings/capabilities/community-settings.mdx; settings-faq.mdx | AGPL |
| HB-374 | Checklista vid start. | Namn och logotyp, tidszon och datumformat, mejl/kalender, kontrollera standardroll innan inbjudan, bjud in, roller. | settings/overview.mdx | AGPL |
| **Legal (juridik, dataskydd, drift)** | | | | |
| HB-375 | Datalagring och region. | Molnet körs i AWS Frankfurt. Val av region "från 2027", först för nya arbetsytor; byte för befintliga senare. Underbiträden listas i Trust Center. EU:s standardavtalsklausuler (med UK- och schweiziska tillägg) för överföringar utanför EU. | legal/how-tos/legal-faq.mdx | AGPL |
| HB-376 | Personuppgiftsbiträdesavtal (DPA). | Genereras och signeras med ett klick under Settings → Legal → DPA (egen sida per arbetsyta); finns på alla planer. Ändrade villkor (annan avtalspart, egna notifieringsfrister) bara på "Enterprise-planen". Twenty är biträde, kunden personuppgiftsansvarig. | legal-faq.mdx | AGPL (handboken: Enterprise-plan för avvikande DPA) |
| HB-377 | AI-data och träning. | Ingen egen modell; ingen träning på kunddata; standardleverantörer (Azure OpenAI, OpenAI, Anthropic, Mistral) tränar inte. Valfria modeller (t.ex. Gemini) och klassningsleverantören används bara om admin aktiverar dem. | legal-faq.mdx | AGPL |
| HB-378 | Integritetsinställningar för AI. | Settings → General → Privacy: bearbetningsregion "endast EU" och "Zero data retention"; då används bara modeller som uppfyller båda och övriga anrop nekas (färre och ibland dyrare modeller). | legal-faq.mdx | AGPL |
| HB-379 | Stänga av AI helt. | Ingen data skickas till AI om ingen kör AI. Blockera allt: AI-användningsgräns 0 för arbetsytan (Settings → Billing; gäller alla inklusive admin). Eller ta bort behörigheten "Ask AI" från redigerbara roller (Admin behåller den alltid). | legal-faq.mdx | AGPL |
| HB-380 | Supportåtkomst till arbetsytan. | Twentys teknik- och supportpersonal kan gå in för felsökning; kan stängas av när som helst under Settings → General → Privacy (förblir av tills den slås på). Kräver tvåfaktor hos Twenty; på Organization loggas varje session i revisionsloggen; under impersonering syns sessionen märkt "Impersonation" under Settings → Profile → Devices. | legal-faq.mdx | AGPL |
| HB-381 | Impersonering mellan medlemmar. | Roller med behörigheten Impersonate kan se arbetsytan som vilken medlem som helst, även admin. | legal-faq.mdx; settings/capabilities/member-management.mdx | AGPL |
| HB-382 | Revisionsloggar. | Organization och uppåt; lagringstid ställs in under Settings → General → Security. Kan inte flyttas mellan arbetsytor. | legal-faq.mdx; billing/capabilities/pricing-plans.mdx; data-migration/how-tos/export-faq.mdx | AGPL (handboken: Organization/Premium) |
| HB-383 | Enheter/sessioner i profilen. | Settings → Profile → Devices visar sessioner (impersonering märkt). | legal-faq.mdx | AGPL |
| HB-384 | Mjuk radering och lagringstid. | Raderad post är först mjukraderad och kan återställas; slutgiltigt bort efter lagringstid eller manuell permanent radering ("destroy"). Standard 14 dagar; ändras under Settings → General → Security. I säkerhetskopior 30 dagar till. | legal-faq.mdx | AGPL |
| HB-385 | Radering av arbetsyta (tidslinje). | Data bort ur drift inom cirka 90 dagar efter avslut, säkerhetskopior inom ytterligare 90 dagar; isolerad under tiden; skriftligt intyg på begäran. | legal-faq.mdx | AGPL |
| HB-386 | Säkerhet och kontinuitet. | Kryptering i transit och i vila; isolering med ett schema per kund; nyckelrotation. Säkerhetskopior löpande med dagliga ögonblicksbilder, 30 dagars lagring, krypterade, geografiskt separerade inom samma jurisdiktion. RTO och RPO 6 timmar. Incidentnotis utan onödigt dröjsmål, mål senast 72 timmar. | legal-faq.mdx | AGPL |
| HB-387 | Efterlevnad. | GDPR och SOC 2 enligt Trust Center; HIPAA pågår. | legal-faq.mdx | AGPL |
| HB-388 | Licensfrågor. | Intern ändrad version behöver inte publiceras; nätverksklausulen gäller när utomstående använder den ändrade instansen. Egen front mot oförändrat Twenty via API: inget att publicera. Ändringar som säljs vidare måste publiceras (eller Organization-licens). Appar som bara använder publicerade API:er/SDK får valfri licens ("Twenty Application Exception"). Kärnan mest AGPLv3, vissa paket (bl.a. SDK) MIT. | legal-faq.mdx | AGPL |
| **Tillägg vid kontrolläsning (sidor som saknade rader)** | | | | |
| HB-389 | Produktens tio huvudområden (presentationssida). | Sidan "What is Twenty" räknar upp tio huvudfunktioner: Calendar & Emails, Data Model, Data Migration (CSV eller API), Views & Pipelines (tabell, kanban, säljpipeline), Workflows, AI, Dashboards, Permissions & Access (rollbaserat), Notes & Tasks (kopplade till poster), API & Webhooks. Fördelar som anges: anpassningsbart, communitydrivet, ingen inlåsning tack vare självhosting. Ingen egen funktion utöver de som har egna rader. | user-guide/getting-started/capabilities/what-is-twenty.mdx | AGPL |
| HB-390 | Ordlista i handboken (två nästan identiska sidor). | 24 rubriker (25 begrepp om Company och People räknas var för sig): API, Apps, Code Actions, Command Menu, Company & People, Custom Fields, Data Model, Favorites, Field, Iterator, Kanban, Object, Opportunities, Record, Relation Fields, Standard Fields, Tasks, Triggers, Views, Upsert, Webhooks, Workflows, Workspace, Workspace Members. En arbetsyta har ett enda domännamn, normalt bolagets e-postdomän. Kommandomenyn öppnas med Cmd+K (Mac) / Ctrl+K (Windows). Medlemmar kan vara ägare eller tilldelade för poster. Sidorna skiljer sig bara i beskrivningsraden och en formulering. Termerna finns i Ordlistan nedan. | getting-started/core-concepts/glossary.mdx; user-guide/getting-started/capabilities/glossary.mdx | AGPL |
| HB-391 | Navigeringssida för datamodellen. | Länksida utan egna regler: skapa objekt, skapa fält, skapa relationsfält, plus länkar till översikt, objekt, fält, relationsfält och FAQ. Allt täcks av HB-043–HB-088. | user-guide/data-model/how-tos/customize-your-data-model.mdx | AGPL |
| HB-392 | Professionell hjälp med arbetsflöden. | Handboken rekommenderar certifierade implementeringspartner för integrationer mellan flera system, avancerad affärslogik, storskalig databehandling, egen API-utveckling, utbildning, eller när interna resurser saknas. Kontakt via Twentys kontaktadress och partnersidan. Ingen produktfunktion. | user-guide/workflows/how-tos/need-more-help/professional-services.mdx | AGPL |
| HB-393 | Sidor som finns men inte syns i innehållsförteckningen. | Nio engelska sidor saknas i `docs.json` och nås bara via länk eller sökning: ai/capabilities/mcp, data-migration/how-tos/export-faq, getting-started/capabilities/glossary, getting-started/capabilities/implementation-services, getting-started/capabilities/what-is-twenty, getting-started/how-tos/configure-your-workspace, getting-started/how-tos/create-workspace, getting-started/how-tos/navigate-around-twenty (alla under user-guide/) och user-guide/views-pipelines/overview. Inga sidor i `docs.json` saknar fil. Följd för facit: dessa sidor kan vara äldre eller under omarbetning, vilket kan förklara motsägelserna i Oklarheter 3, 4 och 13. | docs.json; user-guide/** | AGPL |

<!-- RADER-SLUT -->

## Ordlista

| Term i handboken | Förslag på svensk term | Kommentar |
|---|---|---|
| Workspace | Arbetsyta | En kund/ett bolag; har en domän. |
| Workspace Member | Medlem | Användare med åtkomst; kan vara ägare/tilldelad. |
| Object | Objekt | Standard eller eget. |
| Standard object / Custom object | Standardobjekt / eget objekt | |
| Record | Post | En instans av ett objekt. |
| Field / Standard Field / Custom Field | Fält / standardfält / eget fält | |
| Relation Field | Relationsfält | |
| Data Model | Datamodell | |
| Company / People / Person | Bolag (Företag) / Personer (Kontakter) | |
| Opportunity | Affärsmöjlighet (Affär) | |
| Task / Note | Uppgift / Anteckning | |
| View | Vy | |
| Table / Kanban / Calendar view | Tabellvy / Kanbanvy / Kalendervy | |
| Group By | Gruppering | |
| Favorites | Favoriter | Personliga. |
| Command Menu | Kommandomeny | Cmd/Ctrl+K. |
| Side Panel | Sidopanel | |
| Record page | Postsida | |
| Widget | Widget (ruta) | |
| Sidebar | Sidofält | |
| Workflow | Arbetsflöde | |
| Trigger | Utlösare (trigger) | |
| Action / Step | Steg (åtgärd) | |
| Code Action | Kodsteg | |
| Iterator | Iterator (slinga) | |
| Branch | Gren (förgrening) | |
| Upsert | Uppdatera-eller-skapa (upsert) | |
| Webhook | Webhook | |
| App | App (tillägg) | |
| Logic Function | Logikfunktion | |
| Front Component | Frontkomponent | |
| Skill | Färdighet (skill) | |
| Agent / AI Chatbot | Agent / AI-chatt | |
| Dashboard | Instrumentpanel (dashboard) | |
| Soft delete / Hard delete | Mjuk radering (papperskorg) / permanent radering | |
| Early Access | Tidig åtkomst | Under Settings → Updates. |
| Implementation Partner | Implementeringspartner | |
| Deactivate / Activate (object, field) | Avaktivera / återaktivera | Data bevaras. |
| Unique field | Unikt fält | |
| Main display field / record text field | Visningsfält (postens namn) | |
| Validation rule | Valideringsregel | Organization. |
| Junction object | Kopplingsobjekt | Många-till-många. |
| Morph relation / relation to multiple object types | Flerobjektsrelation | |
| Self-referencing relation | Självrelation | |
| API name / API value | API-namn / lagrat värde | För Select-alternativ. |
| Currency micros | Mikrobelopp | 1 enhet = 1 000 000. |
| Field mapping | Fältmappning (kolumnkoppling) | |
| Sample file | Exempelfil | |
| Soft-deleted / Destroy | Mjukraderad / radera permanent | |
| Mailbox / Message / Message Participant | Brevlåda / meddelande / meddelandedeltagare | |
| Message Folder | Mejlmapp | |
| Contact auto-creation | Autoskapande av kontakter | |
| Visibility (Metadata only, Subject and metadata, All content) | Synlighet (bara metadata, ämne och metadata, allt innehåll) | |
| Email channel / shared inbox | E-postkanal / delad inkorg | |
| Forwarding address | Vidarebefordringsadress | |
| Sending domain / Domain authentication | Avsändardomän / domänautentisering | |
| Unsubscribe link / page / topic | Avregistreringslänk / -sida / -ämne | |
| Unsubscribers | Avregistrerade | |
| Campaign / List / List Member | Kampanj / lista / listmedlem | |
| Test email | Testmejl | |
| Draft / Scheduled / Sending / Sent / Sent with errors / Canceled | Utkast / schemalagd / skickas / skickad / skickad med fel / avbruten | Kampanjstatus. |
| Warm-up | Uppvärmning | Ny avsändardomän. |
| Record is Created / Updated / Updated or Created / Deleted | Post skapad / uppdaterad / skapad eller uppdaterad / raderad | Triggers. |
| Manual trigger: Global / Single / Bulk | Manuell: global / per post / i klump | |
| Schedule (cron) | Schema | UTC. |
| Search Records / Upsert Record / Pick Record | Sök poster / uppdatera eller skapa / välj post | |
| Round Robin / Load Balanced | Turordning / jämn belastning | |
| Filter (workflow) / If/else | Filtersteg / om-annars | |
| Delay | Fördröjning | |
| Form | Formulär | |
| Send Email / Draft Email | Skicka mejl / skapa mejlutkast | |
| HTTP Request | HTTP-anrop | |
| Classify | Klassa | |
| Run / Version | Körning / version | |
| Variable picker | Variabelväljare | |
| Credit / workspace credits / personal AI usage | Kredit / arbetsytans krediter / personlig AI-kvot | |
| Credit pack / rollover | Kreditpaket / överföring | |
| Usage limit / scope / meter / period | Användningsgräns / omfång / mätare / period | |
| MCP server / direct mode / meta mode | MCP-server / direktläge / metaläge | |
| Inbox (AI) | Inkorg (AI-trådar) | Labbfunktion. |
| Customization mode (sidebar) | Anpassningsläge | |
| Custom link | Egen länk | |
| Tab / widget / layout editor | Flik / widget / layouteditor | |
| Allow editing | Tillåt redigering | Widgetinställning. |
| Unlisted / Workspace (view visibility) | Privat (olistad) / delad med arbetsytan | |
| Compact view | Kompakt vy | Kanban. |
| Aggregation (Count, Sum, Average, Min, Max) | Aggregering (antal, summa, medel, min, max) | |
| Advanced filter / rule / rule group | Avancerat filter / regel / regelgrupp | |
| Date granularity | Datumindelning | |
| Ratio / Cumulative / Group by / Stacked | Andel / kumulativ / gruppera efter / staplad | |
| Aggregate chart | Nyckeltalsruta | |
| Role / Default role / Admin / Member | Roll / standardroll / administratör / medlem | |
| Object-level / Row-level / Field-level permission | Objekt-, rad-, fältbehörighet | |
| See / Edit / Delete / Destroy Records | Se / redigera / radera (papperskorg) / radera permanent | |
| Settings All Access / Application All Access | Full inställningsåtkomst / full åtgärdsåtkomst | |
| SSO / JIT provisioning | Enkel inloggning / automatisk kontoskapning vid första inloggning | |
| Premium features | Premiumfunktioner | Organization. |
| Pro / Organization / Early / Free (self-hosted) | Pro / Organization / tidig plan / gratis självhostad | |
| Organization Key | Organisationsnyckel (licensnyckel) | |
| Approved Access Domain | Godkänd domän | |
| Impersonate | Logga in som (impersonera) | |
| Recovery code | Återställningskod | Tvåfaktor. |
| Audit logs | Revisionslogg | |
| Support access | Supportåtkomst | |
| Zero data retention | Ingen datalagring hos AI-leverantören | |
| DPA | Personuppgiftsbiträdesavtal (PUB) | |
| Danger Zone | Riskzon | |

<!-- ORDLISTA-SLUT -->

## Uppräkningar i handboken (räknade)

Räknat i de engelska .mdx-filerna. Handbokens listor är inte alltid fullständiga
mot koden; kodläsarnas listor (twenty-01 till twenty-12) är facit för koden,
dessa är facit för vad användaren får veta.

| Uppräkning | Antal | Innehåll | Var i förlagan |
|---|---|---|---|
| Fälttyper i datamodellens tabell | 18 | Address, Array, Boolean, Currency, Date, Date & Time, Domain, Email, JSON, Links, Long Text, Multi-Select, Number, Phone, Rating, Relation, Select, Text | user-guide/data-model/capabilities/fields.mdx (avsnittet Field Types) |
| Fälttyper som nämns på andra ställen men saknas i tabellen | 4 | Full Name, Actor, File/Attachment (Files), Emails/Phones i pluralform som sammansatta typer. Kom-igång-sidan säger "20+ fälttyper". | getting-started/core-concepts/data-model.mdx; key-features.mdx; views-pipelines/capabilities/filters-and-sorting.mdx |
| Filteroperatorer (distinkta) | 14 | Contains, Doesn't contain, Is empty, Is not empty, Is, Is not, Greater than or equal, Less than or equal, Is relative, Is in past, Is in future, Is today, Is before, Is after or equal; fördelade på 9 grupper av fälttyper (HB-273) | user-guide/views-pipelines/capabilities/filters-and-sorting.mdx |
| Vytyper | 3 | Table, Kanban, Calendar | user-guide/views-pipelines/capabilities/*.mdx |
| Triggers i arbetsflöden | 7 | Record is Created, Record is Updated, Record is Updated or Created, Record is Deleted, Manual Trigger, On a Schedule, Webhook | user-guide/workflows/capabilities/workflow-triggers.mdx |
| Steg (actions) i arbetsflöden | 17 | Record: Create Record, Update Record, Delete Record, Search Records, Upsert Record, Pick Record (6). Flow: Iterator, Filter, Delay (3). Communication: Send Email, Draft Email, Create Calendar Event, Form (4). Integration: Code, HTTP Request (2). AI: AI Agent, Classify (2). Därtill appars logikfunktioner som steg. | user-guide/workflows/capabilities/workflow-actions.mdx |
| Fördelningslägen i Pick Record | 3 | Random, Round Robin, Load Balanced | workflow-actions.mdx |
| Delay-lägen | 2 | Duration (dagar, timmar, minuter, sekunder), Scheduled Date | workflow-actions.mdx |
| Widgettyper i dashboards | 7 | Bar Chart, Pie Chart, Line Chart, Aggregate Chart, iFrame, Table, Rich Text (gauge "på färdplanen") | user-guide/dashboards/capabilities/widgets.mdx |
| Diagraminställningar | 19 | Data (2): Source, Filter. X-axel (4): Data on display, Date granularity, Sort by, Omit zero values. Y-axel (8): Data on display, Ratio, Group by, Date granularity, Sort by, Cumulative, Min range, Max range. Stil (5): Colors, Axis name, Stacked bars, Data labels, Legend | user-guide/dashboards/capabilities/chart-settings.mdx |
| Datumindelningar i diagram | 8 | Day, Week, Month, Quarter, Year, Day of week, Month of year, Quarter of year | chart-settings.mdx |
| Behörighetsområden | 3 | Objects and Fields, Settings, Actions | user-guide/permissions-access/capabilities/permissions.mdx |
| Objektbehörigheter (standard för alla objekt) | 4 | See Records, Edit Records, Delete Records (mjuk), Destroy Records (permanent) | permissions.mdx |
| Fältbehörigheter | 3 | See Field, Edit Field, No Access | permissions.mdx |
| Inställningsbehörigheter som namnges | 1 + 6 | Settings All Access, eller exempelvis API-nycklar, arbetsytepreferenser, rolltilldelning, datamodell, säkerhet, arbetsflödeshantering ("e.g." – listan är inte uttömmande; se Oklarheter 14) | permissions.mdx |
| Åtgärdsbehörigheter som namnges | 1 + 3 | Application All Access, eller Send Email, Import CSV, Export CSV ("such as" – inte uttömmande) | permissions.mdx |
| Formatval i Experience | 5 | Time zone, Date format, Time format (12/24 h), Number format, Calendar start day (söndag/måndag) | user-guide/settings/capabilities/experience-settings.mdx |
| Temaval | 3 | Light, Dark, System settings | experience-settings.mdx |
| Kortkommandon som handboken nämner | 2 | Cmd+K / Ctrl+K (kommandomenyn), `/` (sök). Handboken hänvisar till kommandomenyn för en fullständig lista men återger den inte. | getting-started/core-concepts/layout.mdx; user-guide/getting-started/how-tos/navigate-around-twenty.mdx |
| Planer (moln) | 2 + 2 äldre | Pro, Organization; Pro (Early), Organization (Early). Organization finns även som självhostad. | user-guide/billing/capabilities/pricing-plans.mdx |
| Utfall i valideringsregelns förhandsgranskning | 3 | Valid, Blocked, Error | user-guide/data-model/capabilities/validation-rules.mdx |
| datePart-delar i valideringsregler | 8 | YEAR, QUARTER, MONTH, WEEK, DAY, DAY_OF_WEEK, HOUR, MINUTE | validation-rules.mdx |
| Orsaker i avregistreringslistan | 3 | Unsubscribed, Bounce, Complaint | user-guide/email-campaigns/how-tos/manage-unsubscribes-and-topics.mdx |

## Rättat vid kontroll

Stickprov av 38 rader mot källan (främst tal, gränser, standardvärden och
uppräkningar): HB-002, HB-009, HB-016, HB-026, HB-027, HB-032, HB-053, HB-063,
HB-068, HB-078, HB-081, HB-083, HB-086, HB-089, HB-115, HB-119, HB-165, HB-180,
HB-193, HB-205, HB-211, HB-216, HB-217, HB-273, HB-279, HB-296, HB-297, HB-298,
HB-333, HB-340, HB-342, HB-343, HB-344, HB-352, HB-370, HB-384, HB-385, HB-386.
Alla uppgifter i dessa rader gick att belägga i de angivna .mdx-filerna. Inga
rättelser behövdes.

| ID | Vad som stod | Vad som gäller | Sökväg |
|---|---|---|---|
| (inga) | | | |

## Det jag inte hann läsa

- `docs.json` (382 kB) är nu jämförd mot filerna för de engelska user-guide- och getting-started-sidorna (132 sidor i navigationen, 141 filer; skillnaden i HB-393). Övriga delar av docs.json (utvecklarfliken, språkversionerna) är inte lästa.
- Sidor med bara en hänvisning i tabellen (t.ex. calendar-view, table-views, fields-and-columns, workflow-runs, workflow-versions och flera recept under workflows/how-tos) lästes inte om vid kontrolläsningen; de kan ha fler detaljer än raderna återger.
- Uppräkningarna ovan är räknade ur handboken, inte ur koden. Fullständiga listor över behörighetsflaggor och kortkommandon finns inte i handboken.
- Utvecklardokumentationen (`packages/twenty-docs/developers`) ingick inte i uppdraget och är inte läst; handboken hänvisar dit för API, appar (logikfunktioner, frontkomponenter, valideringsregler i appar), självhosting och webhooks. De delarna täcks av andra underlag (twenty-07).
- Bilder och inbäddade videor i handboken är inte granskade (bara text).
- Licenskontrollen mot `@license Enterprise` gjordes som ett avbrutet stickprov i `twenty-server/src` (sökningen tidsgränsades efter 200 filer). Träffarna låg i `engine/permissions/internal`, `engine/permissions/record-share`, `engine/permissions/private-record`, `engine/permissions/permission-table` och migrationshanterarna för valideringsregler och radnivåregler. Övriga paket (front, shared, sdk) är inte genomsökta. Kodläsarna ska avgöra licensen för SSO, revisionslogg, användningsgränser, egen domän och supportåtkomst.

## Oklarheter

Motsägelser i handboken och sådant som bara går att avgöra i den körande appen:

1. **Obligatoriska fält:** datamodell-FAQ säger att egna fält inte kan göras obligatoriska, medan valideringsregler (Organization) uttryckligen gör detta. Importguiderna nämner "obligatoriska fält" som feltyp. Vilka fält är obligatoriska i praktiken?
2. **Många-till-många:** FAQ och importsidor säger "kommer H2 2026" respektive "H1 2026", men kopplingsobjekt med reglaget "This is a relation to a Junction Object" finns beskrivet som fungerande.
3. **API-gränser:** 100 anrop/min och 60 poster per batch (importguiden) mot 50/100 anrop/min per plan och 200 poster per anrop (export-FAQ).
4. **Exportformat:** CSV enligt exportguiden, Excel enligt export-FAQ.
5. **Datumformat vid import:** fältmappningen tillåter fyra format; felsökningsguiden säger att bara ÅÅÅÅ-MM-DD godtas.
6. **Nya Select-alternativ vid import:** importguiderna säger att de kan skapas i mappningssteget; fältmappningsguiden säger att de inte skapas automatiskt.
7. **Interna mejl:** reglaget "Sync Internal Emails" anges under Settings → Communication på en sida och Settings → General → Security på en annan; en felsökningssida säger att interna mejl aldrig synkas.
8. **Skriva mejl i appen:** sidan om att skicka mejl beskriver både "Compose email" i kommandomenyn och att inbyggd mejlskrivning är "på färdplanen" och att Reply omdirigerar till brevlådan.
9. **"Nya mejl syns direkt"** mot synkintervall var 5:e minut.
10. **Mejlsynk på Opportunities:** visar bara bolagets mejl, inte affärens personer; okänt om det gäller kalendern likadant.
11. **Formelfält och nästlade fält:** "H2 2026" i FAQ, "2026" i recept; valideringsreglernas villkorsspråk liknar en formelmotor som redan finns.
12. **@-omnämnanden:** saknas i anteckningar/uppgifter enligt receptet, men Inbox-notiser nämner "mentions". Vad omfattar omnämnanden i Inbox?
13. **SSO-protokoll:** nyckelfunktionssidan nämner OIDC, SSO-sidan bara SAML 2.0, Google Workspace och Entra ID. SSO-sidan placerar inställningen under Settings → Security; andra sidor använder Settings → General → Security.
14. **Behörigheter som bara nämns i förbigående:** "Create calendar event", "Layouts", "Impersonate", "Ask AI", "Billing", "Security", "Workspace settings" finns i olika sidor men inte i behörighetslistan. Hela listan måste läsas av i appen.
15. **Respitperiod efter "Cancel Plan"** anges inte.
16. **Postdelning och privata poster:** serverkoden har Enterprise-märkta moduler för postdelning (record share) och privata poster som handboken inte beskriver alls. Kodläsarna måste beskriva dem.
17. **"Enterprise-plan"** nämns bara i juridik-FAQ (ändrad DPA); prissidorna känner bara Pro och Organization.
18. **Dashboards:** "realtid" mot en manuell uppdateringsknapp; tidszon per betraktare.
19. **Kampanjer** är beta och måste slås på av Twenty; ytan går inte att kontrollera utan påslag.
20. **Arbetsflödeskörningar** "kan arkiveras automatiskt"; hur länge de sparas anges inte.
21. **Fälttyper:** datamodellens tabell har 18 typer, men Full Name, Actor och Files förekommer i filter- och kom-igång-sidorna utan att finnas i tabellen, och "20+ fälttyper" utlovas. Vilka typer som går att välja vid "+ New Field" syns bara i appen.
22. **Kortkommandon:** handboken säger att kommandomenyn visar kortkommandon för att nå objekt men återger dem inte; listan måste läsas av i appen eller i koden.
23. **Föräldralösa sidor** (HB-393) kan beskriva äldre beteende; där de krockar med sidor i navigationen bör navigationens sida gälla tills appen visat annat.
