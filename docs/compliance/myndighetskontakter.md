# Myndighets- och incidentkontakter (utkast)

Datum: 2026-11-18. Skrivet av Claude (agent) på Antons uppdrag. Status: **utkast**.
Kolumnen "Vem kontaktar" är tom med flit: det är ägarens beslut. Underlag för ISO 27001
A.5.5 och A.5.24–A.5.26, GDPR DS-5. Rutinen för personuppgiftsincidenter står i
`INCIDENT_RESPONSE.md`; den här listan är vart man vänder sig.

Uppgifterna om myndigheterna är allmänt publicerade. **Kontrollera dem mot källan när
listan beslutas och minst en gång om året**; datum för senaste kontroll står i sista
kolumnen. Leverantörernas säkerhetskontakter är inte verifierade av agenten och står
som "verifieras".

## 1. Myndigheter

| Vem | När | Hur | Vem kontaktar | Kontrollerad |
|---|---|---|---|---|
| **IMY** (Integritetsskyddsmyndigheten) | Personuppgiftsincident där Snajp är personuppgiftsansvarig (leadsdelen, egna konton): anmälan inom 72 timmar om den inte är osannolik att medföra risk (art. 33, `INCIDENT_RESPONSE.md`). Är Snajp biträde underrättas kunden, som anmäler | E-tjänsten för anmälan av personuppgiftsincident på imy.se. Växel 08-657 61 00, imy@imy.se. E-tjänsten: imy.se › Verksamhet › Utföra ärenden › Anmäla personuppgiftsincident | | 2026-11-18, imy.se/om-oss/kontakta-oss (agenten) |
| **CERT-SE** (MSB) | It-incident som kan beröra andra (intrång, skadlig kod, läckta nycklar som används), eller när vi behöver råd. Frivilligt för Snajp, som inte omfattas av NIS-reglerna såvitt känt (inte bedömt) | cert@cert.se, 010-382 80 00, bemannat dygnet runt alla dagar (cert.se/kontakt). Utkastet hade 010-240 40 40, som var fel | | 2026-11-18, cert.se/kontakt (agenten) |
| **Polisen** | Brott: dataintrång, utpressning, bedrägeri. Anmälan behövs ofta också för försäkring | 114 14; 112 vid pågående brott och akut fara. Många brott kan anmälas i polisens e-tjänster på polisen.se | | 2026-11-18, polisen.se/kontakt (agenten) |
| **Kundens kontakt** | Varje incident som rör en kunds data (Snajp är biträde): underrättelse utan onödigt dröjsmål enligt PUB-avtalet | Kundregistret (`ss_customer_details`), avtalet | | – |

## 2. Leverantörer: driftstörning och säkerhetsincident

| Leverantör | Vad vi använder | Störning | Säkerhetsincident / anmälan | Vem kontaktar |
|---|---|---|---|---|
| Railway | All drift: web, api, support, Postgres, Redis (`drift-och-tillgangar.md` §1) | status.railway.com; support i Railways konsol | verifieras | |
| Google Cloud (Vertex AI) | Alla modellanrop | status.cloud.google.com; supportärende i GCP-konsolen | verifieras | |
| GitHub | Källkod, CI, migrationer, övervakning | www.githubstatus.com; GitHub Support | verifieras | |
| Resend | Utgående mejl | verifieras | verifieras | |
| ScrapeGraphAI | Hämtning av bolagssajter | verifieras | verifieras | |
| TypeSafe (Jev) | Förfiltrering av leads | Kontaktperson enligt avtal | Kontaktperson enligt avtal | |
| Loopia | DNS för snajp.se | Loopias support | verifieras | |
| Supabase, Render, Redis Cloud (avvecklade, inte raderade) | Inget i drift | – | Gäller vid läckage ur kvarvarande data | |

Hela leverantörsförteckningen med roller: `leverantorer.json`, `leverantorsgranskning.md`.

## 3. Myndighetsförfrågningar

En förfrågan från en myndighet om att lämna ut uppgifter (polis, Skatteverket, domstol)
besvaras inte av den som tar emot den. Den förs vidare till ägaren och noteras med datum,
myndighet, vad som begärdes och vad som lämnades ut. Var loggen ska föras är inte
beslutat (G01, se `ramverk/iso27001/matris.md` A.5.5).

## 4. Det Anton beslutar

1. Vem som kontaktar respektive part, och vem som ersätter den personen.
2. Om CERT-SE ska kontaktas vid incidenter som inte kräver det.
3. Var förfrågningsloggen förs.
4. Att uppgifterna i avsnitt 1 och 2 kontrolleras mot källan, och hur ofta.
