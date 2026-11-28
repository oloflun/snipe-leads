# Steg 5.17: inloggning, återställning och onboarding i CRM:ets form

Bildernas prefix: `517-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

SK-020 till SK-037, SK-110 till SK-138, SK-175 till SK-188 (`docs/crm/underlag/app-01-skal-inloggning-onboarding.md`), SU-190 till SU-192 (`docs/crm/underlag/app-06-support.md`).

## VIKTIGT: dagens sidor byts INTE ut

`/login`, `/auth/reset` och `/onboarding` är dagens sidor och används av varje kund. De får inte röras
förrän Anton säger till (växlingen, fas 6). Du bygger de nya som KOMPONENTER och visar dem BARA i
förhandsvisningen:

- Komponenter under `components/crm/app/konto/` (`Inloggning.tsx`, `Aterstallning.tsx`,
  `Onboarding.tsx`).
- Sidor under `app/forhandsvisning/crm-konto/` (`inloggning`, `aterstallning`, `onboarding`), med
  påhittade svar. Lägg till mappen i din avgränsade typkontroll.
- Ingen ändring i `app/login/`, `app/auth/`, `app/onboarding/`, `components/auth/` eller någon
  serveråtgärd. Komponenterna tar sina åtgärder som props, så att växlingen blir att byta komponent.

## Facit för beteendet (läs, kopiera inte formen)

`components/auth/LoginForm.tsx`, `ResetPasswordForm.tsx`, `OnboardingWizard.tsx`, `app/login/page.tsx`,
`app/onboarding/page.tsx`, `app/auth/reset/`.

## Det som ska byggas

Inloggningen (mejl och lösenord, tvåstegskoden, felen, spärren efter för många försök), återställningen,
och onboardingen som stegguide (`Stegguide` från steg 5.3). Egna sidor utanför skalet, i CRM:ets form
(tema, typografi, radier). Lösenordsfält är `type="password"` med rätt `autocomplete`, och inget
lösenord skrivs någonsin i en bild, en logg eller exempeldata.

Commit: `feat(crm): inloggning, aterstallning och onboarding i CRM:ets form (bara forhandsvisning)`.
