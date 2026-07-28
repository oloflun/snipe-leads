# Snajp-Support — guide för piloten

Kort intern guide för er som kör piloten. Ingen teknisk förkunskap krävs.

---

## Vad agenten gör — och inte gör

Agenten läser inkommande kundmail, sorterar dem i åtta fack och skriver ett
förslag på svar. **Den skickar aldrig något själv.** Ni läser förslaget,
ändrar om ni vill, och trycker skicka.

Den hittar heller aldrig på. Svaren bygger enbart på texten ni lagt in i
kunskapsbasen. Saknas underlag skriver den inget svar — ärendet markeras
**Eskalerat** och lämnas till er.

Facken är: Teknisk support, Garanti, Leverans & frakt, Utbildning &
användarstöd, Reklamation & retur, Betalning & faktura, Orderstatus, Övrigt.

---

## 1. Fyll kunskapsbasen

Gå till **Kundtjänst → Kunskapsbas**.

Tryck **Hämta branschmall** för att få strukturen: ett tjugotal rubriker som
täcker de vanligaste frågorna i branschen. Alla är märkta `[PLATSHÅLLARE]` och
innehåller generell text — **den måste ersättas med era egna villkor.**

Öppna varje artikel och skriv om texten så att den säger det ni faktiskt lovar
kunderna: era garantitider, era leveranstider, era returvillkor. Skriv som ni
skulle svara en kund i ett mail — det är precis så texten kommer användas.

Ni kan också trycka **Lägg till artikel** för frågor som är specifika för er.

> **Tumregel:** om ni inte skulle stå för formuleringen i ett mail till en
> kund, ska den inte ligga i kunskapsbasen.

Så länge artiklar är märkta *Platshållare* varnar dashboarden överst. Sikta på
noll platshållare innan ni svarar riktiga kunder.

---

## 2. Koppla inkorgen

Inkorgen kopplas via IMAP med ett **app-lösenord** — inte ert vanliga
lösenord.

**Gmail:** slå på tvåstegsverifiering på kontot, gå till
[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords),
skapa ett lösenord och spara de 16 tecknen.

Uppgifterna läggs sedan in som miljövariabler på servern (`IMAP_HOST`,
`IMAP_USER`, `IMAP_PASSWORD`). Det gör den som sköter tekniken — hör av er så
hjälper vi till.

När det är klart: tryck **Hämta nya mail** i inkorgen. Agenten hämtar olästa
mail, markerar dem som lästa och sorterar dem. Samma mail hämtas aldrig två
gånger.

> Använd gärna en egen supportadress under piloten, inte någons personliga
> inkorg.

---

## 3. Så arbetar ni med utkast

Varje ärende har en status:

| Status | Betyder |
|---|---|
| **Utkast** | Agenten har skrivit ett förslag som väntar på er |
| **Godkänt** | Ni har godkänt men inget mail har skickats |
| **Skickat** | Svaret har gått iväg till kunden |
| **Eskalerat** | Agenten avstod — ni behöver svara själva |
| **Avvisat** | Ni slängde förslaget |
| **Övertaget manuellt** | Ni tog över ärendet |

Klicka på ett mail för att se kundens text, agentens förslag och en
**beslutslogg** som förklarar varför agenten gjorde som den gjorde.

I förslaget kan ni:

- **Godkänn & skicka** — svaret mailas till kunden i samma tråd
- **Godkänn utan att skicka** — om ni hellre svarar från er vanliga mail
- **Kopiera text** — lägger svaret i urklipp
- **Avvisa** — slänger förslaget
- **Ta över ärendet** — markerar att ni sköter det manuellt

**Läs alltid igenom innan ni skickar.** Ändra fritt i textrutan — era ändringar
sparas och syns i historiken.

---

## 4. Regler per fack

Under **Regler** kan varje fack ställas in:

- **Utkast** — kräver alltid godkännande *(rekommenderat under hela piloten)*
- **Auto** — får skickas automatiskt vid hög säkerhet
- **Eskalera** — går alltid direkt till er, agenten skriver inget förslag

Även om ett fack står på *Auto* skickas ingenting så länge autosvar är
avstängt globalt — bannern högst upp visar **Granskningsläge** när så är
fallet. Låt det vara kvar under piloten.

Oavsett regler eskalerar agenten alltid ärenden som rör återbetalning,
juridik, GDPR, en arg kund, eller en inträffad incident.

---

## 5. Vad ni ska hålla koll på

**Varje dag under första veckan:**

- Läs igenom varje förslag innan ni skickar — även de som ser bra ut.
- Håller texten det ni faktiskt lovar? Rätta i kunskapsbasen, inte bara i svaret.
- Hamnade mailet i rätt fack? Notera fall där det blev fel.

**Signaler på att kunskapsbasen behöver fyllas på:**

- Många ärenden blir *Eskalerat* med motiveringen att underlag saknas.
- Ni skriver om samma sak i flera svar — då hör det hemma i kunskapsbasen.

**Signaler på att något är fel:**

- Ett svar innehåller påståenden ni inte känner igen → kontrollera artikeln det
  bygger på (visas under förslaget), texten är sannolikt otydlig.
- Låg konfidenssiffra på många ärenden → frågorna liknar varandra för mycket,
  eller så saknas ord ur kundernas språk i kunskapsbasen.

**Efter piloten** kan ni överväga att sätta enstaka, väl fungerande fack till
*Auto* — men bara sådana där ni läst igenom många svar och litar på dem.

---

## Om något strular

- **"Ingen inkorg är kopplad"** — IMAP-uppgifterna är inte satta på servern.
- **"Backenden svarar inte"** — servern sover (den vaknar på en minut) eller är
  nere. Ladda om och försök igen.
- **Ett svar gick inte att skicka** — utkastet ligger kvar och kan skickas om.
  Ärendet markeras aldrig som skickat om mailet inte gick fram.

Vid frågor: hör av er till oss.
