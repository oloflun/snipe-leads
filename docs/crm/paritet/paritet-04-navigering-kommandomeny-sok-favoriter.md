# Paritet 04: Navigering, kommandomeny, sök och favoriter

Området är skalet runt arbetet i Twenty: sidofältet med favoriter och menyposter, kommandomenyn (Ctrl K) med sina kommandon, den globala sökningen, kortkommandon, inkorg och aviseringar, introduktionen och appens ramverk för adresser, fel och mobil. Här står varje funktionsrad ur `docs/crm/underlag/twenty-04-navigering-kommandomeny-sok-favoriter.md` med sitt läge mot det som finns i Snajp CRM i arbetskatalogen 2026-11-26.

Antal per läge (166 rader): verifierad 2, byggd 6, delvis 40, inte gjord 117, avstår 1.

## De största luckorna

- Ingen global sökning över alla objekt. Varje lista söker i sina egna fasta kolumner med en delsträng (`q` i `lagring.lista_poster`), och kommandopaletten söker bara bolag, inte personer, affärer eller uppgifter. Ingen rangordning, ingen ordbörjan, accenter räknas.
- Inga favoriter alls, och sidofältet går inte att anpassa: inga mappar, inga egna länkar, inga vyer eller poster i menyn. Menyn är fast i `CrmRam.tsx`.
- Kommandopaletten har bara Gå till, tre Skapa-kommandon och bolagssök. Inga kommandon som gäller markeringen eller den post man står på, inga sektioner efter sammanhang, inga reservkommandon.
- Inga kortkommandon utöver Ctrl K: inget `/` för sök, inga G-sekvenser, ingen hjälpmeny som listar kortkommandon.
- Ingen export till CSV, ingen sammanslagning av dubbletter och ingen massuppdatering av valfria fält. Åtgärdsraden kan bara ändra relation (bolag), sätta Kontakta inte (personer) och ta bort.
- Permanent radering finns bara i API:t, inte i papperskorgen i gränssnittet.
- Ingen egen postsida, ingen brödsmula och ingen nästa eller föregående post: posten visas bara i panelen.
- Ingen högerklicksmeny på poster och inga snabbåtgärder för att skapa uppgift, anteckning eller bilaga från posten, fast backend för dem finns.
- Inga banderoller överst (kundbesök, läsroll, demo, raderad post) och ingen notisräknare i sidofältet.
- Introduktion och kom igång ligger kvar utanför CRM:et i Snajps egen `/onboarding`; arbetsyteväxlaren saknar tema, språk, logga ut och byte av kund.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| NAV-001 | En integratör kan söka i alla objekt på en gång med en enda fråga. | delvis | Fritextsökning `q` finns per objekt (`/v1/companies`, `/v1/people`, affärer, uppgifter, anteckningar m.fl.) i `snajp-support/app/crm/lagring.py:lista_poster`, prövad i `test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr` (`snajp-support/tests/crm/test_api.py`). Saknas: en fråga över alla objekt, listor över objekt att ta med eller utesluta. | 3 |
| NAV-002 | Varje sökträff beskrivs likadant oavsett objekt: id, objekttyp, etikett och bild. | delvis | Kommandopaletten (`components/crm/app/Kommandopalett.tsx`) visar bolagsträffar med namn, ort och initialavatar. Saknas: en enhetlig träff med objekttyp och rangvärden, och träffar för andra objekt än bolag. | 3 |
| NAV-003 | Vilka objekt som söks styrs av en sökbarhetsflagga per objekt. | delvis | Vilka kolumner som söks är fast per objekt i `lagring._LISTA`. Saknas: en flagga per objekt, som bara behövs med egna objekt. | ej planerad |
| NAV-004 | Sökningen går mot ett förberäknat sökfält per objekt där accenter ignoreras. | delvis | Sökningen är `ilike` över de fasta kolumnerna i `lagring._LISTA` (namn, orgnr, domän, ort för bolag; namn, e-post, titel för personer). Saknas: förberäknat sökindex och accentokänslighet. | 3 |
| NAV-005 | Sökningen delar texten i ord och matchar ordbörjan, alla ord i första hand. | delvis | `lista_poster` söker hela texten som en delsträng (`%q%`). Saknas: uppdelning i ord, prefixmatchning, alla-ord före något-ord, och tecknen `%` och `_` neutraliseras inte. | 3 |
| NAV-006 | Sökträffarna rangordnas över objektgränser med objektprioritet. | inte gjord | Varje objekt söks för sig och sorteras på namn eller ändringstid; ingen rangordning. | 3 |
| NAV-007 | Sökresultatet kan bläddras med markör. | delvis | Markör per objekt i `lista_poster`, prövad i `test_sidindelning_med_markor` (`snajp-support/tests/crm/test_api.py`). Saknas: en markör över en sammanslagen sökning. | 3 |
| NAV-008 | Sökning på kinesiska, japanska och koreanska fungerar via en reservsökning på delsträng. | avstår | Ersätts av det Snajp redan har: sökningen i `lagring.lista_poster` är redan en delsträngssökning (`ilike`), så tecken i alla skript träffar utan reservsteg. | |
| NAV-009 | Sökträffar visar profilbild, filbild eller favicon. | delvis | Paletten visar en initialavatar för bolag (`Kommandopalett.tsx`, `Avatar`). Saknas: riktiga bilder och favicon. | 3 |
| NAV-010 | Sökningen respekterar filter och visar inte raderade poster om man inte ber om dem. | byggd | `lagring.lista_poster` lägger `q` ihop med likhetsfilter (`lika`) och utesluter raderade om inte `include_deleted` är satt. | |
| NAV-011 | Fel i sökningen ges som begripliga felkoder, och bara behöriga får söka. | byggd | `q` högst 200 tecken med valideringsfel på två språk (`snajp-support/app/api/crm_v1.py`, `_LISTPARAMETRAR`); sökning kräver nyckel med läsomfång (`snajp-support/app/crm/nycklar.py`). Twentys metadatafel finns inte eftersom objekten är fasta. | |
| NAV-012 | En integratör kan läsa alla menyposter som gäller den inloggade, delade och egna. | inte gjord | Menyn är fast i `components/crm/app/CrmRam.tsx`; inga menyposter som data. | ej planerad |
| NAV-013 | En menypost har en av tolv typer: objekt, vy, post, länk, mapp med flera. | inte gjord | Inga menyposttyper; sidofältet har fem fasta poster. | ej planerad |
| NAV-014 | Inbyggda sektioner (favoriter, AI-sektioner) kan finnas i menyn. | inte gjord | Sidofältet har två fasta sektioner, Arbetsyta och Data (`CrmRam.tsx`). | ej planerad |
| NAV-015 | Menyposter kan ordnas i hierarki: flik, sektion, mapp, post. | inte gjord | Ingen hierarki utöver de två fasta sektionerna. | ej planerad |
| NAV-016 | Användaren kan skapa en menypost, delad eller som egen favorit. | inte gjord | Favoriter finns inte i Snajp CRM. | ej planerad |
| NAV-017 | Användaren kan ändra en menyposts position, förälder, namn, ikon och färg. | inte gjord | Inga redigerbara menyposter. | ej planerad |
| NAV-018 | Arbetsytan kan dölja och återställa menyposter som en installerad app lagt dit. | inte gjord | Inga appar från tredje part och inga menyposter som data. | ej planerad |
| NAV-019 | Användaren kan ta bort menyposter, med innehållet i en mapp. | inte gjord | Inga menyposter att ta bort. | ej planerad |
| NAV-020 | Favoriter och menyposter städas bort när det de pekar på raderas. | inte gjord | Inga favoriter eller menyposter som kan peka på poster. | ej planerad |
| NAV-021 | En menypost som pekar på en post visar postens namn och bild. | inte gjord | Inga menyposter som pekar på poster. | ej planerad |
| NAV-022 | Menypostens namn översätts till användarens språk. | delvis | De fasta menyposterna är tvåspråkiga via `OBJEKT[...].namn` och `useLocale().text` (`CrmRam.tsx`, `kit.tsx`). Saknas: översättning av menyposter som data, som inte finns. | ej planerad |
| NAV-023 | AI-assistenten kan läsa, skapa, ändra och ta bort menyposter. | inte gjord | Ingen AI-assistent i CRM:et och inga menyposter. | ej planerad |
| NAV-024 | Listan med menyposter kan avgränsas på omfång, förälder, typ och antal. | inte gjord | Inga menyposter. | ej planerad |
| NAV-025 | Appar kan leverera egna menyposter via sitt manifest. | inte gjord | Inga appar från tredje part i CRM:et. | ej planerad |
| NAV-026 | En integratör kan läsa alla kommandon i kommandomenyn. | inte gjord | Kommandona är fasta i `Kommandopalett.tsx`; inget API för dem. | ej planerad |
| NAV-027 | Ett kommando har etikett, kort etikett, ikon, position, fästning och kortkommandon. | delvis | Paletten har fasta kommandon med etikett och ikon på två språk (`Kommandopalett.tsx`, `kommandon`). Saknas: kort etikett, position, fästning, kortkommandon och villkor. | ej planerad |
| NAV-028 | Ett kommando gäller i ett visst sammanhang: alltid, i ett objekt, vid markering eller som reserv. | inte gjord | Alla paletter-kommandon gäller alltid; inga tillgänglighetstyper. | 3 |
| NAV-029 | Vad ett kommando gör avgörs av en motornyckel bland ett sjuttiotal. | delvis | Paletten har tre slag: gå till, skapa och bolagsträff (`slag` i `Kommandopalett.tsx`). Saknas: de flesta åtgärder (radera, exportera, slå ihop, favorit, arbetsflöden, AI m.fl.). | 3 |
| NAV-030 | Navigeringskommandon pekar på en sökväg eller ett objekt. | delvis | Gå till-kommandona pekar på en adress (`mal` i `Kommandopalett.tsx`). Saknas: objekt som mål och validering, eftersom kommandona inte är data. | ej planerad |
| NAV-031 | Användaren kan skapa egna kommandon som startar ett arbetsflöde eller visar en appkomponent. | inte gjord | Inga arbetsflöden eller appar i CRM:et. | ej planerad |
| NAV-032 | Användaren kan ändra ett kommando, och systemkommandon sparas som överlagring. | inte gjord | Kommandona går inte att ändra. | ej planerad |
| NAV-033 | Användaren kan återställa ett systemkommando till standard. | inte gjord | Inga ändringsbara kommandon. | ej planerad |
| NAV-034 | Användaren kan ta bort ett kommando. | inte gjord | Inga kommandon som data. | ej planerad |
| NAV-035 | En app kan lägga till egna poster i inställningsmenyn. | inte gjord | Inga appar från tredje part; CRM:et har inga inställningssidor än. | ej planerad |
| NAV-036 | Systemet håller reda på var i introduktionen varje användare är. | delvis | `app/crm/layout.tsx` kör `requireOnboarded()`, så en kund som inte gått igenom Snajps introduktion skickas till `/onboarding` utanför CRM:et. Saknas: stegstatus per användare i CRM:ets form. | 5 |
| NAV-037 | Användaren kan gå tillbaka ett steg i introduktionen. | inte gjord | Snajps introduktion ligger utanför CRM:et (`app/onboarding/`). | 5 |
| NAV-038 | Användaren kan hoppa över steget att synka e-post i introduktionen. | inte gjord | Ingen e-postsynk in i CRM:et; introduktionen ligger utanför. | 5 |
| NAV-039 | Introduktionen föreslår kollegor att bjuda in, hämtade ur e-posten. | inte gjord | Ingen e-postsynk som kan ge förslag. | ej planerad |
| NAV-040 | Större bolag erbjuds att boka ett samtal med leverantören i introduktionen. | inte gjord | Inget sådant steg. | ej planerad |
| NAV-041 | Arbetsytan får krediter beroende på bolagets storlek. | inte gjord | Snajp har inga krediter; CRM:et är ett tillägg (`snajp-support/app/crm/tillgang.py`). | ej planerad |
| NAV-042 | Användaren får en kom igång-lista anpassad efter sin profil. | inte gjord | Kom igång-kortet på översikten är planerat (OV-045 i `docs/crm/MIGRERING-FUNKTIONSLISTA.md`). | 5 |
| NAV-043 | Kom igång-steg visas bara när användaren har behörighet att utföra dem. | inte gjord | Ingen kom igång-lista. | 5 |
| NAV-044 | Varje kom igång-steg har titel, beskrivning, ikon och klar-text. | inte gjord | Ingen kom igång-lista. | 5 |
| NAV-045 | Användaren kan välja, slutföra, snooza och dölja kom igång-listan. | inte gjord | Ingen kom igång-lista. | 5 |
| NAV-046 | Användaren kan förhandsvisa och skapa kom igång-arbetsflöden. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-047 | Webbläsaren kan registrera sig för aviseringar hos kända aviseringstjänster. | inte gjord | Inga webbaviseringar. | ej planerad |
| NAV-048 | Användaren väljer vad som ger avisering: allt, bara omnämnanden eller inget. | inte gjord | Inga webbaviseringar; Snajps mejlnotiser (SK-170) är något annat. | ej planerad |
| NAV-049 | Servern skickar aviseringar till alla användarens webbläsare. | inte gjord | Inga webbaviseringar. | ej planerad |
| NAV-050 | Systemet vet vilka medlemmar som har appen öppen och i vilken flik. | inte gjord | Ingen fliknärvaro. | ej planerad |
| NAV-051 | Väntande arbetsflöden och agentkörningar kan vakna av tid, händelse eller svar. | inte gjord | Inga arbetsflöden eller agenter i CRM:et. | ej planerad |
| NAV-052 | Användaren öppnar och stänger kommandomenyn med Ctrl K eller Cmd K. | verifierad | `Kommandopalett.tsx` (`useHotkeys` för `mod+k` och `ctrl+k`, växlar öppen och stängd); öppen palett i `docs/crm/bilder/app/palett-1440.png`. Snajp visar den som dialog mitt på skärmen, inte som högerpanel (DESIGN-CRM.md § Skalet). | |
| NAV-053 | Användaren kan börja söka poster direkt genom att trycka snedstreck. | inte gjord | Bara Ctrl K öppnar paletten. | 3 |
| NAV-054 | Användaren kan börja fråga AI:n direkt genom att trycka snabel-a. | inte gjord | Ingen AI-chatt i CRM:et. | ej planerad |
| NAV-055 | Escape tömmer sökningen, backar eller stänger kommandomenyn. | delvis | Escape stänger paletten (Astryx `CommandPalette`, "Esc Stäng" syns i `palett-1440.png`). Saknas: undersidor att backa i, och backsteg i tom sökruta. | 3 |
| NAV-056 | Kommandomenyn listar kommandon i sektioner i fast ordning. | delvis | Paletten grupperar i Gå till, Skapa och Bolag (`group` i `Kommandopalett.tsx`). Saknas: Twentys åtta sektioner (Markering, Aktuell vy, Detta objekt m.fl.). | 3 |
| NAV-057 | Kommandomenyn visar bara kommandon som passar där användaren står. | inte gjord | Paletten visar samma kommandon överallt. | 3 |
| NAV-058 | Användaren kan filtrera kommandona genom att skriva. | byggd | `Kommandopalett.tsx`: `enkel()` gör texten till gemener utan accenter och filtrerar kommandonas etiketter; tom text visar alla. | |
| NAV-059 | Hittar sökningen inget kommando erbjuds "sök poster" och "fråga AI" med texten. | delvis | Från två tecken söks bolag med texten automatiskt (`Kommandopalett.tsx`, `search`), annars "Inga träffar". Saknas: reservkommandon som rader, och AI. | ej planerad |
| NAV-060 | Användaren kan söka poster i alla objekt från panelens söksida, med förhandsvisning vid hovring. | delvis | Bolag söks mot `/v1/companies?q=` med 180 ms fördröjning, trimmad text, högst 8 träffar och fyrkantig avatar (`Kommandopalett.tsx`). Saknas: personer och övriga objekt, avgränsning till ett objekt, förhandsvisning vid hovring. | 3 |
| NAV-061 | Kommandon kan fästas som knappar i sidhuvudet med förlopp och enbokstavskortkommando. | inte gjord | Sidhuvudet har en fast primärknapp per vy (`Sida.tsx`, `Sidhuvud`), inga fästa kommandon. | ej planerad |
| NAV-062 | Användaren kan anpassa kommandomenyn i ett redigeringsläge. | inte gjord | Kommandona är fasta i koden. | ej planerad |
| NAV-063 | Kommandon kan nås via högerklick på poster. | inte gjord | Ingen snabbmeny vid högerklick i `BolagVy.tsx` eller `PersonerVy.tsx`. | 3 |
| NAV-064 | Användaren kan skapa en post i valfritt objekt från kommandomenyn. | delvis | Paletten har "Nytt bolag", "Ny anslutning" och "Ny nyckel" (`Kommandopalett.tsx`, beställning via `?ny=1` och `useBestallning` i `kit.tsx`). Saknas: ny person, affär, uppgift och övriga objekt. | 3 |
| NAV-065 | Användaren kan radera markerade poster till papperskorgen. | byggd | Åtgärdsraden i `BolagVy.tsx` (`taBort`) och `PersonerVy.tsx`: bekräftelse, radering i mängd med förlopp, Ångra i notisen. Nås från åtgärdsraden, inte från paletten. | |
| NAV-066 | Användaren kan återställa raderade poster. | verifierad | Återställ per rad i `components/crm/app/Papperskorg.tsx` och Ångra efter radering i `BolagVy.tsx`; prövad i `test_papperskorgen_aterstaller_och_permanent_radering_tommer` (`snajp-support/tests/crm/test_api.py`). | |
| NAV-067 | Användaren kan radera poster permanent efter en varning. | delvis | `DELETE /v1/companies/{id}?permanent=true` och samma för personer (`crm_v1.py`, `_radera`), prövad i `test_papperskorgen_aterstaller_och_permanent_radering_tommer`. Saknas: knappen i papperskorgen i gränssnittet. | 3 |
| NAV-068 | Användaren kan exportera markerade poster eller hela vyn till CSV. | inte gjord | Ingen export till fil i CRM:et. | 3 |
| NAV-069 | Användaren kan lägga markerade poster bland favoriter och ta bort dem, med Shift F. | inte gjord | Favoriter finns inte. | ej planerad |
| NAV-070 | Användaren kan slå ihop flera poster eller en post med en annan. | inte gjord | Ingen sammanslagning för hand; synken skyddar bara mot dubbletter på orgnr och e-post. | 3 |
| NAV-071 | Användaren kan massuppdatera valda fält på markerade poster. | delvis | "Ändra relation" för markerade bolag (`BolagVy.tsx`) och "Kontakta inte" för markerade personer (`PersonerVy.tsx`). Saknas: valfria fält. | 3 |
| NAV-072 | Användaren kan dela en post. | inte gjord | Ingen delningsfunktion; postens adress `?bolag=<id>` finns men erbjuds inte som delning. | 3 |
| NAV-073 | Användaren kan gå till nästa och föregående post från en postsida. | inte gjord | Ingen postsida och ingen bläddring mellan poster i panelen. | 3 |
| NAV-074 | Användaren kan visa och dölja raderade poster, skapa vy och importera från kommandomenyn. | delvis | Papperskorgen är en vy i vyraden (`BolagVy.tsx`, `PersonerVy.tsx`, filtret `papperskorg`). Saknas: som kommando, skapa vy och import i gränssnittet. | 3 |
| NAV-075 | Ett kommando kan starta ett arbetsflöde på markerade poster. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-076 | Globala kommandon finns för att skriva e-post, skriva kampanj, ny AI-chatt och redigera layout. | inte gjord | Inget av dem finns i paletten. | ej planerad |
| NAV-077 | Ett kommando som kraschar slår inte ut resten av menyn. | delvis | Paletten fångar fel i bolagssöket och visar kommandona i stället (`Kommandopalett.tsx`, `catch`); vyns felgräns `app/crm/error.tsx`. Saknas: felgräns per kommando. | 3 |
| NAV-078 | Appen vet alltid var användaren står: objekt, vy, markering och filter. | delvis | `CrmRam.tsx` läser aktiv vy ur adressen; varje vy håller sin markering och sitt filter (`BolagVy.tsx`); beställningar går via adressen (`useBestallning`). Saknas: ett delat sammanhang som kommandon kan läsa. | 3 |
| NAV-079 | Markeringen kan vara en lista av poster eller "alla utom". | delvis | Markering som lista av id (`useTableSelectionState` i `BolagVy.tsx`, `PersonerVy.tsx`). Saknas: läget "alla utom" och åtgärder mot ett filter. | 3 |
| NAV-080 | Användaren kan se alla kortkommandon i en hjälpmeny. | inte gjord | Ingen hjälpmeny; bara `Kbd` vid sökraden i sidofältet. | 3 |
| NAV-081 | Kortkommandon gäller bara där fokus ligger. | delvis | Astryx `useHotkeys` och dialogernas fokusfälla (`Kommandopalett.tsx`). Saknas: en fokusstapel för flera kortkommandon, eftersom det bara finns ett. | 3 |
| NAV-082 | Sidofältet har lägena Hem, AI eller Inkorg och Inställningar. | inte gjord | Sidofältet har ett läge; Inställningar leder ut till `/settings` (`CrmRam.tsx`). | 5 |
| NAV-083 | Startsidan väljs automatiskt utifrån menyn och behörigheter. | delvis | `/crm` leder alltid till översikten (`app/crm/page.tsx`), och ej inloggad går till inloggningen (`proxy.ts`). Saknas: val utifrån menyposter. | ej planerad |
| NAV-084 | Appen minns senast besökta vy per objekt. | inte gjord | Vyvalet sparas inte (`BolagVy.tsx`, `PersonerVy.tsx`); inga sparade vyer. | ej planerad |
| NAV-085 | Navigeringsmenyn visar favoriter och arbetsytans poster med typens namn, ikon och färg. | delvis | Fasta sektioner Arbetsyta och Data med objektikon i objektets färg och vald post utifrån adressen (`CrmRam.tsx`, `post`), synligt i `docs/crm/bilder/app/oversikt-1440.png`. Saknas: favoritdelen och menyposttyperna. | ej planerad |
| NAV-086 | Långa sektioner i menyn fälls ihop efter fem poster med Visa mer. | inte gjord | Sektionerna har två och tre poster. | ej planerad |
| NAV-087 | Mappar i menyn kan fällas ut och ihop. | inte gjord | Inga mappar. | ej planerad |
| NAV-088 | Användaren kan anpassa sidofältet i ett redigeringsläge. | inte gjord | Sidofältet är fast. | ej planerad |
| NAV-089 | Användaren kan lägga till objekt, vyer, poster, mappar och länkar i menyn. | inte gjord | Sidofältet är fast. | ej planerad |
| NAV-090 | Användaren kan ordna menyn med dra och släpp eller menyval. | inte gjord | Sidofältet är fast. | ej planerad |
| NAV-091 | Användaren kan byta namn, ikon och färg på menyposter och mappar. | inte gjord | Sidofältet är fast. | ej planerad |
| NAV-092 | Användaren kan ta bort en mapp med innehåll efter bekräftelse. | inte gjord | Inga mappar. | ej planerad |
| NAV-093 | Användaren kan ta bort en post från sidofältet eller från favoriter. | inte gjord | Inga favoriter eller redigerbara menyposter. | ej planerad |
| NAV-094 | Sidofältet kan delas in i flikar och sektioner som döps om och ordnas. | inte gjord | Två fasta sektioner. | ej planerad |
| NAV-095 | Inbyggda sektioner (favoriter, AI) visas efter behörighet. | inte gjord | Inga inbyggda sektioner. Grupper per produkt är planerade (Iris, Kundtjänst), men det är en annan sak. | ej planerad |
| NAV-096 | Arbetsyteväxlaren samlar byte av arbetsyta, inbjudan, tema, postvisning och utloggning. | delvis | Arbetsyteväxlaren i `CrmRam.tsx` (`SideNavHeading`) visar arbetsytans namn med menyn Till arbetsytan och Inställningar. Saknas: tema, språk, logga ut, byt kund, bjud in (planerade i `MIGRERING-FUNKTIONSLISTA.md` § Sidofältet). | 5 |
| NAV-097 | Användaren kan välja om poster öppnas i sidopanel eller som hel sida. | inte gjord | Posten öppnas bara i panelen (`BolagPanel.tsx`, `PersonPanel.tsx`); ingen postsida. | ej planerad |
| NAV-098 | En växel i sidofältet slår på utvecklarloggar. | inte gjord | Ingen loggväxel. | ej planerad |
| NAV-099 | Inloggning och registrering visar vilka arbetsytor användaren kan nå. | inte gjord | Inloggningen ligger utanför CRM:et (`/login`). | 5 |
| NAV-100 | Användaren ser sina AI-chattar i en inkorg med lista och konversation. | inte gjord | Ingen AI-chattinkorg. | ej planerad |
| NAV-101 | Användaren kan filtrera AI-inkorgen med förinställda filter. | inte gjord | Ingen AI-chattinkorg. | ej planerad |
| NAV-102 | Användaren kan triagera AI-chattar: klar, snooza, öppna igen. | inte gjord | Ingen AI-chattinkorg. | ej planerad |
| NAV-103 | Användaren kan navigera i chattlistan med tangentbordet och markera flera. | inte gjord | Ingen AI-chattinkorg. | ej planerad |
| NAV-104 | AI-chattar kan organiseras i kanaler och direktmeddelanden. | inte gjord | Ingen AI-chattinkorg. | ej planerad |
| NAV-105 | Inkorgen visar markering och antal för olästa och väntande chattar. | inte gjord | Ingen AI-chattinkorg. Snajps notisräknare (SK-171) är planerad men gäller Leads. | ej planerad |
| NAV-106 | Användaren får webbläsaraviseringar om AI-chattar. | inte gjord | Inga webbaviseringar. | ej planerad |
| NAV-107 | Appen rapporterar fliknärvaro var 30:e sekund. | inte gjord | Ingen fliknärvaro. | ej planerad |
| NAV-108 | Banderoller överst informerar om systemtillstånd, fakturering, personifiering och raderad post. | delvis | Helsidan när tillägget saknas (`components/crm/app/Tillagg.tsx`, `TillaggSaknas`) och synkkortet i sidofältet (`CrmRam.tsx`, `Synkkort`). Saknas: banderoller överst för kundbesök, läsroll och demo (SK-076 till SK-079) och för raderad post. | 4 |
| NAV-109 | En supportchatt kan öppnas från appen. | inte gjord | Felsidan hänvisar till kontakt@snajp.se (`app/crm/error.tsx`); ingen supportchatt i CRM:ets skal. Kontakt i arbetsyteväxlaren är planerad. | 5 |
| NAV-110 | Ny användare leds steg för steg genom introduktionen i fast ordning. | inte gjord | Snajps introduktion finns i `app/onboarding/`, utanför CRM:et (SK-110 till SK-127). | 5 |
| NAV-111 | Arbetsytan skapas och aktiveras automatiskt med en väntscen och berikning från e-postdomänen. | inte gjord | Väntan medan arbetsytan läggs upp finns i Snajps introduktion utanför CRM:et (SK-118). | 5 |
| NAV-112 | Användaren kan ansluta e-post och kalender i introduktionen. | inte gjord | Ingen e-post- eller kalendersynk in i CRM:et; att koppla inkorg hör till Snajps introduktion utanför CRM:et. | 5 |
| NAV-113 | Användaren skapar sin profil med namn, titel och bild. | inte gjord | Kontaktpersonen fylls i Snajps introduktion utanför CRM:et (SK-114). | 5 |
| NAV-114 | Användaren bjuder in kollegor i introduktionen. | inte gjord | Inget inbjudningssteg; teamet hanteras i Snajps inställningar utanför CRM:et. | 5 |
| NAV-115 | Användaren kan boka ett samtal i introduktionen. | inte gjord | Inget sådant steg. | ej planerad |
| NAV-116 | Användaren väljer plan och startar provperiod. | inte gjord | Paket väljs i Snajps introduktion utanför CRM:et (SK-117); CRM-tillägget är fritt under provperioden (`tillgang.py`). | 5 |
| NAV-117 | Användaren tjänar gratiskrediter genom att slutföra introduktionens steg. | inte gjord | Snajp har inga krediter. | ej planerad |
| NAV-118 | Användaren kan gå tillbaka i introduktionen. | inte gjord | Introduktionen ligger utanför CRM:et. | 5 |
| NAV-119 | Efter introduktionen visas en kom igång-sida med stegkort och förhandsvisning per steg. | inte gjord | Kom igång-kortet på översikten är planerat (OV-045). | 5 |
| NAV-120 | Kom igång kan snoozas eller döljas, och ett kort i sidofältet leder dit. | inte gjord | Ingen kom igång-lista. | 5 |
| NAV-121 | Appen skickar användaren till rätt sida utifrån inloggning, arbetsyta och introduktion. | delvis | `proxy.ts` skickar ej inloggad till `/login` med `next` tillbaka; `app/crm/layout.tsx` ger 404 för andra än plattformsadmin och kör `requireOnboarded()`. Saknas: plan krävs, avstängd arbetsyta och kom igång-sidan som mål. | 5 |
| NAV-122 | Användaren kan hoppa till objekt med G följt av en bokstav. | inte gjord | Inga G-kortkommandon. | 3 |
| NAV-123 | Sidofältet kan fällas ihop, fällas ut och ändras i bredd, och läget minns. | delvis | Hopfällning som minns i webbläsaren (`CrmRam.tsx`, `fallIhop` och `localStorage`), synlig i `docs/crm/bilder/app/nav-hopfalld-1440.png`. Saknas: ändring av bredd och hopfällbara sektioner. | 3 |
| NAV-124 | Länkar i menyn och listor beter sig som riktiga länkar, med ny flik vid modifierare. | delvis | Menyposterna är riktiga länkar via `LinkProvider` med `NextLink` (`CrmRam.tsx`). Saknas: postchipen som öppnar panelen i listorna är knappar, inte länkar (`BolagVy.tsx`, `PersonerVy.tsx`, `onClick` på `Postchip` och `Personchip`), och ingen navigering redan vid musknapp ned. | 3 |
| NAV-125 | Sidhuvudet visar en brödsmula med objekt, vy och post. | inte gjord | Sidhuvudet visar objektets ikon och rubrik (`Sida.tsx`, `Sidhuvud`), ingen brödsmula. | 3 |
| NAV-126 | Webbläsarflikens titel och ikon speglar sidan och väntande uppmärksamhet. | delvis | Titeln "Snajp CRM" för hela CRM:et (`app/crm/layout.tsx`, `metadata`). Saknas: titel per vy och prick på ikonen. | 3 |
| NAV-127 | Inte hittad-sidan hjälper användaren tillbaka. | delvis | Okända adresser och CRM:et för andra än plattformsadmin ger Snajps 404 (`app/not-found.tsx`). Saknas: länken leder till `/dashboard`, inte till CRM:ets start, och sidan ritas utanför CRM:ets skal. | 3 |
| NAV-128 | Fel i appen fångas på tre nivåer och skickas till felrapportering. | delvis | Felgränser i `app/global-error.tsx`, `app/error.tsx` och `app/crm/error.tsx` (inuti skalet, med Försök igen och felkod). Saknas: felrapportering till en tjänst; felet loggas bara i konsolen. | 3 |
| NAV-129 | Fel visas som begripliga notiser, och en krock med en befintlig post länkar dit. | byggd | `CrmFel` bär API:ts meddelande på två språk (`lib/crm/api.ts`, `lib/crm/felkoder.ts`) och visas i notiser och `Felruta` (`Sida.tsx`); krock på orgnr eller e-post visar `Krocklank` till den befintliga posten (`BolagFormular.tsx`, `PersonFormular.tsx`, `Papperskorg.tsx`). | |
| NAV-130 | Appen laddar om sig själv när en ny version gjort en koddel omöjlig att ladda. | inte gjord | Ingen sådan hantering hittad i `app/` eller `components/`. | 3 |
| NAV-131 | På liten skärm har appen ett eget skal med navigeringsfält i botten. | delvis | Under brytpunkten `md` blir sidofältet ett toppfält med låda och sökknapp (`CrmRam.tsx`, `mobileNav`, `MobilSok`), synligt i `docs/crm/bilder/app/meny-390.png`. Saknas: navigeringsfältet i botten som döljs vid scroll. | 3 |
| NAV-132 | Mobilens startsida samlar arbetsyteväxlare, meny och kom igång. | delvis | Mobilens låda samlar arbetsyteväxlare, sökrad, menyn och synkkortet (`meny-390.png`). Saknas: en egen startsida och kom igång-kortet. | ej planerad |
| NAV-133 | Sidlayouten har gemensamma byggstenar: sidhuvud, flikrader, menyer, dialoger, verktygstips. | byggd | `components/crm/app/Sida.tsx` (`Sidhuvud`, `Vyrad`, `Sida`), `kit.tsx` och Astryx `Layout`, `Drawer`, `Dialog`, `DropdownMenu`, `Table` med markering och `Tooltip` enligt `docs/crm/DESIGN-CRM.md`. | |
| NAV-134 | En stegrad visar aktuellt och klara steg i flerstegsflöden. | inte gjord | Stegguiden är planerad för introduktionen (SK-110). | 5 |
| NAV-135 | Användaren kan aktivera ett arbetsflöde från kommandomenyn. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-136 | Användaren kan inaktivera ett arbetsflöde. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-137 | Användaren kan kasta ett arbetsflödesutkast. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-138 | Användaren kan testköra ett arbetsflöde. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-139 | Användaren kan se ett arbetsflödes aktiva version, versioner och körningar. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-140 | Användaren kan lägga till ett steg och städa layouten i ett arbetsflöde. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-141 | Användaren kan duplicera ett arbetsflöde. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-142 | Användaren kan växla ett arbetsflödes synlighet mellan privat och delat. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-143 | Användaren kan stoppa och köra om arbetsflödeskörningar, även många på en gång. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-144 | Användaren kan använda en äldre arbetsflödesversion som utkast. | inte gjord | Inga arbetsflöden i CRM:et. | ej planerad |
| NAV-145 | Användaren kan redigera, spara, avbryta och duplicera en instrumentpanel. | inte gjord | Översikten har fasta nyckeltal och diagram (`OversiktVy.tsx`), inga egna instrumentpaneler. | ej planerad |
| NAV-146 | Användaren kan skriva, skicka, testa, avbryta och duplicera e-postkampanjer. | inte gjord | Kampanjer finns i Leads utanför CRM:et och flyttas in som `/crm/iris/kampanjer`. | 4 |
| NAV-147 | Användaren kan lägga poster eller en hel vy i en utskickslista och duplicera listor. | inte gjord | Listor finns i Leads utanför CRM:et och flyttas in som `/crm/iris/listor`. | 4 |
| NAV-148 | Användaren kan skriva e-post från kommandomenyn med mottagarna ifyllda. | inte gjord | Panelens snabbval Mejla öppnar bara `mailto:` (`BolagPanel.tsx`); utkast och utskick finns i Leads utanför CRM:et. | 4 |
| NAV-149 | Användaren kan svara på en e-posttråd. | inte gjord | Konversationer finns i Leads utanför CRM:et och flyttas in som `/crm/iris/konversationer`. | 4 |
| NAV-150 | Användaren kan triagera AI-chattar från kommandomenyn, flera på en gång. | inte gjord | Ingen AI-chattinkorg. | ej planerad |
| NAV-151 | Kommandot Redigera layout går in i layoutläget för sidan. | inte gjord | Inga redigerbara layouter. | ej planerad |
| NAV-152 | Kommandot Ny AI-chatt öppnar en ny chatt. | inte gjord | Ingen AI-chatt i CRM:et. | ej planerad |
| NAV-153 | E-postredigerarens blockinställningar och sidstil nås som kommandon. | inte gjord | Ingen e-postredigerare i CRM:et. | ej planerad |
| NAV-154 | Användaren kan skapa uppgift, anteckning, bilaga, e-post eller kalenderhändelse kopplad till en post. | delvis | Backend för uppgifter, anteckningar, aktiviteter och bilagor kopplade till bolag och personer (`snajp-support/app/crm/objekt.py`, `snajp-support/app/api/crm_v1_objekt.py`, `snajp-support/tests/crm/test_objekt_ovriga.py`). Saknas: åtgärderna i postens panel, e-post och kalenderhändelse. | 3 |
| NAV-155 | Bekräftelsedialoger för kommandon hanteras centralt. | delvis | Bekräftelse före radering finns per vy (`BolagVy.tsx` och `PersonerVy.tsx`, dialogen för `radera`). Saknas: en gemensam hanterare som kommandon kan begära. | 3 |
| NAV-156 | Relationsväljaren söker med samma globala sökning. | delvis | Bolagsväljaren i `PersonFormular.tsx` (`Selector` med `hasSearch`) söker lokalt bland en hämtad lista. Saknas: sökning mot servern och samma sökning som paletten. | 3 |
| NAV-157 | Dra och släpp i menyn håller sig inom favoriter respektive arbetsyta. | inte gjord | Ingen dra och släpp i sidofältet. | ej planerad |
| NAV-158 | Menyposttyper grupperas i tilläggsmenyn: objektbaserade och automatiseringar. | inte gjord | Ingen tilläggsmeny. | ej planerad |
| NAV-159 | Gå till-bokstaven kommer från objektets egen kortkommandobokstav. | inte gjord | Inga G-kortkommandon. | 3 |
| NAV-160 | Appen har en fast uppsättning adresser för sidor, objekt och poster. | delvis | `/crm`, `/crm/oversikt`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (`app/crm/`), posten via `?bolag=<id>` och skapa via `?ny=1`. Saknas: postsida, inställningar, introduktion och övriga adresser i CRM:et. | 5 |
| NAV-161 | Kom igång-mallen lämnar över vunna affärer med uppgift och mejl till kontoansvarig. | inte gjord | Inga arbetsflöden; affärer finns i backend (`objekt.py`) men ingen automation. | ej planerad |
| NAV-162 | Webbaviseringar godkänns bara mot fyra kända tjänster. | inte gjord | Inga webbaviseringar. | ej planerad |
| NAV-163 | Svepet för väntande uppvakningar arbetar i omgångar. | inte gjord | Inga väntande arbetsflöden. | ej planerad |
| NAV-164 | Introduktionen visar vad gratiskrediterna räcker till. | inte gjord | Snajp har inga krediter. | ej planerad |
| NAV-165 | AI-inkorgens layout väljs i en meny. | inte gjord | Ingen AI-chattinkorg. | ej planerad |
| NAV-166 | En banderoll visar när instansen inte är produktion. | inte gjord | Ingen banderoll; banderollmönstret är planerat för kundbesök, läsroll och demo (SK-076 till SK-079). | 4 |
