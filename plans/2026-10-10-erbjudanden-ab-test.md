# Plan 2026-10-10: A/B-test av erbjudanden i Iris kalla mejl

Antons beställning: testa de starkaste erbjudandena han väljer, bevaka och mäta löpande, och kunna byta enkelt. Erbjudandets struktur ska finnas i systemet, anpassas efter kunden och alltid skrivas i skrivstilen. Villkoren bestäms efter att erbjudandet valts.

Underlag: `docs/hormozi-erbjudanden-2026-10-10.md` (42 verktyg), katalogen `agent-core/prompts/leads-erbjudanden.md` (sex erbjudanden), sidan https://claude.ai/artifact/GJyGt86xgcnjbbvd24ogjS (exempelmejl och val).

## Delar

1. **Katalog** (`leads-erbjudanden.md`, läses av `app/leads/erbjudanden.py`): var i mejlet erbjudandet sitter, hur det sägs, vad som ska undvikas. Inga villkor i katalogen.
2. **Kundens val** (`agent_configs.settings.erbjudanden`, agent leads): aktiva erbjudanden med vikt och kundens villkor per erbjudande. Utan villkor kan ett erbjudande inte slås på. Inga aktiva = dagens beteende.
3. **Tilldelning**: deterministisk per prospekt (hash), viktad, fast. Sparas som `offers`-rad per (kund, nyckel) och `outreach_threads.offer_id` (tabellerna finns sedan migration 010).
4. **Prompt**: blocket "Erbjudandet i det här mejlet" + kundens villkor ordagrant i utkaststeget och humanizern. Villkoren läggs i faktagrindens underlag, så att deras siffror släpps igenom men inga andra.
5. **Stilkontroll** (`app/leads/stilkontroll.py`): robotmarkörer enligt skrivstilen, även över en hel körning (samma ingång eller uppmaning). Fynd skickar utkastet till granskning.
6. **Mätning**: per erbjudande skickade, svar, positiva svar, möten. "Leder" först vid minst 30 skickade per arm och signifikant skillnad (tvåproportions z-test, 95 %).
7. **Gränssnitt**: kortet Erbjudanden i Iris inställningar, på/av, vikt, villkor, resultat. Tvåspråkigt.
8. **Provkörning** (`snajp-support/scripts/prova_erbjudanden.py`): fyra syntetiska kunder × tre branscher × varje erbjudande genom den riktiga utkastvägen, med textkvalitet, gissningsgrind, stilkontroll och ett LLM-omdöme om grammatik och mänsklig ton. Körs före varje aktivering och varje ändring av katalogen eller skrivstilen.

## Arbetsgång för ett test

1. Anton väljer två kandidater (högst tre) och skriver deras villkor.
2. Provkörningen körs; inga grammatikfel och inga återkommande stilfynd innan aktivering.
3. Erbjudandena slås på med lika vikt. Allt annat hålls lika (målgrupp, skrivstil, avsändare).
4. Veckovis avläsning: svar först (snabbast signal), positiva svar och möten därefter.
5. Beslut: när en arm leder enligt grinden, eller efter förbestämd volym. Förloraren slås av, nästa kandidat slås på. Historiken ligger kvar.

## Volym och tid

För att säkert skilja 5 % från 10 % svarsfrekvens krävs cirka 435 skickade per arm (95 % säkerhet, 80 % styrka). Med autopilotens 10 leads per vardag tar två armar ungefär 17 veckor. Därför: två armar åt gången, tidiga beslut bara vid stora skillnader, och mer volym förkortar testet rakt av.

## Öppet

- Villkoren per erbjudande (Anton). FAQ:n om provperioden måste rättas innan "Riskfri start" används.
- Mätningen av möten bygger på samtalsutfallet "Möte bokat" och svarsklassen positivt; ett möte bokat via mejl utan samtal syns bara som positivt svar.
- Uppföljningsmejlen (delmål 12) bär inte erbjudandet i första versionen.
