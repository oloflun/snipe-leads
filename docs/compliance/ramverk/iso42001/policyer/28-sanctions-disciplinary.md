# Sanctions & Disciplinary

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`), och när någon anställs eller anlitas |
| Ramverkets mall | `frk_pt_685e45f736049f188c3439b4` (avdelning `hr`) |
| Täcker kontroll | Disciplinary process (`frk_ct_683f4457b14856e700c8c25b`) |
| Täcker krav | 7.2, och genom egen koppling A.3.3. Fyller också gapet i ISO 27001 A.6.4 (`../../iso27001/matris.md`) |

## Syfte

Säga vad som händer när någon bryter mot säkerhets-, dataskydds- eller AI-reglerna, så att följden är förutsägbar och rättvis. Mallen förutsätter en HR-avdelning; Snajp har två personer och ingen anställd.

## Omfattning

Alla som arbetar för Snajp, oavsett avtalsform: i dag Anton och Sebbe, senare anställda och konsulter. Reglerna som avses är de godkända policyerna G01–G06, P07–P27.

## Läget i dag

- Inga sanktioner är skrivna. Om Sebbes avtal reglerar följden av regelbrott är okänt (`../../iso27001/matris.md` A.6.2, A.6.4).
- Som ägare av en enskild firma bär Anton ansvaret själv. Policyn kan inte disciplinera ägaren; den styr i stället hur ett eget avsteg dokumenteras (avsnittet Undantag).

## Hur ett brott hanteras

1. **Säkra först.** Ett brott som rör kunddata eller en AI-tjänst stoppas innan något annat görs: dra in åtkomst, stäng av variabeln, rotera nyckeln. Incidentrutinen gäller parallellt (G03).
2. **Utred.** Anton går igenom vad som hänt med git-historik, `agent_runs`, `ss_decision_log` och leverantörernas loggar. Den berörda får förklara sig innan något beslutas.
3. **Bedöm allvar.** Avsikt, tidigare händelser och risk för kundernas kunder vägs in.
4. **Besluta och skriv.** Beslutet skrivs med skäl i en rad som inte ligger i det publika repot: [FYLL: plats, t.ex. `docs/compliance/loggar/`].

## Nivåer

- **Mindre** (t.ex. en hemlighet i en commit som upptäcks före push): samtal och genomgång av regeln.
- **Måttlig** (t.ex. en modell eller leverantör slås på för kunddata utan godkännande enligt P27 avsnitt 6): skriftlig erinran och åtgärdsplan.
- **Allvarlig** (t.ex. kunddata lämnas ut avsiktligt, eller ett avsteg upprepas): åtkomsten dras in och avtalet prövas enligt sina villkor. Polisanmälan vid brott.

Hur nivåerna kan tillämpas på Sebbe beror på hans avtal. **Ska ske:** avtalet kompletteras med en hänvisning till den här policyn, [FYLL: datum], ansvarig Anton.

## Den som anmäler

Den som i god tro anmäler oro om säkerhet, dataskydd eller AI-användning får inte missgynnas (krav A.3.3, P27 avsnitt 8).

## Undantag

Mallens överklagande till "senior leadership" går inte med en ägare. I stället: ett beslut mot Sebbe kan på hans begäran prövas av [FYLL: extern person, t.ex. revisor eller jurist]. Eget avsteg av Anton skrivs i BESLUT.md med skäl, som enligt P08.

## Mätning

Varje ärende har ett beslut och en stängd åtgärd. Antalet ärenden tas upp vid ledningens genomgång (P10).

## Förbättring

Policyn ses över när den första personen utöver Anton och Sebbe börjar.
