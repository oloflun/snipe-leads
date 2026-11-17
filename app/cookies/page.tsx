import type { Metadata } from "next";
import { notFoundOnTenant } from "@/lib/tenants/server";
import { CookiesSida } from "./CookiesSida";

export const metadata: Metadata = {
  title: "Cookies — Snajp",
  description:
    "Vilka kakor och vilken lagring snajp.se använder, och hur demolänken i utskicken registrerar klick och besök. Inga analys- eller marknadsföringskakor.",
  alternates: { canonical: "/cookies" }
};

/**
 * Cookie-namnet importeras ur lib/tema.ts i stället för att skrivas av
 * (i CookiesSida.tsx, där texten bor på svenska och engelska).
 *
 * En avskriven sträng hade blivit fel den dag cookien döps om, och en
 * cookiesida som anger fel namn är sämre än ingen sida alls: den ser ut som
 * en redovisning och är en gissning.
 *
 * VARFÖR DET INTE FINNS NÅGON SAMTYCKESBANNER: en strikt nödvändig cookie
 * kräver inget samtycke. En banner för den hade lärt besökaren att klicka
 * bort rutor utan att läsa, vilket är precis det beteende en riktig banner
 * behöver. Läggs analys- eller marknadsföringscookies till måste den här
 * sidan och en banner finnas INNAN cookien sätts, inte efteråt.
 *
 * ÖPPET (kartläggningen 2026-11-17): demolänkens registrering
 * (components/demo/DemoBesok.tsx, app/prova/[token]/route.ts), service workerns
 * cache (components/InstalleraApp.tsx, public/sw.js) och CRM-demons
 * localStorage, som skrivs när demon öppnas, är inte uppenbart nödvändiga för
 * en tjänst besökaren begärt. Om de kräver samtycke är ägarens och juristens
 * fråga. Sidan beskriver dem som de är; beteendet är inte ändrat.
 */
export default async function Page() {
  await notFoundOnTenant();

  return <CookiesSida />;
}
