# DPIA — supportagenten

Konsekvensbedömning enligt artikel 35. Gäller den automatiska klassificeringen
av inkommande kundmejl, utkastgenereringen och eskaleringslogiken.

**Status: förstautkast, internt. Ska läsas av jurist och beslutas av
personuppgiftsansvarig — vilket för det här flödet är KUNDEN, inte Snajp.**

Uppdaterad 2026-08-24.

---

## 0. Behövs en DPIA alls?

Artikel 35.1 kräver en DPIA vid "sannolikt hög risk". Frågan ska ställas, inte
förutsättas.

**Argument för att den behövs:**

- Behandlingen är **systematisk och storskalig** i förhållande till kundens
  hela kundstock — varje inkommande kundmejl passerar.
- Innehållet är **okontrollerat**. En konsument som skriver till en
  kundtjänst kan skriva vad som helst, inklusive personnummer, hälsouppgifter
  eller uppgifter om någon annan. Vi kan inte styra det och ska inte låtsas
  att vi kan.
- De registrerade är **konsumenter**, alltså den svagare parten, och de har
  inte valt Snajp — de har valt kunden.
- Ny teknik (artikel 35.1) i den mening bestämmelsen avser.

**Argument emot:**

- Ingen automatiserad beslutsfattning med rättslig verkan enligt artikel 22:
  agenten föreslår, en människa godkänner. Se avsnitt 4.

**Slutsats: DPIA görs.** Två av IMY:s förteckningskriterier är uppfyllda
(storskalighet och sårbara registrerade), och när frågan är nära ska den
besvaras med en bedömning, inte med ett antagande.

## 1. Behandlingen

| | |
|---|---|
| **Ändamål** | Klassificera inkommande kundmejl i rätt ärendekategori, föreslå ett svar grundat i kundens kunskapsbas, och lämna över till en människa när underlag saknas |
| **Personuppgiftsansvarig** | Kunden |
| **Personuppgiftsbiträde** | Snajp |
| **Underbiträden** | Google (Gemini) för textgenerering, Supabase för lagring, Railway för drift |
| **Kategorier av registrerade** | Kundens kunder — konsumenter och företagskontakter |
| **Uppgifter** | Avsändarens namn och e-postadress, meddelandets fulla innehåll, bilagor |
| **Lagringstid** | Enligt `ss_gallringspolicy`. **Ännu inte beslutad** |
| **Rättslig grund** | Kundens — normalt fullgörande av avtal eller berättigat intresse |

## 2. Nödvändighet och proportionalitet

Behandlingen ersätter en manuell genomläsning som ändå sker. Uppgifterna
behandlas alltså inte i högre grad än om en anställd läste inkorgen — men de
behandlas **automatiskt och samlat**, och det är skillnaden som ska bedömas.

**Uppgiftsminimering, som den faktiskt är implementerad:**

- Bilder lagras inte efter att de beskrivits
  ([`vision.py`](../snajp-support/app/agent/vision.py)).
- Bokföringsagentens originalfiler lagras aldrig, bara en sha256-summa
  ([045](../supabase/migrations/045_bookkeeping.sql)).
- Ingen kunds data är läsbar för en annan kund — radnivåsäkerhet i databasen,
  inte en inställning i koden.

**Det som INTE minimeras, och som är den ärliga svagheten:** hela mejltexten
skickas till modelleverantören. Personnummer och samordningsnummer maskeras
sedan 2026-08-24 (se R1), men allt annat går som det står — och innehållet är
okontrollerat. En hälsouppgift i löptext passerar. Se risk R1.

## 3. Riskerna

### R1 — Överföring av okontrollerat innehåll till modelleverantören

**Vad som kan gå fel:** en kund skriver sitt personnummer eller en
hälsouppgift i ett supportmejl. Texten skickas till leverantören som vilken
text som helst. Är leverantörsavtalet på en nivå som tillåter användning för
produktförbättring, har uppgiften lämnat vår kontroll.

**Sannolikhet:** hög. Konsumenter skriver personnummer i kundtjänstmejl.

**Konsekvens:** hög, om avtalet inte håller. Låg om det gör det.

**Åtgärd:** *Grundfrågan är AVGJORD och svaret är negativt.* Googles eget
kvotfel namnger nivån: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`.
Gratisnivåns villkor tillåter leverantören att använda innehållet för
produktförbättring. Se P0.1c i [`JURIDIK_ATGARDER.md`](JURIDIK_ATGARDER.md).

**Behandlingen är därför pausad:** produktionen kör simuleringsläge, alltså
går ingen kundtext till någon modelleverantör alls. Det är inte en lösning,
det är ett stopp — men det är rätt läge tills avtalsnivån är bytt.
**Grundrisken kan inte stängas i kod, bara i avtal**, och tills den är stängd
är den här DPIA:n inte färdig.

**Mitigering byggd 2026-08-24:** personnummer och samordningsnummer maskeras
innan texten går till modellen, i både triagen och svarsgenereringen. Se
[`app/moderation/maskering.py`](../snajp-support/app/moderation/maskering.py).
Maskeringen kräver att numret passerar BÅDE en datumkontroll och Luhn, vilket
gör falska utslag sällsynta nog att den kan stå på i drift — ett grovt mönster
som fällde ordernummer hade blivit avstängt. Originalet ligger kvar i
databasen; det är bara prompten som bär en maskerad kopia.

Vad mitigeringen INTE gör: den tar bort den vanligaste och mest identifierande
formen av känslig uppgift, inte alla. En hälsouppgift i löptext går fortfarande
igenom. Läs inte R1 som löst.

### R2 — Ett felaktigt svar går ut i kundens namn

**Vad som kan gå fel:** agenten svarar fel på ett ärende som rör pengar,
returrätt eller garanti.

**Sannolikhet:** medel utan spärrar.

**Åtgärd, implementerad:** grundningsregeln kräver stöd i kunskapsbasen —
saknas underlag eskalerar ärendet till en människa i stället för att gissa.
Verifierat skarpt 2026-08-24: agenten svarade *"Jag har tyvärr ingen
information om leveranstider i kunskapsbasen"* i stället för att hitta på ett
svar. Utkast kräver dessutom mänskligt godkännande enligt kundens inställning
per ärendekategori.

**Kvarstående risk:** låg, men beroende av att kunden inte sätter alla
kategorier till `auto`. Se R4.

### R3 — Felaktig kategorisering fördröjer ett brådskande ärende

**Vad som kan gå fel:** ett ärende som borde eskalerats hamnar i fel fack och
blir liggande.

**Åtgärd, implementerad:** eskaleringen är fail-open mot människa — vid låg
konfidens eller vid ord som tyder på en upprörd kund går ärendet till en
människa. Beslutet loggas med sin motivering i `ss_decision_log`, alltså går
det att granska i efterhand vad agenten trodde och varför.

**Kvarstående risk:** låg.

### R4 — Kunden sätter alla kategorier till automatiskt svar

**Vad som kan gå fel:** hela spärren i R2 kringgås av en inställning.

**Åtgärd:** defaulten är `draft` för varje kategori, alltså mänsklig
granskning. Kunden kan ändra det.

**Kvarstående risk:** medel, och den ligger hos kunden. **Åtgärdat
2026-08-24:** [`/villkor`](../app/villkor/page.tsx) säger nu uttryckligen att
autonominivån är Kundens val och Kundens ansvar, och att en omställning till
automatiskt svar upphäver den mänskliga inblandningen — med hänvisning till
artikel 22.

### R5 — Den registrerade vet inte att en AI läser mejlet

**Vad som kan gå fel:** en konsument skriver till en kundtjänst och antar att
en människa läser. Informationsplikten enligt artikel 13 ligger på **kunden**,
som är personuppgiftsansvarig, och gäller på kundens egen webbplats.

**Åtgärd:** kravet står i [`/villkor`](../app/villkor/page.tsx) under Kundens
ansvar. Chattwidgeten bär dessutom en dataskyddsflik
([`AgentMenu.tsx`](../components/snajp/AgentMenu.tsx)).

**Kvarstående risk:** medel, och den är kundens. Vi kan inte kontrollera vad
kunden skriver på sin sajt — men vi kan sluta anta att de gjort det.
**Åtgärdat 2026-08-24:** [textmall](kundmall_informationstext.md) att ge vid
onboarding, plus ett uttryckligt krav i [`/villkor`](../app/villkor/page.tsx).
En färdig text som går att klistra in blir inklistrad; ett krav i ett avtal
blir det inte.

### R6 — Överlagring: data ligger kvar för alltid

**Åtgärd:** gallringsmekanismen finns
([048](../supabase/migrations/048_gallring.sql), [`gallra.py`](../scripts/gallra.py)).
Retentionsperioden är **inte beslutad**, och utan beslutad period gallras
ingenting. Det är den ofarliga defaulten men inte ett slutläge.

**Kvarstående risk:** medel. **Öppen punkt.**

## 4. Artikel 22 — automatiserat beslutsfattande

Artikel 22 gäller beslut som "enbart" grundas på automatisk behandling och som
har rättsliga följder eller på liknande sätt i betydande grad påverkar
personen.

**Bedömning: artikel 22 är inte tillämplig**, av två skäl som båda måste
gälla:

1. Utkast kräver mänskligt godkännande enligt kundens inställning per
   kategori — den mänskliga inblandningen är reell, inte en formalitet.
2. Att besvara en supportfråga har inte rättslig verkan och påverkar inte i
   betydande grad.

**Men punkt 1 beror på en inställning kunden kan ändra** (R4). Sätter kunden
allt till `auto` blir behandlingen helt automatisk, och då ska bedömningen
göras om. Det bör stå i villkoren.

## 5. Samlad bedömning

Med åtgärderna i avsnitt 3 bedöms restrisken som **acceptabel för R2, R3 och
R5**, och **inte fastställd för R1**.

**R1 är avgörande och öppen.** Går okontrollerat kundinnehåll till en
leverantör vars avtal tillåter användning för produktförbättring, hjälper
ingen av de andra åtgärderna. Den frågan ska besvaras innan fler kunder
onboardas.

Förhandssamråd med IMY enligt artikel 36 bedöms **inte** krävas, förutsatt att
R1 stängs. Krävs det ett samråd är det kunden som ska begära det, i egenskap
av personuppgiftsansvarig.

## 6. Öppna punkter

- [x] R1: Googles avtalsnivå fastställd — GRATISNIVÅ, bekräftat av Googles
      eget kvot-id. Behandlingen pausad tills nivån är bytt (P0.1c)
- [ ] R6: retentionsperiod beslutad
- [x] R4: kundens ansvar för autonominivån inskrivet i villkoren
- [x] R5: textmall till kunden för deras egen informationstext
- [x] Maskering av personnummer före modellanropet — byggd och testad
- [ ] Läst av jurist
- [ ] Beslutad av kunden som personuppgiftsansvarig
