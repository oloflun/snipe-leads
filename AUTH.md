# Auth: flöde, konfiguration, testning

Uppdaterad 2026-11-18 mot koden i `development` (ISO 27001 A.5.37; den förra
versionen beskrev Supabase Auth, som inte används längre). Varje påstående
nedan pekar på filen där det går att kontrollera.

## Två lager

| Lager | Vem | Hur | Kod |
|---|---|---|---|
| Webben (Next.js, tjänsten `web`) | Kundens användare, plattformsadmin | Auth.js (NextAuth v5) med sessions-JWT i en cookie | `lib/auth.ts`, `lib/actions/auth.ts`, `proxy.ts` |
| Backenden (FastAPI, tjänsten `api`) | Webben för en kunds räkning, provisioneringen, kundens egna integrationer | `X-API-Key`: kundnyckel, master-nyckel eller demonyckel | `snajp-support/app/api/deps.py` |

Användaren pratar aldrig direkt med backenden med sin session. Webben slår upp
kundens nyckel ur sessionens arbetsyta och skickar anropet vidare
(`app/api/snajp-support/_auth.ts:proxyAsTenant`).

## Webben: inloggning

```
/login (LoginForm) → lib/actions/auth.ts:signInWithPassword
                   → Auth.js Credentials (lib/auth.ts)
                   → auth.users (lösenordshash, scrypt)
                   → JWT-cookie → /dashboard, /admin eller ?next=
```

- **Identiteten bor i `auth.users`** i appens egen Postgres (Railway). Tabellen
  och funktionerna `auth.uid()` m.fl. kommer från `railway/000_auth_compat.sql`,
  en ersättning för Supabases auth-schema. Supabase Auth (GoTrue) används inte;
  adaptern togs bort 2026-11-18 (`docs/BESLUT.md`).
- **Lösenord** hashas med Nodes scrypt, format `scrypt$1$<salt>$<hash>`
  (`lib/password.ts`). Minsta längd 8 tecken (`MIN_PASSWORD_LENGTH` i
  `lib/actions/auth.ts`). Verifieringen körs även när kontot saknas, så att
  svarstiden inte avslöjar vilka adresser som finns (`lib/auth.ts:authorize`).
- **Felmeddelandet** säger aldrig om det var adressen eller lösenordet som var fel.
- **Sessionen** är en JWT signerad med `AUTH_SECRET` (`session: { strategy: "jwt" }`).
  Den bär bara användarens id; onboardingstatus, arbetsyta, roll och adminstatus
  läses färskt ur databasen vid varje request (`lib/auth/onboarding-gate.ts`,
  `lib/auth/admin.ts`). Livslängden är Auth.js standard (30 dagar), ingen egen
  inställning finns. Utloggning: `signOut` i `lib/actions/auth.ts`. Det finns
  ingen server-side spärrlista för sessioner: en utfärdad JWT gäller tills den
  löper ut eller `AUTH_SECRET` byts.
- **Skyddade sidor:** `proxy.ts` släpper inte in `/dashboard`, `/settings`,
  `/onboarding` eller `/admin` utan giltig JWT (omdirigering till `/login?next=`).
  Saknas `AUTH_SECRET` i miljön är alla skyddade sidor stängda.
- **API-rutterna** under `app/api/` täcks inte av proxyn med flit; varje rutt
  kontrollerar sessionen själv (`proxyAsTenant`). Anonyma rutter står i
  allowlistan för INV-SEC-010 (`tests/invariants/test_inv_sec_010.py`).
- **Spärr mot upprepade försök** (migration 125, `lib/auth/inloggningsregler.ts`,
  2026-11-18). Räknas per e-postadress och per klient-IP, likadant för en adress
  med och utan konto:

  | Handling | Per adress | Per IP | Fönster |
  |---|---|---|---|
  | Misslyckad lösenordsinloggning | 5 | 20 | 15 minuter |
  | Begäran om lösenordsåterställning (varje begäran räknas) | 3 | 10 | 60 minuter |

  Når en nyckel tröskeln spärras den i 1 minut, sedan 5, 15 och 60 minuter för
  varje ny spärr inom ett dygn. Ett spärrat inloggningsförsök prövar aldrig
  lösenordet; en spärrad återställning skapar ingen token och skickar inget mejl.
  Beskedet är "För många försök" på sidans språk (`for_manga_forsok`), samma för
  alla adresser. En lyckad inloggning nollställer adressens räknare, inte IP:ts.
  Spärren sitter i `authorize` (`lib/auth.ts`) och gäller därför också den som
  postar direkt till `/api/auth/callback/credentials`. Nycklarna är HMAC med
  `AUTH_SECRET`, aldrig adress eller IP i klartext; tabellen nås bara genom
  funktionerna (security definer) och gallras efter ett dygn utan försök. Varje
  spärrat försök och varje ny spärr loggas i web-loggen som JSON
  (`"logg":"inloggningsspärr"`) med maskerad adress och IP, aldrig lösenordet.
  Ett fel mot databasen släpper igenom försöket och loggas (fail open: en deploy
  som hinner före migrationen ska inte låsa ute alla).
- **Ingen tvåfaktor** finns i appen (A.8.5, öppet i
  `docs/compliance/ramverk/iso27001/matris.md`).

### Registrering och arbetsyta

`signUpWithPassword` skriver raden i `auth.users` direkt. Triggern
`on_auth_user_created` (`db/migrations/001_handle_new_user.sql`,
`006_auth_selfheal.sql`) skapar profil och arbetsyta och löser in en väntande
inbjudan (`workspace_invites`, med roll). Triggern sväljer sina egna fel; saknas
profilen ändå läker `ensure_workspace_for_current_user()` den vid nästa
inloggning (`lib/auth.ts:ensureWorkspace`, körs med användarens identitet via
`sqlAsUser`).

Ingen e-postverifiering: `email_confirmed_at` sätts direkt vid registrering.
Det är ett medvetet val i koden (kommentaren i `signUpWithPassword`), inte en
verifiering som görs någon annanstans.

**Demo:** `startDemo` skapar ett konto med slumpad adress `demo-<uuid>@snajp.se`
och slumpat lösenord och markerar arbetsytan `is_demo` genom
`markera_demoarbetsyta()` (migration 127), med användarens identitet satt
(`sqlAsUser`). Funktionen märker bara den inloggades egen, nyss skapade och
tomma arbetsyta, och bara för ett demokonto yngre än tio minuter. Går
märkningen inte igenom startar ingen demo. Före 127 träffade uppdateringen
noll rader (ingen update-policy, ingen identitet) och varje demo fick fullt
löptak.

### Glömt lösenord

1. `requestPasswordReset(email)` skapar en engångstoken, sparar bara dess hash i
   `password_reset_tokens` (en aktiv per konto) och mejlar länken
   `<SITE_URL>/auth/reset?token=…` via Resend (`lib/mail.ts`). Länken gäller
   60 minuter (`lib/reset-token.ts`). Svaret är detsamma för en adress med och
   utan konto. Utan `RESEND_API_KEY` svarar formuläret att återställning inte är
   konfigurerad.
2. `/auth/reset` (`app/auth/reset/page.tsx`) anropar `updatePassword(password, token)`.
   Tokenen förbrukas atomiskt i samma UPDATE som prövar den, och kan bara byta
   lösenord på ett befintligt konto. Inloggad användare kan byta utan token.

### Google och Microsoft 365

Koden finns: Auth.js-providrarna `Google` och `MicrosoftEntraID` slås på när
`AUTH_GOOGLE_ID` respektive `AUTH_MICROSOFT_ENTRA_ID_ID` (med tillhörande
hemligheter) är satta (`lib/auth.ts`). Callback-URL hos leverantören:
`<SITE_URL>/api/auth/callback/google` respektive
`<SITE_URL>/api/auth/callback/microsoft-entra-id`. Första inloggningen skapar
raden i `auth.users`, så triggern och inbjudningarna fungerar som vid lösenord.

**I drift är ingen av dem påslagen:** variablerna finns inte i någon miljö
(`docs/compliance/railway-baslinje.json`). Knappen svarar då att inloggningen
inte är konfigurerad.

## Roller

| Roll | Var | Vad den ger |
|---|---|---|
| Medlem (`owner`, `member` m.fl.) | `profiles.role`, per arbetsyta | Arbete i den egna arbetsytan. RLS i databasen skopar på arbetsytan/kunden |
| Läsroll (`viewer`) | `profiles.role`, via inbjudan | Läser arbetsytan, skriver ingenting: `proxyAsTenant` vägrar skrivande anrop och server actions frågar `arLasare()` (`lib/auth/lasroll.ts`) |
| Plattformsadmin | `platform_admins` (migration 020, 037) | `/admin` och kundbesök i alla kunders arbetsytor (`lib/auth/admin.ts`). Uppslaget är fail-closed: ett fel betyder inte admin |

### Databasrollen `snajp_web`

Webben ansluter till Postgres som `snajp_web` (`nobypassrls`). Sedan migration 126
(2026-11-18) har rollen bara det webbens egen SQL gör, 13 tabeller och på flera av dem bara
vissa kolumner, och ingen rättighet på tabeller som skapas senare. Migration 127 tog bort
update-rätten på `workspaces.is_demo`; demon märks genom en funktion i stället. `auth.users` läses av
`snajp_web` (inloggningen) och, för `id` och `email`, av `snajp_app`; ingen annan roll når
den. En ny fråga i webben mot en tabell utanför listan kräver en grant i en ny migration och
en rad i `TILLATET` i `snajp-support/tests/db/test_snajp_web_rattigheter.py`, som annars
fäller i CI. Listan och kartläggningen: `docs/compliance/datamangder.md` §1.

### Plattformsadmin

`platform_admins` är skild från `profiles.role` med flit: annars blir varje
kund som äger sin arbetsyta admin över alla andras. Tabellen har inga
skrivpolicyer. En adress blir admin på två sätt, båda bara med ägarrollen i
databasen (migrationer eller SQL som `postgres`, aldrig från appen):

- Adressen står i `platform_admin_bootstrap` (migration 032): kontot blir
  admin när det registreras, oavsett ordning.
- Direkt rad:

```sql
insert into public.platform_admins (user_id)
select id from auth.users where lower(email) = lower('adressen@exempel.se')
on conflict (user_id) do nothing;
```

Lösenordet sätts av personen själv. Aldrig av en agent, aldrig i en migration.

Varje kundbesök och varje anrop med master-nyckeln loggas i `audit_logs`
(migration 123, INV-SEC-013; `docs/compliance/drift-och-tillgangar.md` §5).

## Backenden: nycklar

`require_api_key` i `snajp-support/app/api/deps.py` godtar tre slags nycklar
i `X-API-Key`:

| Nyckel | Var den finns | Ger |
|---|---|---|
| Kundnyckel | Hashad i `ss_api_keys`; i klartext bara i Railway-variablerna `SNAJP_KEY_<SLUG>` på `web` | Kundens egna data (`require_tenant`), RLS sätts på kundens `tenant_id` |
| Master-nyckel | `SNAJP_MASTER_API_KEY` på `web` och `api` | `/api/admin/*` och `/api/keys` (`require_master_key`). Avvisas mot kunddata-endpoints. Varje anrop loggas |
| Demonyckel | `SNAJP_DEMO_API_KEY` på `api` | Demokunden |

Plattformsadminens id skickas med i `X-Snajp-Admin` från webben och prövas mot
`platform_admins` i databasen innan det skrivs i loggen.

## Konfiguration som måste finnas

| Variabel | Tjänst | Saknas den |
|---|---|---|
| `AUTH_SECRET` | `web` | Ingen kan logga in; skyddade sidor stängda |
| `DATABASE_URL` | `web` | Inloggningen svarar att den inte är konfigurerad |
| `NEXT_PUBLIC_SITE_URL` / `SITE_URL` | `web` | Återställningslänkar och OAuth-callback pekar fel |
| `RESEND_API_KEY` | `web` | Glömt lösenord går inte |
| `SNAJP_MASTER_API_KEY`, `SNAJP_KEY_<SLUG>` | `web`, `api` | Adminytan respektive kundens backendanrop svarar 401/503 |

Läget per miljö: `python scripts/railway_baslinje.py --jamfor` (namn, aldrig värden).

## Testning

Automatiskt:
- `tests/invariants/test_inv_sec_010.py`: anonyma API-rutter bara enligt allowlistan.
- `tests/invariants/test_inv_auth_001.py`: auth-invarianten.
- `snajp-support/tests/db/test_adminlogg.py`: åtkomstloggen (CI-jobbet `databas`).
- `snajp-support/tests/db/test_snajp_web_rattigheter.py`: webbens databasroll har exakt
  listans rättigheter, och varje SQL-sats i webben går att köra som `snajp_web` (CI-jobbet `databas`).
- `snajp-support/tests/db/test_demo_markering.py`: demon märks `is_demo` med
  identiteten satt, och funktionen vägrar allt annat än den nya demons egen yta
  (CI-jobbet `databas`).
- `snajp-support/tests/db/test_inloggningsforsok.py`: spärrens trösklar, stigande
  väntetid, fönster och att approllerna inte når tabellen (CI-jobbet `databas`).
- `lib/auth/inloggningsregler.test.ts`: nycklar, klient-IP och loggmaskering
  (`node --test lib/auth/inloggningsregler.test.ts`, Node 22 eller senare).

Manuellt, mot en lokal stack (`python scripts/lokal_stack.py --apply`, aldrig
mot development-spegeln):
1. `/login` → Skapa konto → ska landa på `/onboarding`, sedan `/dashboard`.
2. Logga ut och in igen med lösenord.
3. Glömt lösenordet → länken i mejlet → nytt lösenord → inloggad.
4. Ett fel lösenord ger "Fel e-postadress eller lösenord." oavsett om kontot finns.
