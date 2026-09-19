# Chattwidgeten — inbäddad support på kundens egen sajt

Byggd för Livrustning-piloten (2026-09-19) som en generell per-tenant-widget,
inte en engångslösning. Kundens besökare chattar med supportagenten direkt på
kundens webbplats, i en panel som bär kundens logotyp och accentfärg.

## Vad kunden klistrar in

```html
<script src="https://<vår domän>/widget.js"
        data-nyckel="pk_<kund>_…" async></script>
```

En rad, före `</body>`. Ingenting annat. Livrustnings nyckel står i
`lib/tenants/livrustning.ts` (`publicKey`).

## Arkitekturen i fyra meningar

1. **`public/widget.js`** ritar knappen och panelen och laddar en iframe mot
   `/embed/<publik nyckel>` — ren DOM, inga beroenden, allt i en IIFE som
   aldrig kan fälla kundens sida.
2. **`app/embed/[nyckel]/page.tsx`** löser nyckeln mot registret
   (`lib/tenants`), sätter kundens palett och renderar `SupportChat` i
   fyll-layout — samma chatt, samma anonyma API, som `/chat/<slug>`.
3. **`proxy.ts`** sätter `Content-Security-Policy: frame-ancestors` per nyckel
   ur tenantens `embedOrigins` — webbläsaren vägrar rendera iframen på en
   domän som inte står i listan.
4. Chatten går same-origin inuti iframen till `/api/snajp-support/chat` —
   **ingen CORS behövs**, och ingen hemlig nyckel finns i klientkod.

## Säkerhetsmodellen

| Fråga | Svar |
|---|---|
| Är nyckeln hemlig? | Nej — den är en adressbokspost, samma exponering som sluggen i `/chat/<slug>`. Slumpad så att `/embed` inte går att räkna upp. |
| Vad händer om nyckeln läcker? | Ingenting utöver det publika: `frame-ancestors` stoppar rendering på främmande domäner, och direktöppning visar bara den publika chatten. |
| Rate limits? | Samma som chatten: IP-tak (migration 019), tenant-timtak (400 LLM-anrop/h) och supportens dygnsbudget (`app/budget.py`). |
| Avtalsgrinden? | `kraver_avtal` utan registrerat avtal ⇒ chatten svarar med den vänliga spärrtexten (migration 070, `app/avtalsgrind.py`). |

## Graciös degradering

- Backend nere ⇒ chatten visar sin offline-mening; kundens sida påverkas inte.
- Iframen laddar inte alls ⇒ panelen visar en vänlig felruta (`widget.js`).
- Rate limit/budget nådd ⇒ backendens egna svenska 429-text visas i chatten.
- `widget.js` felar ⇒ ingenting händer på kundens sida — allt är fångat.

## Lägga till widget för en ny kund

1. Sätt `publicKey` (slumpad, `pk_<slug>_<24 hex>`) och `embedOrigins`
   (fullständiga origins med schema) i kundens `lib/tenants/<slug>.ts`.
2. Verifiera: öppna `/widget-test.html` (testsidan bäddar in via 'self'),
   och kontrollera att `/embed/<nyckel>` svarar med rätt
   `Content-Security-Policy`-huvud.
3. Skicka snippet-raden till kunden.

Testerna bor i `lib/tenants/widget.test.ts` (`npm test`).
