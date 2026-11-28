# Steg 4.3: utkastredigeraren och `/crm/iris/utkast`

Bildernas prefix: `43-`. Läs `git log --oneline -15` först: stegen före ditt är byggda, och du återanvänder deras komponenter (läs dem) i stället för att bygga egna.

## Raderna

LU-030 till LU-070, LU-080 till LU-088, LU-150 till LU-159, LU-172 till LU-183 (`docs/crm/underlag/app-05-leads-utkast-konversationer-samtal.md`,
avsnitten B, C, D, I och K, och "Rättat vid kontroll"), och AP15 (`docs/crm/underlag/app-10-api-under-ytorna.md`). Många av
raderna LU-050 till LU-070 är "ingen egen vy": de syns som utfall och skäl på utkastet (varför det inte
skickats, när det skickas). Visa skälet backenden lämnar, i klartext på två språk.

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/IrisGranskning.tsx`, `KorningensUtkast.tsx`, `SkickatLista.tsx`, `BekraftaUtskick.tsx`,
`ProvmejlKnapp.tsx`, `StrukturVal.tsx`, `components/email/EmailStudioEditor.tsx` (redigerarens beteende),
och `docs/UTKASTKEDJAN-REFERENS-2026-10-16.md` (vad ett utkast är och varför det ser ut som det gör:
gränssnittet ändrar aldrig utkastets innehåll på egen hand, och visar aldrig en mall som utkast).

## Det som ska byggas

1. **Utkastredigeraren** (NYTT MÖNSTER, `components/crm/app/iris/Utkastredigerare.tsx`), en gång, så att
   panelen (4.2), körningarna (4.4), konversationerna (4.6) och Kundtjänst (fas 5) använder samma:
   ämne och text som går att redigera, signatur, logga och lagstadgad fot som mottagaren ser dem, spara
   före godkänn, struktur A/B, handlingskontrollen före Skicka, Skriv om med önskemål, provmejl, och
   förlopp medan Iris skriver (pollning som dagens). Astryx `TextArea`, `TextInput`, `Card`, `Dialog`.
2. **Vyn** `components/crm/app/iris/UtkastVy.tsx` på `/crm/iris/utkast` med vyerna Att granska,
   Skickas snart och Skickat. Markering med mängdåtgärder (godkänn, avvisa, ändra tid, skicka nu,
   tillbaka till Iris, skapa uppföljning) med bekräftelse där dagens har det. Nyckeltalen (LU-088) står i
   vyraden i räknefotens stil, inte som en egen ruta.
3. **Koppla in redigeraren i leadets panel** från steg 4.2 (utkastfliken): läs `LeadPanel.tsx` och ersätt
   platsen som lämnats åt redigeraren.
4. Posten Utkast i gruppen Iris i navigeringsregistret, och i kommandopaletten.

Commit: `feat(crm): utkastredigeraren och Iris utkast (att granska, skickas snart, skickat)`.
