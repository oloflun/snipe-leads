# Privilegierade verktyg och skript

Datum: 2026-11-18. Skrivet av Claude (agent) på Antons uppdrag. Status: förteckning
över det som finns, med ett **förslag** på vem som får köra vad. Förslaget är inte
beslutat. Underlag för ISO 27001 A.8.18 (och A.8.2, A.5.15–A.5.18).

Ett verktyg räknas som privilegierat när det kan gå förbi appens egna spärrar: läsa
eller skriva alla kunders data utan RLS, ändra driftens konfiguration, eller ändra
källkod och CI utan granskning.

## 1. Åtkomstvägarna

| Väg | Vad den når | Var nyckeln finns | Vem som har den i dag |
|---|---|---|---|
| Ägarrollen `postgres` i Railway-Postgres (main och development) | Allt i databasen, förbi RLS. Publik TCP-proxy är påslagen i båda miljöerna (`drift-och-tillgangar.md` §1) | `.env.deploy` (`RAILWAY_<MILJÖ>_PG_*`, gitignorerad) på ägarens dator; repo-hemligheterna `RAILWAY_<MILJÖ>_PG_{PASSWORD,HOST,PORT}` och `ENV_DEPLOY` i GitHub Actions | Anton (dator), CI-jobben `migrera` och `synk`. Övriga: **inte belagt** |
| Railway-API och `railway`-CLI | Variabler (också hemligheternas värden), deploy-triggrar, domäner, volymer, TCP-proxy för hela projektet `brave-passion` | `~/.railway/config.json` (CLI-inloggningen), `RAILWAY_TOKEN` i `.env.deploy` | Anton. Vilka fler som är medlemmar i Railway-projektet: **inte belagt** |
| GitHub (`gh`, webben) | Källkod, Actions-hemligheter, arbetsflöden, ärenden. Grenskyddet på `main` gäller inte på gratisplanen (`drift-och-tillgangar.md` §3) | Personliga konton | `oloflun` (admin), `bergmansebastian2002` (write) (`bevis/github-2026-11-18.txt`) |
| Master-nyckeln (`SNAJP_MASTER_API_KEY`) | Backendens `/api/admin/*` och `/api/keys`: alla kunders administration. Loggas i `audit_logs` (INV-SEC-013) | Railway-variabel på `web` och `api`; `.env.deploy` | Webbens adminyta (plattformsadmin), skripten nedan |
| Kundnycklar (`SNAJP_KEY_<SLUG>`) | En kunds data i backenden | Railway-variabler på `web`; `.env.deploy` | Webben, skripten nedan |
| Plattformsadmin i appen | `/admin` och kundbesök i alla arbetsytor | Rad i `platform_admins` | Se tabellen själv; tilldelas bara med ägarrollen (`AUTH.md`) |
| Loopia-API | DNS för `snajp.se` | `.env.deploy` | Anton |
| Resend-API | Avsändardomäner och utskick | Railway-variabel `RESEND_API_KEY`; `.env.deploy` | Webben, api, skripten nedan |
| Google Cloud (Vertex) | Modellanropen, tjänstekontots nycklar | `GOOGLE_SERVICE_ACCOUNT_JSON` i Railway | Driften. Vem som är ägare i GCP-projektet: **inte belagt** |

AI-kodverktyg (Claude Code, Codex m.fl.) som körs på ägarens dator använder samma
nycklar som ägaren: `.env.deploy`, CLI-inloggningarna och `gh`. De är alltså inte en
egen åtkomstväg utan en användare av ägarens. Projektets regler (`CLAUDE.md`)
förbjuder dem att skriva till Supabase, skriva ut hemligheter och pusha till `main`,
men det är regler, inte tekniska spärrar.

## 2. Skripten i `scripts/`, efter vad de når

Urvalet är gjort med sökning efter anslutningar och nycklar i varje fil (2026-11-18).
"Skriver" betyder att skriptet kan ändra något utanför den egna datorn.

| Grupp | Skript | Når | Skyddsräcke |
|---|---|---|---|
| **Databas, alla kunder, skriver** | `railway_migrate.py`, `railway_synk.py`, `railway_synk_anslut.py`, `gallra.py`, `gdpr_radera.py` (`--radera`, `--begransa`, `--hav-begransning`), `admin_cleanup.py`, `radera_prospekt.py`, `rensa_exempelbolag.py`, `railway_seed_dev.py`, `railway_drift.py`, `set_railway_postgres_url.py`, `flytta_korningar_till_main.py`, `flytta_redo_till_ny.py`, `omklassa_listspar.py`, `omrakna_rangpoang.py`, `aterstall_bedomning.py`, `fyll_embeddings.py`, `fyll_kundregister.py`, `koade_utkast_till_granskning.py`, `demolank_i_utkorgen.py`, `lagg_pa_utskicksfot.py`, `konvertera_testkund.py`, `koppla_testytor.py`, `los_sandsparr.py`, `omskriv_utkast.py`, `skapa_qa_kund.py`, `skapa_livrustning_konto.py`, `skapa_snajp_intern_kund.py`, `railway_env_bootstrap.py`, `railway_provision.py` | Ägarrollen mot vald miljö | De flesta kräver `--apply` och har torrkörning; `gdpr_radera.py --radera` kräver att adressen skrivs igen; `gdpr_verktyg.dsn_for` vägrar den gamla Supabase-stacken mot fjärrvärd |
| **Databas, alla kunder, läser** | `gdpr_radera.py` (sök, `--export`), `utkast_status.py`, `granska_utkast.py`, `kor_evals.py`, `mat_modellbyte.py`, `verifiera_instruktioner.py`, `publish_skills.py`, `railway_link_admin_workspace.py`, `run_live_tests.py`, `verify_railway.py`, `keys.py`, `qa_radera_konto.py` | Ägarrollen | Inget utöver att nyckeln finns lokalt |
| **Railway-konfiguration, skriver** | `railway_provision.py`, `api_key_setup.py`, `web_mailvag.py`, `railway_env_bootstrap.py`, `railway_gor_klart.py`, `railway_llm_provider.py`, `railway_repair_llm_key.py`, `railway_tenantnyckel.py`, `railway_tenant_keys.py`, `railway_agentsajt.py`, `railway_doman.py`, `railway_verifiera_doman.py`, `migrera_till_railway.py`, `set_railway_token.py`, `llm_provider.py`, `gemini_web_konfig.py`, `integration_nyckel.py`, `flytt_nycklar.py` | Railway-API | Flera kräver `--apply`. Ingen ändring loggas hos Railway; `railway_baslinje.py --jamfor` visar avvikelser i efterhand (A.8.9) |
| **Railway, läser** | `railway.py`, `railway_baslinje.py`, `railway_region.py`, `verify_railway.py` | Railway-API | `railway_baslinje.py` vägrar mutationer och skriver aldrig hemliga värden |
| **Backendens API med master- eller kundnyckel** | `onboard_tenant.py`, `snajp_malgrupp.py`, `satt_mejlsignatur.py`, `badda_in_kb.py`, `livrustning_kb_synk.py`, `livrustning_produktkontext.py`, `pilot_kb_utkast.py`, `ombedom_leads.py`, `granska_leads_underlag.py`, `las_agentinstruktioner.py`, `lasttest.py`, `seed_demo.py` | Backenden i vald miljö | Master-anropen loggas i `audit_logs` |
| **DNS och e-post** | `loopia_dns.py`, `loopia_nycklar.py`, `resend_doman.py`, `smtp_konfig.py`, `railway_verifiera_doman.py` | Loopia, Resend | `--apply` |
| **Redis** | `redis_konfig.py`, `redis_kontroll.py`, `redis_provisionera.py`, `redis_cloud_nycklar.py`, `redis_tls_pa.py` (inaktuellt, får inte köras: `INCIDENT_RESPONSE.md`) | Redis Cloud (avvecklad) och Railway-Redis | – |
| **GitHub** | `overvakning_dodman.sh`, `sakerhetsbevakning.py` | Ärenden i repot | Körs bara i Actions med den inbyggda tokenen |

Lokala skript som bara rör en lokal databas (`lokal_stack.py`) och skript utan
nätverk räknas inte hit.

## 3. Förslag: vem som får köra vad

**Obeslutat.** Anton väljer; tabellen är agentens utgångspunkt.

| Grupp | Förslag |
|---|---|
| Databas, skriver, mot `main` | Bara Anton, eller en agent på Antons uttryckliga ord i samma session. Migrationer bara via `migrera.yml` |
| Databas, skriver, mot `development` | Anton och Sebbe; agenter när uppgiften kräver det. Development är en spegel med riktig kunddata och behandlas som produktionen (`CLAUDE.md`) |
| Databas, läser | Anton och Sebbe; agenter för felsökning, utan att skriva ut kunddata |
| Railway-konfiguration, skriver | Bara Anton, eller en agent på hans uttryckliga ord. `railway_baslinje.py --jamfor` före och `--skriv` efter varje avsiktlig ändring |
| Rättighetsskriptet (`gdpr_radera.py`) | Den som handlägger begäran enligt rutinen (Anton), med begäran dokumenterad |
| GitHub admin | Anton |
| Plattformsadmin i appen | De som står i `platform_admins`; listan ses över av Anton |

## 4. Det som återstår, och är Antons

- Besluta förslaget i avsnitt 3.
- Belägga vilka personer som är medlemmar i Railway-projektet och i Google Cloud-projektet,
  och vilka som har en `.env.deploy` med ägarrollens lösenord.
- Stänga Postgres publika TCP-proxy (A.8.20), så att ägarrollen bara nås från Railways
  privata nät och CI.
- Byta ägarrollen mot en smalare roll för skripten som bara läser.
