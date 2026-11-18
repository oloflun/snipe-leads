# Access Control & Least Privilege

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); åtkomstgranskning kvartalsvis |
| Ramverkets mall | `frk_pt_685e42188e2df1c285cca159` (avdelning `it`) |
| Täcker kontroll | Access Rights (`frk_ct_683f4a410cf5bf6d40bf3583`) |
| Täcker krav | A.5.3, A.5.15, A.5.16, A.5.18, A.8.2, A.8.3 |

## Syfte

Var och en ska ha den åtkomst arbetet kräver och inte mer, och åtkomsten ska följa med när någon börjar, byter uppgift eller slutar.

## Omfattning

Alla konton: personliga, delade och servicekonton, i appen och hos leverantörerna (GitHub, Railway, Google Cloud, Redis Cloud, Resend, Loopia, ScrapeGraphAI, TypeSafe, Gmail-kontot `snajpsupport@gmail.com`). Bara datorer som uppfyller `13-acceptable-use-workstation-security.md` får nå driften.

## Börja, byta, sluta

- **Börja:** Anton beslutar vilka system och vilken roll. Beslutet skrivs i `../../../loggar/atkomst.md` (finns inte; införs [FYLL: datum]). Åtkomst ges först efter kvittens av utbildningen (G05).
- **Byta:** ändras inom 48 timmar.
- **Sluta:** följer avslutsrutinen i `15-background-screening-on-off-boarding.md`, samma dag.
- Det finns ingen central inloggningstjänst (IdP); varje leverantörskonto hanteras för sig. Mallens krav på att knyta konton till HR-status ersätts av förteckningen i `atkomst.md`. Undantag som Anton godkänner.

## Roller

| System | Roller i dag | Ska vara |
|---|---|---|
| Appen | Kundroller per workspace; plattformsadmin i `platform_admins`, ges bara via SQL (`AUTH.md:118-125`) | Oförändrat. Plattformsadmin på personliga konton i stället för det delade `snajpsupport@gmail.com` (`AUTH.md:134-136`) |
| Agentsajten | En gemensam inloggning (`AGENTSAJT_EPOST`/`AGENTSAJT_LOSEN`, `DEPLOY.md:559`) | Personliga inloggningar eller SSO från appen; [FYLL: beslut] |
| Databasen | Approll `snajp_app` utan BYPASSRLS (INV-SEC-001) | Oförändrat. RLS verifieras mot Railway (JA #23) |
| GitHub | [FYLL: vem är admin, vem har skrivrätt] | Anton admin, Sebbe skrivrätt; code owner-granskning på `main` (finns) |
| Railway | [FYLL] | Anton ägare, Sebbe medlem |
| Google Cloud | [FYLL]; ett servicekonto `snajp-vertex` i alla miljöer (JA #14) | Ett servicekonto per miljö, minsta behörighet |
| Övriga leverantörer | [FYLL] | Personliga konton där leverantören tillåter det |

Servicekonton har en ägare, ett syfte, minsta behörighet och ingen inloggning för människor.

## Förhöjd åtkomst

- Plattformsadmin, Railway-ägare och GitHub-admin räknas som privilegierade. Förteckningen står i `atkomst.md`.
- Mallen kräver tidsbegränsad admin (högst 24 timmar) och godkännande av ledningen. Med två personer som båda arbetar i driften dagligen är det inte praktiskt. I stället: privilegierade konton kräver tvåfaktor (P12), och varje skrivande åtgärd mot driften görs med skript som har torrkörning (`scripts/railway_migrate.py`). Undantag som Anton godkänner.

## Åtkomstgranskning

- Varje kvartal går Anton och Sebbe igenom alla konton i tabellen ovan, tar bort det som inte behövs och skriver datum, granskare, fynd och åtgärder i `../../../loggar/atkomstgranskning.md`. Första granskningen: [FYLL: datum]. Ingen har gjorts.
- Granskningen är beviset för uppgiften *Access Review Log*.

## Mätning

Varje kvartal: inga konton utan ägare, alla privilegierade konton i förteckningen med tvåfaktor.

## Undantag

Nödåtkomst högst åtta timmar, med skäl och vem som godkände, och tas upp i nästa granskning.

## Brister

Okänd eller överflödig behörighet tas bort inom en vecka. Delade konton ska vara borta senast [FYLL: datum].

## Förbättring

Rollerna förenklas efter varje granskning.
