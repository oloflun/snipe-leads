# Handoff 2026-11-26: demofilmen får en supportdel

**Till:** agenten som Sebastian kör (Fable eller Opus, med bara Opus-agenter under sig).
**Gren:** `development` · **Skriven av:** Claude (sessionen som gjorde leadsfilmen, 2026-11-25–26, på
Antons dator) · **Status:** committad och pushad till `development` samma dag som filen skrevs.

## Uppdraget i en mening

Förläng Snajps click-through-film om Leads med en likadan del om supportagenten: kundtjänstens
Instagramreel först, hel och obeskuren, sedan supportagentens funktioner med fokus på vad kunden får,
och sist datasäkerhet, Vad ni får och den kostnadsfria piloten.

## Läs i den här ordningen

1. [`docs/marknad/UPPDRAG-DEMOFILM-SUPPORT.md`](docs/marknad/UPPDRAG-DEMOFILM-SUPPORT.md): uppdraget steg
   för steg, Antons domar ordagrant, reglerna och ett utkast till manuset. **Det här är din instruktion.**
2. [`marknad/demofilm/README.md`](marknad/demofilm/README.md): projektet, hur det installeras och körs.
3. [`docs/marknad/DEMOFILM-LEADS-2026-11-25.md`](docs/marknad/DEMOFILM-LEADS-2026-11-25.md): hur
   leadsdelen gjordes, varje instruktion från Anton, varje version och varje fel. Sökvägarna på `D:\` i
   det dokumentet finns bara på Antons dator; allt du behöver ligger i `marknad/demofilm/`.

## Det du behöver från Sebastian

Originalreelen om kundtjänst (Instagram, `snajp.ai`, 14 november 2026, "Kundmejl som ligger och
väntar?"). Helst källprojektet med en 4:5-komposition, annars originalfilen. Den ska ligga som
`marknad/demofilm/public/reel-support.mp4` och checkas inte in. Ladda aldrig ned den från Instagram.

## Läget när du tar över

| | |
|---|---|
| Leadsfilmen | Klar, 1 min 34 s, skickad till Anton. Hans dom över den slutliga versionen har inte kommit |
| Projektet | `marknad/demofilm/` i repot, fristående. Provat på Antons dator: typkontroll, tidslinjen (2 831 rutor, samma som filmen), stillbilder, en renderad del, och ljudet ur `verktyg/ljud.mjs`, som blev identiskt med leadsfilmens |
| Inte provat | En fullständig `npm install` och `bash bygg.sh` på en annan dator. Gör steg 1 i uppdraget och bygg leadsfilmen en gång innan du ändrar något |
| Inte kontrollerat | Ingen har lyssnat på leadsfilmens ljud |
| Iris-reelen | Checkas inte in. Rendera den ur `marknad/video` till `marknad/demofilm/public/reel.mp4` (README) |

## Utanför uppdraget

- En ändring i integritetspolicyn (`lib/bolag.ts`, ScrapeGraphAI-raden, och en post i `docs/BESLUT.md`)
  väntar på Antons ja och ligger ocommittad på hans dator. Den ingår inte i den här committen. Rör inte
  den raden i din del.
- Leadsdelens bilder och manus är godkända. Spela inte in dem igen (`rec/record-leads.mjs` skriver över
  dem).
