# Kundsajter (multi-tenant)

**Snajp bygger inte om kundens hemsida.** Kunden behåller sin egen sajt. Det vi
levererar är supportchatten, dit besökaren kommer via en länk därifrån eller i
ett mejl. En kund = en configfil plus rader i databasen — ingen kopierad kodbas,
inget separat repo.

Juridisk text (villkor, garanti, ångerrätt) läggs **aldrig** som sidor hos oss.
Den hör hemma på kundens egen sajt och i agentens kunskapsbas. Två kopior av
samma villkor hamnar förr eller senare ur synk, och då är vår kopia den felaktiga.

## Vad kunden får

```
https://<slug>.<domän>/            → skickar vidare till chatten
https://<slug>.<domän>/chat/<slug> → den statiska länk kunden publicerar
                                     ↓ varje besök
                                   /chat/<slug>/<uuid>  — egen session, noindex
```

Allt annat på kundens domän ger 404: Snajps produktsidor, designutkast och
marknadsföring ska aldrig synas där.

---

## Rutin: lägg upp en ny kund

### 1. Samla in från kundens sajt

Gå igenom **varje** sida, inte bara startsidan. Hämta länklistan först:

```javascript
[...document.querySelectorAll('a[href]')].map(a => a.href).filter(h => h.includes('KUNDDOMÄN'))
```

Läs sedan varje sida och fånga allt: tjänster, priser, policyer (kvalitet, miljö,
integritet), certifieringar, standarder, medlemskap, garantier, kontaktuppgifter.
Policysidor ligger ofta bara i sidfoten och innehåller uppgifter kunden själv
glömmer nämna.

**Notera avvikelser mellan sajten och det kunden berättat.** Hos Livrustning stod
8 års garanti på sajten och 1 år i det underlag vi fick — två olika saker som
gäller i olika situationer. Sådant måste redas ut, inte jämkas ihop.

### 2. Kunskapsbas

`snajp-support/app/tenants/<slug>_kb.py`, registrerad i `TENANTS` i
`snajp-support/app/tenants/__init__.py`.

- Skriv artiklarna som svar på faktiska kundfrågor, inte som kopierad webbtext.
- **Kategorierna måste matcha `ss_knowledge_base_category_check` i databasen.**
  Kontrollera först, den har avvikit från migrationerna i repot:
  ```sql
  select pg_get_constraintdef(oid) from pg_constraint
  where conname = 'ss_knowledge_base_category_check';
  ```
  Håll `CATEGORIES` i `app/config.py` synkad med samma lista, annars klassificerar
  agenten ärenden som databasen sedan vägrar spara.
- **Motstridiga eller obekräftade uppgifter kodas som eskalering**, inte som ett
  svar. Skriv in i artikeln att agenten ska fråga vad kunden köpt och lämna över
  till en människa. En agent som gissar en garantitid åt kundens räkning är värre
  än en som säger "jag kopplar in en kollega".
- Skilj på garanti (frivilligt åtagande) och reklamationsrätt (lagstadgad). Kunder
  blandar ihop dem, och fel svar där kan kosta kunden pengar.

Seeda: `python -m app.scripts.seed_kb <slug>` (kräver `DATABASE_URL`).

### 3. Logotyp

Ladda ner från kundens sajt till `public/tenants/<slug>/logo.png`.

**Kontrollera alltid logotypen mot båda bakgrunderna innan `background` sätts.**
Livrustnings ordbild är vit på transparent — mot vårt varma papper syns bara
figuren och företagsnamnet försvinner helt. Öppna filen och titta på den; det
syns inte i koden. Sätt `background: "dark"` så hamnar den på mörkt fält.

### 4. Configfil

**Configfilen styr den PUBLIKA chatten, inte kundens inloggade arbetsyta.**
Sedan migration 061 kopplar uppstarten varje ny arbetsyta till en egen
backend-tenant automatiskt (`kund-<8 tecken ur workspace-id>`), och nyckeln
sparas i `workspace_tenant_keys`. Kunden kan alltså logga in och använda
översikt, röstdokument, målgrupp och kunskapsbas utan att någon av oss gör
något — det som tidigare krävde `scripts/onboard_tenant.py` och en deploy per
kund. Se `lib/snajp/provisionering.ts`.

Rutinen nedan gäller fortfarande för kunder som ska ha en egen chattlänk på sin
egen domän med sitt eget varumärke. Den ska inte gissas fram.

`lib/tenants/<slug>.ts`, registrerad i `tenants` i `lib/tenants/index.ts`.
Innehåller logotyp, palett, kontaktuppgifter till sidfoten, kundens hemsida och
agentens startfrågor.

Startfrågorna måste handla om kundens egen verksamhet. Demons frågor om felkoder
i kassan såg trovärdiga ut i koden och blev pinsamma först när sidan renderades.

Paletten behöver inte matcha kundens grafiska profil — chatten bär Snajps
formspråk med kundens logotyp. Accenten ska däremot inte kunna förväxlas med
`--danger` (fel) eller `--moss` (bekräftelse).

### 5. Databas

```sql
insert into ss_tenants (slug, name) values ('<slug>', '<Namn AB>');
insert into workspaces (name, slug, ss_tenant_id, products) values (...);
```

Se [007_workspace_tenants.sql](supabase/migrations/007_workspace_tenants.sql).
Fyll även `business_contexts` för workspacet — det är leads-agentens produktdata.

### 6. Nycklar och drift

| Vad | Var | Hur |
|---|---|---|
| API-nyckel | `SNAJP_KEY_<SLUG>` | `POST /api/keys` mot backenden med master-nyckeln |
| IMAP-lösenord | `IMAP_PASSWORD_<SLUG>` | Kundens app-lösenord. **Aldrig i databasen** |
| Inkorg | `ss_mailboxes` | En rad per kund; `imap_host` behövs bara för egen server |
| DNS | Vercel | `<slug>.<domän>` |

### 7. Verifiera innan kunden får länken

Statuskoder räcker inte — rendera och **titta på sidan**:

- `/chat/<slug>` ger unik URL vid varje anrop (ladda om tre gånger).
- Logotypen är läsbar, inte bara närvarande.
- Inget "Snajp" i texten utom "Powered by Snajp".
- `/leads`, `/support`, `/design-drafts/*` ger 404 på kundens domän.
- Snajps egen domän är oförändrad.
- Ställ de fem startfrågorna till agenten och kontrollera att svaren är grundade
  i kunskapsbasen — och att den eskalerar där den ska.

---

## Teknisk not: var tenanten löses upp

I [lib/tenants/server.ts](lib/tenants/server.ts), inte i `proxy.ts`. Proxyns
matcher täcker bara den inloggade ytan, och att bredda den till de publika
sidorna hade kostat ett Supabase-anrop per anonym besökare.

Lokalt fungerar `<slug>.localhost:3005` direkt — moderna webbläsare löser
`*.localhost` utan att hosts-filen rörs.

## Invite-only för kundens interna dashboard

Åtkomst går bara via `workspace_invites`. Triggern `on_auth_user_created` läser
tabellen: finns en obrukad inbjudan för adressen hamnar användaren i det
befintliga workspacet med inbjudans roll, annars får hen ett eget. Ingen
självbetjäningsväg leder in i en kunds workspace. Se [AUTH.md](AUTH.md).
