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
 * `/dashboard` visar INTE alla vyer. Flera poster i `lib/routes.ts` bär
 * `preview: true` — Företag, Kontakter, Svar, Analys, Assistant — och
 * `routesForProducts` filtrerar bort dem om inte anroparen ber om dem.
 *
 * Demon speglar därför arbetsytans icke-preview-uppsättning, i samma ordning.
 * Vyerna finns kvar och svarar på sina adresser (sidan har en `switch` som är
 * sanningen om vad som är giltigt) — de annonseras bara inte i headern,
 * precis som på /dashboard.
 *
 * Snajp Suite (2026-10-03): samma platta meny som arbetsytan. Aktivitet
 * finns sedan 2026-10-07 med exempelkörningar (lib/demo/aktivitet.ts), och
 * Inställningar visar bara Iris del, den enda som är demobar (arbetsytans
 * /settings kräver inloggning).
 * CRM-listan (/demo/crm) står inte längre i menyn: kundens egen lista in är
 * i dag Leads › Listor › Importera CSV. Routen svarar fortfarande.
 */

import type { Localized } from "@/lib/i18n";

export type DemoNavChild = { slug: string; label: Localized };

export type DemoNavItem = { slug: string; label: Localized; children?: DemoNavChild[] };

export const DEMO_NAV: DemoNavItem[] = [
  { slug: "", label: { sv: "Översikt", en: "Overview" } },
  { slug: "att-gora", label: { sv: "Att göra", en: "To do" } },
  { slug: "leads", label: { sv: "Leads", en: "Leads" } },
  { slug: "support", label: { sv: "Kundtjänst", en: "Customer service" } },
  { slug: "kvitton", label: { sv: "Kvitton", en: "Receipts" } },
  { slug: "installningar", label: { sv: "Inställningar", en: "Settings" } }
];

/** Länken till en sektion. Tom sträng = demons startsida. */
export function demoSektionsVag(vag: string): string {
  return `/demo${vag ? `/${vag}` : ""}`;
}
