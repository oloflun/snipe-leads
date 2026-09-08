# Designhookarnas spärrar — routing, grind, kod-tokens, svenska

## Scope

Fyra spärrar i den delade hookkedjan `~/.claude/hooks/`, som alla adresserar
samma felklass: hookarna behandlade något som designarbete fast det inte var
det. Två på skrivsidan (vilka FILER som routas) och två på promptsidan (vilka
ORD som räknas som designavsikt).

## Completed

- [x] `is_ui_write(path, event)` i `design_hook_lib.py` — löser ut innehållet ur
      hunken plus filen på disk i stället för att svara på extension allena
- [x] `design-route.py` frågar spärren; backend-`.ts` ger inte längre en route
      som ingen skill kan ladda (rapporten 2026-09-02 hade GAP = 2)
- [x] `design-gate.py` frågar samma spärr; slutar köra detektorn och kvittera
      `gate-pass` för backend-filer
- [x] `strip_code_tokens()` i `design-intent.py` — maskerar inline-kod och
      sökvägar med icke-UI-extension innan ordlistan får se prompten
- [x] `_SV_BOJNING` — svenska böjningsändelser efter stammen
- [x] Svaga signaler räknas på stam (`group(1)`), inte böjd form
- [x] `STRONG_SAMMANSATT` / `WEAK_SAMMANSATT` — opt-in-lista med femton stammar
- [x] Två testsviter och ett mätverktyg i `~/.claude/hooks/tests/`

## Remaining

- [ ] Fler stammar i sammansättningslistan, om behovet visar sig. Kräver ny
      körning av `matt_bojning.py` och granskning av varje ny träff.
- [ ] "motioner" ger en svag signal (svenska för motion/förslag). Kräver två
      signaler för att fyra, så det är tolererat men inte löst.
- [ ] Befordra `design-gate.py` till blockerande (`DESIGN_GATE_BLOCKING=1`).
      Kräver en ren körning på meritlistan först.

## Deferred

- Sammansättningar för korta stammar (`nav`, `ui`, `ux`, `css`, `cta`, `hero`,
  `font`, `motion`, `premium`). Medvetet uteslutna: stammen är prefix till
  orelaterade ord, och kostnaden är falska larm i varje projekt.

## Blockers

- Conclude-protokollets mekaniska halva kunde inte köras: `conclude-finalize.py`
  och `render-status.py` saknas i `~/.agents/scripts/`.

## Next Steps

- Kör båda sviterna innan någon rör hookkedjan igen:
  `python "C:/Users/sebbe/.claude/hooks/tests/test_intent_guard.py"`
  `python "C:/Users/sebbe/.claude/hooks/tests/test_ui_write_guard.py"`
- Kör `matt_bojning.py` från ett repo med svensk prosa innan ordlistan breddas.
