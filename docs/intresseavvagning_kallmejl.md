# Intresseavvägning — utgående kallmejl

Artikel 6.1 f kräver att den som stödjer sig på berättigat intresse **har gjort
avvägningen och kan visa den**. Ett påstående om berättigat intresse utan en
dokumenterad avvägning är inte en rättslig grund, det är en förhoppning.

Gäller: Snajps egna kallmejl (A2 i [registerförteckningen](registerforteckning.md))
och, i tillämpliga delar, kundens utskick via leadsagenten (B2).

**Status: förstautkast, internt. Ska läsas av jurist tillsammans med
[`/villkor`](../app/villkor/page.tsx) och PUB-avtalet.**

Uppdaterad 2026-08-24.

---

## Steg 1 — Finns ett berättigat intresse?

**Intresset:** att marknadsföra en programvara till företag som sannolikt har
nytta av den, genom direktkontakt med rätt person på bolaget.

Direktmarknadsföring pekas uttryckligen ut som ett möjligt berättigat intresse
i skäl 47 till dataskyddsförordningen. Det avgör inte saken, men det gör att
frågan är öppen snarare än stängd.

**Intresset är kommersiellt och det är i sig inget problem.** Ett berättigat
intresse behöver inte vara ädelt. Det behöver vara verkligt, lagligt och
tillräckligt konkret för att gå att väga — och "vi vill sälja mer" är för vagt
för att väga mot något. Formuleringen ovan är den som gäller.

## Steg 2 — Är behandlingen nödvändig för intresset?

Nödvändig betyder "det finns inget mindre ingripande sätt att nå samma mål",
inte "det är det bekvämaste sättet".

Alternativ som övervägts:

- **Enbart annonsering och inbound.** Når inte de specifika bolag där
  produkten gör mest nytta, och kräver en varumärkeskännedom ett nystartat
  bolag inte har. Otillräckligt, inte likvärdigt.
- **Enbart funktionsadresser** (`info@`, `kontakt@`). Är faktiskt ett mindre
  ingripande alternativ och används där det går. Men på mindre bolag är
  funktionsadressen ofta obevakad, och ärendet når ingen.
- **Uppsökande via telefon.** Mer ingripande, inte mindre.

**Slutsats:** behandlingen är nödvändig, men bara i den minimala form som
faktiskt tillämpas — se steg 4.

## Steg 3 — Vad väger på den registrerades sida?

Här ska man vara ärlig, annars är avvägningen inte en avvägning.

**Det som talar för att intrånget är litet:**

- Uppgifterna är rena tjänsteuppgifter: namn, roll och tjänstemejladress hos
  en arbetsgivare. Ingen privatadress, inga känsliga uppgifter, inga
  ekonomiska uppgifter om personen.
- Uppgifterna är hämtade ur offentliga och yrkesmässiga källor — bolagets egen
  webbplats och offentliga företagsregister — där personen förekommer just i
  sin yrkesroll.
- Ett mejl om verksamhetens behov, till någon som ansvarar för verksamheten,
  ligger inom vad en yrkesperson **rimligen kan förvänta sig**. Det är det
  test skäl 47 pekar på.
- Ingen profilering av personen. Bedömningen görs på BOLAGET (bransch, storlek,
  signaler), inte på individen. Ingen automatiserad beslutsfattning enligt
  artikel 22.

**Det som talar emot, och inte ska bortförklaras:**

- Personen har inte bett om kontakten och har inte lämnat uppgiften till oss.
- `fornamn.efternamn@bolaget.se` **är en personuppgift**, även om den är
  yrkesmässig. Att kalla den "företagsuppgift" är en bekvämlighet, inte en
  analys.
- Mejlet är skrivet av en språkmodell, vilket kan uppfattas som mer
  påträngande än ett individuellt skrivet mejl om det märks.
- Volym är en tung faktor. Enstaka relevanta mejl är något annat än massutskick,
  och skillnaden avgörs av vad koden faktiskt tillåter — inte av avsikten.

## Steg 4 — Skyddsåtgärderna, och var de sitter i koden

Det här avsnittet är avvägningens tyngdpunkt. Åtgärderna nedan är inte
riktlinjer utan **spärrar i kod som blockerar utskicket**, och de går att
falsifiera. Se [`send_guard.py`](../snajp-support/app/leads/send_guard.py) och
[`utskicksfot.py`](../snajp-support/app/leads/utskicksfot.py).

| Åtgärd | Var | Vad som händer om den brister |
|---|---|---|
| Avsändaren identifieras fullständigt: namn, org.nr, postadress | Regel 1 | Utskicket **blockeras** |
| Klickbar avregistreringslänk i varje mejl | Regel 2 | Utskicket **blockeras** |
| Avregistrering gäller omedelbart och för HELA kunden, inte kampanjen | Regel 3 | Utskicket **blockeras** |
| Artikel 14-information vid personlig adress: vem, varför, varifrån, rätten att invända | Regel 4 | Utskicket **blockeras** |
| Högst en kontakt per bolag per kvartal | Regel 5b | Utskicket **blockeras** |
| Volymtak under uppvärmning, 20/dag i 14 dagar | Regel 5c | Utskicket **köas om** |
| Bara kontorstid, vardagar 08–17 svensk tid | Regel 5a | Utskicket **köas om** |
| De tre första utskicken för en ny kund granskas alltid av en människa | Regel 6 | Går till **granskningskö** |
| Inget mejl går ut utan att koden godkänt det — modellen kan bara köa | INV-SEC-004 | Modellen har inget sändverktyg |

Två av dessa är starkare än vad lagen kräver: karensen per bolag och den
mänskliga granskningen av de tre första. De står med här därför att de är det
som gör volymargumentet i steg 3 hanterligt.

## Steg 5 — Slutsats

**Berättigat intresse bedöms som en hållbar grund för behandlingen, under
förutsättning att spärrarna i steg 4 finns kvar.**

Avvägningen står och faller med dem. Tas regel 2 eller regel 4 bort är den här
bedömningen inte längre giltig, och det är därför de reglerna bär sitt eget
motiv i koden — nästa person som frestas ta bort en spärr möter skälet i samma
skärmbild.

**Rätten att invända** (artikel 21.2) är ovillkorlig vid direktmarknadsföring:
den registrerade behöver inte ange något skäl, och vi måste sluta omedelbart.
Det är precis vad avregistreringslänken gör, och den är därför inte en
artighet utan grunden för hela avvägningen.

## Att ompröva

Den här bedömningen ska göras om vid något av följande:

- Volymen ökar väsentligt utöver dagens tak.
- Personlig profilering införs, alltså bedömning av individen och inte bolaget.
- Källorna vidgas bortom offentliga och yrkesmässiga uppgifter.
- Någon spärr i steg 4 tas bort eller mjukas upp.

## Öppna punkter

- [ ] Läst av jurist
- [ ] Beslutad lagringstid för kontaktuppgifter (kopplas till
      [gallringen](../scripts/gallra.py))
- [ ] Formulering av källangivelsen i utskicksfoten granskad — i dag
      "offentliga företagsuppgifter", vilket ska stämma med vad som faktiskt
      används
