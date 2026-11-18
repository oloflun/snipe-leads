# Remote Access & BYOD

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e426ccbb0de15a90cf446` (avdelning `it`) |
| Täcker kontroll | Endpoint Protection (`frk_ct_684072e06f4a49ee669076cc`) |
| Täcker krav | A.6.7, A.7.9, A.8.1 |

## Syfte

Skydda kunddata när allt arbete sker på distans och på privata enheter.

## Omfattning

All åtkomst till GitHub, Railway, Google Cloud, Redis Cloud, Resend, Loopia och appens adminytor, från datorer och telefoner. Snajp har inget eget nät eller kontor. All åtkomst är distansåtkomst.

## Godkända sätt att nå driften

- Leverantörernas webbkonsoler och verktyg över HTTPS, med tvåfaktor (`12-authentication-password.md`).
- Ingen VPN behövs: det finns inget eget nät att ansluta till. Mallens VPN-krav är inte tillämpligt.
- Snajp kör inga egna servrar med SSH eller RDP; tjänsterna är containrar hos Railway. Mallens SSH-regel gäller om sådana servrar tillkommer.
- Databasen i `main` nås i dag också via Railways publika TCP-proxy (`../../../bevis/railway-konfiguration-2026-11-17.txt` rad 216-218), som synken från GitHub använder (`.github/workflows/synk.yml:34-44`). Ska stängas när synken flyttats till Railway (JA #11), [FYLL: datum], ansvarig Anton.
- Lokala utvecklingsservrar pekas aldrig mot testmiljön eller produktionen; använd `scripts/lokal_stack.py` (`DEPLOY.md:173-174`).
- Arbete från länder utanför EU med åtkomst till kunddata: [FYLL: tillåtet eller kräver Antons ja].

## Krav på enheten

Samma som i `13-acceptable-use-workstation-security.md`: stödd och uppdaterad programvara, diskkryptering, antivirus, skärmlås. Mallen säger 15 minuter; Snajp har 10.

## Telefoner

- En telefon som når GitHub, Railway, kundmejl eller appens admin ska ha PIN eller biometri, kryptering och möjlighet till fjärradering.
- Om telefonerna når något av detta i dag är okänt: [FYLL].
- Försvinner en enhet: meddela Anton direkt, logga ut sessionerna hos leverantörerna och byt lösenord. Behandlas som incident (G03).

## Arbetsplats

- Arbete med kunddata sker inte där obehöriga ser skärmen. På allmänna platser används skärmskydd eller annat arbete.
- Offentligt wifi används bara med HTTPS-tjänster; inga okrypterade anslutningar till driften.
- Datorn lämnas inte olåst och obevakad utanför hemmet.

## Övervakning av sessioner

Mallen kräver loggning av VPN-sessioner. Det finns inga sådana. Leverantörernas egna inloggningsloggar (GitHub, Railway, Google Cloud) gås igenom vid den kvartalsvisa åtkomstgranskningen (P11). Undantag som Anton godkänner.

## Mätning

Varje kvartal: alla enheter i enhetslistan uppfyller kraven.

## Undantag

En enhet som inte uppfyller kraven får användas tillfälligt bara med Antons ja och ett datum då den är rättad.

## Brister

Enheter som inte uppfyller kraven loggas ut från driften tills de rättats.

## Förbättring

Ses över varje år och när någon börjar arbeta från en ny plats eller ett nytt land.
