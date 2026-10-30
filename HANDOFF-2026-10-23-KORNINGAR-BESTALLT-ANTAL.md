# Handoff 2026-10-23: körningarna ska nå beställt antal

## 1. Läget just nu, verifierat
- Git: `development` = `origin/development` = 968e0ea; inget opushat. Main har allt via PR 38 (mergad av Anton, merge 12a20ad).
- Miljöer: development och main deployar sig själva från sin gren. Deployen i main och en ny körning där är INTE kontrollerade.
- Migrationer: inga i den här releasen.
- Extern blockering: sidhämtningar faller hos tjänsten (86 i körningen f0961755, troligen ScrapeGraph-krediten). 8 av 43 researchade föll på "Inget källmaterial".
- Agentens läsning av main-databasen nekas nu av behörighetsspärren (läsning av development fungerar).

## 2. Vad som byggdes
- Uppdrag (Anton): läs Sebbes senaste commit och få körningarna att leverera beställt antal.
- Uppmätt i main, körning f0961755 (200, Göteborg): 18 levererade, 11 rundor varav 4 tomma. Orsaker: (a) fällda registerbolag prövades om varje runda — Sebbes 7496a97; (b) `allabolag.MAX_LISTSIDOR = 40` gav 2 007 av 8 400 bolag (detaljhandel 7 003, bygg 1 396). ~5 % av registret blir Iris-kandidater, ~40 % klarar researchen.
- 968e0ea: taket 40 → 400 sidor; första tomma rundan utan sökfel sätter `korning["bred"]` och rundorna därefter söker breda B2B-branscher (~20 000 bolag i Göteborg) i SAMMA område, samma filter/Jev/research; sammanfattningen säger det. Filer: `snajp-support/app/leads/sources/allabolag.py`, `app/leads/discovery.py` (`hitta_bolag(bred=)`), `app/leads/korning.py`, `app/api/leads.py` (`_sla_in_sokrunda`), test i `tests/invariants/test_inv_leads_n_001.py`. Beslut i `docs/BESLUT.md`.
- Verifiering: 2128 tester gröna (invariants, leads, api). PR 38 uppdaterad; en CI-kontroll föll på 429 från AWS bildregister och kördes om.

## 3. Vad som återstår
1. Agent: kontrollera att mains deploy gick igenom och följ nästa körning på 200 (antal levererade, om `bred` slog till, Jev-tokens).
2. Anton: fyll på ScrapeGraph-krediten, annars försvinner ~20 % av researchade bolag på "Inget källmaterial".
3. Anton: säga om breddningen till andra branscher i området är okej för alla kunder (beslutet är taget under "vad som än krävs").

## 4. Fällor
- Varje runda börjar om på sida 1 och läser tidigare sidor ur cachen; djupt in i en körning blir det hundratals cacheläsningar per runda.
- Körningens tratt växer med alla bortval (tusentals rader i JSON-tillståndet).

## 5. Antons instruktioner ordagrant
- "Läs senaste committen från Sebbe och gör vad som krävs för att körningarna ska leverera beställt antal, vad som än krävs."
- "Öppna release-PR:en development → main"
- "Slå på Auto-fix för PR 38" (gick inte: PR:en var redan mergad)
