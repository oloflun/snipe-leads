# Leads: thinking PÅ vs AV — fullständig jämförelse

Tenant: **Snajp** · Prospekt: **Gina Tricot, Blomsterlandet, Sportamore** · Lägen: **AV**

Onboarding saknas: `inget` · kontextpaket 2705 tecken

Varje körning = 8 research-steg + 4 outreach-steg, ett LLM-anrop per steg.

> **Detta dokument är GENERERAT rådata** — det skrivs över av nästa körning.
> Slutsatserna, och de två kundvända fynden körningen avslöjade, står i
> [`THINKING_MODE_COMPARISON.md` §8](THINKING_MODE_COMPARISON.md).
> Analys och rådata hålls isär med flit: förra rundans slutsatser fick
> korrigeras två gånger, och då ska rätt fil vara den som ändras.

---

## 1. Sammanfattning per körning

| Prospekt | Thinking | Steg | Omförsök | in-tok | ut-tok | reasoning-tok | Latens | Kvalificerad | ICP | Köad |
|---|---|---|---|---|---|---|---|---|---|---|
| Gina Tricot | AV | FEL | — | — | — | — | — | — | — | APITimeoutError: Request timed out. |
| Blomsterlandet | AV | FEL | — | — | — | — | — | — | — | APITimeoutError: Request timed out. |
| Sportamore | AV | FEL | — | — | — | — | — | — | — | APITimeoutError: Request timed out. |

## 2. Aggregat per läge

| Läge | Körningar | in-tok | ut-tok | reasoning-tok | Latens totalt | Latens/körning |
|---|---|---|---|---|---|---|
| AV | 0 | 0 | 0 | 0 | 0s | 0s |

## 3. Per skill-steg — kostnad och läge

Bevisar att thinking-läget nådde VARJE anrop (kolumnen `läge`) och att hela skillen injicerades (`injicerat`, jämför skill-audit).

### Gina Tricot

| # | Skill | Läge | Försök | in | ut | reasoning | injicerat | ms | Eskalerad |
|---|---|---|---|---|---|---|---|---|---|

### Blomsterlandet

| # | Skill | Läge | Försök | in | ut | reasoning | injicerat | ms | Eskalerad |
|---|---|---|---|---|---|---|---|---|---|

### Sportamore

| # | Skill | Läge | Försök | in | ut | reasoning | injicerat | ms | Eskalerad |
|---|---|---|---|---|---|---|---|---|---|

---

## 3b. Skiljde lägena sig i BESLUT, inte bara i kostnad?

Den avgörande frågan. Kostar thinking mer OCH ger ett annat svar, eller kostar det bara mer? Fälten nedan är de beslut research-kedjan faktiskt fattar.

| Prospekt | Fält | AV | PÅ | Skiljer |
|---|---|---|---|---|
| Gina Tricot | qualified | None | None | = |
| Gina Tricot | icp_fit | None | None | = |
| Gina Tricot | erbjudandenamn | None | None | = |
| Gina Tricot | cta | None | None | = |
| Gina Tricot | svagaste spak | None | None | = |
| Gina Tricot | offer_confidence | None | None | = |
| Gina Tricot | ämnesrad | None | None | = |
| Gina Tricot | utkast tecken | 0 | 0 | = |
| Blomsterlandet | qualified | None | None | = |
| Blomsterlandet | icp_fit | None | None | = |
| Blomsterlandet | erbjudandenamn | None | None | = |
| Blomsterlandet | cta | None | None | = |
| Blomsterlandet | svagaste spak | None | None | = |
| Blomsterlandet | offer_confidence | None | None | = |
| Blomsterlandet | ämnesrad | None | None | = |
| Blomsterlandet | utkast tecken | 0 | 0 | = |
| Sportamore | qualified | None | None | = |
| Sportamore | icp_fit | None | None | = |
| Sportamore | erbjudandenamn | None | None | = |
| Sportamore | cta | None | None | = |
| Sportamore | svagaste spak | None | None | = |
| Sportamore | offer_confidence | None | None | = |
| Sportamore | ämnesrad | None | None | = |
| Sportamore | utkast tecken | 0 | 0 | = |

---

## 4. Slutliga mejlutkast — sida vid sida

### Gina Tricot

**Thinking AV**

_Ingen utdata: APITimeoutError: Request timed out._

### Blomsterlandet

**Thinking AV**

_Ingen utdata: APITimeoutError: Request timed out._

### Sportamore

**Thinking AV**

_Ingen utdata: APITimeoutError: Request timed out._

---

## 5. Fullständig utdata — varje steg, varje läge

Ingenting är sammanfattat här. Detta är rådatan.

## Gina Tricot

### Gina Tricot — thinking AV

**FEL:** `APITimeoutError: Request timed out.`

## Blomsterlandet

### Blomsterlandet — thinking AV

**FEL:** `APITimeoutError: Request timed out.`

## Sportamore

### Sportamore — thinking AV

**FEL:** `APITimeoutError: Request timed out.`
