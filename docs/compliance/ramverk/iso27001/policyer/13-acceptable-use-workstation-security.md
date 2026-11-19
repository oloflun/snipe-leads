# Acceptable Use & Workstation Security

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); datorkontroll kvartalsvis |
| Ramverkets mall | `frk_pt_685e453cad89de25e5aebf4a` (avdelning `it`) |
| Täcker kontroller | Acceptable Use (`frk_ct_68407c9513000617776104c7`), Endpoint Protection (`frk_ct_684072e06f4a49ee669076cc`) |
| Täcker krav | A.5.10, A.6.2, A.7.7, A.7.10, A.8.1, A.8.7, A.8.19, A.8.23 |

## Syfte

Regler för hur datorer och konton används, och vilket skydd en dator ska ha innan den når kod, driften eller kunddata.

## Omfattning

Alla datorer och telefoner som Anton och Sebbe använder i arbetet. Snajp äger inga datorer; alla är privata. Mallens regler för BYOD gäller därför alla enheter (se också `14-remote-access-byod.md`).

## Tillåten användning

- Konton och nycklar används bara för Snajps arbete.
- Privat användning av datorn är tillåten om den inte ökar risken: inga piratkopierade program, inga okända tillägg i den webbläsare som används för driften.
- Inget olagligt, trakasserande eller upphovsrättsintrång.
- AI-kodverktyg följer `CLAUDE.md`. Kunddata ur testmiljön eller produktionen klistras inte in i AI-tjänster utanför Snajps avtalade leverantörer.

## Datorns inställningar

Varje dator ska ha:

- diskkryptering (BitLocker eller FileVault),
- brandvägg påslagen,
- automatiska säkerhetsuppdateringar,
- skärmlås efter högst 10 minuter, och lösenord eller PIN för att låsa upp,
- inbyggt antivirus påslaget (Microsoft Defender eller macOS XProtect),
- webbläsarens skydd mot skadliga webbplatser påslaget (krav A.8.23).

**Läget är okänt.** Ingen dator är kontrollerad. Skärmbilder per dator till uppgiften *Secure Devices*, och listan till *Device List*: [FYLL: datum], ansvarig Anton och Sebbe.

## Mejl och meddelanden

- Kunddata skickas inte till privata mejladresser.
- Arbetssamtal om kunddata förs i [FYLL: godkänd kanal]. Skärmdumpar med kunddata delas inte (`DEPLOY.md:171`).

## Lagringsmedier och utskrifter

- Kunddata och `.env.deploy` sparas inte på USB-minnen eller externa diskar. Behövs det ska mediet vara krypterat. Om sådana finns i dag är okänt.
- Databasdumpar från produktionen eller testmiljön sparas inte lokalt. Behövs en dump för felsökning raderas den samma dag.
- Utskrifter med kunddata görs inte.

## Privata enheter och lokal lagring

- Kunddata lagras bara i driftmiljöerna, inte lokalt (G02).
- Programvara som når driften (Railway CLI, psql, git) installeras från leverantörens officiella källa.

## Mätning

Varje kvartal: skärmbilder eller en kontroll av varje dator mot listan ovan. Mål: alla datorer uppfyller allt.

## Undantag

Tillfälliga avsteg (till exempel en dator på service) skrivs i undantagsregistret med slutdatum.

## Brister

En dator som inte uppfyller kraven får inte nå driften förrän den rättats. Gäller från godkännandet.

## Förbättring

Reglerna uppdateras när nya verktyg börjar användas.
