# Intressenter och deras krav (utkast)

Datum: 2026-11-18. Skrivet av Claude (agent) på Antons uppdrag. Status: **utkast,
inte beslutat**. Underlag för ISO 27001 4.2 och ISO 42001 4.2. Listan sammanställer
det som redan står i avtal, policyer och lagar; den lägger inte till nya krav. Vilka
krav som tas in i ledningssystemet (4.2 c) är ägarens beslut.

| Intressent | Krav på informationssäkerhet och AI | Källa | Hur Snajp möter kravet i dag | Öppet |
|---|---|---|---|---|
| **Kunderna** (hyr support-, leads- och kvittoagenterna) | Konfidentialitet mellan kunder; att data bara behandlas enligt instruktion; underrättelse vid incident; underbiträden redovisade; radering vid avtalets slut; ingen överföring till tredje land utan grund; begriplig AI-upplysning till deras kunder | `docs/pub-avtal.md`, `docs/pilotavtal.md` (utkast) | RLS per kund verifierad i CI (INV-SEC-001); DeepSeek spärrad i drift (`CLAUDE.md`); AI-upplysning i svaren (`processor.med_ai_upplysning`); systemblad per AI-system (`ai-system/`) | PUB och pilotavtal osignerade; radering vid avslut är inte en rutin |
| **Kundernas kunder** (skriver till kundens support) | Art. 13/14-information; rättigheter enligt art. 15–21; inget automatiserat beslut med rättslig verkan; säkerhet i behandlingen | GDPR; DPIA | Rättighetsskriptet `scripts/gdpr_radera.py` (sök, utdrag, radering, begränsning art. 18), provkört i CI; mänsklig granskning av utkast (autonominivåer) | Rutinen för rättigheter osignerad; release-PR 72 inte mergad |
| **Prospekten och deras kontaktpersoner** (leadsdelen; Snajp ansvarig) | Laglig grund (berättigat intresse); art. 14-information i första mejlet; avregistrering som gäller direkt; inga privatpersonsidor; webbplatsbedömningen hemlig | GDPR, marknadsföringslagen, `CLAUDE.md` leadsregler | Sändningsspärren `send_guard` (avsändare, avregistrering, spärrlista, art. 14-fot, volymtak, granskning); spärrlistan överlever radering; begränsningsmarkering (migration 124) | Intresseavvägningen ej juristgranskad (LBT-2) |
| **Kundens användare och plattformsadmin** | Skydd av konto och lösenord; att admins åtkomst syns | Användarvillkor | scrypt-hashade lösenord, sessions-JWT (`AUTH.md`); åtkomstlogg för admin (migration 123) | Ingen tvåfaktor, ingen spärr mot upprepade inloggningsförsök (A.8.5) |
| **IMY** | Anmälan inom 72 timmar; registerförteckning; DPIA där det krävs; dokumenterad ansvarsskyldighet | GDPR art. 30, 33, 35 | `INCIDENT_RESPONSE.md`; `docs/registerforteckning.md`; `datamangder.md` | Lagringstider obeslutade (LBT-1); incidentposter ej bedömda (DS-5) |
| **Andra myndigheter** (polis, Skatteverket, domstol) | Att förfrågningar besvaras korrekt; bokföringsunderlag i sju år där Snajp är bokföringsskyldig | Lag; BFL | Kontaktlistan (`myndighetskontakter.md`, utkast) | Ingen förfrågningslogg |
| **EU:s AI-förordning** | Transparens mot den som interagerar med AI (art. 50); för de flesta system inga högriskkrav | `ramverk/iso42001/ai-forordningen.md` | AI-upplysning i svar och chatt; systemblad | Bedömningen inte beslutad |
| **Leverantörer och underbiträden** (Railway, Google, Resend, ScrapeGraphAI, TypeSafe, GitHub, Loopia) | Att deras villkor följs; att nycklar inte delas; att incidenter hos oss som rör dem meddelas | Deras villkor och DPA:er | `leverantorer.json`, `leverantorsgranskning.md` | DPA:er med Railway och ScrapeGraphAI osignerade (AG-2) |
| **Ägaren (Anton) och medarbetaren (Sebbe)** | Att systemet går att drifta och granska utan att lita på minnet; att ingen ensam ändring når produktion ogranskad | `CLAUDE.md`, `DEPLOY.md` | CI-grindar (`drift-och-tillgangar.md` §4); release till `main` är Antons handgrepp | Grenskyddet gäller inte på gratisplanen; Sebbes avtal okänt (A.6.2) |
| **AI-agenterna som arbetar i repot** (Claude Code m.fl.) | Tydliga gränser: inga hemligheter, ingen skrivning till Supabase, inget till `main` | `CLAUDE.md`, `AGENTS.md` | Projektreglerna, invarianttesterna | Reglerna är inte tekniska spärrar (`privilegierade-verktyg.md`) |

## Det Anton beslutar

1. Vilka intressenter och krav som är relevanta för ledningssystemet (4.2 b–c).
2. Hur ofta listan ses över, och av vem.
