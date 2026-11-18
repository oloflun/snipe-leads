# Förteckning och kontroll: enheter

Följer P13, P14 och P17. Gäller varje dator och telefon som når kod, driftkonton (GitHub, Railway, Google Cloud, Resend, Loopia) eller kunddata, även via mejl. Kopieras till `docs/compliance/loggar/enheter.md`. Kontroll [FYLL: intervall; P13 säger varje kvartal]. Skärmbilderna är bevis till uppgifterna *Device List* och *Secure Devices*.

Krav (P13): diskkryptering, skärmlås efter högst 10 minuter med lösenord eller PIN, automatiska uppdateringar, inbyggt skydd mot skadlig kod påslaget, brandvägg på.

## Förteckning

| Enhet | Ägare | Operativsystem och version | Diskkryptering | Skärmlås (min) | Automatiska uppdateringar | Skydd mot skadlig kod | Når | Kontrollerad |
|---|---|---|---|---|---|---|---|---|
| Dator 1 | Anton | Windows 11 Pro [FYLL: version] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] |
| Telefon | Anton | [FYLL] | [FYLL] | [FYLL] | [FYLL] | – | [FYLL: mejl, GitHub, Railway?] | [FYLL] |
| Dator 1 | Sebbe | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] | [FYLL] |
| Telefon | Sebbe | [FYLL] | [FYLL] | [FYLL] | [FYLL] | – | [FYLL] | [FYLL] |
| [FYLL: fler] | | | | | | | | |

Används någon dator av andra i hushållet: [FYLL]. Finns USB-minnen eller externa diskar med kunddata, dumpar eller `.env.deploy`: [FYLL].

## Så kontrollerar du, och vad skärmbilden ska visa

Döp skärmbilderna `<ägare>-<enhet>-<kontroll>-<datum>.png` och spara dem i `docs/compliance/bevis/enheter/`. Skärmbilden ska visa datornamnet eller vara tagen så att det framgår vilken enhet det är.

### Windows 10/11

| Kontroll | Var | Skärmbilden visar |
|---|---|---|
| Diskkryptering | Inställningar › Sekretess och säkerhet › Enhetskryptering, eller Kontrollpanelen › BitLocker-diskkryptering. Alternativt i PowerShell som administratör: `manage-bde -status C:` | "På" eller "Skydd: På", "Krypterat: 100 %". Windows Home saknar BitLocker; då finns bara Enhetskryptering |
| Skärmlås | Inställningar › Konton › Inloggningsalternativ (kräv inloggning efter frånvaro) och Inställningar › System › Ström och batteri (skärm och viloläge) | Viloläge eller skärmsläckare inom 10 minuter och krav på inloggning |
| Uppdateringar | Inställningar › Windows Update | "Du är uppdaterad" och datum för senaste kontroll |
| Skydd mot skadlig kod | Windows-säkerhet › Skydd mot virus och hot | Realtidsskydd på |
| Brandvägg | Windows-säkerhet › Brandvägg och nätverksskydd | På för alla nätverkstyper |
| Version | Inställningar › System › Om | Version och datornamn |

Skärmbild: Windows + Shift + S.

### macOS

| Kontroll | Var | Skärmbilden visar |
|---|---|---|
| Diskkryptering | Systeminställningar › Integritet och säkerhet › FileVault. Alternativt i Terminal: `fdesetup status` | "FileVault är aktiverat" |
| Skärmlås | Systeminställningar › Låsskärm | "Kräv lösenord" direkt eller inom några minuter, och skärmsläckare/viloläge inom 10 minuter |
| Uppdateringar | Systeminställningar › Allmänt › Programuppdatering › (i) vid Automatiska uppdateringar | Installera säkerhetssvar och systemfiler på |
| Skydd mot skadlig kod | XProtect är inbyggt och följer med uppdateringarna ovan. Integritet och säkerhet › tillåt program från App Store och kända utvecklare | Inställningen och att uppdateringarna är på |
| Brandvägg | Systeminställningar › Nätverk › Brandvägg | På |
| Version | Apple-menyn › Om den här datorn | Version och modell |

Skärmbild: Cmd + Shift + 4 (del) eller Cmd + Shift + 3 (hela skärmen).

### Telefoner

Kontrollera att skärmlås med PIN eller biometri finns, att telefonen är krypterad (standard på iPhone och nyare Android med skärmlås), att systemuppdateringar är på och att fjärradering via Hitta min iPhone eller Hitta min enhet är påslagen.

## När en enhet inte klarar kraven

Den får inte nå driften förrän den är rättad (P13). Tillfälliga avsteg, till exempel en dator på service, skrivs i undantagsregistret med slutdatum. En dator som säljs eller byts raderas först (A.7.14): Windows "Återställ den här datorn" med "Ta bort allt" och rensning av enheten; macOS "Radera allt innehåll och inställningar".
