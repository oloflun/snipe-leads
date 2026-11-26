# Paritet 07: API, webhooks, appar och MCP

Området gäller allt en utvecklare eller integratör möter i Twenty: REST- och GraphQL-API:t för poster och schema, API-nycklar, webhooks, hastighetsgränser, OpenAPI, OAuth, MCP-servern för AI-klienter, appplattformen med SDK, CLI och marknadsplats, och Zapier-kopplingen. Snajp CRM har ett eget REST-API under `/api/crm/v1` med nycklar med omfång, synk in, ändringsflöde och signerade webhooks, men ingen GraphQL, ingen OAuth, ingen MCP-server och ingen appplattform.

Antal per läge (räknat i tabellen nedan, 351 rader): verifierad 23, byggd 3, delvis 42, inte gjord 263, avstår 20.

## De största luckorna

1. Inget filterspråk i API:t. Det går bara att filtrera på fasta parametrar (fritext, relation, organisationsnummer, bolag, ändrad sedan), aldrig på valfritt fält med jämförare eller med and, or och not.
2. Ingen MCP-server: Claude, ChatGPT, Cursor och andra AI-klienter kan inte kopplas till CRM:et för att läsa och skriva poster.
3. Ingen OAuth. En extern app kan inte be en användare om åtkomst; det enda sättet in är en API-nyckel som kunden skapar och klistrar in.
4. Inget GraphQL-API och inget metadata-API för schemat. Allt går genom ett fast REST-API för sju fasta objekt.
5. API-nycklar saknar utgångsdatum, roll, namnbyte och regenerering; en nyckel kan bara skapas med omfång och återkallas.
6. Inga massoperationer: det går inte att uppdatera, radera eller återställa många poster genom ett filter, och det finns ingen dubblettsökning eller sammanslagning via API:t.
7. Svaren går inte att forma: inget totalantal, ingen bläddring bakåt, inget val av fält, inga relaterade poster i samma svar och ingen gruppering med summor utöver affärstavlan.
8. Ingen appplattform: inga appar, logikfunktioner, frontkomponenter, SDK, CLI eller marknadsplats att installera från.
9. Ingen realtid. Gränssnittet får inga ändringar skickade till sig, och integratören har bara ändringsflödet och webhooks.
10. Ingen playground för att prova API:t i inställningarna och ingen Zapier-koppling.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| API-001 | Integratören får ett API som byggs automatiskt ur arbetsytans schema, även för egna objekt. | inte gjord | API:t är fast och handskrivet för sju objekt (`snajp-support/app/api/crm_v1.py`, `crm_v1_objekt.py`); egna objekt finns inte. | ej planerad |
| API-002 | Integratören väljer mellan ett API för poster och ett API för schemat, båda i REST och GraphQL. | delvis | Finns: REST för poster under `/api/crm/v1` (`snajp-support/app/api/crm_v1.py`). Saknas: metadata-API för schemat och GraphQL. | ej planerad |
| API-003 | Integratören autentiserar med en token i huvudet, och saknad eller fel token ger 401. | delvis | Finns: nyckeln i `X-API-Key`, 401 utan eller med fel nyckel (`snajp-support/tests/crm/test_api.py::test_utan_nyckel_och_med_fel_nyckel`). Saknas: `Authorization: Bearer`, OAuth-klienter och apptoken. | ej planerad |
| API-004 | Integratören listar ett objekts poster och får totalantal och sidinformation. | delvis | Finns: `GET /companies`, `/people`, `/deals` m.fl. med `data` och `next_cursor` (`test_api.py::test_sidindelning_med_markor`). Saknas: totalantal och information om föregående sida. | ej planerad |
| API-005 | Integratören hämtar en enskild post på id, och en post som inte finns ger 404. | verifierad | `GET /companies/{id}` och motsvarande (`crm_v1.py:_en`); `test_api.py::test_felformat_id_ger_404_aldrig_500`. |  |
| API-006 | Integratören skapar en post genom att skicka fälten som JSON. | verifierad | `POST /companies`, `/people`, `/deals` m.fl. (`crm_v1.py:_skapa`); `test_api.py::test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr`, `test_objekt.py::test_affar_skapas_andras_raderas_och_aterstalls`. |  |
| API-007 | Integratören skapar många poster i ett enda anrop. | verifierad | Satserna `POST /sync/companies` och `/sync/people`, högst 500 poster (`crm_v1.py`, `MAX_SATS`); `test_api.py::test_synk_i_ett_anrop_och_omsynk_andrar_ingenting`, `test_satsens_granser`. Bara bolag och personer. |  |
| API-008 | Integratören skapar eller uppdaterar en post efter unika fält (upsert), också en raderad. | verifierad | `POST /companies` uppdaterar på organisationsnummer, `POST /people` på e-post, synken matchar källans id, orgnr, domän och namn (`snajp-support/app/crm/synk.py`); `test_api.py::test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr`, `test_raderad_i_kallan_blir_gravsten_och_kan_komma_tillbaka`. |  |
| API-009 | Integratören skapar relaterade poster nästlat i samma anrop. | delvis | Finns: koppling till en befintlig post med `company_id`, `person_id` och `deal_id`, och i synken via källans bolags-id (`test_api.py::test_personer_synkas_och_knyts_via_kallans_bolags_id`). Saknas: nästlat skapande. | ej planerad |
| API-010 | Integratören ändrar valda fält på en post. | verifierad | `PATCH /companies/{id}` m.fl. (`crm_v1.py:_andra`); `test_api.py::test_andra_och_tom_ett_falt`. PUT som alias finns inte. |  |
| API-011 | Integratören uppdaterar många poster på en gång genom ett filter. | inte gjord | Ingen massuppdatering i API:t; varje post ändras för sig. | ej planerad |
| API-012 | Integratören raderar en post permanent. | verifierad | `DELETE /companies/{id}?permanent=true` (`crm_v1.py:_radera`); `test_api.py::test_papperskorgen_aterstaller_och_permanent_radering_tommer`. |  |
| API-013 | Integratören raderar en post mjukt, så att den går att återställa. | verifierad | `DELETE` utan `permanent` lägger posten i papperskorgen i 30 dagar; `test_api.py::test_radering_ar_mjuk_och_syns_for_den_som_synkar_ut`. |  |
| API-014 | Integratören raderar många poster genom ett filter, och ett tomt filter vägras. | inte gjord | Ingen massradering. Närmast är full synk med `missing_records: delete`, som bara tar bort det källan saknar. | ej planerad |
| API-015 | Integratören återställer en mjukt raderad post. | verifierad | `POST /companies/{id}/restore` m.fl. (`crm_v1.py:_aterstall`); `test_api.py::test_papperskorgen_aterstaller_och_permanent_radering_tommer`. Verbet är POST, inte PATCH. |  |
| API-016 | Integratören återställer många raderade poster genom ett filter. | inte gjord | Återställning sker en post i taget. | ej planerad |
| API-017 | Integratören letar dubbletter till kandidatposter eller befintliga poster. | delvis | Finns: förhandsgranskningen `POST /connections/{c}/preview` visar om en kandidat skulle skapa eller uppdatera en post (`test_api.py::test_forhandsgranskning_skriver_ingenting`), och en krock ger `conflicting_id`. Saknas: dubblettsökning bland befintliga poster. | ej planerad |
| API-018 | Integratören slår ihop två till nio poster, med torrkörning. | inte gjord | Ingen sammanslagning i API:t (`docs/crm/API.md`, "Det som inte finns än"). | ej planerad |
| API-019 | Sammanslagningen följer fasta regler per fälttyp och flyttar relationerna. | inte gjord | Ingen sammanslagning. | ej planerad |
| API-020 | Integratören grupperar poster och får antal och summor per grupp. | delvis | Finns: affärstavlan `GET /deals/board` med antal och summa per steg (`test_objekt.py::test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa`) och översiktens fasta tal (`snajp-support/app/api/crm.py`). Saknas: valfri gruppering och valfria aggregat. | ej planerad |
| API-021 | Integratören begränsar svaret till valda fält. | inte gjord | Svaret bär alltid hela posten. | ej planerad |
| API-022 | Ett objekt med mycket många fält ger ett standardurval när fälten inte anges. | avstår | Ersätts av fasta fält plus högst 50 egna värden i `custom` (`snajp-support/app/crm/synk.py`): inget objekt blir så brett att ett urval behövs. |  |
| API-023 | Integratören väljer om relaterade poster ska följa med i svaret. | inte gjord | Svaret bär bara relationens id (`company_id`); den relaterade posten hämtas för sig. | ej planerad |
| API-024 | Integratören styr sidans storlek med `limit`, med standardvärde och tak. | byggd | `limit` 1 till 500, standard 50, annat ger 422 (`crm_v1.py:_LISTPARAMETRAR`). `test_api.py::test_sidindelning_med_markor` använder `limit` 3 och 500, men inget test prövar standardvärdet eller att ett värde över taket ger 422. |  |
| API-025 | Integratören bläddrar framåt och bakåt med markörer. | delvis | Finns: framåt med `cursor` och `next_cursor`, en oläslig markör ger 422 (`test_api.py::test_sidindelning_med_markor`). Saknas: bakåt. | ej planerad |
| API-026 | Integratören sorterar på valfritt fält och riktning, med stabil ordning. | delvis | Finns: `sort` med `updated`, `-updated` och `name`, och egna ordningar för affärer och uppgifter (`test_handelser_webhooks.py::test_senast_andrad_forst_med_sidindelning`, `test_objekt_ovriga.py::test_uppgifter_sorteras_pa_forfallodag_och_filtreras`). Saknas: valfritt fält och val av var tomma värden hamnar. | ej planerad |
| API-027 | Integratören filtrerar med fält, jämförare och värde. | delvis | Finns: fasta filter som `q`, `relation`, `org_number`, `company_id`, `updated_since`, personernas `source_type`, affärernas `stage_id` och `lost_reason_code`, och uppgifternas `status`, `owner` och `due_before` (`test_objekt_ovriga.py::test_uppgifter_sorteras_pa_forfallodag_och_filtreras`). Saknas: ett filterspråk med jämförare. | ej planerad |
| API-028 | Integratören kombinerar filtervillkor med and, or och not. | inte gjord | De fasta filtren slås alltid ihop med och; inget filterspråk. | ej planerad |
| API-029 | Integratören filtrerar på en lista av värden och på tomt eller ifyllt. | delvis | Finns: ett fast tomt-filter, `missing_source` på `GET /people` (personer utan källa; `crm_v1.py:lista_personer`; inget test prövar just filtret). Saknas: `in` mot en lista av värden och tomt/ifyllt på valfritt fält. | ej planerad |
| API-030 | Vilka jämförare som går att använda beror på fältets typ. | inte gjord | Inget filterspråk. | ej planerad |
| API-031 | Varje fälttyp valideras och normaliseras innan något skrivs, och ett fel namnger fältet. | verifierad | `snajp-support/app/crm/falt.py` (organisationsnummer, telefon, postnummer, datum, belopp); `test_api.py::test_ogiltiga_falt_ger_422_med_faltnamn`. |  |
| API-032 | En för tung fråga avvisas med ett komplexitetstak. | avstår | Ersätts av fasta tak i `crm_v1.py`: inga nästlade frågor, `limit` högst 500, satser högst 500 poster och 8 MB (`MAX_SATS`, `MAX_KROPP`). |  |
| API-033 | Massändringar kräver ett filter, så att allt inte ändras av misstag. | delvis | Finns: en full synk utan poster vägras i stället för att tömma registret (`tom_full_synk`, `test_api.py::test_tom_full_synk_tommer_inte_registret`). Saknas: massändringar via filter över huvud taget. | ej planerad |
| API-034 | Felsvaren har fast form, fasta statuskoder och ett läsbart meddelande. | verifierad | `{"detail": {code, message, meddelande}}` på engelska och svenska (`crm_v1.py:fel`), koderna i `docs/crm/API.md`; `snajp-support/tests/crm/test_openapi_fil.py::test_varje_felkod_i_koden_ar_stabil_och_dokumenterad`. |  |
| API-035 | En felaktig sökväg avvisas tidigt med ett tydligt fel. | delvis | Finns: ett felformat id ger 404 och aldrig 500 (`test_api.py::test_felformat_id_ger_404_aldrig_500`). Saknas: 400 med exempel på giltiga sökvägar. | ej planerad |
| API-037 | Databasfel blir begripliga API-fel, och tillfälliga fel märks så att de kan göras om. | delvis | Finns: en unik-krock blir 409 `conflict` med `conflicting_id` (`test_handelser_webhooks.py::test_en_krock_sager_vilken_post_som_redan_har_nyckeln`). Saknas: egna koder för tillfälliga databasfel och tidsgränser. | ej planerad |
| API-038 | Servern har interna tjänster för att läsa och skriva poster som AI-verktyg och arbetsflöden använder. | delvis | Finns: `synk.skapa`, `synk.andra`, `synk.radera` och `synk.aterstall` (`snajp-support/app/crm/synk.py`), som API:t och synken delar. Saknas: AI-verktyg och arbetsflöden som använder dem. | ej planerad |
| API-036 | Läsningar och skrivningar filtreras genom rollens behörigheter på objekt, fält och rader. | delvis | Finns: kundisolering med radskydd och nyckelns omfång (`test_api.py::test_en_kund_ser_aldrig_en_annans_poster`). Saknas: roller, fält- och radbehörigheter och postdelning. | ej planerad |
| API-040 | Integratören skapar, läser, ändrar och raderar objekttyper via REST. | inte gjord | Inga egna objekt och inget metadata-API. | ej planerad |
| API-041 | Integratören hanterar fältdefinitioner via REST. | inte gjord | Inget fältmetadata-API; egna värden läggs i `custom` på posten. | ej planerad |
| API-042 | Integratören hanterar vyer med kolumner, filter, grupper och sorteringar via REST. | inte gjord | Inga sparade vyer i CRM:et. | ej planerad |
| API-043 | Integratören hanterar sidlayouter, flikar och widgetar via REST. | inte gjord | Inga sidlayouter. | ej planerad |
| API-044 | Integratören hanterar API-nycklar och webhooks via REST. | delvis | Finns: webhooks med lista, hämta, skapa, ändra och ta bort under `/api/crm/v1/webhooks` (`test_handelser_webhooks.py::test_webhooken_far_handelsen_signerad`), nycklar under `/api/crm/nycklar` med lista, skapa och återkalla (`test_api.py::test_appens_nyckelhantering_och_oversikt`). Saknas: hämta och ändra en enskild nyckel. | ej planerad |
| API-045 | Metadatalistor sidindelas med markör. | avstår | Ersätts av små listor som lämnas hela: högst tio webhooks per arbetsyta (`snajp-support/app/crm/webhooks.py`, `MAX_PER_KUND`). |  |
| API-050 | Integratören läser och skriver poster genom GraphQL, med ett schema per arbetsyta. | inte gjord | Inget GraphQL-API; samma poster nås genom REST i `crm_v1.py`. | ej planerad |
| API-051 | GraphQL-frågorna heter efter objektet (lista, en post, dubbletter, gruppering). | inte gjord | Inget GraphQL-API. | ej planerad |
| API-052 | GraphQL-mutationerna heter efter objektet (skapa, ändra, radera, förstöra, återställa, slå ihop). | inte gjord | Inget GraphQL-API. | ej planerad |
| API-053 | GraphQL-listan tar sidindelning, filter och sortering med förbjudna kombinationer. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-054 | GraphQL-listan svarar som en connection med kanter, markörer och totalantal. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-055 | Varje GraphQL-mutation har fasta argument. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-056 | Integratören delar en ny post med medlemmar eller roller när den skapas. | inte gjord | Ingen postdelning; alla med tillgång till kundens CRM ser alla poster. | ej planerad |
| API-057 | En GraphQL-fråga grupperar poster med aggregat och exempelposter. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-058 | Aggregat som antal, tomma, summa, medel, min och max genereras per fält och fälttyp. | inte gjord | Inga valfria aggregat; bara affärstavlans antal och summa per steg (`crm_v1_objekt.py`, `/deals/board`). | ej planerad |
| API-059 | Varje fälttyp har en egen filtertyp i GraphQL. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-060 | GraphQL sorterar på en lista av fält med riktning och tomma först eller sist. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-061 | GraphQL-schemat har egna skalärer och typer för sammansatta fält. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-062 | GraphQL tar emot många poster i ett anrop och skapa-eller-uppdatera. | inte gjord | Inget GraphQL-API; samma sak görs med satserna i REST (`/sync/companies`). | ej planerad |
| API-063 | En GraphQL-fråga begränsas i antal fält och rotanrop. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-064 | Schemats introspektion och felförslag döljs för den som inte är inloggad. | inte gjord | Inget GraphQL-API. Närmast: OpenAPI-specifikationen kräver nyckel (`test_api.py::test_specifikationen_tacker_varje_vag_och_kraver_nyckel`). | ej planerad |
| API-065 | GraphQL-fel bär fasta felkoder. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-066 | Ett GraphQL-API för schemat: objekt, fält, vyer, roller, nycklar, webhooks, appar med mera. | inte gjord | Inget metadata-API. | ej planerad |
| API-067 | Klienten prenumererar på ändringar i en händelseström i realtid. | delvis | Finns: ändringsflödet `GET /changes` med markör, som läses genom att fråga (`test_handelser_webhooks.py::test_varje_skrivning_blir_en_handelse_i_flodet`), och webhooks. Saknas: en ström som skickar ändringarna direkt. | ej planerad |
| API-068 | Händelserna bär före- och eftervärden, ändrade fält och vem som ändrade. | delvis | Finns: `/changes` bär objekt, id, typ, ändrade fält, källa och aktör (`crm_v1.py:handelse_ut`). Saknas: före- och eftervärden; loggen sparar med flit aldrig värdena (`snajp-support/app/crm/handelser.py`). | ej planerad |
| API-069 | Händelseströmmen lever en begränsad tid och hålls vid liv med hjärtslag. | inte gjord | Ingen händelseström. | ej planerad |
| API-070 | Egna realtidskanaler för funktionsloggar, agentchatt och arbetsytehändelser. | inte gjord | Inga realtidskanaler. | ej planerad |
| API-080 | Administratören skapar en API-nyckel med namn, utgångsdatum och roll. | delvis | Finns: namn och omfång, och bara med kundens egen nyckel (`snajp-support/app/crm/nycklar.py:skapa`, `test_api.py::test_appens_nyckelhantering_och_oversikt`). Saknas: utgångsdatum och roll. | ej planerad |
| API-081 | Nyckelns hemlighet visas en enda gång, när den skapas. | verifierad | Klartexten finns bara i skapasvaret, en sha256-hash sparas (`nycklar.py`); `test_api.py::test_appens_nyckelhantering_och_oversikt`. |  |
| API-082 | Användaren listar nycklarna och läser en enskild nyckel, aldrig hemligheten. | delvis | Finns: `GET /api/crm/nycklar` utan hemlighet (`test_api.py::test_appens_nyckelhantering_och_oversikt`) och tabellen i bilden `docs/crm/bilder/app/utvecklare-1440.png`. Saknas: hämta en enskild nyckel. | ej planerad |
| API-083 | Användaren byter namn på en nyckel eller ändrar dess utgång. | inte gjord | Nycklar går bara att lista, skapa och återkalla (`snajp-support/app/api/crm.py`). | ej planerad |
| API-084 | Användaren återkallar en nyckel, som därefter avvisas. | verifierad | `DELETE /api/crm/nycklar/{id}` (`nycklar.aterkalla`); `test_api.py::test_aterkallad_nyckel_slutar_galla`. |  |
| API-085 | En nyckel vars utgångsdatum passerat avvisas. | inte gjord | Nycklar har inget utgångsdatum. | ej planerad |
| API-086 | Nyckeln knyts till en roll som avgör vad den får göra. | delvis | Finns: omfången `crm:las`, `crm:skriv`, `crm:synk` och `crm:admin` (`nycklar.OMFANG`, `test_api.py::test_varje_omfang_oppnar_bara_sitt`). Saknas: roller och byte av omfång efter att nyckeln skapats. | ej planerad |
| API-087 | Driftpersonal skapar en nyckel från serverns kommandorad. | avstår | Gäller bara egen drift av Twenty. I Snajp skapar kunden nyckeln under CRM › Utvecklare (`components/crm/app/UtvecklareVy.tsx`). |  |
| API-088 | Nyckelfel har egna koder och meddelanden. | delvis | Finns: 401 utan nyckel och 403 `scope_missing` (`crm_v1.py:kraev`, `test_api.py::test_varje_omfang_oppnar_bara_sitt`). Saknas: egna koder för återkallad och utgången nyckel. | ej planerad |
| API-090 | Administratören skapar en webhook med adress, händelser, beskrivning och hemlighet. | verifierad | `POST /webhooks` (`snajp-support/app/crm/webhooks.py:skapa`), hemligheten genereras och visas en gång; `test_handelser_webhooks.py::test_webhooken_far_handelsen_signerad`. Ingen roll och ingen egen hemlighet. |  |
| API-091 | Administratören listar, ändrar och raderar webhooks. | byggd | `GET /webhooks`, `GET`, `PATCH` och `DELETE /webhooks/{id}` (`crm_v1.py:lista_webhooks`, `andra_webhook`, `radera_webhook`). Raderingen är permanent och tar loggen med. Testen prövar bara delar: `PATCH` av `active` (`test_handelser_webhooks.py::test_webhook_som_bara_misslyckas_stangs_av_och_sager_det`) och listan (`test_webhooken_far_handelsen_signerad`); `DELETE` och ändring av adress eller händelser prövas av inget test. |  |
| API-092 | Webhooken filtreras per objekt och händelse, med jokertecken. | delvis | Finns: exakta händelsenamn eller `*` (`webhooks._vill_ha`, `test_handelser_webhooks.py::test_webhooken_far_handelsen_signerad`). Saknas: jokertecken för en del, som `company.*` eller `*.created`. | ej planerad |
| API-093 | Webhooks för ändringar i schemat. | inte gjord | Inget schema att ändra; den enda händelsen utanför posterna är `sync.completed`. | ej planerad |
| API-094 | Webhooken ser bara det dess roll får läsa. | delvis | Finns: en webhook får bara sin egen kunds händelser (`test_handelser_webhooks.py::test_webhooken_far_handelsen_signerad`). Saknas: roll per webhook. | ej planerad |
| API-095 | Leveransen bär händelsens id, namn, tid och posten. | delvis | Finns: `id` (samma vid omförsök), `type`, `created_at` och `data` med objekt, id och post (`handelser._data`, `test_handelser_webhooks.py::test_webhooken_far_handelsen_signerad`). Saknas: ändrade fält och vem som ändrade. | ej planerad |
| API-096 | Mottagaren kontrollerar en HMAC-signatur över tid och kropp. | verifierad | `X-Snajp-Signature: t=..,v1=..`, HMAC-SHA256 över `{t}.{kropp}` (`webhooks.signera`); `test_handelser_webhooks.py::test_webhooken_far_handelsen_signerad`. Ingen nonce. |  |
| API-097 | Leveransen har en tidsgräns, 2xx räknas som lyckat och interna adresser blockeras. | byggd | Tio sekunder (`webhooks.TIDSGRANS`) genom nätvakten (`snajp-support/app/integrationer/natvakt.py`). Testen prövar att 204 räknas som levererad och att ett namn som pekas inåt blockeras (`test_handelser_webhooks.py::test_misslyckad_leverans_forsoks_igen_och_gar_att_skicka_om`, `test_adressen_provas_igen_nar_leveransen_gar`); inget test prövar tidsgränsen. |  |
| API-098 | Varje leverans loggas med status och utfall. | verifierad | Leveransloggen i 30 dagar, `GET /webhooks/{id}/deliveries`; `test_handelser_webhooks.py::test_webhooken_far_handelsen_signerad`. |  |
| API-099 | En misslyckad leverans görs om. | verifierad | Sju försök över drygt ett dygn (`webhooks.VANTETIDER`) och omskick för hand; `test_handelser_webhooks.py::test_misslyckad_leverans_forsoks_igen_och_gar_att_skicka_om`. |  |
| API-100 | Webhookanropen har en hastighetsgräns per arbetsyta. | delvis | Finns: jobbet skickar högst 50 leveranser per kund och varv, ett varv var tionde sekund, och resten väntar i kön (`webhooks.leverera_for_kund`, `run_webhookjobb`). Saknas: en uttalad gräns; inget kastas. | ej planerad |
| API-101 | AI-verktyg skapar, ändrar, raderar och listar webhooks. | inte gjord | Inga AI-verktyg i CRM:et. | ej planerad |
| API-102 | Webhooks kompletteras av arbetsflöden med HTTP-steg och inkommande webhookutlösare. | delvis | Finns: utgående webhooks (`webhooks.py`). Saknas: arbetsflöden med HTTP-steg och inkommande utlösare (se paritet 06). | ej planerad |
| API-110 | API-anrop med nyckel har en hastighetsgräns per arbetsyta. | verifierad | 600 anrop per minut och kund (`crm_v1.py:_TAK`); `test_api.py::test_taket_ger_429_med_retry_after`, `test_taket_ar_per_kund`. |  |
| API-111 | Appars anrop har en gemensam gräns över alla arbetsytor. | inte gjord | Inga appar. | ej planerad |
| API-112 | En överskriden gräns ger 429 med rubriker om väntetid och kvarvarande anrop. | delvis | Finns: 429 `rate_limited` med `Retry-After`, `X-RateLimit-Limit` och `X-RateLimit-Remaining` (`crm_v1.py:kraev`, `test_api.py::test_taket_ger_429_med_retry_after`). Saknas: `X-RateLimit-Reset`, gränsens detaljer i kroppen och felen för slut på krediter eller kvot. | ej planerad |
| API-113 | Gränser finns i tre slag: hastighet, kvot per period och bestånd. | delvis | Finns: hastighet (600 per minut) och bestånd (500 MB bilagor per arbetsyta, `test_objekt_ovriga.py::test_bilagans_storlek_typ_och_kvot`). Saknas: kvot per period och andra betalare än kunden. | ej planerad |
| API-114 | Varje resurs har standardgränser för AI, lagring, poster, e-post och webhooks. | delvis | Finns: API 600 per minut, bilagor 10 MB per fil och 500 MB totalt, högst tio webhooks. Saknas: gränser för antal poster, AI och e-post i CRM:et. | ej planerad |
| API-115 | Administratören sätter egna användningsgränser. | inte gjord | Gränserna är fasta i koden. | ej planerad |
| API-116 | Kvotperioder, kvotantagning och krediter per plan. | avstår | Enterprise-fil i förlagan. |  |
| API-117 | Användningsanalys och kreditförbrukning per API-typ. | avstår | Enterprise-fil i förlagan. |  |
| API-120 | Integratören hämtar en OpenAPI-beskrivning av API:t. | verifierad | `GET /api/crm/v1/openapi.json` med nyckel och `docs/crm/openapi.json` (`crm_v1.py:specifikation`); `test_api.py::test_specifikationen_tacker_varje_vag_och_kraver_nyckel`, `test_openapi_fil.py::test_specifikationen_i_docs_stammer_med_koden`. Beskrivningen är fast, inte byggd per arbetsyta. |  |
| API-121 | Varje objekt dokumenteras med alla sina vägar. | verifierad | Specifikationen täcker varje registrerad väg (`test_api.py::test_specifikationen_tacker_varje_vag_och_kraver_nyckel`). |  |
| API-122 | Frågeparametrar och felsvar dokumenteras. | verifierad | Parametrarna med beskrivning (`crm_v1.py:_LISTPARAMETRAR`), felkoderna i `docs/crm/API.md`; `test_openapi_fil.py::test_varje_felkod_i_koden_ar_stabil_och_dokumenterad`. |  |
| API-123 | Webhookarnas händelser och signaturrubriker dokumenteras i OpenAPI. | delvis | Finns: signatur och omförsök i specifikationens beskrivning (`crm_v1.py:_BESKRIVNING`) och i `docs/crm/API.md` § Webhooks. Saknas: ett avsnitt per händelse i OpenAPI. | ej planerad |
| API-124 | Integratören hämtar OpenAPI för schema-API:t. | inte gjord | Inget metadata-API. | ej planerad |
| API-125 | Inställningarna har interaktiv dokumentation där API:t går att provköra. | inte gjord | Utvecklarsidan länkar bara till specifikationen som JSON (`UtvecklareVy.tsx`, bilden `docs/crm/bilder/app/utvecklare-1440.png`). | ej planerad |
| API-126 | API:erna går att upptäcka maskinellt genom en well-known-katalog. | inte gjord | Ingen well-known-katalog. | ej planerad |
| API-127 | Ett MCP-serverkort beskriver MCP-servern för upptäckt. | inte gjord | Ingen MCP-server. | ej planerad |
| API-128 | OAuth-servern går att upptäcka genom well-known-adresser. | inte gjord | Ingen OAuth. | ej planerad |
| API-129 | Korta, spårbara länkar för utskick registreras och slås upp. | inte gjord | Inga korta länkar i CRM:et. | ej planerad |
| API-130 | En extern app registrerar sig själv som OAuth-klient. | inte gjord | Ingen OAuth i Snajp CRM; bara API-nycklar (`nycklar.py`). | ej planerad |
| API-131 | En OAuth-app begär omfången api och profile. | inte gjord | Ingen OAuth. | ej planerad |
| API-132 | Användaren godkänner en app i ett auktoriseringskodflöde med PKCE och samtyckesskärm. | inte gjord | Ingen OAuth. | ej planerad |
| API-133 | Appen byter koden mot en åtkomsttoken och en förnyelsetoken. | inte gjord | Ingen OAuth. | ej planerad |
| API-134 | Appen förnyar sin token med förnyelsetoken. | inte gjord | Ingen OAuth. | ej planerad |
| API-135 | En server hämtar en token utan användare (client credentials). | inte gjord | Ingen OAuth; server till server sker med API-nyckel. | ej planerad |
| API-136 | Integratören väljer mellan API-nyckel och OAuth efter behov. | inte gjord | Bara API-nycklar finns. | ej planerad |
| API-140 | En AI-klient ansluter till arbetsytans MCP-server över Streamable HTTP. | inte gjord | Ingen MCP-server i Snajp CRM. | ej planerad |
| API-141 | AI-klienten loggar in med OAuth eller API-nyckel och får användarens behörigheter. | inte gjord | Ingen MCP-server. | ej planerad |
| API-142 | Inställningarna ger färdig klientkonfiguration för MCP. | inte gjord | Ingen MCP-server. | ej planerad |
| API-143 | MCP:s standardläge listar samma postverktyg i varje arbetsyta. | inte gjord | Ingen MCP-server. | ej planerad |
| API-144 | MCP:s postverktyg har fasta regler för urval, filter, gruppering och tak. | inte gjord | Ingen MCP-server. | ej planerad |
| API-145 | MCP:s direktläge listar ett verktyg per objekt och operation. | inte gjord | Ingen MCP-server. | ej planerad |
| API-146 | MCP:s metaläge listar bara verktyg för att lära sig och köra andra verktyg. | inte gjord | Ingen MCP-server. | ej planerad |
| API-147 | Vissa verktyg exponeras aldrig genom MCP. | inte gjord | Ingen MCP-server. | ej planerad |
| API-148 | MCP-verktygen märks som läsande, skrivande eller destruktiva. | inte gjord | Ingen MCP-server. | ej planerad |
| API-149 | MCP-servern ger klienten instruktioner om arbetsytan. | inte gjord | Ingen MCP-server. | ej planerad |
| API-150 | MCP-klienten får förloppsnotiser och kan avbryta en körning. | inte gjord | Ingen MCP-server. | ej planerad |
| API-151 | MCP:s listor får cachetips. | inte gjord | Ingen MCP-server. | ej planerad |
| API-152 | MCP-fel följer JSON-RPC:s felkoder. | inte gjord | Ingen MCP-server. | ej planerad |
| API-153 | MCP-anrop räknas som API-anrop med samma gränser och behörigheter. | inte gjord | Ingen MCP-server. | ej planerad |
| API-160 | AI-verktygen är grupperade i kategorier som byggs efter arbetsyta och roll. | inte gjord | Inga AI-verktyg i CRM:et. | ej planerad |
| API-161 | AI-verktyg hanterar metadata, vyer, layouter, roller, agenter och webhooks. | inte gjord | Inga AI-verktyg i CRM:et. | ej planerad |
| API-162 | AI-verktyg för kalender, e-post, filer, HTTP, kod och hjälpcentersökning. | inte gjord | Inga AI-verktyg i CRM:et. | ej planerad |
| API-163 | Verktygens resultat komprimeras innan modellen får dem. | inte gjord | Inga AI-verktyg i CRM:et. | ej planerad |
| API-164 | Administratören ansluter en extern MCP-server till arbetsytan och synkar dess verktyg. | inte gjord | Inga externa MCP-servrar i CRM:et. | ej planerad |
| API-165 | En extern MCP-server som kräver inloggning får en anslutning där användaren loggar in. | inte gjord | Inga externa MCP-servrar. | ej planerad |
| API-170 | Utvecklaren deklarerar en app som en samling entiteter i ett manifest. | inte gjord | Ingen appplattform i Snajp CRM. | ej planerad |
| API-171 | Varje appentitet har ett stabilt universellt id. | inte gjord | Ingen appplattform. | ej planerad |
| API-172 | Appen deklarerar identitet, standardroll, variabler, krokar och fakturering. | inte gjord | Ingen appplattform. | ej planerad |
| API-173 | Appvariabler finns per arbetsyta eller per användare, med typ och hemlighet. | inte gjord | Ingen appplattform. | ej planerad |
| API-174 | En obligatorisk variabel utan värde gör appen okonfigurerad. | inte gjord | Ingen appplattform. | ej planerad |
| API-175 | Servervariabler fylls i av den som driver registreringen. | inte gjord | Ingen appplattform. | ej planerad |
| API-176 | Plattformen sätter reserverade miljövariabler i varje körning. | inte gjord | Ingen appplattform. | ej planerad |
| API-177 | Appen läser och ändrar sina variabler när den körs. | inte gjord | Ingen appplattform. | ej planerad |
| API-178 | Appens roll styr vad den får göra med objekt, fält och rader. | inte gjord | Ingen appplattform och inga roller. | ej planerad |
| API-179 | Appen kör med två slags token beroende på vems åtkomst anropet ska ha. | inte gjord | Ingen appplattform. | ej planerad |
| API-180 | Appens kortlivade token förnyas. | inte gjord | Ingen appplattform. | ej planerad |
| API-181 | Appen har krokar före och efter installation. | inte gjord | Ingen appplattform. | ej planerad |
| API-182 | Appen har en avinstallationskrok som körs innan dess data tas bort. | inte gjord | Ingen appplattform. | ej planerad |
| API-183 | Appen kan deklarera en hälsokontroll av sin konfiguration. | inte gjord | Ingen appplattform. | ej planerad |
| API-184 | Appens frontkomponenter begär mikrofon, kamera och inbäddade webbplatser. | inte gjord | Ingen appplattform. | ej planerad |
| API-185 | Administratören installerar en app och följer installationen. | inte gjord | Ingen appplattform. | ej planerad |
| API-186 | Administratören avinstallerar en app med allt den äger. | inte gjord | Ingen appplattform. | ej planerad |
| API-187 | En app uppgraderas till en högre version, automatiskt eller för hand. | inte gjord | Ingen appplattform. | ej planerad |
| API-188 | En app kan kräva en viss serverversion. | inte gjord | Ingen appplattform. | ej planerad |
| API-189 | En app kan stoppas, och dess rutter svarar då 403. | inte gjord | Ingen appplattform. | ej planerad |
| API-190 | Utvecklaren synkar en app under utveckling mot en server. | inte gjord | Ingen appplattform. | ej planerad |
| API-191 | En app och dess GraphQL-schema kan exporteras. | inte gjord | Ingen appplattform. | ej planerad |
| API-192 | Appen har ett eget nyckel-värdelager. | inte gjord | Ingen appplattform. | ej planerad |
| API-193 | Manifestets valideringsregler och postvägar översätts till arbetsytans metadata. | avstår | Enterprise-fil i förlagan. |  |
| API-200 | En logikfunktion exponeras som HTTP-rutt. | inte gjord | Inga logikfunktioner i CRM:et (se paritet 06). | ej planerad |
| API-201 | Plattformen svarar med egna statuskoder när en rutt inte kan köras. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-202 | En serverrutt tar emot en leverantörs händelser för alla kunder och skickar dem rätt. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-203 | En logikfunktion körs på schema. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-204 | En logikfunktion körs när en post skapas, ändras eller raderas. | inte gjord | Inga logikfunktioner; posthändelser går bara ut som webhooks (`webhooks.py`). | ej planerad |
| API-205 | En logikfunktion får körningskontext med omförsöksräknare och utlösare. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-206 | En logikfunktion kan vara ett AI-verktyg eller ett arbetsflödessteg. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-207 | En logikfunktion publicerar egna händelser på tidslinjen. | inte gjord | Inga logikfunktioner; tidslinjen komponeras av servern (`snajp-support/app/crm/tidslinje.py`). | ej planerad |
| API-216 | En logikfunktion köar bakgrundsjobb med tidsgräns, omförsök och fördröjning. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-217 | Bakgrundsjobb skiljer mellan permanenta fel och fel som görs om. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-218 | Appens nyckel-värdelager per arbetsyta eller server. | inte gjord | Ingen appplattform. | ej planerad |
| API-219 | Appars operationer debiteras i krediter, och saknade krediter stoppar körningen. | inte gjord | Ingen appplattform. | ej planerad |
| API-208 | Funktionskörningar stryps vid ett tak per minut. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-209 | Frontkomponenter från appar ritas isolerat i gränssnittet. | inte gjord | Ingen appplattform. | ej planerad |
| API-210 | En frontkomponent har konfiguration för var den kan visas. | inte gjord | Ingen appplattform. | ej planerad |
| API-211 | Huvudlösa komponenter och färdiga kommandohjälpare. | inte gjord | Ingen appplattform. | ej planerad |
| API-212 | En frontkomponent anropar funktioner, API:t och värdens tjänster. | inte gjord | Ingen appplattform. | ej planerad |
| API-213 | Frontkomponenter har kända begränsningar i sin sandlåda. | inte gjord | Ingen appplattform. | ej planerad |
| API-274 | Frontkomponenter hanteras som metadata och levereras byggda från servern. | inte gjord | Ingen appplattform. | ej planerad |
| API-215 | En app lägger frontkomponenter i sina egna inställningssidor. | inte gjord | Ingen appplattform. | ej planerad |
| API-214 | Frontkomponenternas delade beroenden och källkod hämtas från servern. | inte gjord | Ingen appplattform. | ej planerad |
| API-220 | En app har en registrering per instans, med ägare och källtyp. | inte gjord | Ingen appplattform. | ej planerad |
| API-221 | Utvecklaren hanterar appregistreringar, hemligheter och servervariabler. | inte gjord | Ingen appplattform. | ej planerad |
| API-222 | En app distribueras privat som tarball med delningslänk. | inte gjord | Ingen appplattform. | ej planerad |
| API-223 | En app publicerad på npm blir synlig på marknadsplatsen. | inte gjord | Ingen marknadsplats. | ej planerad |
| API-224 | Ägaren gör anspråk på sin app med GitHub. | inte gjord | Ingen marknadsplats. | ej planerad |
| API-225 | Marknadsplatsen listar och visar appar, också utan inloggning. | inte gjord | Ingen marknadsplats. | ej planerad |
| API-226 | Appar på marknadsplatsen granskas mot en checklista. | inte gjord | Ingen marknadsplats. | ej planerad |
| API-227 | Appar kan debitera krediter och ha ett pris. | inte gjord | Ingen appplattform. | ej planerad |
| API-228 | Appar kan vara förinstallerade eller följa med servern. | inte gjord | Ingen appplattform. | ej planerad |
| API-229 | OAuth-servern för appar går att upptäcka. | inte gjord | Ingen OAuth. | ej planerad |
| API-230 | OAuth-servern registrerar klienter, utfärdar, återkallar och granskar token. | inte gjord | Ingen OAuth. | ej planerad |
| API-231 | Servern genererar en typad klient per app och arbetsyta. | inte gjord | Ingen appplattform och ingen SDK. | ej planerad |
| API-240 | Utvecklaren skapar ett nytt appprojekt från en mall. | inte gjord | Ingen appplattform. | ej planerad |
| API-241 | SDK:n deklarerar appens entiteter. | inte gjord | Ingen SDK. | ej planerad |
| API-242 | SDK:n ger logikfunktioner hjälpare för AI, jobb, e-post, inkorg och fakturering. | inte gjord | Ingen SDK. | ej planerad |
| API-243 | SDK:n ger frontkomponenter komponenter, krokar och översättningar. | inte gjord | Ingen SDK. | ej planerad |
| API-244 | Typade klienter för poster, metadata och REST. | inte gjord | Ingen klient-SDK; integratören anropar REST-API:t direkt med hjälp av `docs/crm/openapi.json`. | ej planerad |
| API-245 | Ett CLI ansluter till arbetsytor med webbläsarinloggning eller API-nyckel. | inte gjord | Inget CLI. | ej planerad |
| API-246 | CLI:t utforskar data och gör råa REST- och GraphQL-anrop. | inte gjord | Inget CLI. | ej planerad |
| API-247 | CLI:t exporterar poster till CSV eller JSON. | inte gjord | Inget CLI och ingen export till fil i CRM:et. | ej planerad |
| API-248 | CLI:t bygger, synkar, publicerar och installerar appar. | inte gjord | Inget CLI. | ej planerad |
| API-249 | CLI:t kör driftsatta funktioner och strömmar deras loggar. | inte gjord | Inget CLI. | ej planerad |
| API-250 | CLI:t startar och sköter en lokal Twenty-server. | avstår | Gäller bara egen drift av Twenty: en lokal server att utveckla appar mot. |  |
| API-251 | Zapier-kopplingen loggar in med API-nyckel. | inte gjord | Ingen Zapier-koppling. | ej planerad |
| API-252 | Zapier-utlösaren skapar en webhook för valt objekt och händelse. | inte gjord | Ingen Zapier-koppling; webhooks finns (`webhooks.py`) men ingen koppling använder dem. | ej planerad |
| API-253 | Zapier-åtgärden skapar, ändrar eller raderar en post. | inte gjord | Ingen Zapier-koppling. | ej planerad |
| API-254 | Zapier hämtar objektnamn och post-id att välja bland. | inte gjord | Ingen Zapier-koppling. | ej planerad |
| API-260 | Utvecklarsidan har flikar för API, webhooks, appar och CLI. | delvis | Finns: sidan Utvecklare med nycklar och webhooks (`components/crm/app/UtvecklareVy.tsx`, `Webhooks.tsx`; bilden `docs/crm/bilder/app/utvecklare-1440.png` visar nyckeldelen). Saknas: appar och CLI. | ej planerad |
| API-261 | Användaren skapar en API-nyckel i gränssnittet och ser den en gång. | delvis | Finns: dialogen Ny nyckel med namn och omfång, nyckeln visas en gång med kopiering (`UtvecklareVy.tsx`), tabellen i bilden `utvecklare-1440.png`. Saknas: utgång och roll. | ej planerad |
| API-262 | Användaren regenererar eller raderar en nyckel från dess sida. | delvis | Finns: återkalla med bekräftelse (`UtvecklareVy.tsx`). Saknas: regenerera, byta roll och en egen sida per nyckel. | ej planerad |
| API-263 | Användaren skapar och redigerar webhooks i gränssnittet. | delvis | Finns: ny webhook med adress, beskrivning och alla eller valda händelser, hemligheten en gång, slå av och på, ta bort, leveranslogg med omskick och testanrop (`components/crm/app/Webhooks.tsx`). Bilderna `docs/crm/bilder/fas3/panel-webhooks-lista-390.png`, `panel-webhooks-logg-1440.png` och `panel-webhooks-skapad-1440.png` visar lista, logg och hemlighet. Saknas: ändra adress och händelser i gränssnittet. | 3 |
| API-264 | Användaren provkör API:t i en playground. | inte gjord | Ingen playground. | ej planerad |
| API-265 | En CLI-flik visar färdiga kommandon att kopiera. | inte gjord | Inget CLI. | ej planerad |
| API-266 | En appflik visar arbetsytans egna appar och anspråk. | inte gjord | Ingen appplattform. | ej planerad |
| API-267 | Utvecklaren ser en registrerings statistik, konfiguration, OAuth, distribution och övervakning. | inte gjord | Ingen appplattform. | ej planerad |
| API-268 | Administratören ser en installerad apps inställningar och innehåll. | inte gjord | Ingen appplattform. | ej planerad |
| API-269 | Administratören bläddrar bland och installerar tillgängliga appar. | inte gjord | Ingen marknadsplats. | ej planerad |
| API-270 | Användaren godkänner eller nekar en OAuth-klient på en godkännandesida. | inte gjord | Ingen OAuth. | ej planerad |
| API-271 | Gränssnittet hanterar externa MCP-servrar. | inte gjord | Inga externa MCP-servrar. | ej planerad |
| API-272 | Webbklienten håller sig uppdaterad genom händelseströmmen. | delvis | Finns: leveransloggen och synkvyn hämtar om med jämna mellanrum medan något pågår (`Webhooks.tsx`, `LEVERANSPULS`; `SynkVy.tsx`, `SYNKPULS`). Saknas: händelseström och uppdatering av alla vyer när data ändras. | ej planerad |
| API-273 | Frontkomponenter ritas av en egen renderare. | inte gjord | Ingen appplattform. | ej planerad |
| API-300 | Integratören kopplar, skapar eller lossar en relaterad post inne i ett skapa- eller ändra-anrop. | delvis | Finns: koppla med id (`company_id`, `person_id`, `deal_id`), lossa med `null`, och en koppling som pekar fel ger 422 (`test_api.py::test_personer_knyts_till_bolag_och_uppdateras_pa_epost`, `test_objekt_ovriga.py::test_en_kund_ser_och_kopplar_aldrig_till_en_annans_poster`). Saknas: koppla på ett annat unikt fält och skapa den relaterade posten i samma anrop. | ej planerad |
| API-301 | REST-filtret godtar en egen, smalare lista av jämförare. | inte gjord | Inget filterspråk i REST-API:t. | ej planerad |
| API-302 | GraphQL-filtrens fullständiga operander per typ. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-303 | Webhooks finns för sex databashändelser per objekt, med fyra sorters matchning. | delvis | Finns: `created`, `updated`, `deleted`, `restored` och `purged` för sju objekt plus `sync.completed` (`webhooks.HANDELSETYPER`; `test_objekt_ovriga.py::test_varje_objekts_skrivning_syns_i_flodet_och_webhooken_bar_ingen_fil`). Saknas: `upserted` och matchning på `objekt.*` och `*.händelse`. | ej planerad |
| API-304 | Webhookgränsen tillämpas efter rollfiltreringen och resten kastas. | inte gjord | Ingen gräns som kastar anrop och inga roller; kön väntar i stället (`webhooks.leverera_for_kund`). | ej planerad |
| API-305 | Varje leveransresultat sparas med tid, status och utfall, och blockerade anrop märks. | verifierad | Leveransloggen med statuskod, försök och fel (`webhooks.leverera_for_kund`); `test_handelser_webhooks.py::test_misslyckad_leverans_forsoks_igen_och_gar_att_skicka_om`, och nätvaktens nej som fel i `test_adressen_provas_igen_nar_leveransen_gar`. |  |
| API-306 | En app lägger till fält på objekt den inte äger. | inte gjord | Ingen appplattform. | ej planerad |
| API-307 | En app deklarerar valideringsregler med ett uttrycksspråk. | avstår | Reglerna verkställs bara i förlagans Enterprise-del (serverdelen, se API-193). |  |
| API-308 | Synken av en app hanterar fält som en valideringsregel läser. | avstår | Hör till valideringsreglerna, vars serverdel är Enterprise i förlagan. |  |
| API-309 | En app lägger till poster i sidomenyn. | inte gjord | Ingen appplattform; sidomenyn är fast (`components/crm/app/CrmRam.tsx`). | ej planerad |
| API-310 | En app levererar publika filer som logotyp och bilder. | inte gjord | Ingen appplattform. | ej planerad |
| API-311 | En app registrerar kommandon i kommandomenyn. | inte gjord | Ingen appplattform; kommandopaletten har fasta kommandon (`Kommandopalett.tsx`). | ej planerad |
| API-312 | Kommandon visas efter villkorsuttryck över sidans kontext. | inte gjord | Ingen appplattform. | ej planerad |
| API-313 | En app syns på sex ytor: sidomeny, lista, postsida, egen yta, inställningar och kommandomeny. | inte gjord | Ingen appplattform. | ej planerad |
| API-314 | En app levererar extra vyer för ett objekt. | inte gjord | Ingen appplattform och inga sparade vyer. | ej planerad |
| API-315 | En apps vykolumner kan visa fält och aggregat från relaterade poster. | inte gjord | Ingen appplattform. | ej planerad |
| API-316 | Vyfiltrens operander per fälttyp. | inte gjord | Inga sparade vyer eller vyfilter som appar kan deklarera. | ej planerad |
| API-317 | En app deklarerar sidlayouter med flikar. | inte gjord | Ingen appplattform och inga sidlayouter. | ej planerad |
| API-318 | En apps sidlayouter har widgetar för komponenter, iframes, fält och tabeller. | inte gjord | Ingen appplattform. | ej planerad |
| API-319 | En app lägger till en flik eller widget i en befintlig layout. | inte gjord | Ingen appplattform. | ej planerad |
| API-320 | En app deklarerar en anslutning till ett tredjepartskonto. | inte gjord | Ingen appplattform. CRM:ets egna anslutningar är synkkällor, inte konton (`crm_v1.py`, `/connections`). | ej planerad |
| API-321 | En apps anslutning delas av arbetsytan eller är personlig. | inte gjord | Ingen appplattform. | ej planerad |
| API-322 | En app läser sina anslutningar med token som förnyas automatiskt. | inte gjord | Ingen appplattform. | ej planerad |
| API-323 | Det anslutna kontot identifieras, och återanslutning till fel konto vägras. | inte gjord | Ingen appplattform. | ej planerad |
| API-324 | En app har krokar vid anslutning och frånkoppling. | inte gjord | Ingen appplattform. | ej planerad |
| API-325 | En app rapporterar att en inloggning slutat fungera. | inte gjord | Ingen appplattform. | ej planerad |
| API-326 | En app har månadspris i riktig valuta. | inte gjord | Ingen appplattform. | ej planerad |
| API-327 | En apps operationer debiteras i krediter per kategori. | inte gjord | Ingen appplattform. | ej planerad |
| API-328 | En app skickar meddelanden till medlemmars inkorg, med fråga eller formulär. | inte gjord | Ingen appplattform och ingen inkorg i CRM:et. | ej planerad |
| API-329 | En app nämner medlemmar, refererar poster och arkiverar konversationer i inkorgen. | inte gjord | Ingen appplattform. | ej planerad |
| API-330 | En app levererar färdiga arbetsflöden med fyra sorters utlösare. | inte gjord | Inga arbetsflöden i CRM:et (se paritet 06). | ej planerad |
| API-331 | En apps arbetsflöden har 22 stegtyper. | inte gjord | Inga arbetsflöden. | ej planerad |
| API-332 | En app levererar skills och AI-agenter. | inte gjord | Inga AI-agenter i CRM:et. | ej planerad |
| API-333 | En app deklarerar en extern MCP-server för arbetsytans AI. | inte gjord | Ingen appplattform och inga externa MCP-servrar. | ej planerad |
| API-334 | En logikfunktion kör en AI-agent eller en engångsgenerering. | inte gjord | Inga logikfunktioner och inga agenter i CRM:et. | ej planerad |
| API-335 | En app tillför en meddelandekanal, till exempel LinkedIn eller chatt. | inte gjord | Ingen appplattform. | ej planerad |
| API-336 | Synken av en app visar skillnaden innan den tillämpas. | inte gjord | Ingen appplattform. | ej planerad |
| API-337 | Appsynkar körs en i taget och felen klassas. | inte gjord | Ingen appplattform. | ej planerad |
| API-338 | `app pull` återskapar en apps källkod ur arbetsytan. | inte gjord | Ingen appplattform. | ej planerad |
| API-339 | Appägaren övervakar sin app över alla installationer. | inte gjord | Ingen appplattform. | ej planerad |
| API-340 | En apps logghändelser syns i arbetsytans logg. | inte gjord | Ingen appplattform. | ej planerad |
| API-341 | Appar testas och paketeras med en färdig mall. | inte gjord | Ingen appplattform. | ej planerad |
| API-342 | Appar översätts med extraherade strängkataloger. | inte gjord | Ingen appplattform. | ej planerad |
| API-343 | Användarna har en sida som förklarar webhooks. | verifierad | `docs/crm/API.md` § Webhooks (signatur, omförsök, leveranslogg, avstängning) och förklaringen i `components/crm/app/Webhooks.tsx`; bilderna `docs/crm/bilder/fas3/panel-webhooks-lista-390.png` och `panel-webhooks-logg-1440.png` visar förklaringen under rubriken Webhooks och i loggens fot. |  |
| API-344 | En app deklarerar egna objekt. | inte gjord | Ingen appplattform och inga egna objekt. | ej planerad |
| API-345 | En app deklarerar relationer mellan objekt. | inte gjord | Ingen appplattform. | ej planerad |
| API-346 | En app refererar systemfält och systemvyer med härledda id. | inte gjord | Ingen appplattform. | ej planerad |
| API-347 | En app definierar egna typer av tidslinjehändelser. | inte gjord | Ingen appplattform; tidslinjens händelsetyper är fasta (`snajp-support/app/crm/tidslinje.py`). | ej planerad |
| API-348 | En app köar bakgrundsjobb via API:t och läser deras status. | inte gjord | Ingen appplattform. | ej planerad |
| API-349 | En logikfunktion har en tidsgräns på 1 till 900 sekunder. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-350 | Driftaren stoppar en app på hela instansen med en nödbrytare. | avstår | Gäller bara egen drift av Twenty (serverkommando för den som driver instansen). |  |
| API-351 | Medlemmen ser sina egna appinställningar och kör appens hälsokontroll. | inte gjord | Ingen appplattform. | ej planerad |
| API-352 | En apps anslutningar nås via API och egna HTTP-vägar. | inte gjord | Ingen appplattform. | ej planerad |
| API-353 | En apps övervakningsdata nås via API. | inte gjord | Ingen appplattform. | ej planerad |
| API-354 | Apppaket hämtas och packas upp säkert, med versionskontroll. | inte gjord | Ingen appplattform. | ej planerad |
| API-355 | En apps översättningar lagras per språk. | inte gjord | Ingen appplattform. | ej planerad |
| API-356 | Faktureringsansvariga får besked när ett betalt konto ansluts. | inte gjord | Ingen appplattform. | ej planerad |
| API-357 | Appflödets felkoder, räknade. | inte gjord | Ingen appplattform. | ej planerad |
| API-358 | En GraphQL-förfrågan får inte blanda objektfrågor och kärnfrågor. | inte gjord | Inget GraphQL-API. | ej planerad |
| API-359 | Regler på standardobjekten ändrar vad API:t gör, till exempel vem som skapade och vad som följer med en radering. | delvis | Finns: servern sätter aktören på varje skrivning (`crm_v1.py:_ursprung`), en privatperson är alltid `do_not_contact`, och anteckningar, aktiviteter och bilagor töms med sitt bolag eller sin person (`test_objekt_ovriga.py::test_tomt_bolag_och_tomd_person_tar_med_sig_det_som_pekar_pa_dem`). Saknas: spärrade operationer per objekt. | ej planerad |
| API-360 | MCP-inställningarna visar färdiga uppkopplingar för 17 AI-klienter. | inte gjord | Ingen MCP-server. | ej planerad |
| API-361 | Administratören hanterar externa MCP-servrar i gränssnittet, med status per server. | inte gjord | Inga externa MCP-servrar. | ej planerad |
| API-362 | Installationsdialogen visar vad en app begär. | inte gjord | Ingen appplattform. | ej planerad |
| API-363 | En frontkomponents mikrofon och kamera godkänns i webbklienten. | inte gjord | Ingen appplattform. | ej planerad |
| API-364 | CLI:t har gemensamma utdataformat och slutkoder. | inte gjord | Inget CLI. | ej planerad |
| API-365 | CLI:ts anslutningar, prioritet och proxyhantering. | inte gjord | Inget CLI. | ej planerad |
| API-366 | CLI:ts dataläsning och råa anrop med tak. | inte gjord | Inget CLI. | ej planerad |
| API-367 | CLI:ts lokala Docker-miljö. | avstår | Gäller bara egen drift av Twenty: en lokal server att utveckla appar mot. |  |
| API-368 | `doctor` diagnostiserar CLI-installationen. | inte gjord | Inget CLI. | ej planerad |
| API-369 | `app publish` publicerar en app till npm. | inte gjord | Inget CLI och ingen appplattform. | ej planerad |
| API-370 | `app exec` kör en funktion och `app logs` följer loggarna. | inte gjord | Inget CLI. | ej planerad |
| API-371 | 27 behörighetsflaggor grindar API:t, webhooks, appar och MCP. | delvis | Finns: fyra omfång för nycklar (`nycklar.OMFANG`, `test_api.py::test_varje_omfang_oppnar_bara_sitt`) och tillägget som grind (`snajp-support/app/crm/tillgang.py`). Saknas: behörighetsflaggor per roll. | ej planerad |
| API-372 | Användaren ser och återkallar de OAuth-appar hen godkänt. | inte gjord | Ingen OAuth. | ej planerad |
| API-373 | Administratören ser och återkallar arbetsytans alla OAuth-godkännanden. | inte gjord | Ingen OAuth. | ej planerad |
| API-374 | Ett återkallat godkännande gör redan utfärdade apptoken ogiltiga. | inte gjord | Ingen OAuth. | ej planerad |
| API-375 | Appens begärda roll kopieras till en egen roll per installation. | inte gjord | Ingen appplattform och inga roller. | ej planerad |
| API-376 | En apps innehållsförteckning nås via GraphQL. | inte gjord | Ingen appplattform. | ej planerad |
| API-377 | Klienten läser en apps beskrivning, roll, agenter och om den är stoppad. | inte gjord | Ingen appplattform. | ej planerad |
| API-378 | Pris per anslutet konto visas bara när fakturering är på. | inte gjord | Ingen appplattform. | ej planerad |
| API-379 | Varje publicerad version av en app sparas. | inte gjord | Ingen appplattform. | ej planerad |
| API-380 | Automatisk uppgradering av appar körs som bakgrundsjobb. | inte gjord | Ingen appplattform. | ej planerad |
| API-381 | Färdiga MCP-serverkopplingar följer med som appar. | inte gjord | Ingen appplattform och inga MCP-kopplingar. | ej planerad |
| API-382 | Frontkomponenternas delade beroenden levereras med lång cache. | inte gjord | Ingen appplattform. | ej planerad |
| API-383 | En apps inställningsmenyposter har fasta fält och regler. | inte gjord | Ingen appplattform. | ej planerad |
| API-384 | En apps inställningsflikar har egna adresser. | inte gjord | Ingen appplattform. | ej planerad |
| API-385 | En frontkomponent har 11 krokar för sin körkontext. | inte gjord | Ingen appplattform. | ej planerad |
| API-386 | En frontkomponent har 9 värdfunktioner som navigering, dialog och filuppladdning. | inte gjord | Ingen appplattform. | ej planerad |
| API-387 | En frontkomponent har en REST-klient som förnyar sin token. | inte gjord | Ingen appplattform. | ej planerad |
| API-388 | Appars HTTP-funktioner får en egen domän per arbetsyta i molnet. | inte gjord | Ingen appplattform. | ej planerad |
| API-389 | En frontkomponent läser och skriver appens variabler. | inte gjord | Ingen appplattform. | ej planerad |
| API-390 | En frontkomponent har lagring avgränsad per app och användare. | inte gjord | Ingen appplattform. | ej planerad |
| API-391 | En frontkomponents nätverksanrop och filval går genom värden. | inte gjord | Ingen appplattform. | ej planerad |
| API-392 | En frontkomponents DOM och händelser har uttalade gränser. | inte gjord | Ingen appplattform. | ej planerad |
| API-393 | Mikrofon, kamera och inbäddade webbplatser i frontkomponenter. | inte gjord | Ingen appplattform. | ej planerad |
| API-394 | Frontkomponenter stilsätts så att de följer värdens tema. | inte gjord | Ingen appplattform. | ej planerad |
| API-395 | Råd och tak för appar som körs i många arbetsytor. | inte gjord | Ingen appplattform. | ej planerad |
| API-396 | Ett nytt appprojekt har en fast struktur och fasta beroenden. | inte gjord | Ingen appplattform. | ej planerad |
| API-397 | Den lokala utvecklingsservern har version, port och uppgradering. | avstår | Gäller bara egen drift av Twenty: en lokal server att utveckla appar mot. |  |
| API-398 | Signeringsnycklar för token roteras. | avstår | Gäller bara egen drift av Twenty (instansens nycklar). |  |
| API-399 | Hemligheter krypteras i vila och nyckeln kan roteras. | avstår | Gäller bara egen drift av Twenty. Snajp krypterar redan webhookarnas hemligheter (`snajp-support/app/integrationer/hemligheter.py`, använd i `webhooks.skapa`). |  |
| API-400 | Vilka sökvägar som måste vara publika vid egen drift. | avstår | Gäller bara egen drift av Twenty. |  |
| API-401 | `app init` skapar ett nytt projekt utan sidoeffekter. | inte gjord | Inget CLI. | ej planerad |
| API-402 | `app add` genererar definitioner för objekt, fält och funktioner. | inte gjord | Inget CLI. | ej planerad |
| API-403 | `app build` och `app typecheck` bygger och kontrollerar en app. | inte gjord | Inget CLI. | ej planerad |
| API-404 | `app plan` förhandsgranskar en appsynk utan att ändra något. | inte gjord | Inget CLI. Närmast för data: synkens förhandsgranskning `POST /connections/{c}/preview`. | ej planerad |
| API-405 | `app apply` bygger, laddar upp och synkar en app. | inte gjord | Inget CLI. | ej planerad |
| API-406 | `app dev` bevakar filer och synkar löpande. | inte gjord | Inget CLI. | ej planerad |
| API-407 | `app generate-client` genererar om den typade klienten. | inte gjord | Inget CLI. | ej planerad |
| API-408 | `app pull` jämför arbetsytan mot en baslinje. | inte gjord | Inget CLI. | ej planerad |
| API-409 | `app install` installerar en registrerad version. | inte gjord | Inget CLI. | ej planerad |
| API-410 | `app uninstall` tar bort en app och dess data. | inte gjord | Inget CLI. | ej planerad |
| API-411 | CLI:t hanterar utgångna sessioner och beskriver sig själv. | inte gjord | Inget CLI. | ej planerad |
| API-412 | `app publish --private` och `app translations extract`. | inte gjord | Inget CLI. | ej planerad |
| API-413 | En app deklarerar index, också unika. | inte gjord | Ingen appplattform. | ej planerad |
| API-414 | En app deklarerar relaterade postvägar för behörigheter. | inte gjord | Ingen appplattform. | ej planerad |
| API-415 | En logikfunktion har fem sorters utlösare. | inte gjord | Inga logikfunktioner. | ej planerad |
| API-416 | Driftaren väljer körmiljö för logikfunktioner och kodtolk. | avstår | Gäller bara egen drift av Twenty. |  |
| API-417 | Utgående anrop till interna adresser blockeras. | verifierad | Nätvakten släpper bara publika https-adresser, också när namnet pekas om efteråt (`snajp-support/app/integrationer/natvakt.py`); `test_handelser_webhooks.py::test_bara_publika_https_adresser_och_kanda_handelser`, `test_adressen_provas_igen_nar_leveransen_gar`. Undantagslistan för egen drift behövs inte. |  |
| API-418 | Jobbkön har minnesgränser per arbetsyta och app. | avstår | Gäller bara egen drift av Twenty. |  |
| API-419 | API och webbklient kan ligga på olika värdar. | avstår | Gäller bara egen drift av Twenty. |  |
| API-420 | En exempelapp och en introduktion med tre spår för utvecklare. | delvis | Finns: "Kom igång" i `docs/crm/API.md`, tre steg från nyckel till synkade kunder. Saknas: exempelapp och appspår. | ej planerad |
| API-421 | Bidragsdokumentation för Zapier-kopplingen, funktionsflaggor och köer. | avstår | Gäller bara den som utvecklar och driver Twenty själv. |  |
| API-422 | Filer i svaren får signerade adresser. | delvis | Finns: bilagans `content_url` pekar på en nyckelskyddad nedladdning (`crm_v1_objekt.py`, `/attachments/{id}/content`; `test_objekt_ovriga.py::test_bilagan_laddas_upp_listas_utan_innehall_och_laddas_ned`). Saknas: signerade adresser och bilder i rik text. | ej planerad |
| API-423 | Relaterade poster i svaret hämtas per förälder med tak. | inte gjord | Relaterade poster följer aldrig med i svaret. | ej planerad |
| API-424 | Meddelanden, kalender och tidslinje döljs enligt kanalens synlighetsnivå. | inte gjord | Inga synlighetsnivåer per kanal i CRM:ets tidslinje (`snajp-support/app/crm/tidslinje.py`). | ej planerad |
| API-425 | Bara vissa av en frontkomponents egenskaper får ändras. | inte gjord | Ingen appplattform. | ej planerad |
| API-426 | MCP-servern ger klienten instruktioner om hur verktygen används. | inte gjord | Ingen MCP-server. | ej planerad |
| API-427 | Webbklientens applistor hålls aktuella och tredjepartsappar märks. | inte gjord | Ingen appplattform. | ej planerad |
| API-428 | Playgroundens formulär väljer nyckel, schema och typ. | inte gjord | Ingen playground. | ej planerad |
| API-429 | Appanslutningarnas inloggningsflöden har tidsgränser. | inte gjord | Ingen appplattform. | ej planerad |
| API-430 | Händelseströmmen skickas med behörighetsfilter per mottagare. | inte gjord | Ingen händelseström. | ej planerad |
| API-431 | Förlagan deklarerar 75 AI-verktyg för metadata. | inte gjord | Inga AI-verktyg i CRM:et. | ej planerad |
| API-432 | En AI-agent startas av en posthändelse eller ett schema. | inte gjord | Inga AI-agenter i CRM:et. | ej planerad |

## Rättat vid kontroll 2026-11-27

Kontrollen räknade 351 ID:n i underlaget (tabellraderna ovanför "Rättat vid kontroll") och 351 i den här filen; inga saknades. Prövade mot koden: alla 25 rader som stod som verifierade, raden som stod som byggd, alla 41 som stod som delvis och ett femtiotal rader som stod som inte gjorda och handlar om affärer, tidslinje, papperskorg, webhooks, händelser, bilagor och spärrar (bland dem API-011, 014, 016, 018, 019, 021, 023, 028, 029, 056, 069, 070, 093, 101, 207, 304, 347, 424 och 430). Spärrlistan (`/suppressions`, `sparr.py`) finns ännu inte i koden och har ingen rad här.

| ID | Från | Till | Varför |
|---|---|---|---|
| API-024 | verifierad | byggd | Testet använder bara `limit` 3 och 500; standardvärdet 50 och 422 över taket prövas av inget test. |
| API-091 | verifierad | byggd | `DELETE /webhooks/{id}` och ändring av adress eller händelser prövas av inget test; testen visar bara `PATCH` av `active` och listan. |
| API-097 | verifierad | byggd | Tidsgränsen på tio sekunder prövas av inget test; 2xx och blockerade adresser prövas. |
| API-343 | byggd | verifierad | Bilderna `panel-webhooks-lista-390.png` och `panel-webhooks-logg-1440.png` visar förklaringen i gränssnittet. |
| API-029 | inte gjord | delvis | `missing_source` på `GET /people` är ett fast tomt-filter (inget test). |
| API-027 | delvis | delvis | Texten saknade filtren `source_type`, `stage_id` och `lost_reason_code` (de två senare prövade i `test_kalla_forlustorsak.py`). |
| API-263 | delvis | delvis | Texten sa att en bild saknades; bilderna finns under `docs/crm/bilder/fas3/panel-webhooks-*`. |
