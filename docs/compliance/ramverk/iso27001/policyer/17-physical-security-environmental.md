# Physical Security & Environmental

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e4508d8c0d14ae873e644` (avdelning `it`) |
| Täcker kontroller | Physical & Environmental Security (`frk_ct_69e65ef9c20933590d85cc31`), Asset Inventory (`frk_ct_683f42c71eea99f22f9df060`) |
| Täcker krav | A.5.9, A.7.1–A.7.14 |

Mallen förutsätter kontor och serverrum. Snajp har inget av det. All drift ligger hos Railway, Redis Cloud och Google Cloud (`../../../bevis/railway-regioner-2026-11-17.txt`). Det som återstår är datorerna och telefonerna, och leverantörernas datacenter.

## Syfte

Skydda datorer och kunddata mot stöld, insyn och förlust, och veta att leverantörernas datacenter är skyddade.

## Omfattning

Datorer och telefoner som når kod, driften eller kunddata, var de än används. Leverantörernas datacenter genom deras intyg.

## Lokaler och tillträde (mallens "Facility Access Control" och "Visitor Management")

**Inte tillämpligt.** Inga egna lokaler, inga dörrar, inga besökare. Krav A.7.1–A.7.4 och A.7.6 bedöms som ej tillämpliga i `../soa.md`. Leverantörernas skalskydd följs upp genom deras intyg: Railway SOC 2 Type II, Redis SOC 2 och ISO 27001, Google ISO 27001 (`../../../leverantorsgranskning.md` §1, 3, 4). Intygen hämtas och sparas vid den årliga leverantörsgranskningen (G06). Får Snajp lokaler gäller mallen fullt ut.

## Miljöskydd (mallens "Environmental Protections")

**Inte tillämpligt för egna anläggningar** (krav A.7.5, A.7.11, A.7.12). Kyla, ström, brand och vatten i datacentren är leverantörernas ansvar. En stulen eller förstörd dator ska inte innebära dataförlust: kunddata ligger bara i driften, och driften ska ha säkerhetskopior (`18-backup-business-continuity-disaster-recovery.md`).

## Utrustning

- **Förteckning (A.5.9):** varje dator och telefon som når driften står i `../../../loggar/enheter.md` med ägare, typ, operativsystem och diskkryptering. Finns inte; införs [FYLL: datum], ansvarig Anton. Beviset för uppgiften *Device List*.
- **Placering och förvaring (A.7.8, A.7.9):** datorer förvaras inlåsta eller i hemmet när de inte används, lämnas inte i bil eller obevakade på allmän plats.
- **Skärm och skrivbord (A.7.7):** skärmlås efter högst 10 minuter (P13). Skärmen låses när man går ifrån. Inga papper med kunddata.
- **Lagringsmedier (A.7.10):** se P13. Inga okrypterade USB-minnen eller externa diskar med kunddata eller nycklar.
- **Service (A.7.13):** en dator som lämnas på reparation ska först loggas ut från driften. Lämnas disken med, byts lösenorden till de tjänster datorn varit inloggad mot. Om detta har hänt tidigare är okänt.
- **Kassering och återanvändning (A.7.14):** före försäljning, byte eller kassering raderas disken med operativsystemets återställning med kryptering påslagen, eller förstörs. Telefoner återställs till fabriksläge. Varje kassering skrivs i enhetslistan med datum och metod. Mallen hänvisar till NIST SP 800-88; återställning av en krypterad disk motsvarar den nivån för Snajps behov.

## Granskning

En gång per år går Anton igenom enhetslistan och frågar Sebbe om förändringar. Mallens månatliga kontroll av passerloggar och kameror är inte tillämplig.

## Mätning

Alla enheter står i listan. Alla kasserade enheter har datum och metod.

## Undantag

Tillfällig användning av en enhet som inte står i listan kräver Antons ja och ska föras in inom en vecka.

## Brister

En förlorad enhet behandlas som incident (G03).

## Förbättring

Policyn skrivs om i sin helhet om Snajp skaffar lokaler eller egen utrustning för drift.
