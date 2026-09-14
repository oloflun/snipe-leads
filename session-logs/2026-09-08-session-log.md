# Session Log — 2026-09-08

## Session Summary

Fyra spärrar i den delade designhookkedjan (`~/.claude/hooks/`), som routade
backend-filer som om de vore gränssnitt och fällde ut hela designproceduren på
ordet "design" inuti ett filnamn. Varje spärr är mätt eller testad mot det fall
den påstår sig laga, och tre av felen hittades av testerna först efter att jag
skrivit spärren — inklusive ett där min egen lagning rev upp den föregående.
Utöver hookarna granskade jag en systersessions raderingsskript och hittade ett
hål som hade tagit en riktig kunds kunskapsbas.

## What Changed

### Files Created
- `~/.claude/hooks/tests/test_ui_write_guard.py` — regressionstest för routern och kontraktsgrinden; 9 enhetsfall, reproduktion av den gamla buggen, två e2e-körningar och en vakt som faller om testet skriver i repots ledger
- `~/.claude/hooks/tests/test_intent_guard.py` — 24 fall för promptsidan: kod-tokens, svensk böjning, sammansättningar och varje falsk vän jag stötte på
- `~/.claude/hooks/tests/matt_bojning.py` — mätverktyg som kör tre stadier av ordlistan (ursprung / böjning / sammansättning) över repots prosa och listar varje ny träff för granskning
- `session-logs/2026-09-08-session-log.md` — denna logg
- `plans/2026-09-08-designhookarnas-spaerrar.md` — planen för spärrarna, med kvarvarande punkter

### Files Modified
- `~/.claude/hooks/design_hook_lib.py` — ny `is_ui_write(path, event)` som löser ut innehållet (hunken plus filen på disk) i stället för att svara på extension allena
- `~/.claude/hooks/design-route.py` — routern frågar spärren i stället för `is_ui_file(path)`
- `~/.claude/hooks/design-gate.py` — kontraktsgrinden likaså; dess docstring lovade redan "the target is a UI file"
- `~/.claude/hooks/design-intent.py` — `strip_code_tokens()`, `_SV_BOJNING`, `STRONG_SAMMANSATT`/`WEAK_SAMMANSATT`, och svag räkning på stam i stället för böjd form
- `~/.claude/projects/.../memory/snipe-leads-designskills-och-hydrering.md` — de fyra spärrarna, fällorna och mätsiffrorna
- `.impeccable/design-session.jsonl` — sex syntetiska rader från mina egna e2e-körningar bortplockade (filen är gitignorerad)

## Decisions Made

- **Spärren läser hunken PLUS filen på disk, inte hunken ensam:** en hunk ur en
  äkta komponent bär ofta ingen UI-signal, så att bara lita på den hade bytt
  falsk route mot falsk tystnad. Regressionsvakten i testet är exakt det fallet.
- **Kontraktsgrinden fick samma spärr:** den körde detektorn över backend-filer
  och kvitterade en `gate-pass` för var och en. Ändringen gör att koden gör det
  dess egen docstring redan lovade.
- **Sammansättningar som opt-in-lista, inte `\w*`:** `nav` hade fällt på
  "navigering", `motion` på "motionsspåret", `font` på "fontänen", `hero` på
  "heroisk", `premium` på "premiumkund". De står därför inte i listan.
- **Sammansättningens svans är bokstäver, inte `\w`:** `_` är ett ordtecken, så
  `design\w{2,}` åt upp `DESIGN_GATE_BLOCKING` och rev upp kod-token-spärren
  igen. Testet föll på just det.
- **`isk` bort ur böjningen:** den lät "heroisk" fyra som stark signal. Min egen
  regel från steget innan, borttagen samma session. "typografisk" bärs nu av
  sammansättningsregeln.
- **Svaga signaler räknas på STAMMEN:** med böjning inlagd räknades
  "komponenten" och "komponenterna" som två signaler, så ett enda begrepp
  räckte för att fyra.
- **Mätning framför resonemang:** varje breddning av ordlistan kördes mot 12 056
  rader riktig svensk prosa, och varje ny träff granskades för hand. Det var så
  engelskans "designed" hittades — den stod för fyra av nitton nya träffar.

## Context & Discussion

- Sebbe arbetade i små steg ("Ta X också") och lade till en spärr i taget:
  router → grind → kod-tokens → böjning → sammansättningar.
- `~/.claude/hooks/` är inte ett git-träd, så ändringarna ligger på disk utan
  versionshistorik. Det är delad infrastruktur för alla agenter och projekt.
- Bash-verktygets heredoc kollapsar `\` till `\`, vilket gör att `\b` blir en
  backspace-byte i filen. Det kostade tre reparationsrundor. Bygg
  regexbackslashes med `chr(92)` när mönstret skrivs via ett skript.
- `~` expanderas inte av skalet bakom appens Run-knapp. Kommandon till Sebbe ska
  bära absolut sökväg med framåtsnedstreck inom citattecken.
- En systersession (`snipe-leads-93`) städade testkund-arbetsytor i development.
  Jag svarade att `testkund-2b07d88b` inte var min men pekade på att två andra
  sessioner var levande i katalogen och att ägaren troligen var en av dem.
- Deras raderingsskript hade tagit `ss_knowledge_base` ur kunddataspärren
  globalt, fast seedningen bara gäller `testkund-`-slugar. Jag flaggade att en
  onboardad men inaktiv kund då skulle förlora sin kunskapsbas. De verifierade
  mot körande databas, bekräftade hålet och lagade det (`99c4690`).
- Deras seedantal rörde sig 16 → 28 mellan två meddelanden samma dygn, vilket
  bekräftade att en radräkningsspärr hade tystnat av sig själv.

## Open Threads

- Sammansättningslistan i `design-intent.py` täcker i dag femton stammar. Om
  fler ord ska med måste `matt_bojning.py` köras om mot prosan och varje ny
  träff granskas — särskilt korta stammar, som är prefix till annat.
- Ordet "motioner" ger fortfarande en svag signal (svenska för motion/förslag).
  Det krävs två signaler för att fyra, så det är tolererat men inte löst.
- `design-gate.py` körs fortfarande i rådgivande läge. Att befordra den till
  blockerande (`DESIGN_GATE_BLOCKING=1`) kräver en ren körning på meritlistan
  först, vilket ingen har gjort.
- Conclude-protokollets mekaniska halva kunde inte köras: `conclude-finalize.py`
  och `render-status.py` saknas i `~/.agents/scripts/`. Bara
  `update-global-status.py` finns. Nästa session bör antingen återställa dem
  eller uppdatera conclude-skillen så den beskriver det som faktiskt finns.

## Cross-Project Handoffs

Ingen `Outgoing/`-fil. Ändringarna ligger i `~/.claude/hooks/`, som är delad
infrastruktur för alla Sebbes projekt — de får alltså effekt överallt utan att
något behöver flyttas. Den observerbara skillnaden: en `[design · ...]`-rad ska
inte längre dyka upp när en Python- eller backend-`.ts`-fil skrivs, och
designproceduren ska inte fällas ut av ett filnamn i prompten.

## Current State After This Session

Fyra spärrar sitter i hookkedjan, med två testsviter och ett mätverktyg som gör
dem falsifierbara. Snipe-leads egen kod är orörd av mig denna session — allt
arbete låg i den delade hookkedjan och i granskningen av systersessionens
raderingsskript. Development står med tre arbetsytor och sex tenants efter
deras städning. Nästa session bör antingen ta conclude-skriptens frånvaro eller
återgå till produktarbetet; hookarna behöver inget mer just nu.

<!-- session-state
date: 2026-09-08
type: infrastructure-hardening
files_created:
  - ~/.claude/hooks/tests/test_ui_write_guard.py
  - ~/.claude/hooks/tests/test_intent_guard.py
  - ~/.claude/hooks/tests/matt_bojning.py
  - session-logs/2026-09-08-session-log.md
  - plans/2026-09-08-designhookarnas-spaerrar.md
files_modified:
  - ~/.claude/hooks/design_hook_lib.py
  - ~/.claude/hooks/design-route.py
  - ~/.claude/hooks/design-gate.py
  - ~/.claude/hooks/design-intent.py
decisions_made: 7
open_threads: 4
handoffs_pending: []
priority_changes: false
status_updated: true
goals_updated: "skipped -- infrastruktur i den delade hookkedjan, malbilden i GOALS.md orord"
next_session_focus: "Antingen aterstalla conclude-finalize.py/render-status.py i ~/.agents/scripts, eller ater till produktarbetet i snipe-leads"
session-state -->
