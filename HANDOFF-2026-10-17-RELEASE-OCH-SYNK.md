# Handoff 2026-10-17: release till main och synken

## Läget just nu, verifierat
- **git:** `development` på `02d63e2`, pushad. `main` på `5c41630` (PR oloflun/snipe-leads#31 mergad av Anton 10:11 UTC). Sebbes sex commits (`1b32cbb`–`f04134f`) följde med i releasen.
- **Railway:** api i development kör `cf7b9c4` (envags-reglerna), api i main kör `5c41630`. Main och development ligger på migration 111.
- **Volymer:** Postgres-volymerna i båda miljöerna är 5000 MB (de var 500 MB). Development kraschade 10:31 av full disk och återhämtade sig utan dataförlust (redeploy via GraphQL `serviceInstanceRedeploy`).
- **Synken:** första synken är gjord (11:08 och 11:30 UTC). `mirror_meta.lage = 'envags'` i development. Main och development har lika antal: 2788 körningar, 868 prospekt och 189 köade utkast (ej test). GitHub-jobbet `synk.yml` kördes för hand 11:33 och var grönt med 0 överhoppade rader.
- **Utskick:** de 189 köade utkasten har `godkand_i = 'main'` och skickas av main när sändfönstret öppnar måndag 08:00. Development skickar inget.

## Vad som byggdes
1. **CI-rättning** (`7285ff5`): `test_inv_data_003` laddade `railway_synk.py`, som importerar psycopg2, och CI har bara asyncpg. Testet stubbar nu modulen.
2. **Migrationer 103–111 mot main**: torrkörda och sedan körda på Antons order.
3. **Ny synkmodell** (`cf7b9c4`), på Antons beställning: första synken för över allt från development, därefter är main sanningen. `railway_synk.planera`: main vinner varje skillnad, raderingar i main slår igenom, och rader som bara finns i development står kvar tills de flyttas (Byt kund → Flytta till main, `admin_flytt`). `scheduler.utskick_bara_i_main` gör att development aldrig skickar, och "Godkänn och skicka" i development hänvisar till main. Första synken skrev om `godkand_i` från development till main (366 rader). Beslutet står i `docs/BESLUT.md`.
4. **Synkens skalning** (`02d63e2`): planeringen jämför bara nycklar och md5, och raderna hämtas 100 åt gången. Genererade kolumner (`prospects.foretagsnyckel`) skrivs inte.
5. **Verifiering:** backendsviten (3359 grönt; `test_loopvakt` är tidskänslig och går grönt ensam), `tests/test_railway_synk.py`, och räkning av rader och föräldralösa rader i båda databaserna.

## Vad som återstår, i prioritetsordning
1. **Anton:** godkänn eller ändra regeln att development inte skickar något. Den ersätter beslutet 2026-10-10 om utskick från development. Står i BESLUT.md som agentens tolkning.
2. **Agent:** följ upp nästa schemalagda körning av `synk.yml`. Den ska gå grönt med 0 överhoppade rader.
3. **Anton:** säg till när säkerhetskopiorna kan raderas. Det är schemana `synk_kopia_202610171108` och `synk_kopia_202610171130` i båda databaserna. Agenten raderar inget utan ditt ja.
4. **Agent:** när development-only-körningar flyttas med Flytta till main följer prospekt och körning med, men inte trådar, utkast eller köposter. Utkasten måste skapas om i main. Avgör med Anton om flytten ska bära dem.
5. **Anton:** 3 mejl fanns i båda miljöerna under olika id (samma `provider_message_id`). Main behåller sina, development sina. Ingen åtgärd behövs om det duger.
6. **Från tidigare sessioner, oförändrat:** granskningskön, `LEADS_DAILY_TOKEN_BUDGET` i development och dataskyddsfrågan om språkmodell-leverantören.

## Fällor
- **Railway-volymer skapade på provplanen stannar på 500 MB** även på Hobby-planen. Växa går via GraphQL `environmentPatchCommit` med `{"volumes": {<volumeId>: {"sizeMB": 5000}}}`. Kontrollera sedan att filsystemet faktiskt vuxit, med `copy df from program 'df -m …'`. Railways mätare `currentSizeMB` släpar efter.
- **Synkens backup** (`create table as`) dubblerar tabellerna i samma databas. Kontrollera ledigt utrymme först.
- **`--forsta` vägrar när `lage = 'envags'`.** För att köra om måste `mirror_meta.lage` nollställas, och då vinner development igen.
- **Lokalt minne:** läs aldrig in alla `agent_runs` med spår på en gång.

## Antons instruktioner ordagrant
- "Kör /standup och förbered för push till main. se till att ALLA körningar följer med, enligt de senaste instruktionerna, ENDAST körningar märkta testkörningar följer inte med."
- "Permissions är lyfta, kör migrationerna"
- "Updatera PR:en med Sebbes ändringar"
- "Kör synken nu"
- "Lös det, gör vad som krävs, datan måste speglas sömlöst, OBS: när vi fått över alla körningar från development blir main sanningen och synkar till development och körningar gjorda i development behöver flyttas aktivt enligt tidigare principer."
