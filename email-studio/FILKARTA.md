# Filkarta — var koden lever

Alla filer nedan finns **live** i `C:\Users\sebbe\snipe-leads\`.  
Kopior (säkerhetskopia) finns under `email-studio/kopior/` med samma struktur.

## Email Studio — kärna

| Fil | Roll |
|-----|------|
| `app/emails/page.tsx` | Sidan `/emails`, laddar data |
| `components/email/EmailStudioEditor.tsx` | UI, knappar, POST till API |
| `app/api/email-studio/route.ts` | **Huvud-API** — LLM + simulation |
| `lib/actions/emails.ts` | Server action `refineEmail` (legacy) |
| `lib/data/emails.ts` | Supabase-loader + mock-fallback |

## Agent / LLM

| Fil | Roll |
|-----|------|
| `lib/agent/llm.ts` | DeepSeek / OpenAI-anrop |
| `lib/agent/marketing-skills.ts` | Läser alla skills från disk |
| `lib/agent/email-studio-prompt.ts` | System/user-prompt |
| `lib/agent/snipra-tone.ts` | Svensk B2B-ton |
| `lib/agent/skills-corpus.json` | Bundlad skills (via `npm run bundle:skills`) |

## Supabase Edge (hosted, ej lokal dev)

| Fil | Roll |
|-----|------|
| `supabase/functions/refine-email/index.ts` | Edge Function |
| `supabase/functions/_shared/prompts/email-studio.ts` | Delade prompts |
| `supabase/functions/_shared/llm.ts` | Delad LLM-klient |

## Auth (krävs för inloggad /emails)

| Fil | Roll |
|-----|------|
| `middleware.ts` | Route-skydd |
| `lib/supabase/client.ts` | Browser-klient |
| `lib/supabase/server.ts` | Server cookies |
| `lib/supabase/admin.ts` | Service role |
| `lib/auth.ts` | Session helpers |
| `lib/workspace.ts` | Workspace-kontext |
| `lib/actions/auth.ts` | Login/signup |
| `lib/actions/onboarding.ts` | Onboarding save |
| `components/auth/LoginForm.tsx` | Login-UI |
| `components/auth/OnboardingForm.tsx` | Onboarding-UI |
| `components/auth/useUser.ts` | Client hook |
| `supabase/migrations/001_handle_new_user.sql` | Signup trigger |

## Referenser & scripts

| Fil | Roll |
|-----|------|
| `references/marketingskills-main/skills/` | 44 marketing skills |
| `scripts/bundle-marketing-skills.mjs` | Bundlar skills till JSON |
| `.agents/product-marketing.md` | Produktkontext |
| `Snipra prompt.txt` | Tonalitetsregler |

## Dokumentation

| Fil | Roll |
|-----|------|
| `plans/2026-06-10-email-studio-agent.md` | Arkitekturplan |
| `session-logs/2026-06-10-session-log.md` | Sessionlogg |
| `STATUS.md` | Projektstatus (sektion 2026-06-10) |
| `email-studio/` | **Detta paket** |