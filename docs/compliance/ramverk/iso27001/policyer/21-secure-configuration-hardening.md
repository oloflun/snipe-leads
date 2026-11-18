# Secure Configuration & Hardening

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); jämförelse av driftkonfigurationen månadsvis |
| Ramverkets mall | `frk_pt_685e42a3bbd08ad14de297f0` (avdelning `it`) |
| Täcker kontroller | Asset Inventory, Change management, Endpoint Protection, Standard Operating Procedures, Utility Tool monitoring, Vulnerability Management |
| Täcker krav | A.8.9, A.8.18, A.8.19, A.8.31, A.5.37 |

## Syfte

Driften och datorerna startar i ett säkert läge och stannar där.

## Omfattning

Railway-tjänsterna (web, api, support, Postgres, Redis) i båda miljöerna, Redis Cloud, Google Cloud-projektet, GitHub-repot och datorerna.

## Baslinje

Det här är baslinjen. Avsteg ska rättas eller stå som undantag:

| Område | Baslinje | Läge 2026-11-17 |
|---|---|---|
| Uppstartsspärrar | DeepSeek fäller uppstarten där data är riktig; standardvärdet för huvudnyckeln fäller uppstarten (`snajp-support/app/config.py:609-736`) | Finns |
| Databasroll | `snajp_app` utan BYPASSRLS (INV-SEC-001) | Finns enligt `DATABASE_URL` |
| Databas | Nås bara via Railways interna nät | **Avsteg:** publik TCP-proxy i `main` (`../../../bevis/railway-konfiguration-2026-11-17.txt` rad 216-218) |
| Redis | TLS, egen databas per miljö | **Avsteg:** `redis://`, delad mellan miljöerna (bevis rad 118, 256) |
| Leverantörer för kunddata | Bara godkända enligt G06 | **Avsteg:** `INKORG_JEV=auto` (bevis rad 95, 235) |
| Testmiljön | Inga utskick till riktiga mottagare | **Avsteg:** utskick tillåtna (Inv. §6.3 p. 6) |
| GitHub | Grenskydd på `main`, hemlighetsskanning, push-skydd, Dependabot | Grenskydd finns; resten saknas |
| Datorer | Enligt `13-acceptable-use-workstation-security.md` | Okänt |

## Ändringar i konfigurationen

- Kod och migrationer ändras via git (P19).
- Driftvariabler i Railway ändras bara efter beslut i `docs/BESLUT.md` (P19).
- Ingen infrastruktur som kod finns. Railway-tjänsterna sätts upp med skript (`scripts/railway_provision.py`, `scripts/railway_agentsajt.py`).

## Avvikelsekontroll

- **Ska införas:** en gång i månaden exporterar en agent driftkonfigurationen utan värden, på samma sätt som `../../../bevis/railway-konfiguration-2026-11-17.txt`, med läsrättighet, och jämför mot baslinjen och förra månaden. Avvikelser rättas eller beslutas inom fem arbetsdagar. [FYLL: datum], ansvarig agent, Anton beslutar. Mallen kräver veckovis; månadsvis räcker för två personer. Undantag som Anton godkänner.

## Verktyg med full åtkomst (krav A.8.18)

Railway CLI och Railway-token, psql mot driften, Google Cloud-konsolen och skript med `--apply`. Förteckning med vem som använder vad förs i `../../../loggar/atkomst.md` (P11). Skript som skriver mot driften ska ha torrkörning först, som `scripts/railway_migrate.py` och `scripts/redis_tls_pa.py`.

## Säkerhetskopior av konfiguration

Den månatliga exporten sparas (de fem senaste). Värdena finns bara i `.env.deploy` hos Anton och Sebbe och i Railway.

## Mätning

Månadsjämförelsen gjord. Inga avsteg från baslinjen utan beslut.

## Undantag

Avsteg skrivs i undantagsregistret med skäl, kompenserande skydd och slutdatum.

## Brister

En okänd ändring i driften behandlas som incident (G03).

## Förbättring

Baslinjen uppdateras efter incidenter och när leverantörer eller tjänster tillkommer.
