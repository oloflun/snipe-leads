## [FYLL: datum] (Anton) — Gallring efter 24 månader, satt per kund vid onboarding

**Bakgrund.** Integritetspolicyn lovar att uppgifter sparas i 24 månader från senaste behandlingen och att gallringen är automatiserad och loggas. Inget gallringsjobb körs i dag, och registerförteckningen har "[fylls i]" som lagringstid på fem poster. `scripts/gallra.py` kan sätta en period per kund och gallra supportdata, men det är aldrig kört skarpt och omfattar inte leads, chattar eller `agent_runs`. Löftet i policyn är alltså inte sant i dag. GDPR art. 5.1 e kräver att uppgifterna inte sparas längre än nödvändigt.

**Beslut.**
1. Uppgifterna i alla kategorier som integritetspolicyn anger raderas 24 månader efter den senaste behandlingen: kontouppgifter, kunddata i produkten (ärenden, mejl, chattar, utkast, stegloggar i `agent_runs`) och uppgifter i Snajps egna utskick (prospekt, kontakter, trådar).
2. **Undantag:**
   - Spärrlistan (`suppressions`) raderas inte efter 24 månader. Den finns för att personen aldrig ska kontaktas igen, och skyddet försvinner med raden.
   - Bokföringsunderlag (`bk_underlag`) sparas i sju år enligt bokföringslagen 7 kap. 2 §. Det är kundens underlag; kunden avgör.
3. **Per kund.** För kunddata där Snajp är biträde sätts perioden vid onboarding, i steg 5 i `docs/pilot_onboarding.md`. Standard är 24 månader. Kunden får välja en kortare period. Perioden skrivs in i biträdesavtalets Bilaga 1 punkt 5 och i kundens art. 13-text.
4. **Mekanismen är inte i drift.** Ett schemalagt gallringsjobb för alla kategorier byggs i en separat PR. Tills det körs, och har körts i torrkörning mot produktionen minst en gång, ska integritetspolicyn inte säga att gallringen är automatiserad.

**I praktiken.** Registerförteckningens tomma lagringstider fylls med 24 månader och undantagen. Integritetspolicyns mening om automatiserad gallring stryks eller väntar på jobbet. Vid onboarding körs `gallra.py --satt-policy <dagar>` för kunden (730 dagar om kunden inte väljer kortare). Beslutet blir helt sant först när jobbet körs schemalagt och dess logg finns.

Krav: GDPR DS-2, LBT-1, LBT-3; ISO 27001 A.8.10; uppgiften *Review Data Retention, Minimization, and Encryption*.

Datum: ____________________

Anton: ____________________
