# Steg 4.2: `/crm/iris/leads` med panelen `?lead=`

Iris leads som lista och post i CRM:ets form. Grunden som körningar, utkast och listor senare öppnar
poster i. Bildernas prefix: `42-`.

## Raderna

LR-001 till LR-075 och LR-090 till LR-114 (underlaget
`docs/crm/underlag/app-03-leads-oversikt-pipeline-bolag.md`, avsnitten A, C, E och H, och "Rättat vid
kontroll" och "Anrop följda hela vägen" i samma fil). Ändpunkterna står i
`docs/crm/underlag/app-10-api-under-ytorna.md` (AP63 till AP70 med flera: sök på `prospects`).
Hör en rad i spannet till en annan vy (översikten LR-020 till LR-027 byggs i steg 4.11, bolagssöket
LR-080 till LR-082 i 4.12, listorna LR-120 till LR-135 i 4.9), bygg den inte och säg det i rapporten.

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/LeadsSida.tsx`, `LeadsTabell.tsx`, `LeadsControls.tsx`, `IrisBolag.tsx`,
`Bolagssida.tsx`, `Tidslinje.tsx`, `Svar.tsx`, `sidindelning.tsx`, `pafyllnad.ts`, och `lib/leads/*`
(etiketter, statusar, listvyn). Backendens svar: `snajp-support/app/api/leads.py` (prospekten),
`snajp-support/app/leads/listvy.py` (vad som får synas i listan).

## Det som ska byggas

1. **Listan** `components/crm/app/iris/LeadsVy.tsx` på `/crm/iris/leads`, byggd som `BolagVy`:
   - Vyraden: Att bearbeta per status (dagens statusremsa "Pipeline" blir vyer med antal), Bortvalda,
     Arkiverade, Testyta. Läs raderna för exakt vilka statusar som finns och vad de heter.
   - Tabellen: bolaget som postchip, status, kontakt, signal, källa, senast ändrad, och det raderna
     kräver. Markering med `TableSelectionToolbar` för de mängdåtgärder dagens tabell har. Sök, sortering
     och sidindelning som dagens (läs `sidindelning.tsx` och `pafyllnad.ts`).
   - Telefon: rader, som i `BolagVy`.
   - Räknefoten säger samma tal som vyraden.
2. **Panelen** `components/crm/app/iris/LeadPanel.tsx`, byggd som `BolagPanel`, öppnad med `?lead=<id>`:
   flikarna raderna kräver (översikt med bolag och kontakt, Iris bedömning och motivering, utkastet,
   historik, källa). Statusbyte, anteckning, arkivera, välj bort, kontakta inte och det övriga raderna
   beskriver, med Ångra där dagens har det.
   - **Utkastet** visas i panelen som mottagaren ser det, med de handlingar som inte kräver redigeraren
     (godkänn, avvisa, skriv om om ändpunkten finns). Redigeraren själv byggs i steg 4.3: lämna en tydlig
     plats för den i koden, men visa ingen knapp som inte gör något.
   - **Historiken** återanvänder `components/crm/app/Tidslinje.tsx` om leadet har en tidslinje i CRM:ets
     API, annars visar den det dagens låda visar. Skriv i rapporten vilket du valde och varför.
3. **Webbgrinden, en gång** (LR-090 till LR-097): en liten hjälpare `lib/crm/iris/webb.ts` som svarar om
   en rad bär webbplatsbedömningen (fälten finns i svaret), och kolumnen, filtret, sorteringen och
   panelens del om sajten visas BARA då. Skriv ett test i förhandsvisningen: `?webb=1` ger svar med
   fälten, utan parametern saknas de, och då ska ingenting om sajten finnas på sidan, inte ens en tom
   kolumn. Ta bild på båda.
4. **Anropen** i `lib/crm/iris/anrop.ts`: en `irisAnrop<T>(vag, init)` mot `/api/snajp-support/leads/...`
   med samma felhantering som `crmAnrop` (läs vilken felform leads-API:t har: den är inte CRM-API:ts),
   och typerna för prospektet i `lib/crm/iris/lead.ts`.
5. **Navigeringen:** slå på posten Leads i gruppen Iris i registret från steg 4.1, och lägg till Leads i
   kommandopaletten (Gå till).
6. **Läsroll och kundbesök:** skrivande knappar stängs av med förklaringen ur hjälparen från 4.1.

Commit: `feat(crm): Iris leads som lista och panel i CRM:et`.
