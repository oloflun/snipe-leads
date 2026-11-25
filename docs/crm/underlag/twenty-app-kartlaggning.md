# Twenty i drift: genomgång av den hostade appen

Genomgången gjordes 2026-11-25 i arbetsytan `snajp.twenty.com` (provperiod, Antons konto,
enbart arbetsytans egna exempeldata). Twentys villkor § 10 tillåter att en agent använder
appen i webbläsaren för kontoinnehavarens räkning. Ingen e-post anslöts, inga
inställningar ändrades och inga poster skapades.

Det här är en beskrivning av vad som syns och vilka anrop appen gör. Ingen kod är hämtad
ur appen. Bilderna ligger i `docs/crm/bilder/twenty/`.

## Vad som inte gick

- **`rea` kördes inte.** MCP-servern dör vid start. `rea-agents` 6.10.1 kräver Node
  `^22.23.4 || ^24.22.1 || >=26.12.1` och datorn har Node 24.11.0. API-anropen fångades
  i stället med en logg runt `fetch` i sidan och med panelens nätverkslista.
- **Mobilvyn** gick inte att fånga: i panelens mobilemulering stannade appen på
  laddningsskelett. Mobilbeteendet tas ur källkodsinventeringen.
- **Ett anrop jag inte beställde:** när sidan Inställningar › Allmänt öppnades skickade
  appen själv en `UpdateWorkspace`. Inget fält ändrades av mig.

## Skalet

| Del | Iakttagelse | Bild |
|---|---|---|
| Vänsterrail | Arbetsytans namn överst med sök och fäll ihop. Tre lägen i en liten rad: Hem, AI-chatt, Inställningar. Under "Workspace" objekten: Companies, People, Opportunities, Tasks, Notes, Dashboards, Workflows (med Workflow Runs under), Campaigns. "Opened" visar senast öppnade sidor. Railen går att fälla ihop till ikoner och dra bredare. | 02 |
| Sidhuvud | Objektets ikon och namn litet till vänster. Till höger: Create (enda fyllda knappen), Ask AI, kommandomeny. | 02 |
| Vyrad | Vyns namn med antal ("All Companies · 5") som öppnar vyväljaren med "Add view". Till höger Filter, Sort, Options. | 02, 03 |
| Options | Layout (Table, List, Calendar, Kanban), Visibility (Workspace eller privat), Fields ("7 selected"), Group, Delete view. | 03, 04 |
| Filter | Sökruta, sedan "Visible fields" och "Hidden fields" (dolda fält går alltså att filtrera på: Annual Revenue, Deleted at, ID, Last update). | 05 |
| Kom igång | En räknare för provperioden, en stege av steg (Import your data, Import your contacts, Tailor your workspace, Follow up on closing deals, Install an app) och en AI-guide i sidopanelen som frågar "Where should we start?" med fyra val. Importkortet visar hur kolumner ur en HubSpot-export paras ihop med fält. | 01 |

## Listan

- Tabellen är tät: en rad är cirka 32 px, kolumnhuvudet bär fälttypens ikon, första
  kolumnen är postens namn som chip med logotyp, och varje rad har en kryssruta.
- Sista raden är "Add New". Under tabellen står en rad "Calculate" med ett aggregat per
  kolumn (Count all, Empty of Linkedin 100 %, Not empty of Address 5, Unique of Emails 5).
- Tavlan grupperar affärer per steg (New, Screening, Meeting, Proposal, Customer) med
  summa per kolumn i huvudet (80k, 75k ...), kort med fältrader och "+ New" i varje kolumn.
- Tomläget är en illustration, en rubrik ("Add your first Task"), en rad om API:t och en knapp.

## Posten

- Klick på en post öppnar den i en **sidopanel** till höger, med listan kvar. Adressen får
  `?panel=/object/company/<id>`, så panelen går att länka till. En knapp fäller ut posten
  till helsida.
- Panelens flikar: Home, Timeline, Tasks och "+4 More" (Notes, Files, Messages, Calendar).
- Fliken Home: fältgrupper som går att fälla ihop (General, Business, Contact, System), och
  därefter relationskort (People, Opportunities) med länk till listan och en penna.
- Helsidan: brödsmula med läge ("Companies / Airbnb (1/5)") och pilar till föregående och
  nästa post, fälten i en vänsterkolumn, flikarna (Timeline, Tasks, Notes, Files, Messages,
  Calendar) över resten.
- Sidfoten i panelen: fler åtgärder, favoritmarkera, Send Email.

## Kommandomenyn

Öppnas med Ctrl+K som en panel till höger, inte som en dialog mitt på skärmen. Avsnitt:

1. **Selection** (den aktuella posten): Add to Favorites, Edit, Delete, Duplicate.
2. **Object**: Edit Layout.
3. **Ask & find**: Ask AI (`@`), Search (`/`), New chat, Open chat.
4. **Create record**: en rad per objekt.
5. **Workspace**: Compose Email, Compose Campaign, manuella arbetsflöden (Quick Lead),
   Collapse sidebar, Copy link to page, byt tema.
6. **Go to**: nästa och föregående post, varje inställningssida, varje objekt. Vanliga mål
   har tvåstegs kortkommando: `G` sedan `C` (Companies), `D`, `N`, `O`, `P`, `T`, `S` (Settings).
7. **Developer**: Show logs.

Go to-listan visar också systemobjekt som annars inte syns i railen: Attachments,
Blocklists, Calendar events, Call Recordings, Campaigns, Lists, List Members, Messages,
Message Threads, Note Targets, Task Targets, Timeline Activities, Workflow Runs,
Workspace Members med flera.

## Arbetsflöden och dashboards

- Arbetsflödeslistan: Name, Statuses (Active), Recent runs, Last run, Runs 14d, Visibility,
  Last update. Två flöden följer med: "Quick Lead" och "Create company when adding a new person".
- Redigeraren: flikarna Overview, Flow, Runs. Knappar See Runs, Test, Deactivate. Flödet
  ritas uppifrån och ner: Trigger (Launch manually), Human Input (formulär), Data (Create
  Company), Data (Create Person), och ett plus för nästa steg.
- Dashboarden: ett rutnät av widgetar. Exemplet har rik text, ring ("Deals by Company"),
  staplat stapeldiagram ("Pipeline Value by Stage"), linje ("Revenue Timeline"), stapel per
  ägare, en iframe och två nyckeltal. Edit-knappen växlar till redigeringsläge.

## Inställningar

| Grupp | Sida | Innehåll |
|---|---|---|
| User | Profile | Bild, namn, e-post, tvåfaktor (autentiseringsapp), sätt lösenord via mejl, enheter med aktiv session, radera konto. |
| User | Experience | Tema (ljust, mörkt, system, och ett Enterprise-tema), språk, skala, om poster öppnas i sidopanel eller helsida, och format: tidszon, datumformat, tidsformat, talformat, veckans första dag. Varje format har valet "System settings" och visade här `2024 Mar 12`, `10:30`, `1 234,56`, måndag. |
| User | Apps preferences | Inställningar per installerad app. |
| Workspace | General | Flikarna General och Security. Logotyp, namn, underdomän eller egen domän, radera arbetsytan. |
| Workspace | Data model | Diagram över objekten, lista med Name, App (Standard eller Custom), Fields, Records, "Add object", "Visualize". Ett objekt har flikarna Fields, Settings, Layout; relationer (Has many) och fält med datatyp (Address, Currency, Actor, Date and Time, Links, Text). |
| Workspace | Layout | "Customize" och en sammanräkning: Commands 115, Sidebar items 13, Views 53, Pages 58, Widgets 0. |
| Workspace | Members | Flikarna Team, Invite, Roles. Roller: Admin (Standard) och Member (Custom), "Create Role". |
| Workspace | Billing | Inte öppnad. |
| Workspace | Developers | Flikarna API, Webhooks, Apps, CLI. API: lekplats för REST eller GraphQL per schema (Core eller Metadata), API-nycklar med Name, Role, Expiration. Webhooks: URL-lista och "Create webhook". |
| Workspace | Apps | Marketplace (beta) och Installed. Appar: Claude, ChatGPT, Twenty CLI, Call Recorder, People Data Labs, Last contact, Exa, Slack, Teams, Fathom, Granola. |
| Workspace | AI | Flikarna MCP, Models, Skills, Tools, Usage. MCP-sidan har färdiga installationslänkar för ett femtontal klienter. |
| Workspace | Communication | Flikarna Emails, Whatsapp (snart), Calls (snart). Delade e-postkanaler, synk av interna mejl, spärrlista, spårning av öppningar och klick i kampanjer, avregistrering. |
| Other | Community, Support, Documentation, Logout | |

## API-kartan (208 anrop under genomgången)

Appen talar GraphQL över två ändpunkter. Inga REST-anrop gjordes av själva gränssnittet.

| Ändpunkt | Används till | Operationer som sågs |
|---|---|---|
| `POST /graphql` | Poster i arbetsytans objekt | `FindMany<Objekt>` (`filter`, `limit`, `orderBy`), `FindOne<Objekt>` (`objectRecordId`), `Aggregate<Objekt>` (`filter`), `<Objekt>GroupByRecords` och `<Objekt>GroupByAggregates` (tavlan: `groupBy`, `orderByForRecords`), samt arbetsflödenas egna: `GetCoreWorkflows`, `GetCoreWorkflow`, `GetCoreWorkflowVersions`, `GetCoreWorkflowVersion`, `GetCoreWorkflowRunInsights`, `GetCoreWorkflowsWithCurrentVersions` |
| `POST /metadata` | Metadata, inställningar, diagram, realtid | `GetRecordPermissions`, `MyConnectedAccounts`, `MyMessageChannels`, `MyCalendarChannels`, `FindManyTimelineActivityTypes`, `FindOnePageLayout`, `PieChartData`, `BarChartData`, `LineChartData`, `GetIframeWidgetMediaPermissions`, `CurrentUserSessions`, `CurrentUserApplicationAuthorizations`, `ObjectRecordCounts`, `MostlyEmptyFieldMetadataIds`, `GetApiKeys`, `GetWebhooks`, `FindManyMarketplaceApps`, `UpdateWorkspace`, `TrackAnalytics` |
| Realtid | Varje lista och post anmäler sin fråga | `AddQueryToEventStream` när en vy öppnas och `RemoveQueryFromEventStream` när den lämnas (16 av vardera). Klienten prenumererar alltså på just de frågor som visas, och servern skickar ändringar för dem. |

Tre saker att ta med till Snajp CRM:

1. **En operation per objekt och verb, med samma parametrar för alla objekt.** Det är det som
   gör att egna objekt fungerar utan ny kod i gränssnittet.
2. **Aggregat är egna anrop**, skilda från radhämtningen. Sidfotens "Calculate" och tavlans
   kolumnsummor laddas om utan att raderna hämtas igen.
3. **Realtid är prenumeration på en fråga**, inte på ett objekt. Det håller trafiken nere när
   många har olika vyer öppna.

## Vad genomgången säger om gränssnittet

- Ytan är nästan utan färg. Färg bär betydelse på tre ställen: objektets ikon, stegets
  etikett på tavlan och den enda fyllda knappen (Create).
- Typsnittet är Inter i 13 px för data och etiketter. Rubriker är små: objektnamnet i
  sidhuvudet är inte större än brödtexten.
- Allt sekundärt öppnas åt höger: posten, kommandomenyn och AI-chatten delar samma
  sidopanel. Listan blir aldrig övertäckt.
- Det som saknas för en svensk användare: gränssnittet stod på engelska trots svensk
  inloggningssida, exempeldatan är amerikansk (dollar, amerikanska adresser, `+1`-nummer),
  och bolaget har varken organisationsnummer, momsnummer eller bransch som fält.
