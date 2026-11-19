# Rutin och förteckning: åtkomstgenomgång

Följer P11 och P15. Förteckningen kopieras till `docs/compliance/loggar/atkomst.md`; varje genomgång skrivs i `loggar/atkomstgranskning.md`. Skriv aldrig lösenord, nycklar eller värdnamn här.

## Förteckning

Ifyllt ur underlaget 2026-11-17. "Belagt" anger var uppgiften kommer ifrån; resten är [FYLL].

| Tjänst | Vem har åtkomst | Roll | Tvåfaktor | Delat konto | Senast granskad | Belagt / kommentar |
|---|---|---|---|---|---|---|
| GitHub (repo `snipe-leads`) | Anton, Sebbe, [FYLL] | Anton code owner på `main`; [FYLL: admin/skrivrätt per person] | [FYLL] | Nej | [FYLL] | CODEOWNERS. Plan (Free/Team): [FYLL]. Actions-hemligheten `ENV_DEPLOY` bär hela `.env.deploy` |
| Railway | [FYLL] | [FYLL: ägare/medlem] | [FYLL] | [FYLL] | [FYLL] | P11 föreslår Anton ägare, Sebbe medlem. Railway-token i `.env.deploy` |
| Google Cloud (Vertex) | [FYLL] | [FYLL: IAM-roller] | [FYLL] | Servicekontot `snajp-vertex` delas av alla miljöer | [FYLL] | JA #14: ett servicekonto per miljö ska skapas |
| Resend | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | |
| Loopia (DNS, domän) | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | |
| Redis Cloud (tills raderad) | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | Används inte sedan 2026-11-17. Stängs enligt brev e |
| TypeSafe | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | Inkorgsläget av sedan 2026-11-17; leads använder fortfarande Jev |
| ScrapeGraphAI | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | |
| Supabase (tills raderat) | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | Skrivs aldrig till. Raderas enligt brev d |
| Render (tills raderat) | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | Läckt API-nyckel 2026-08-24, rotation inte belagd |
| Gmail `snajpsupport@gmail.com` | [FYLL: vilka känner lösenordet] | Supportbrevlåda, larm, plattformsadmin | Ja (tvåstegsverifiering, `DEPLOY.md:347-350`) | **Ja** | [FYLL] | Kontot är också appens enda plattformsadmin (`AUTH.md`, `scripts/admin_cleanup.py`) |
| Brevlådor på snajp.se (`kontakt@`, [FYLL: integritet@]) | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | E-postleverantör: [FYLL] |
| Appen: plattformsadmin | Alla som kan logga in på Gmail-kontot ovan | Plattformsadmin (alla kunders data) | Nej (ingen tvåfaktor i appen) | **Ja** | [FYLL] | Lösenordet låg i publik git-historik. Bytt: [FYLL: datum] |
| Agentsajten | [FYLL] | Gemensam inloggning | Nej | **Ja** | [FYLL] | `DEPLOY.md:559` |
| Lokala `.env.deploy` | Anton, Sebbe, [FYLL] | Alla driftnycklar | – | – | [FYLL] | Var den förvaras: [FYLL] |
| Om Comp AI driftsätts: Trigger.dev, AWS, Vercel AI Gateway, OpenAI, Anthropic | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | Konton finns inte än |
| Övriga: Cal.com, Google/Entra-inloggning, [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | |

## Rutin

**När:** [FYLL: intervall; P11 säger varje kvartal]. Första genomgången: [FYLL: datum]. Anton och Sebbe tillsammans, cirka 45 minuter.

**Så går det till:**
1. Logga in i varje tjänst ovan och jämför medlemslistan med förteckningen.
2. Ta bort konton, nycklar och inbjudningar som ingen behöver.
3. Kontrollera att tvåfaktor är på för varje person; ta en skärmbild där tjänsten visar det (bevis till uppgiften *2FA*).
4. Läs tjänsternas inloggningsloggar där de finns (GitHub, Railway, Google Cloud) och leta efter okända inloggningar.
5. Skriv datum, granskare, fynd och åtgärder i `loggar/atkomstgranskning.md`. Båda signerar.

Överflödig behörighet tas bort inom en vecka (P11).

**När någon slutar** (samma dag, P15):
1. Ta bort personen ur varje tjänst i förteckningen och ur `platform_admins`.
2. **Rotera alla nycklar och lösenord personen haft tillgång till.** Har personen haft `.env.deploy` har hen sett alla: rotera varje variabel i den (namnen står i `bevis/railway-konfiguration-2026-11-17.txt`) och Actions-hemligheten `ENV_DEPLOY`.
3. Byt lösenord på de delade kontona: Gmail-kontot, plattformsadmin, agentsajten.
4. Personen raderar kunddata, dumpar och `.env.deploy` från sina enheter och bekräftar skriftligt.
5. Anton stämmer av mot förteckningen inom 24 timmar och skriver listan i `loggar/avslut.md`.
