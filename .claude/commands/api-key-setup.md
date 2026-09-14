---
description: Lägg in en API-nyckel ur .env.deploy på rätt Railway-miljöer, efter att nyckeln mätts mot leverantören
argument-hint: "[GEMINI_API_KEY|OPENAI_API_KEY] [development|main|alla]"
allowed-tools: Bash(python scripts/api_key_setup.py:*), Read, Edit
---

Kör `scripts/api_key_setup.py` för att sätta en API-nyckel som ligger i
`.env.deploy` på Railway-tjänsten `api`.

Argument från användaren: `$ARGUMENTS`
(tomt = `GEMINI_API_KEY` för alla miljöer)

## Gör så här

1. **Torrkör först**, alltid:

   ```bash
   python scripts/api_key_setup.py
   ```

   Saknas raderna i `.env.deploy` skapar skriptet dem tomma
   (`RAILWAY_DEVELOPMENT_GEMINI_API_KEY=`, `RAILWAY_MAIN_GEMINI_API_KEY=`).
   Är de tomma: säg till användaren att klistra in nyckeln där och stanna.
   Fyll aldrig i en nyckel åt användaren och be aldrig om att få se den i
   chatten — den hör hemma i filen, som är gitignorerad.

2. **Läs vad torrkörningen säger.** Skriptet vägrar av två skäl, och båda är
   riktiga fynd att rapportera vidare, inte hinder att kringgå:

   - *fritt tier* — nyckeln fungerar men kvoten räcker inte. En chatt gör
     6 LLM-anrop i snitt (mätt: 5–7, n=8) och fritt tier ger 5/minut.
     Åtgärden är fakturering på Google-projektet som nyckeln tillhör, inte
     en flagga. `--tillat-fri-kvot` finns men ska bara användas om
     användaren uttryckligen ber om det.
   - *delad nyckel mellan miljöer* — `GEMINI_API_KEY` står i
     `PER_ENV_SECRETS` i `scripts/railway_provision.py`: delad nyckel är
     delad kvot, och ett anrop i development kan ge produktionen 429.
     Be om en nyckel per miljö hellre än att sätta `--tillat-delad`.

3. **Skriv först när torrkörningen är ren:**

   ```bash
   python scripts/api_key_setup.py --apply
   ```

   Lägg till `--env development` eller `--env main` om bara en miljö ska
   röras. Att sätta en variabel startar om tjänsten i den miljön — nämn det
   för användaren innan du kör mot `main`.

4. **Verifiera i drift, inte i utskriften.** Efter `--apply`:
   `/health/ready` ska svara `mode: live`, och ett riktigt chattanrop ska nå
   `completed`. En grön mutation bevisar ingenting — det är precis så det här
   projektets tystaste fel har sett ut.

## Regler

- Skriv aldrig ut nyckeln, och läs den aldrig med `cat`. Skriptet visar
  längd och en kort sha256, vilket räcker för att se om två miljöer delar
  nyckel.
- Rör inte `main` utan att användaren sagt det uttryckligen.
- Går något fel: rapportera exakt vad skriptet sa. Kringgå inte en spärr för
  att få kommandot att lyckas.
