# Steg 4.6: tråd- och inkorgsvyn och `/crm/iris/konversationer`

Bildernas prefix: `46-`. Läs `git log --oneline -15` först: stegen före ditt är byggda, och du återanvänder deras komponenter (läs dem) i stället för att bygga egna.

## Raderna

LU-001 till LU-024, LU-081, LU-089, LU-110 till LU-122 (`docs/crm/underlag/app-05-leads-utkast-konversationer-samtal.md`,
avsnitten A, D och F), och OV-105 (`docs/crm/underlag/app-02-oversikt-att-gora-larande.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/Konversationer.tsx`, `KonversationsTrad.tsx`, `IrisInkorg.tsx`, `Svar.tsx`,
`lib/leads/konversationer*`.

## Det som ska byggas

1. **Tråd- och inkorgsvyn** (NYTT MÖNSTER, `components/crm/app/Tradvy.tsx`), en gång, så att Kundtjänst
   (fas 5) använder samma: lista till vänster och öppen tråd till höger (på telefon: listan, sedan
   tråden), meddelanden i tidsordning med avsändare och tid, steg som piller, svarsruta med utkastet
   nederst (redigeraren från 4.3), oläst-markering, och den öppna tråden i adressen (`?trad=`).
2. **Vyn** `components/crm/app/iris/KonversationerVy.tsx` på `/crm/iris/konversationer` med vyerna Att
   göra, Alla och Inkommande. Stegen, återkomdatum, överlämning och möte som dagens.
3. Posten Konversationer i gruppen Iris med räknare (olästa), och i kommandopaletten.
4. Länken från historiken i bolagets panel (`Tidslinje.tsx` länkar i dag till
   `/dashboard/leads?vy=konversationer&trad=`): låt den gå till `/crm/iris/konversationer?trad=` när vyn
   finns, och leadets länk till `/crm/iris/leads?lead=`. Ändringen är i `components/crm/app/Tidslinje.tsx`.

Commit: `feat(crm): tradvyn och Iris konversationer`.
5. **Länkarna som i dag går till dagens app ska gå hit:** notislistan i skalet (`Notiser.tsx`, svaren och
   utkasten länkar till konversationen), den skickade konversationen i `UtkastPanel.tsx` (en väg till
   hela tråden), och leadets panel (`LeadHistorik.tsx`, om den länkar till en tråd). Läs var de pekar i
   dag och peka om dem till `/crm/iris/konversationer?trad=` (i förhandsvisningen under samma bas).
