# Handoff till Sebbe, 2026-09-19

Anton gick igenom produktionen efter PR #20/#21 och bad om fyra saker. Allt nedan
ligger på `development` i den här pushen. Inget har gått till `main`.

## 1. Iris ersätter Leads, Leadslistor och Email studio

- Menyn har en post, **Iris**, med underflikarna **Bolag** (`/dashboard/iris`),
  **Granskning** (`/dashboard/iris/granskning`) och **Inställningar**
  (`/dashboard/iris/installningar`). Samma sak under `/admin/iris/...` och
  `/demo/iris/...`. I demon ligger CRM-listan som fjärde underflik.
- Leadslistor är ett filter på Bolag-sidan (`?vy=listor`), inte en egen flik.
  Tilläggsgrinden för `leadlists` sitter kvar.
- Email studio har ingen egen sida längre. Den öppnas bara i detaljpanelen när
  man klickar på ett bolag som har ett utkast. En editor per öppnat bolag hålls
  monterad, samma mönster som CrmDemo.
- Listraderna har kortformatet från den gamla rutan "3 exempelbolag inlagda".
  Rutan är borta. Exempelkörningen lägger bolagen överst i listan, märkta
  EXEMPEL.
- Demolistan går att klicka i. Detaljpanelen ersätter länken till
  `/dashboard/companies/<id>`, som låg bakom inloggning.
- Gamla adresser redirectar: `/dashboard/leads(/listor|/kontroll)` och
  `/dashboard/emails` till motsvarande Iris-adress, likaså i `/demo`.
- Nya filer: `components/leads/IrisBolag.tsx`, `IrisGranskning.tsx`,
  `IrisInstallningar.tsx`, `IrisEskalering.tsx`, `lib/iris.ts` (portad ur
  `leads-webb/lib/iris.ts`). Borttagen: `components/leads/Discovery.tsx`.
- Inte portat från den gamla Bolagsregister-tabellen: massåtgärderna (flytta
  test/skarp, skapa utkast för valda, processa om). Tabellen finns kvar bakom
  den dolda `/dashboard/companies`.

## 2. Utkasten i demon

Texten Anton reagerade på skrevs aldrig av en modell. `simulateAction()` i
`app/api/email-studio/route.ts` byggde allt med mallar: signalen saknades i
anropet och föll tillbaka på "det som händer hos er just nu", rollen
"Inköpschef" användes som namn, och knapparna gav nästan samma text.

- `simulateAction()` är borttagen.
- **Inloggade får aldrig simulerad text.** Fallerar modellen svarar routen med
  ett ärligt fel (503/429/502) i samma ton som `kvotfel.py`.
- Demon använder handskrivna svar per exempelbolag och knapp ur
  `lib/demo/iris-exempel.ts`.
- `lib/agent/halsning.ts` hälsar med förnamn bara när värdet ser ut som ett namn.

**Öppen fråga, Antons regel:** "Använd aldrig en färdig mall som utkast, någonsin,
det ska alltid genereras." De handskrivna demosvaren är i praktiken färdiga
mallar. CrmDemo:s `startutkast()` är det också, och den hälsar dessutom på roller
och gemenar bolagsnamnet. Att generera på riktigt för anonyma demobesökare krockar
med INV-SEC-010 (kostnad och nyckel). CRM-listan är dessutom besökarens riktiga
kunddata, vilket gör det till en dataskyddsfråga. Anton avgör. Rör inte demovägen
förrän han har gjort det.

## 3. Admin och vänsterrailen

- Railet är utbrutet till `components/shell/Rail.tsx` och används av både
  `AppShell` och `AdminShell`. Admin har inget flikfält överst längre.
- Railet klarar underflikar (`children` på en nav-post, och på `AppRoute` i
  `lib/routes.ts`).
- 404:an Anton fick på `/admin/handelser` kommer från grinden i
  `app/admin/layout.tsx`. `getPlatformAdmin()` gav null, troligen på grund av en
  utgången session. Loggarna från tillfället är borta. Förslag, inte gjort:
  redirecta till `/login` när sessionen saknas och behåll 404 bara för den som är
  inloggad men inte admin.

## 4. Agentsajterna

- `bokforing-webb/` och `leads-webb/` är borttagna ur repot. Huvudappen hade redan
  allt de innehöll.
- `scripts/railway_bokforing.py` är borttaget.
- Registret `lib/agentsajt.ts` har bara `support` kvar.
- På `web` i båda miljöerna är `BOKFORING_EXTERN_URL`, `BOKFORING_SSO_SECRET`
  och `LEADS_EXTERN_URL` borttagna.
- Railway-tjänsterna `bokforing`, `leads` och dubbletten `bokforing-4f55535c-…`
  i main är **inte** raderade än. Det gör Anton.
- **`support-webb/` står kvar orörd**, med dina commits från i natt
  (Integrationer-vyn med mera). Anton ville vika in alla tre, men du bygger
  aktivt i portalen. Ni två avgör om den ska in i huvudappen. SSO-bryggan för
  support fungerar som förut.

## 5. RLS: NULLIF-vakten

`scripts/lokal_stack.py --apply` från noll stannade på sin egen kontroll: sex
tenant-policyer från 051, 052, 059, 060 och 061 saknade 028:s
`NULLIF(current_setting('app.tenant_id', true), '')`. Dina 066 och 067 lade till
fem till (`ss_chat_state`, `ss_integrations`, `ss_channel_*`).

- **Ny migration `20260919100000_068_rls_nullif_vakt.sql`** skriver om alla elva
  med vakten. Den är idempotent, och dina fem är villkorade på att tabellen finns.
  Körd mot Railway `development`: 0 oskyddade policyer kvar. **Inte körd mot
  `main`.**
- **Nytt test `tests/test_rls_nullif_vakt.py`** fäller varje migration efter 028
  som skriver `current_setting('app.tenant_id', ...)` utan `nullif(`. Skriv nya
  policyer med vakten så slipper du det.
- I liggaren i `development` finns en rad `20260919100000_066_rls_nullif_vakt`.
  Det var samma fil innan den döptes om till 068 för att inte krocka med din 066.
  Raden är ofarlig.

## 6. Kontrast (WCAG AA)

De dämpade textstegen (`text-ink/45`, `ink/55`, `paper/35`, `text-mineral`)
föll på AA. axe mätte 66 noder på produktionens `/demo/leads`. De är ersatta
med namngivna tokens per bakgrund, och DESIGN.md beskriver dem. Använd tokens,
inte opacitetsklasser, för sekundär text.

## Verifierat

- `npx tsc --noEmit` ren.
- `npm test` passerar.
- `npm run build` går igenom.
- `pytest` i snajp-support passerar.
- Iris är granskad i skärmbilder på 1440 och 375 px: ingen horisontell scroll,
  inga konsolfel.
- Admin i det nya railet är **inte** granskad renderad, eftersom den kräver
  inloggning. Gör gärna en snabb runda.

## Lokalt

`scripts/lokal_stack.py` går nu hela vägen igen, med Postgres via Docker
(`pgvector/pgvector:pg16`, lösenord `localdev`, port 5432). Om `rlwy.net`
blockeras av NextDNS kan `railway_migrate.py` köras med `PGHOSTADDR=<ip>`.
