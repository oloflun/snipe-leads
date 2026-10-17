# Handoff 2026-10-10: skrivstil för kalla mejl och Hormozis erbjudanden

## 1. Läget just nu, verifierat
- Gren `development`. Två lokala commits, opushade: `8332ffc` (skrivstilen) och `ca9ade4` (rapporten). Push: `git push origin development`.
- En annan session hade samtidigt ocommittade ändringar i samma arbetskatalog (listutkast via Iris, `leads.py`, `docs/BESLUT.md`, `test_listutkast.py` som inte går att köra just nu). De ändringarna är inte rörda och inte committade härifrån.
- Ingen sparad grundprompt för leads i databasen, varken i development eller main (läst 2026-10-10), så filen `agent-core/prompts/leads-systemprompt.md` gäller.
- `bd` svarade inte (dolt startade inte), så uppföljningsärendet är inte skapat.

## 2. Vad som byggdes
- **Skrivstil** (`agent-core/prompts/leads-skrivstil.md`): kritiska regler, en struktur i fyra steg (deras arbete, igenkänningsfråga, vad agenten gör åt dem och vad de vinner, en tidsatt uppmaning), ordval, meningsbyggnad, före/efter-exempel och feedbackrundor. Byggd efter mönstret `03-writing-style.md` i ai-job-search. Där finns ingen skill som underhåller filen: `/setup` skapar den och varje feedbackrunda läggs in för hand som "omgång N". Samma rutin gäller här.
- Inkopplad via `leads_systemprompt.skrivstil()` i V1 (`leads_agent.py`), V2 inklusive humanizern (`leads_research_v2.py`) och listutkasten (`listutkast.py`). Grundpromptens §10 är omskriven till samma ordning.
- Verifierat: 774 tester gick igenom, plus en provkörning mot modellen (DeepSeek lokalt, syntetiska bolag, ingen databas). Första rundan kopierade modellen exemplen, så regel 7 (exemplen visar formen, inte orden) lades till. Andra rundan gav varierade mejl.
- **Hormozi-rapport** (`docs/hormozi-erbjudanden-2026-10-10.md`): 42 verktyg med källa i valvet, tio exempelmeningar, tolv varningar för svensk marknad och en topp 5.

## 3. Vad som återstår
1. Anton: bekräfta provperioden (två månader gratis, inga kortuppgifter) som det officiella erbjudandet och vad som händer när den tar slut. Därefter (agent): rätta `lib/faq.ts` (gratis-period) och `snajp_kb.py`, som säger att villkoren inte är fastställda, och lägg villkoren i Snajps affärskontext så att faktagrinden släpper igenom dem.
2. Anton: välj gratisprov per agent (Iris-, Kvitto- och Supportprovet) och kostnadstaket per prov, samt om en villkorad garanti på första resultatet ska införas.
3. Agent: se över skrivstilen mot de första riktiga utkasten från Gemini i development, och lägg Antons nästa feedback som omgång 2 i filen.
4. Skapa uppföljningsärendet i `bd` när dolt går att starta.

## 4. Fällor
- `cat > fil` utan heredoc i ett skript väntar på indata och hänger tyst.
- Lokala `.env` pekar mot en fjärrdatabas, så DeepSeek-spärren stoppar LLM-anrop. Kör med `DATABASE_URL=` tomt, och bara mot syntetiska data.
- Commita bara egna filer: andra sessioner arbetar i samma katalog.

## 5. Antons instruktion ordagrant
"Så här ser utkasten ut just nu: Det är anpassat efter varje kund, men känns ändå väldigt platt och oinspirerande, nästan informerande. Vi behöver göra varje erbjudande mer attraktivt och trycka mer på vad vi kan göra för dem med en tydlig CTA. Istället för Jag ser att ni är bla bla, säg: För företag som ert i *branchen* eller När man jobbar med *typ av jobb* som ni - Uppstår ofta de här problemen, eller Kan det här vara jobbigt/tidskrävande. Istället för vi har skapat, säg vår *agent* hjälper er med att *specifkt* för att ni ska få mer tid till att göra det ni gör bäst. I korthet, skapa ett writing-style regelset, precis som det jag har i ai-job-search repot, undersök om någon skill används för att skapa och updatera denna, för vi behöver förbättra strukturen, ordvalen och meningsuppbyggnaden även om det vi säger är korrekt, vi behöver bara uttrycka det på ett sådant sätt som känns verkligt personligt, inte bara som information. Jag vill att du gör detta, sedan vill jag att du noga undersöker alla säljtips om erbjudanden vi har från Alex Hormozi och presenterar alla alternativ du kan hitta på för vårt erbjudande, med den tonen jag precis förklarade."
