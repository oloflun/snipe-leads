# Encryption & Crypto Controls

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e4177d5da489e7c5e1b1b` (avdelning `it`) |
| Täcker kontroller | Credential Management (`frk_ct_683f4ae4acbd63d0e558a6f5`), Encryption Key Management (`frk_ct_68407429371f33886d8ab80d`), Secure Data Transfer (`frk_ct_68406fc94e08f884cc085ded`) |
| Täcker krav | A.8.20, A.8.21, A.8.24, A.5.14 |

## Syfte

Kunddata ska vara krypterad på väg och i vila, med nycklar som hanteras och byts. GDPR art. 32.1 a nämner kryptering uttryckligen.

## Omfattning

Allt som bär kunddata: Postgres, Redis, trafiken mellan tjänsterna och till leverantörerna, säkerhetskopior, datorerna och appens egna nycklar.

## Kryptering på väg

- Publika adresser är HTTPS (`../../../bevis/railway-konfiguration-2026-11-17.txt` rad 161, 176). Utgående anrop går över HTTPS med `snajp-support/app/tls.py:19`.
- **Avsteg:** Redis Cloud nås med `redis://` utan TLS, från båda miljöerna (bevis rad 118, 256). `scripts/redis_tls_pa.py --apply` slår på TLS. Ansvarig Anton, [FYLL: datum] (`../../../BESLUTSUNDERLAG-2026-11-17.md` A3).
- Kravet är TLS 1.2 eller senare. En mätning med SSL Labs av webb, api och support ska göras och sparas, [FYLL: datum], ansvarig agent. Beviset är uppgiften *TLS / HTTPS*.
- HSTS sätts inte av appen (`next.config.ts:37-66`). Om Railways kant sätter den är inte kontrollerat. Ska kontrolleras vid SSL Labs-mätningen och läggas till om den saknas.
- Trafiken till databasen går via Railways interna nät. Om den är krypterad är inte belagt. Den publika TCP-proxyn ska stängas (P14).

## Kryptering i vila

- **Databaser och volymer:** Railway uppger i sin DPA att data krypteras i vila (`../../../leverantorsgranskning.md` §3). Egen skärmbild saknas. Redis Cloud: ej belagt. Begärs vid DPA-signeringen, [FYLL: datum], ansvarig Anton. Beviset är uppgiften *Encryption at Rest*.
- **Kundernas integrationsnycklar** krypteras med Fernet i produktionen (`INTEGRATION_NYCKEL`, `snajp-support/app/integrationer/hemligheter.py`). **Avsteg:** de ligger i klartext i testmiljön (JA #16). Ska krypteras där, [FYLL: datum], ansvarig agent.
- **Säkerhetskopior** ska vara krypterade (P18). Det finns inga i dag.
- **Datorer** ska ha diskkryptering (P13). Okänt.

## Nycklar

| Nyckel | Var | Används till |
|---|---|---|
| `INTEGRATION_NYCKEL` | Railway, api | Fernet-kryptering av kundnycklar |
| `AUTH_SECRET` | Railway, web | Signering av sessioner |
| `SNAJP_MASTER_API_KEY` och kundnycklar `SNAJP_KEY_*` | Railway | Åtkomst mellan web och api |
| Leverantörsnycklar (Vertex, Resend, ScrapeGraphAI, TypeSafe) | Railway | Anrop till leverantörer |

Namnen är ur `../../../bevis/railway-konfiguration-2026-11-17.txt`. Värdena står aldrig i dokument.

- Nycklar skapas med kryptografiskt säkra generatorer (`scripts/keys.py` använder `secrets`). De lagras som variabler i Railway och lokalt i gitignorerade filer. Aldrig i koden.
- **Rotation:** minst en gång per år, när någon slutar, och vid misstänkt läcka. Ingen rotation är dokumenterad. Att byta `INTEGRATION_NYCKEL` kräver att kundnycklarna krypteras om; en rutin för det ska skrivas, [FYLL: datum], ansvarig agent.
- Varje rotation skrivs i `docs/BESLUT.md` med datum och vilka nycklar.

## Mätning

Varje år: SSL Labs-mätning, bekräftad kryptering i vila hos Railway och Redis, inga nycklar äldre än tolv månader.

## Undantag

Ett system utan kryptering skrivs i undantagsregistret med plan och slutdatum. Redis står där tills TLS är påslaget.

## Brister

Kunddata i klartext på väg eller i vila, utanför ett beslutat undantag, behandlas som incident (G03).

## Förbättring

Algoritmer och inställningar ses över varje år.
