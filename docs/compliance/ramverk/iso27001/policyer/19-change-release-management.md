# Change & Release Management

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e42c38c3267d391674ce3` (avdelning `it`) |
| Täcker kontroller | Change management (`frk_ct_683f4c30e2d3f1117fa58e13`), Secure SDLC Integration (`frk_ct_683f50aae46f5e4e096e6bb3`), Standard Operating Procedures (`frk_ct_683f4ef6c6a5481a377be413`) |
| Täcker krav | 8.1, A.5.3, A.5.37, A.8.4, A.8.9, A.8.31, A.8.32 |

## Syfte

Ändringar i kod, databas och driftkonfiguration ska vara granskade, provade och gå att backa.

## Omfattning

Kod och migrationer i repot, driftvariabler i Railway, DNS hos Loopia, och inställningar hos leverantörerna. Båda Railway-miljöerna, eftersom `development` bär produktionens persondata (`DEPLOY.md:155-174`).

## Så fungerar det i dag

- `development` deployas av sig själv vid varje push (`CLAUDE.md`; `DEPLOY.md:27`). Ingen granskning krävs. Sebbe och Anton pushar flera gånger per dag.
- `main` deployas vid merge av en PR från `development`. Grenskyddet kräver granskning av code owner (Anton) (`.github/CODEOWNERS`; PR #43, #44).
- CI (`.github/workflows/verify.yml`) kör tester, invarianter och bygge, men **Railway väntar inte på CI**: en röd körning stoppar ingen deploy (`verify.yml:21-26`).
- Migrationer körs av `.github/workflows/migrera.yml`, ska vara additiva och idempotenta, och PR-kontrollen visar vilka som följer med (`CLAUDE.md`).
- Driftvariabler ändras för hand i Railway utan logg. Exempel: `INKORG_JEV=auto`, okänt av vem och när (`../../../BESLUTSUNDERLAG-2026-11-17.md` A2).

## Ändring och godkännande

- Varje ändring mot `main` går via PR. Beskrivningen säger vad som ändras, risken och hur man backar. Ärendet finns i `bd` eller i PR:en.
- Anton granskar. Anton kan inte granska sina egna PR:er meningsfullt; för dem granskar Sebbe innan Anton mergar (krav A.5.3). Nytt åtagande från godkännandet.
- **Driftvariabler** som styr dataflöden (leverantörer, autonomi, utskick) ändras bara efter beslut i `docs/BESLUT.md` med datum och namn. Nytt åtagande från godkännandet, ansvarig Anton.

## Test och konsekvens

- Tester och invarianter körs i CI på varje push och PR.
- **Ska införas:** deploy till `main` bara när CI är grön, [FYLL: datum], ansvarig agent efter Antons ja (Railway kan vänta på GitHub-kontroller).
- Ändringar som rör kunddata, behörigheter eller leverantörer får en säkerhetsfråga i PR:en: ny tabell eller leverantör uppdaterar registerförteckningen och leverantörslistan i samma commit (G02).

## Release

- Releaser till `main` sker vid behov, inte efter schema. Ingen förvarning ges, eftersom ingen planerad nertid förekommer. Mallens 24 timmars förvarning gäller om en ändring väntas ge nertid.
- Att backa: återställ föregående deploy i Railway, eller revertera PR:en. Migrationer backas inte; därför är de additiva.

## Akuta ändringar

Tillåtna för att återställa drift eller täppa ett säkerhetshål. Dokumenteras i `docs/BESLUT.md` inom 24 timmar och granskas i efterhand.

## Efter release

Kontrollera att tjänsterna svarar och att felen inte ökar. Lärdomar skrivs i `docs/BESLUT.md`.

## Miljöer

- `development` är testmiljön men innehåller produktionens persondata. Det strider mot krav A.8.31 och A.8.33. Anton beslutar om minimering eller pseudonymisering (JA #16), [FYLL: datum].
- Lokal utveckling sker mot `scripts/lokal_stack.py`, aldrig mot driften.

## Mätning

Alla ändringar i `main` har en granskad PR. Andelen deployer som backas följs upp vid ledningsgenomgången.

## Undantag

Bara akuta ändringar enligt ovan.

## Brister

En ogranskad ändring i `main` backas eller granskas i efterhand inom en arbetsdag.

## Förbättring

Flödet ses över varje kvartal utifrån misslyckade deployer.
