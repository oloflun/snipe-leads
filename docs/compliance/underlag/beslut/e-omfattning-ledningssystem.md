## [FYLL: datum] (Anton) — Vad ledningssystemet för säkerhet och AI omfattar

**Bakgrund.** ISO 27001 4.3 och ISO 42001 4.3 kräver ett beslutat omfång. Utan det går det inte att säga vilka system, personer och leverantörer som policyerna 01–28 gäller. Förslaget i P07 räknar fortfarande med Redis Cloud, som jobbkön lämnade 2026-11-17. Snajp har inga lokaler; allt arbete sker på egna datorer och all drift hos leverantörer.

**Beslut.** Ledningssystemet för informationssäkerhet och AI omfattar:

- **Tjänsten:** supportagenten, leadsagenten (Iris), Jev i leads, kvittohanteraren, med webb, api och agentsajt.
- **AI-systemen:** supportagenten, Iris och Jev, och modellerna de använder (Gemini via Vertex AI i EU, Jev hos TypeSafe). AI-kodverktyg som Anton och Sebbe använder i arbetet ingår.
- **Driften:** Railway-miljöerna `main` och `development` i Amsterdam (web, api, Postgres och Redis), Google Cloud, Resend, Loopia (DNS) och övriga leverantörer i `leverantorer.json`. Redis Cloud, Supabase och Render ingår tills de är raderade och raderingen bekräftad.
- **Utvecklingen:** koden och CI i GitHub, migrationerna och synken mellan miljöerna.
- **Personerna:** Anton och Sebbe.
- **Utrustningen:** deras datorer och telefoner som når kod, driftkonton eller kunddata.

Utanför omfånget:
- kundernas egna system och konton (inkorgar, CRM, kanaler), som kunden ansvarar för;
- leverantörernas egna datacenter och fysiska skydd, som följs upp genom deras intyg (A.5.19–A.5.23);
- fysiska lokaler, eftersom Snajp inte har några (A.7.1–A.7.6, A.7.11, A.7.12 ej tillämpliga);
- privat användning av datorerna som inte rör Snajp.

**I praktiken.** Omfånget i P07 och P27 ersätts av den här posten, och raden om Redis Cloud gäller bara tills databasen är raderad. En ny leverantör, ett nytt AI-system eller en ny person tas in i omfånget genom beslut f (leverantörer och modeller) respektive P15 (personer). Omfånget ses över varje år.

Krav: ISO 27001 4.3, 4.4 (delvis); ISO 42001 4.3, 4.4 (delvis).

Datum: ____________________

Anton: ____________________
