# Secure Software Development Lifecycle

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e4319a5bb1d2d411975e6` (avdelning `it`) |
| Täcker kontroller | Data Masking (`frk_ct_6849c343d7fbe4e71446ce78`), Network Security (`frk_ct_684070f0b4f6c2036306e23c`), Secure SDLC Integration (`frk_ct_683f50aae46f5e4e096e6bb3`), Vulnerability Management (`frk_ct_683f4d7360a876b972aba39a`) |
| Täcker krav | A.5.8, A.8.11, A.8.21, A.8.22, A.8.25–A.8.30 |

## Syfte

Säkerheten byggs in när koden skrivs, inte i efterhand.

## Omfattning

All kod i repot: Next-appen, `snajp-support`, `agent-core`, skript, migrationer och CI-flöden. Kod som skrivs av AI-kodverktyg omfattas på samma sätt.

## Säkerhetskrav

- Säkerhetskraven står som invarianter i `ARCHITECTURE_INVARIANTS.md` och prövas av tester i `tests/invariants` (INV-SEC-001–012, INV-GROUND-001–004). Bland dem: tenant kommer aldrig från modellen, opålitlig text aldrig i instruktionsposition, modellen kan inte skicka, utgående nät allowlistas.
- En ny funktion som rör kunddata, publika ytor eller leverantörer får en ny eller ändrad invariant i samma arbete (krav A.5.8). Det görs ofta i dag men är inget krav. Nytt åtagande från godkännandet.
- Indata valideras: Pydantic i API:t (`snajp-support/requirements.txt`). Next-appens validering är inte genomgången; Zod används inte. Ska kontrolleras, [FYLL: datum], ansvarig agent. Beviset är uppgiften *Sanitized Inputs*.

## Granskning och statisk analys

- PR:er till `main` granskas av Anton (`.github/CODEOWNERS`). Push till `development` granskas inte (P19).
- Statisk analys finns inte. CodeQL ska slås på, [FYLL: datum], ansvarig agent efter Antons ja (JA #21).

## Beroenden och hemligheter

- Ingen skanning av beroenden i dag (`.github/dependabot.yml` finns inte). Dependabot ska slås på (P22).
- Vendorade skills ändras bara med deklarerad uppdatering (INV-SKILL-006, `verify.yml:91-99`).
- Hemligheter har committats tidigare: 16 unika värden i historiken (`../../../bevis/historik-hemligheter-2026-11-17.txt`). GitHubs hemlighetsskanning och push-skydd ska slås på (JA #2), och gitleaks köras i CI (JA #21). [FYLL: datum].

## Byggkedjan

- Bygget sker hos Railway ur repot. CI körs på GitHubs runners.
- Hela `.env.deploy` ligger som en Actions-hemlighet (`ENV_DEPLOY`) och skrivs till disk på runnern (`.github/workflows/synk.yml:36-39`). Ska smalnas av (JA #21).
- Synkens logg sparas som artefakt i 14 dagar (`synk.yml:45-50`). Att den inte innehåller persondata är inte kontrollerat; ska kontrolleras, [FYLL: datum], ansvarig agent.
- Artefakter signeras inte. Mallen kräver signering; för Snajp, som bygger direkt ur repot hos Railway, är det inte meningsfullt i dag. Undantag som Anton godkänner.

## Penetrationstest

Inget har gjorts. Ett test av publika ytor (chattwidget, agentsajt, inloggning, API) görs före eller strax efter första betalande kund: [FYLL: datum och leverantör]. Fynd följs upp till stängning.

## AI-kodverktyg och utlagd utveckling (krav A.8.30)

- AI-kodverktyg följer `CLAUDE.md` och invarianterna. Deras ändringar granskas som andras.
- De läser i dag testmiljöns kunddata (JA #28). Anton beslutar om regler, [FYLL: datum].
- Sebbes avtalsform är okänd (`15-background-screening-on-off-boarding.md`).

## Mätning

CI grön före deploy till `main`. Inga öppna kritiska fynd vid release.

## Undantag

Tillfälliga undantag i skanningen kräver en skriven risk och ett datum.

## Brister

Kod som gått in utan granskning eller skanning backas eller granskas i efterhand.

## Förbättring

Verktyg och regler ses över varje år mot OWASP:s aktuella listor.
