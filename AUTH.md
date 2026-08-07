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
