# Handoff 2026-10-08 — CRM-flödet: översikt, utkast/skickat, massåtgärder, kontaktsökning, ringlista, återkoppling

Antons beställning 2026-10-07. Plan: `~/.claude/plans/pasted-content-id-f377-k-r-standup-steady-moonbeam.md`.
Allt ligger på `development` (pushat, `ed31791`), migration 107 körd i development. **Main är orörd.**

## Till Sebbe: det här rör filer du också arbetar i

- `components/leads/LeadsTabell.tsx`: kolumnen **Utkast** (utkastets riktiga status), verktygsraden
  (Skicka utkast, Skapa utkast, Skapa om utkast, Arkivera/Återställ, Ta bort, Flytta till main), vyerna
  Bortvalda/Arkiverade, och **kolumnen Typ är borttagen** (tabellen rullade i sidled vid 1440 med Utkast;
  typfiltret finns kvar). Iris-listan visar bara leads före utskick; kontaktade bor i Inkorg › Skickat.
- `components/leads/LeadsSida.tsx`: nytt segment **Samtal** (`?vy=samtal`); Inkorg har flikarna
  Inkommande/Skickat (`?vy=inkorg&flik=skickat`).
- `snajp-support/app/leads/discovery.py`, `sources/merinfo.py`, `sidhamtning.py`, `platshallare.py`:
  kontaktsökningen är omskriven (se nedan). `lage="lista"` behåller sitt VD-krav.
- Regel 10:s "aldrig privat adress/främmande domän" gäller inte längre en adress bolaget självt publicerar
  på sin sajt (Antons regel 13). Se CLAUDE.md, regel 12–17.

## Vad som är byggt

| Del | Var |
|---|---|
| Översikt = Aktivitet, Admin-översikt | `components/dashboard/StartView.tsx`, `AdminShell.tsx` |
| En sanning per lead om utkastet (`utkast_status`) | `app/leads/utkaststatus.py`, `GET /leads/prospects` |
| Väntande utkast = senaste icke-kasserade, avvisade kasseras | migration 107, `storage.get_pending_outreach_message`, `cancel_pending_sends` |
| Massåtgärder | `app/api/leads_massatgard.py` (arkivera, radera), `processa-om` med `ersatt` |
| Skickat flyttar ut, svar flyttar mellan filtren | `IrisInkorg.tsx`, `SkickatLista.tsx` |
| Bevakning: uppföljningar som utkast till granskning | `scheduler.run_godkand_sandare` (var 10:e min, spegelvakt) |
| 90-dagarsspärren räknar inte leadets egen tråd | `send_guard`, `last_contact_with_company(utom_trad=)` |
| Kontaktsökningen | `discovery.kontakt_ur_sidor`, `platshallare.kontaktrader_ur_html` |
| Fördelning Iris / ringlista / ej kvalificerade / prövas om | `sources/merinfo.fordela`, `api/leads._spara_listspar` |
| Ringlista och återkoppling (Leads › Samtal) | `app/leads/samtal.py`, `components/leads/Samtalslista.tsx` |
| Ta bort lista, kopiera/flytta lista till annan kund (admin) | `DELETE /leads/listor/{id}`, `app/api/admin_listor.py` |

## Mätt i development 2026-10-07

26 av Snajps utkast godkändes 16:41–22:05, efter sändfönstret (08–16), och skickas av
`run_godkand_sandare` nästa vardag 08:00. Inget mejl hade gått ut på 28 dygn — därför stod Skickade 0.
`scripts/utkast_status.py --env development` visar läget när som helst (bara antal).

## Kvar

- **Anton:** se `omklassa_listspar.py`-torrkörningens siffror och säg ja till `--apply` (skapar Iris- och
  ringprospekt ur de gamla listraderna, raderar ingenting, märker raderna). Därefter Skapa utkast på de nya
  Iris-leadsen i appen.
- **Anton:** release till main (migration 096–107) när PR #31 är klar.
- Skarp körning N=5 i development för att se fördelningen i körningsraden.
