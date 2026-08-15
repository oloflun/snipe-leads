# Auth — flöde, konfiguration, testning

## Flödet

```
LoginForm → lib/actions/auth.ts → Supabase Auth
                                     ↓ (verifieringslänk / magic link)
                              app/auth/callback/route.ts
                                     ↓ ensure_workspace_for_current_user()
                              proxy.ts → /onboarding → /dashboard
```

Profil och workspace skapas av triggern `on_auth_user_created`
(`supabase/migrations/006_auth_selfheal.sql`). Triggern sväljer sina egna fel:
en trasig trigger får aldrig blockera en registrering. Saknas profilen ändå
skapas den vid nästa inloggning eller callback via RPC:n
`ensure_workspace_for_current_user`.

## Konfiguration som måste vara på plats

**Supabase → Authentication → SMTP Settings.** Den inbyggda mailaren skickar bara
till projektets egna medlemmar och ~2 mail/timme. Utan egen SMTP (Resend) når
inga verifierings- eller inbjudningsmail privata Gmail-/Hotmail-adresser — det
var den ena av två orsaker till att registrering med privat mail inte gick.

**Supabase → Authentication → URL Configuration.**
- Site URL: produktions-URL:en.
- Redirect URLs: `http://localhost:3000/auth/callback`,
  `https://snajp.vercel.app/auth/callback`, samt varje kundsubdomän.

**Vercel → Environment Variables.** `NEXT_PUBLIC_SITE_URL` måste vara satt i
Production och Preview. Saknas den pekar verifieringslänkarna på localhost.

## Automatiskt test

```bash
node scripts/test-auth-flow.mjs
```

Kräver `NEXT_PUBLIC_SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` i `.env.local`.
Testar att registrering ger profil + workspace, att en inbjuden adress hamnar i
rätt workspace, och att ett konto utan profil kan läkas. Städar upp efter sig.

## Manuellt test (det som inte går att automatisera)

Kräver en riktig inkorg. Kör på localhost innan produktion.

1. `npm run dev` → `/login` → "Skapa konto" med en privat mailadress.
2. Förvänta: "Vi har skickat en verifieringslänk till …" — **inte** "Du kan nu
   logga in". Ser du den gamla texten är fel version deployad.
3. Öppna mailet, klicka på länken → ska landa på `/onboarding`.
4. Fyll i onboarding → `/dashboard`.
5. Logga ut, logga in med lösenord → ska gå direkt till `/dashboard`.
6. Kontrollera i Supabase att `profiles` fått en rad för användaren.

Felsökning: `auth`-loggen i Supabase-dashboarden visar status per försök.
En 500 på `/signup` betyder att triggern kastar — läs `raise warning`-raderna i
Postgres-loggen.

---

## Glömt lösenord

Byggt i Fas 2.3. Två steg, ingen egen kodväg för kodväxlingen.

- `requestPasswordReset(email)` i `lib/actions/auth.ts` skickar länken med
  `redirectTo: ${SITE_URL}/auth/callback?next=/auth/reset`. **Via callbacken,
  inte direkt till `/auth/reset`** — länken bär en PKCE-kod som måste växlas
  mot en session, och det kräver skrivbara cookies. En server component har
  inte det, och `/auth/callback` gör redan exakt den växlingen.
- `/auth/reset` kontrollerar bara att sessionen finns och renderar
  `ResetPasswordForm`, som anropar `updatePassword`.
- Svaret på steg 1 är **alltid detsamma**, även för en adress som inte finns.
  Annars är formuläret en kontolista för vem som helst att fråga.

Manuellt test: `/login` → "Glömt lösenordet?" → skriv adressen → öppna mailet →
sätt nytt lösenord → ska landa inloggad på `/dashboard`.

**Kräver i Supabase:** `${SITE_URL}/auth/callback` måste stå i Authentication →
URL Configuration → Redirect URLs. Saknas den landar länken på `localhost:3000`
oavsett var användaren är.

## Google och Microsoft 365

Koden är klar (`signInWithOAuth` + knapparna i `LoginForm`). Callbacken fanns
redan och gör rätt, och invite-modellen håller automatiskt: triggern
`on_auth_user_created` läser `workspace_invites` oavsett inloggningssätt
(`006_auth_selfheal.sql`).

**Konsolmomenten går inte att göra från kod. Checklista:**

### Google
1. Google Cloud Console → APIs & Services → Credentials → Create OAuth client ID
   → Web application.
2. Authorized redirect URI: `https://<projekt>.supabase.co/auth/v1/callback`
   (Supabases callback, **inte** appens).
3. Kopiera Client ID + Client secret.
4. Supabase → Authentication → Providers → Google → klistra in, aktivera.

### Microsoft 365
1. Microsoft Entra admin center → App registrations → New registration.
2. Redirect URI (Web): `https://<projekt>.supabase.co/auth/v1/callback`.
3. Certificates & secrets → New client secret.
4. Supabase → Authentication → Providers → Azure → Client ID + Secret +
   Azure Tenant (`common` för både jobbkonton och privata).

### Gemensamt, lätt att missa
Supabase → Authentication → URL Configuration → Redirect URLs måste innehålla
**varje** sajt som ska kunna logga in, inklusive kunddomäner och
Vercel-previewdomäner. En URL som saknas där ger en lyckad inloggning som
landar på fel värd.

Tills providern är aktiverad svarar knappen med ett begripligt fel
("… är inte aktiverad i Supabase Auth ännu"), inte med en trasig redirect.

## Plattformsadmin

`platform_admins` (migration 020) är en **egen dimension**, skild från
`profiles.role`. Den senare är workspace-scopad: den säger vad någon får göra
inuti sin egen arbetsyta. Hade plattformsrollen bott där skulle varje kund som
äger sitt eget workspace ha blivit admin över alla andras.

Tabellen har **inga skrivpolicyer**. Admin ges enbart via service-rollen eller
SQL-editorn — en självbetjäningsväg in i admin är precis det tabellen finns
för att förhindra.

Ge admin:
```sql
insert into public.platform_admins (user_id)
select id from auth.users where email = 'adressen@exempel.se'
on conflict (user_id) do nothing;
```

Kontot måste finnas i `auth.users` först. `021_seed_platform_admin.sql` gör
detta för `snajpsupport@gmail.com` och är idempotent — kör den igen efter att
kontot skapats om den första körningen inte matchade något.

Lösenordet sätts av dig. Aldrig av en agent, aldrig i en migration.
