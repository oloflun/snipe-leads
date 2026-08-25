/**
 * Demons sektioner. Två listor, för att de svarar på olika frågor.
 *
 * Listan bodde i `app/demo/[[...slug]]/page.tsx` och ritades av sidan själv, i
 * ett eget band OVANFÖR arbetsytans header. AppShell undertryckte samtidigt sin
 * egen flikrad på demoytan för att de två annars staplades på varandra.
 *
 * Följden var att /demo hade en helt annan chrome än /dashboard: tre rader
 * (band, flikar, header) mot arbetsytans en. Nu matar `DEMO_NAV` AppShells
 * ORDINARIE nav-plats, så demon får samma header som den riktiga arbetsytan.
 *
 * ## Varför nav-listan är kortare än sektionslistan
 *
 * `/dashboard` visar INTE alla vyer. Fem av posterna i `lib/routes.ts` bär
 * `preview: true` — Företag, Kontakter, Svar, Analys, Assistant — och
 * `routesForProducts` filtrerar bort dem om inte anroparen ber om dem.
 * Arbetsytan visar alltså fem flikar, inte tolv.
 *
 * Demon ritade tolv. Den exponerade därmed sektioner som den riktiga
 * arbetsytan medvetet döljer, och raden blev så bred att kontrollerna föll ner
 * på en andra rad — vilket var hela anledningen till att den inte såg ut som
 * /dashboard.
 *
 * `DEMO_NAV` speglar därför arbetsytans icke-preview-uppsättning, i samma
 * ordning. Vyerna finns kvar och svarar på sina adresser (sidan har en `switch`
 * som är sanningen om vad som är giltigt) — de annonseras bara inte i headern,
 * precis som på /dashboard.
 *
 * "Inställningar" står inte med: den har ingen demomotsvarighet och pekade
 * förut på /settings, alltså den riktiga appen bakom inloggning. En besökare
 * utan konto möttes av inloggningssidan från en yta vars hela löfte är "ingen
 * inloggning".
 */
export const DEMO_NAV = [
  ["", "Översikt"],
  ["leads", "Leads"],
  ["support", "Kundtjänst"],
  ["emails", "Email studio"],
  ["bokforing", "Bokföring"]
] as const;

/** Länken till en sektion. Tom sträng = demons startsida. */
export function demoSektionsVag(vag: string): string {
  return `/demo${vag ? `/${vag}` : ""}`;
}
