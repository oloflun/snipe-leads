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
 * "Inställningar" står inte med som EGEN toppnivåpost: den har ingen
 * demomotsvarighet utanför Iris (arbetsytans /settings ligger bakom
 * inloggning). Iris eget Inställningar-barn är däremot demobart, se nedan.
 */

export type DemoNavChild = { slug: string; label: string };

export type DemoNavItem = { slug: string; label: string; children?: DemoNavChild[] };

export const DEMO_NAV: DemoNavItem[] = [
  { slug: "", label: "Översikt" },
  {
    slug: "iris",
    label: "Iris",
    children: [
      { slug: "iris", label: "Bolag" },
      { slug: "iris/granskning", label: "Granskning" },
      { slug: "iris/installningar", label: "Inställningar" },
      // Avsteg från spegelregeln ovan, med avsikt: CRM-listan är den omgjorda
      // leadsagentens demo av KUNDENS EGEN kundlista (i stället för att Iris
      // letar prospekt) och finns bara i demon — ett fjärde barn under Iris,
      // inte en egen toppnivåpost.
      { slug: "crm", label: "CRM-lista" }
    ]
  },
  { slug: "support", label: "Kundtjänst" },
  { slug: "kvitton", label: "Kvitton" }
];

/** Länken till en sektion. Tom sträng = demons startsida. */
export function demoSektionsVag(vag: string): string {
  return `/demo${vag ? `/${vag}` : ""}`;
}
