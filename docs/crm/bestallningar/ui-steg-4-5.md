# Steg 4.5: `/crm/installningar/iris`

Bildernas prefix: `45-`. Läs `git log --oneline -15` först: stegen före ditt är byggda, och du återanvänder deras komponenter (läs dem) i stället för att bygga egna.

## Raderna

LK-060 till LK-073 (`docs/crm/underlag/app-04-leads-korningar-listor-kallor.md`, avsnitt D), IN-100 till IN-112 och
IN-144 (`docs/crm/underlag/app-08-installningar.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/IrisInstallningar.tsx`, `IrisProfil.tsx`, `IrisAutomation.tsx`, `IrisProdukter.tsx`,
`IrisEskalering.tsx`, och sidorna under `app/settings/` som visar dem.

## Det som ska byggas

Inställningsskalet byggs i fas 5 (steg 5.1). Bygg därför Iris inställningar som EN sida på
`/crm/installningar/iris` med `Sida` och flikar eller sektioner för profilen och målgruppen, vad ni
säljer, automationen och eskaleringen, på ett sätt som går att lyfta in i skalet senare utan att skrivas
om (en komponent per sektion under `components/crm/app/installningar/iris/`). Förhandsgranskning med
versioner (IN-108) är ett NYTT MÖNSTER: `components/crm/app/Forhandsgranskning.tsx` (fritext in,
förhandsgranskning av hur den bakas in, godkänn och spara, historik och återställ), byggt en gång.
Hemligheter (LK-073) visas aldrig. Posten nås från arbetsyteväxlarens meny (Inställningar) och från
Körningar ("Iris inställningar"), inte som en egen post i gruppen Iris.

Commit: `feat(crm): Iris installningar (profil, vad ni saljer, automation, eskalering)`.

Tänk på: det här är formulär, inte listor. Varje sektion sparar för sig, säger utfallet där man sparade,
varnar innan man lämnar med osparade ändringar, och visar backendens fältfel vid rätt fält (LK-137:
målgruppens validering i `PUT /leads/config`). Signaturen, avsändaren, schemat och spärrlistan (IN-110,
IN-144, LU-179) och strukturen A/B som förval (LU-159, använd `StrukturVal`) hör hit. Autopilotens
inställning (LK-138) hör hit.
