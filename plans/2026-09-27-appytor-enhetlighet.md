# Appytorna: en typografi, en listform, ingen mikrotext

2026-09-27. Beställning (Anton): gå igenom dashboard-sidorna, förbättra logik och layout, gör
text och listor enhetliga i stället för spridda format, lyft designen utan att ändra
grundutseendet, och ta bort all liten beskrivande "editorial"-text — förbjuden i all frontend
sedan FEEDBACK.md F-016 (gate 99). Nödvändig information ersätts med ren text som matchar
den övriga texten. Rent, logiskt, enkelt.

**Läge:** Operate (`~/.claude/skills/design/references/product-surfaces.md`). Tier 0: `DESIGN.md`
är låst. Grundutseendet står kvar: varmt papper, mörk ink-rail med ochre-markör, Fraunces i
rubriker, Geist i text, hårlinjer som struktur, ochre som enda accent.

**Omfång:** alla inloggade appytor — `/admin/**`, `/dashboard/**`, `/settings/**` och samma
komponenter där de renderas i `/demo/**`. Marknadssidorna ingår inte.

## Primitiverna (components/ui.tsx) — använd dem, uppfinn inga nya

| Roll | Primitiv | Utseende |
|---|---|---|
| Sidrubrik h1 | `Sidhuvud` (`title`, `action?`) / klass `rubrikSida` | Fraunces 2.25rem, rak, aldrig kursiv |
| Sektionsrubrik h2 | `Sektion` (`title`, `action?`, `children`) / klass `rubrikSektion` | Fraunces 1.5rem |
| Panel-, kort- och radrubrik h3 | klass `rubrikPanel` | Geist 1.0625rem halvfet |
| Brödtext | — | Geist 0.9375rem, `text-ink` |
| Sekundär text | — | Geist 0.9375rem, `text-ink-muted` |
| Etikett (fält, kolumn, nyckeltal, grupp) | klass `etikett` | Geist 0.8125rem medium, `text-ink-muted`, versal/gemen som vanlig text |
| Meta (datum, domän, stad, antal i en rad) | klass `meta` | Geist 0.8125rem, `text-ink-subtle`, `num` på tal |
| Nyckeltal | `Nyckeltal` (`poster: {etikett, varde, notis?}[]`) | Fraunces 2rem `num`, etikett ovanför, hårlinjer |
| Tabelldata | `Tabell` / `Cell` / `tabellRad` | fasta kolumner, etikett-huvuden |
| Rader som inte är en tabell | `Radlista` / `Rad` | hårlinjer mellan rader |
| Filter- och vyflikar | klasser `flik`, `flikAktiv`, `flikInaktiv` | pillren från Iris "Alla bolag / Listor" |
| Status | `Badge` | tonerna neutral/good/warn/danger |
| Knappar | `btnPrimary`, `btnSecondary`, `btnLiten` | oförändrade |
| Tomt läge | `Tomt` (`children`, `action?`) | en mening på `paper2`-platta med hårlinje |
| Maskin-id (händelsekod, nyckel, run-id) | `font-mono text-[0.8125rem]` | ENDA tillåtna mono |

`PageShell` (components/AppShell.tsx) tar inte längre `kicker` eller `description`. Typfelen
pekar ut varje anropsställe; gå igenom dem ett och ett enligt regel 1.

## Regel 1 — ingen mikrotext

Bort: `.kicker` och allt med `uppercase` + `tracking-*` eller mono som etikett, överrader ovanför
rubriker, ingresser och förklarande rader under sid- och sektionsrubriker, rader som beskriver
sidan eller exemplet, "Påhittade — …"-notiser, sidfotsrader som upprepar det som syns.

Testet (F-016): identifierar, särskiljer, lokaliserar eller möjliggör raden en handling? Om nej:
stryk. Om informationen behövs: lägg den i rubriken, i etiketten, i värdet, eller som EN vanlig
mening i brödtextstorlek (`text-[0.9375rem] text-ink-muted`) precis där den används — eller i
`title`-attributet. Ingen text på sidan får handla om sidan (F-018).

Står kvar, men i enhetlig form: fältetiketter, kolumnhuvuden, nyckeltalsetiketter,
statusbrickor, tidsstämplar/meta som identifierar raden, felmeddelanden, tomlägen.

## Regel 2 — sidans anatomi

`Sidhuvud` (rubrik + ev. åtgärder till höger) → `mt-8` → innehåll. Sektioner via `Sektion`
(`mt-12` mellan sektioner, rubrik + ev. åtgärd, innehåll `mt-4`). Ingen egen sidbredd — layouten
äger containern. Kort runt en sektion bara när innehållet är ett eget objekt; annars hårlinjer.

## Regel 3 — listor och tal

- Tabulär data → `Tabell`. Blandat innehåll → `Radlista`. Aldrig kort-i-lista, aldrig en rå
  `<table>` med egna klasser.
- Radens anatomi: rubrik → meta-rad under → status/tal till höger.
- Lång fritext (AI-resonemang, beskrivningar) i en lista: `line-clamp-2`. Hela texten hör hemma
  i detaljvyn.
- Nyckeltal alltid via `Nyckeltal`, och etiketten bär enhet och period ("Körningar, 7 dagar").
- Tomt värde i en tabellcell: `–` (tankstreck, inte em-streck). Inga em-streck (—) i synlig
  text någonstans (DESIGN.md).

## Regel 4 — logik

- Visa inte samma sak två gånger på en yta (arbetsytans namn står redan i railen).
- Ingen navigering som bara upprepar railen (kort vars enda innehåll är en länk dit railen redan
  leder).
- Ordning efter vad användaren agerar på: det som väntar på användaren först, nyckeltal sedan,
  status och konfiguration sist.
- Rubriker och etiketter i klartext: inga interna koder som rubrik ("admin.impersonation" är
  meta i mono, inte text).

## Regel 5 — inga beteendeändringar

Datahämtning, handlers, grindar, entitlement och props-kontrakt står kvar (utom `kicker`/
`description` på PageShell). Ändra inte i/18n-nycklar som används på marknadssidorna.

## Kontroll per agent

1. `npm run type-check` — inga fel i egna filer.
2. `grep -nE "kicker|uppercase|tracking-\[0\.[1-9]|italic-disp|font-display italic|—" <egna filer>`
   → inga träffar i synlig UI (kommentarer undantagna).
3. Rapport: ändrade filer; för varje struken rad, citatet och vart nödvändig info tog vägen;
   varje logikändring med skäl.

Den visuella verifieringen (varje sida och undersida, admin + testkund, pixlar) gör
orkestreraren.
