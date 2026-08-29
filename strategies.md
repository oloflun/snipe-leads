# Strategier — snipe-leads

(Kanonisk slug är `snipe-leads`. Äldre poster från 2026-08-26 ligger i den omdirigerade
hubben `wiki/projects/snipe/strategies.md`.)

## 2026-08-27

### En juridisk paus som hävs av en deploy är inte en paus
- **När:** arbete stoppas av ett icke-tekniskt skäl (juridik, avtal, kunddata) och stoppet
  bara lever som ett konfigvärde eller en README-rad.
- **Gör:** förankra pausen i något en deploy inte kan återställa — en migration, ett saknat
  hemligt värde, en spärr i koden — och skriv i arbetsposten exakt vilka steg som måste vara
  gjorda innan den får hävas.
- **Undvik:** att lita på att "vi kom överens om att pausa". Arbetspost `snipe-a1c` är öppen
  just därför: produktionen kör Gemini igen utan att de dokumenterade åtgärderna gjorts.
- **Evidens:** Dröm 2026-08-27, bundle §4/§8.

### Kvotgränser mäts, gissas inte
- **När:** en extern gratisnivå misstänks strypa produktionen.
- **Gör:** mät den faktiska gränsen innan arbetet planeras om — mätningen gav 6 anrop per
  minut, inte den dygnsspärr som först antogs, vilket gör att en kö löser problemet i
  stället för ett leverantörsbyte.
- **Undvik:** att bygga en migreringsplan på en antagen kvot.
- **Evidens:** Dröm 2026-08-27, arbetspost `snipe-zfn`.
