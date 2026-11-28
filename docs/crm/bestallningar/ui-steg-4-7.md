# Steg 4.7 och 4.8: `/crm/iris/uppfoljningar` och `/crm/iris/samtal`

Bildernas prefix: `47-`. Läs `git log --oneline -15` först: stegen före ditt är byggda, och du återanvänder deras komponenter (läs dem) i stället för att bygga egna.

## Raderna

LU-100 till LU-107 (uppföljningar) och LU-130 till LU-138, LU-170, LU-171 (samtal), i
`docs/crm/underlag/app-05-leads-utkast-konversationer-samtal.md`, avsnitten E och G. CLAUDE.md, leadsreglerna 15 och 17
(ringlistan, återkopplingen och utfallen) avgör vad vyerna heter och gör: läs dem.

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/Uppfoljningar.tsx`, `Samtalslista.tsx`, och ändpunkterna i
`snajp-support/app/api/leads_suite.py` (`samtalslista`, `samtalsantal`, utfallen).

## Det som ska byggas

1. `components/crm/app/iris/UppfoljningarVy.tsx` på `/crm/iris/uppfoljningar`: listvy som `BolagVy`.
   Uppföljningsmejl är alltid utkast som en människa godkänner: de öppnas i redigeraren från 4.3.
2. `components/crm/app/iris/SamtalVy.tsx` på `/crm/iris/samtal` med vyerna Återkoppling och Ringlista:
   de som ska ringas i dag först, antal anställda alltid synligt, och utfallen Ej svar, Återkom (datum),
   Ej intresserad, Kontakta inte och Möte bokat med samma följder som dagens. Utfallet sätts i raden
   eller i en liten dialog, med Ångra där dagens har det. Spärrade nummer syns inte (backenden tar
   bort dem): gränssnittet filtrerar inte själv.
3. Posterna Uppföljningar och Samtal i gruppen Iris (Samtal med räknaren "ring i dag"), och i
   kommandopaletten.

Commit: `feat(crm): Iris uppfoljningar och samtal (aterkoppling och ringlista)`.
