# Incidentövning: manus för 45 minuter

Deltar: Anton (incidentledare), Sebbe (upptäcker händelsen). Ha `INCIDENT_RESPONSE.md` öppen. Ingen rör driften under övningen: allt är på papper. Övningen uppfyller "skrivbordsövning en gång per år" i G03 och ger belägg till ISO 27001 A.5.24, A.5.27 och GDPR DS-5.

## Scenariot (läs högt, 2 min)

Tisdag 14:10. Sebbe ser att en commit han pushade till `development` för två timmar sedan innehöll filen `.env.deploy`. Repot är publikt. Filen bär bland annat lösenordet till produktionens och testmiljöns Postgres, Resend-nyckeln och Vertex-servicekontot. GitHubs push-skydd stoppade inte pushen, eftersom databaslösenord inte har ett känt nyckelformat. Commiten ligger kvar i historiken.

## Förlopp

| Tid | Vad som händer | Frågor att besvara (skriv svaren i protokollet) |
|---|---|---|
| 0–5 | Sebbe har upptäckt det. Anton svarar inte i telefon | Vem gör vad nu enligt §1? När börjar 72-timmarsfristen? Var skriver Sebbe ned klockslaget? (§2 säger `handoffs/`, som ligger i det publika repot: är det rätt plats?) |
| 5–15 | Stoppa blödningen | I vilken ordning roteras nycklarna (§3)? Vem kan rotera databaslösenordet i Railway, och har Sebbe den rätten? Hur kontrollerar ni att den gamla vägen är död? Hur når ni Anton om han är borta i tre timmar? Klarar ni målet 30 minuter (G03)? |
| 15–25 | Inspel: Anton är tillbaka 15:40. Railways loggar visar inte vilka som anslutit till Postgres via den publika porten | Kan ni visa att ingen läst databasen? Om inte: vad säger §4 om avsaknad av loggar? Är det en personuppgiftsincident? Vilka uppgifter, vems, ungefär hur många? Gäller den testmiljön också, som bär samma kunddata? |
| 25–35 | Anmälan och kunder | Var är Snajp ansvarig (konton, egna kallmejl) och var biträde (kundernas kunders mejl)? Vem anmäler till IMY för vad? Vilka kunder underrättas, av vem, inom hur många timmar (§5; PUB-avtalets frist är [FYLL])? Skriv ett första utkast till underrättelsen med punkterna i §2 |
| 35–45 | Efteråt | Vilken ändring i kod eller rutin gör att det inte händer igen (§6)? Vad saknades i rutinen? Vilka kontaktuppgifter (Railway, Resend, Google, IMY, jurist) saknades och var ska de ligga? |

## Facit att jämföra med efteråt (läs inte före övningen)

- Fristen började 14:10, när Sebbe blev medveten, inte när Anton svarade.
- Rotera först, utred sedan. Databaslösenorden, Resend-nyckeln och servicekontots nyckel byts innan någon läser loggar. Historiken måste rensas separat; rotationen är det som skyddar.
- Kan ni inte visa att ingen läst databasen är det en anmälningspliktig incident (§4: avsaknad av loggar är försvårande).
- För kundernas kunders mejl är Snajp biträde: kunden anmäler till IMY, Snajp underrättar kunden snabbare än 72 timmar. För Snajps egna prospekt och konton anmäler Snajp själv.
- Är Anton inte nåbar inom två timmar dokumenterar Sebbe och behandlar händelsen som anmälningspliktig (§1).

## Protokoll (fyll i och spara i `docs/compliance/loggar/`)

```
Incidentövning
Datum och tid: [FYLL]
Deltagare: Anton, Sebbe
Scenario: läckt .env.deploy i publik commit
Tid till beslutad rotationsordning: [FYLL] min
Tid till beslut om anmälningsplikt: [FYLL] min
Beslut i övningen: personuppgiftsincident ja/nej, skäl: [FYLL]
Vem anmäler till IMY / vilka kunder underrättas: [FYLL]
Det som fungerade: [FYLL]
Det som saknades i INCIDENT_RESPONSE.md: [FYLL]
Åtgärder (vad, vem, senast):
  1. [FYLL]
  2. [FYLL]
Nästa övning: [FYLL: datum, senast om tolv månader]
Signatur Anton: __________   Signatur Sebbe: __________
```

Ändringar som övningen visar behövs görs i `INCIDENT_RESPONSE.md` efteråt, som en egen ändring med Antons godkännande.
