# Data Classification & Handling

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`), och när en ny tabell, miljö eller leverantör får personuppgifter |
| Ramverkets mall | `frk_pt_685e40d46e7b1123022bf3e8` (avdelning `it`) |
| Täcker kontroller | Data Inventory and Mapping (`frk_ct_69e918e6d72a45b4f933a112`), Privacy by Design and by Default (`frk_ct_69e918e805776785f8f80a14`), Data Minimization, Encryption, and Pseudonymization (`frk_ct_69e918e8cc289b978f31a12a`) |
| Täcker krav | LBT-1 Information Audit, DS-1 Privacy by Design and by Default, DS-2 Data Minimization and Pseudonymization |

## Syfte

Skydda uppgifter efter hur känsliga de är. Störst vikt har kundernas kunders mejl och chattar, som kan innehålla vad som helst, även personnummer och hälsouppgifter (`docs/dpia_supportagenten.md` §0).

## Omfattning

All data som Snajp skapar, tar emot eller lagrar: i produktionen (`main`), i testmiljön (`development`, en fullständig spegel av produktionen), i Redis, hos leverantörerna, i repot och på utvecklarnas datorer.

## Klassningsnivåer

| Nivå | Vad | Exempel hos Snajp |
|---|---|---|
| **Begränsad** | Uppgifter vars röjande skadar kunder eller registrerade allvarligt | Kundmejl, chattar, bilagor, utkast och svar (`ss_*`), stegloggar med fulla promptar (`agent_runs`), kundernas integrationsnycklar, lösenord och API-nycklar (`.env.deploy`), webbplatsbedömningen (hemlig enligt `CLAUDE.md`) |
| **Konfidentiell** | Personuppgifter i yrkesroll och affärsdata | Prospekt och kontakter (`contacts`, `prospects`), kundregistret, kontouppgifter, utskick och svar i leadstrådar |
| **Intern** (standard) | Sådant som inte ska ut men inte skadar någon | Källkod, planer, beslut, de här policyerna |
| **Publik** | Redan publicerat | Webbplatsen, integritetspolicyn, villkoren, offentliga bolagsuppgifter |

Det som inte är klassat räknas som Intern. Personuppgifter är aldrig lägre än Konfidentiell.

## Märkning

Klassningen följer platsen, inte en etikett på varje fil:

- Databastabellerna klassas i registerförteckningen (`docs/registerforteckning.md`, raden "Var i systemet"). En ny tabell med personuppgifter läggs in där i samma ändring.
- `docs/compliance/` är Intern eller högre och undantagen från git, eftersom repot är publikt (`.git/info/exclude`).
- Hemligheter ligger bara i gitignorerade filer (`.gitignore:63`).

## Åtkomst och lagring

- **Minsta åtkomst mellan kunder:** databasen skiljer kunderna åt med radnivåsäkerhet och approllen `snajp_app` utan BYPASSRLS (`ARCHITECTURE_INVARIANTS.md`, INV-SEC-001). Verifieringen gjordes mot den gamla databasen; den ska göras om mot Railway, [FYLL: datum], ansvarig agent (JURIDIK_ATGARDER #23).
- **Minsta åtkomst för personer:** Anton och Sebbe har i dag åtkomst till båda miljöerna. Vem som har åtkomst till vilken datamängd ska skrivas in i registerförteckningen, [FYLL: datum], ansvarig Anton.
- **Testmiljön** innehåller produktionens persondata och hanteras som Begränsad (`CLAUDE.md`). Om spegeln ska minimeras eller pseudonymiseras är Antons beslut (JURIDIK_ATGARDER #16). AI-kodverktygens läsning av spegeln ska regleras, [FYLL: datum], ansvarig Anton (JURIDIK_ATGARDER #28).
- **Kryptering i vila:** Railway uppger att databaserna krypteras i vila (Railway DPA Exhibit C, `../../../leverantorsgranskning.md` §3); egen skärmbild saknas. Kundernas integrationsnycklar krypteras med Fernet i produktionen men ligger i klartext i testmiljön (nulägesinventeringen §4). Kryptering av nycklarna i testmiljön ska ske, [FYLL: datum], ansvarig agent.
- **Administrativ åtkomst till Begränsad data loggas inte** särskilt i dag. Ska införas eller medvetet avstås, beslut [FYLL: datum], ansvarig Anton.

## Överföring och delning

- **Kryptering i transit:** utgående HTTPS via `snajp-support/app/tls.py`. Undantag i dag: Redis går utan TLS (`../../../bevis/railway-konfiguration-2026-11-17.txt`, rad 118 och 256). TLS ska slås på, ansvarig Anton (JURIDIK_ATGARDER #4).
- Begränsad data får bara gå till en leverantör som är godkänd enligt leverantörspolicyn (`06-vendor-third-party-risk.md`).
- Begränsad data delas aldrig via öppna länkar, chatt eller skärmdumpar till utomstående (`CLAUDE.md`).
- Personnummer maskeras innan text går till Vertex AI (`snajp-support/app/moderation/maskering.py`). Hälsouppgifter i löptext maskeras inte.

## Inbyggt dataskydd (DS-1)

Det här finns i dag och ska behållas:

- Modellen kan inte välja kund eller skicka mejl; det gör koden (INV-SEC-002, INV-SEC-004).
- Supportagenten levereras med Utkast som standard för varje kategori (`app/villkor/VillkorSida.tsx`).
- Bilder lagras inte efter beskrivning, och kvitton sparas bara som sha256 (`docs/registerforteckning.md` B3).
- DeepSeek fäller uppstarten där data är riktig (`config.py:609-700`).

Det här ska införas:

- **Dataskyddsfråga vid varje ändring:** en ändring som lägger till en tabell, en leverantör eller ett nytt flöde med personuppgifter ska uppdatera registerförteckningen och leverantörslistorna i samma commit (`docs/JURIDIK_ATGARDER.md`, "Löpande"). Införs som punkt i granskningen av PR mot `main`, [FYLL: datum], ansvarig Anton.
- **Skyddande standardval:** avtalsgrinden ska vara på för nya kunder (JURIDIK_ATGARDER #9) och reservvägen till AI Studio spärras (#13). Ansvarig Anton för beslut, agent för kod.

## Lagring och gallring (DS-2)

- Lagringstider står i registerförteckningen. De flesta är [fylls i]. Anton beslutar perioderna, [FYLL: datum] (JURIDIK_ATGARDER #8).
- Gallringen ska köras schemalagt och omfatta supportmejl, `agent_runs`, chattar och leads. I dag finns bara mekanismen för supportmejl och den körs inte (`scripts/gallra.py:23-26`). Ansvarig agent efter Antons beslut.
- Integritetspolicyn säger i dag att gallringen är automatiserad. Det stämmer inte och ska rättas eller göras sant före första kund.
- Spärrlistan (`suppressions`) behålls tills vidare, eftersom den finns för att personen inte ska kontaktas igen (`scripts/gdpr_radera.py`).

## Mätning

Varje kvartal: stickprov på tre tabeller med personuppgifter. Står de i registerförteckningen, med lagringstid, gallring och rätt åtkomst? Målet är att alla gör det.

## Undantag

Undantag kräver Antons beslut i `docs/BESLUT.md` med kvarstående risk och vad som kompenserar.

## Brister

Felhanterad Begränsad data behandlas som en möjlig incident enligt `03-incident-response-breach-notification.md`.

## Förbättring

Klassningstabellen uppdateras när en ny produkt eller datatyp tillkommer.
