# Steg 5.2: Företaget, Vad ni säljer, Kunskapsbas, Så ska agenten låta

Bildernas prefix: `52-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

IN-012, IN-020 till IN-042, IN-146 (`docs/crm/underlag/app-08-installningar.md`), SU-120 till SU-133 (`docs/crm/underlag/app-06-support.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/settings/Affarskontext.tsx`, `Kunskapsbas.tsx`, `WebbplatsForslag.tsx`, `AgentOnskemal.tsx`,
`components/SoulEditor.tsx`, och hur `app/settings/[[...slug]]/page.tsx` hämtar deras data.

## Det som ska byggas

Fyra sektioner i inställningsskalet (steg 5.1), en komponent per sektion under
`components/crm/app/installningar/`:

1. **Företaget** (`foretaget`): bolagsuppgifterna. IN-146 säger att de ska gå att redigera: finns
   ändpunkten, bygg det, annars visa dem och skriv i rapporten vad som saknas.
2. **Vad ni säljer** (`vad-ni-saljer`).
3. **Kunskapsbas** (`kunskapsbas`): listan, lägg till, ändra, ta bort, uppladdning av fil (använd
   importmönstret om det passar, annars Astryx filval), förslag ur webbplatsen (SU-12x), förlopp medan
   något indexeras och utfallet kvar efter omladdning.
4. **Så ska agenten låta** (`rost`): fritexten med förhandsgranskning och versioner
   (`Forhandsgranskning` från steg 4.5).

Slå på sektionerna i sektionsregistret. Commit:
`feat(crm): installningar for foretaget, vad ni saljer, kunskapsbas och agentens rost`.
