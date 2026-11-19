# Background Screening & On/Off-boarding

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`), och varje gång någon börjar eller slutar |
| Ramverkets mall | `frk_pt_685e45c938ad29ad775a2344` (avdelning `hr`) |
| Täcker kontroller | Access Rights (`frk_ct_683f4a410cf5bf6d40bf3583`), Asset Inventory (`frk_ct_683f42c71eea99f22f9df060`). Ramverkets kontroll *Human Resources Security* har ingen policy kopplad; den här policyn täcker den |
| Täcker krav | A.5.11, A.6.1, A.6.2, A.6.5, A.6.6, A.8.30 |

## Syfte

Den som får åtkomst till kunddata ska vara kontrollerad och bunden av sekretess, och åtkomsten ska försvinna helt när personen slutar.

## Omfattning

Alla som får åtkomst till kod, driften eller kunddata: anställda, uppdragstagare, delägare, praktikanter. I dag Anton och Sebbe.

## Kontroll före start

- Identitet kontrolleras mot legitimation. Referenser tas för den som ska nå kunddata.
- Den som börjar skriver under ett avtal med sekretess som gäller också efter avslut, och med Snajps säkerhetsregler (krav A.6.2, A.6.5, A.6.6). Avtalsmall: [FYLL: plats], ansvarig Anton.
- Resultatet sparas av Anton, inte i repot.
- **Undantag för Anton och Sebbe:** de har arbetat ihop före den här policyn, och en kontroll i efterhand tillför inget. Anton godkänner undantaget. Sekretessavtalet gäller ändå: om Sebbe har ett skriftligt avtal med sekretess är okänt, [FYLL: finns / ska tecknas senast datum].

## Start

- Personliga konton, inga delade inloggningar (P11).
- Utbildning och kvittens första veckan, före åtkomst (G05).
- Datorn uppfyller `13-acceptable-use-workstation-security.md` innan den når driften.
- Beslutet skrivs i `../../../loggar/atkomst.md` (P11).

## Avslut

Samma dag som någon slutar:

1. Ta bort personen ur GitHub, Railway, Google Cloud, Redis Cloud, Resend, Loopia och övriga konton i förteckningen (P11), och ur `platform_admins` om hen finns där.
2. **Rotera alla hemligheter personen kunnat se.** Den som har haft `.env.deploy` har sett alla nycklar. Lista: variablerna i `../../../bevis/railway-konfiguration-2026-11-17.txt` (namn, inga värden), plus Actions-hemligheten `ENV_DEPLOY`. Rotation görs med `scripts/keys.py` och Railways konsol.
3. Byt lösenord på delade konton som finns kvar (plattformsadmin, agentsajten, `snajpsupport@gmail.com`).
4. Personen raderar kunddata, dumpar och `.env.deploy` från sina enheter och bekräftar skriftligt.
5. Påminn skriftligt om sekretessen.

Checklistan sparas i `../../../loggar/avslut.md`. Den har aldrig använts.

## Avstämning

Inom 24 timmar efter avslut stämmer Anton av mot kontoförteckningen att inget konto finns kvar. Snajp äger inga datorer, så mallens krav på återlämnad utrustning ersätts av punkt 4. Undantag som Anton godkänner.

## Lagring

Avtal och avslutslistor sparas i sju år efter avslut, utanför det publika repot.

## Mätning

Varje avslut: alla konton borta och nycklar roterade samma dag.

## Undantag

Ett hoppat steg kräver Antons skriftliga beslut och en riskanteckning.

## Brister

Konton som inte stängts i tid stängs inom fem arbetsdagar och tas upp som incident.

## Förbättring

Checklistan uppdateras efter varje avslut.
