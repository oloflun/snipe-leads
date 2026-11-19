# Authentication & Password

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e42445c99797321ef051a` (avdelning `it`) |
| Täcker kontroller | Access Rights (`frk_ct_683f4a410cf5bf6d40bf3583`), Credential Management (`frk_ct_683f4ae4acbd63d0e558a6f5`) |
| Täcker krav | A.5.16, A.5.17, A.8.5 |

## Syfte

Inloggningar som tål gissning och återanvända lösenord, och hemligheter som inte läcker.

## Omfattning

Alla konton som når kod, driften eller kunddata, och alla nycklar och lösenord som appen använder.

## Lösenord

- Minst 12 tecken eller en lösenfras. Mallens minimum är 8; Snajp väljer 12.
- Ett unikt lösenord per tjänst, sparat i en lösenordshanterare: [FYLL: vilken]. Om någon används i dag är okänt.
- Inga byten på schema, men byte direkt vid misstanke om läcka.
- **Att göra nu:** plattformsadminens lösenord och de lösenord som legat i skript (`../../../bevis/historik-hemligheter-2026-11-17.txt`) ska bytas. Ansvarig Anton, [FYLL: datum] (`../../../BESLUTSUNDERLAG-2026-11-17.md` A1).

## Tvåfaktor

- Tvåfaktor med app eller säkerhetsnyckel ska vara påslagen på GitHub, Railway, Google Cloud, Redis Cloud, Resend, Loopia, ScrapeGraphAI, TypeSafe och Gmail-kontot `snajpsupport@gmail.com`. Sms bara som reserv.
- Läget är inte kontrollerat. Gmail-kontot har tvåstegsverifiering enligt `DEPLOY.md:347-350`; det är det enda belägget. Kontroll och skärmbilder: [FYLL: datum], ansvarig Anton och Sebbe. Beviset är uppgiften *2FA*.
- **I appen** finns ingen tvåfaktor. Ska finnas för plattformsadmin innan första betalande kund, [FYLL: datum], ansvarig agent efter Antons ja. För kunder: inloggning via Google eller Microsoft (`lib/auth.ts`) ger leverantörens tvåfaktor.

## Lagring och överföring

- Appens lösenord hashas med scrypt och unikt salt (`lib/password.ts:13-40`). Mallen kräver bcrypt eller Argon2. scrypt är också en minneskrävande funktion och accepteras. Undantag som Anton godkänner.
- Inloggning sker bara över HTTPS.
- Nycklar ligger som variabler i Railway och lokalt i `.env.deploy`, som är gitignorerad (`.gitignore:63`). `scripts/keys.py` läser värden dolt och skriver dem aldrig ut. Mallens krav på valv (KMS) uppfylls av Railways variabler; en egen skärmbild saknas.
- Hela `.env.deploy` ligger som en enda GitHub-hemlighet (`ENV_DEPLOY`, `.github/workflows/synk.yml:36-39`). Den ska smalnas av till de värden synken behöver (JA #21), [FYLL: datum], ansvarig agent.
- Hemligheter committas aldrig. Hemlighetsskanning och push-skydd i GitHub ska slås på (JA #2), [FYLL: datum].

## Spärr och återställning

- Spärr efter upprepade felaktiga inloggningar finns sedan 2026-11-18 (migration 125, `AUTH.md`): fem misslyckade försök per adress eller 20 per IP på 15 minuter, och tre återställningsbegäranden per adress eller tio per IP på en timme, ger en spärr på 1 minut som stiger till 5, 15 och 60 minuter vid nya spärrar samma dygn. (Utkastet föreslog 30 minuter direkt; stigande väntetid valdes för att en användare som skrivit fel ska komma in snart igen medan en gissningsattack bromsas allt mer.)
- `AUTH.md` ("Glömt lösenord") beskriver återställningen i den gamla Supabase-stacken. Hur den fungerar på Railway, och om länken är tidsbegränsad, är inte belagt. Ska kontrolleras, [FYLL: datum], ansvarig agent. Kravet är en tidsbegränsad länk till kontots adress och samma svar oavsett om adressen finns.

## Servicekonton och nycklar

- Inga personliga inloggningar med servicekonton. Minsta behörighet.
- Nycklar roteras minst en gång per år och när någon slutar. Ingen rotation är dokumenterad i dag. Render-nyckeln från 2026-08-24 är fortfarande inte roterad (`INCIDENT_RESPONSE.md:85`).
- Ett servicekonto per miljö hos Google (JA #14).

## Mätning

Tvåfaktor på alla konton i listan. Inga hemligheter i git enligt skanningen. Nyckelrotation inom tolv månader.

## Undantag

Ett konto utan tvåfaktor kräver Antons skriftliga beslut, med kompenserande skydd och slutdatum.

## Brister

Återanvänt lösenord, hemlighet i klartext eller avslagen tvåfaktor leder till byte direkt och genomgång av reglerna.

## Förbättring

Lösenordslösa inloggningar (passkeys) prövas när leverantörerna stöder dem.
