# Steg 4.4: `/crm/iris/korningar`, körningens sida och dialogen Kör Iris

Bildernas prefix: `44-`. Läs `git log --oneline -15` först: stegen före ditt är byggda, och du återanvänder deras komponenter (läs dem) i stället för att bygga egna.

## Raderna

LK-001 till LK-057 och LK-130 till LK-138 (`docs/crm/underlag/app-04-leads-korningar-listor-kallor.md`, avsnitten A, B, C
och K), och OV-031 till OV-037 (`docs/crm/underlag/app-02-oversikt-att-gora-larande.md`). Raderna i avsnitt C (motorn)
är "ingen egen vy": de syns som förlopp, tratt och skäl på körningen. CLAUDE.md, leadsreglerna 23 och
24 (beställt antal, påfyllda leads, vilande körning) avgör vad körningens utfall heter: läs dem.

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/IrisKorningar.tsx`, `LeadsRunForm.tsx`, `KorningensUtkast.tsx`, `LeadsControls.tsx`,
`pafyllnad.ts`, `app/dashboard/leads/` (körningens egen adress), och ändpunkterna
`/api/snajp-support/leads/korningar`, `/leads/jobb/...`, `/leads/runs/batch` i `snajp-support/app/api/leads.py`.

## Det som ska byggas

1. **Körningarna** `components/crm/app/iris/KorningarVy.tsx` på `/crm/iris/korningar`: listan över alla
   körningar med läge, beställt och levererat, och förloppet för den som går (SynkVy är förebilden för
   förlopp och utfall: läs `SynkVy.tsx`). Förloppet pollas som dagens och står kvar efter omladdning.
2. **Körningens sida** `/crm/iris/korningar/[id]` (eller en panel med `?korning=`: välj det som passar
   mönstren och säg varför): tratten, stegen, skälen, körningens leads (öppnas i `LeadPanel` från 4.2),
   körningens utkast (öppnas i redigeraren från 4.3), Bortvalda med skäl, påfyllda leads märkta, och en
   vilande körning sagd i klartext.
3. **Kör Iris** som dialog (`BolagFormular` är förebilden): alla fält dagens formulär har, med samma
   gränser, förhandsbesked och fel. Provkörning och skarp körning som dagens.
4. Posten Körningar i gruppen Iris, och Kör Iris i kommandopaletten (Skapa).

Webbplatsbedömningen: körningens arbetsminne och webbpoolens fördelning lämnar aldrig API:t (LK-033,
OV-037). Visa bara det svaret bär.

Commit: `feat(crm): Iris korningar med forlopp, korningens sida och Kor Iris`.
