## [FYLL: datum] (Anton) — Säkerhetskopior av produktionsdatabasen och mål för återställning

**Bakgrund.** Produktionens Postgres hos Railway har inga säkerhetskopior: Railways API visade 2026-11-17 inget schema och ingen sparad kopia på någon volym. Testmiljön synkas från produktionen men ligger hos samma leverantör och tar emot samma fel. Ett förstört schema går alltså inte att återställa, och GDPR art. 32.1 c kräver förmåga att återställa personuppgifter i rimlig tid. Railway kräver Pro-planen för både schemalagda och manuella kopior av volymer, och kontot ligger på en lägre plan.

**Beslut.**
1. **Mål (förslag, Anton beslutar):**
   - Högsta dataförlust (RPO): **24 timmar**. Den dagliga kopian ger det.
   - Längsta tid för återställning (RTO): **8 arbetstimmar** från beslut om återställning till fungerande tjänst.
   - Värdena är förslag i P18 och rimliga för ett bolag med två personer utan jour. Ett kundavtal som kräver mer går före.
2. När Railway Pro gäller slås schemalagda kopior på för produktionens Postgres-volym: dagliga, veckovisa och månatliga. Railway sparar dem 6, 27 respektive 89 dagar.
3. Pro-planen tecknas senast [FYLL: datum], helst före första betalande kund.
4. Första återställningsprovet görs direkt efter att kopiorna slagits på: senaste kopian återställs till en tom volym, tabellerna kontrolleras och tiden mäts. Därefter provas en återställning [FYLL: intervall; P18 föreslår varje kvartal].
5. Var Railways kopior lagras begärs skriftligt av Railway (brev `brev/c-railway.md`).
6. En kopia utanför Railway: [FYLL: ja, hos vem och hur den krypteras / nej, med skäl].

**I praktiken.** Det här är sant först när kopiorna är påslagna och det första provet är gjort. Till dess gäller: produktionsdatabasen kan inte återställas, och biträdesavtalets punkt 10.3 kan inte fyllas i. Varje prov skrivs i `docs/compliance/loggar/` med datum, kopians ålder, tid till återställd databas och vad som kontrollerades. Ett misslyckat prov åtgärdas direkt. En radering enligt rutinen för registrerades rättigheter måste göras om efter en återställning, eftersom kopiorna bär raderade uppgifter.

Krav: ISO 27001 A.8.13, A.5.30, A.5.29 (delvis), A.8.14 (genom beslut om nivå); GDPR DS-2 (art. 32.1 c); uppgifterna *Planning* och *Backup Restoration Test*.

Datum: ____________________

Anton: ____________________
