import type { Metadata } from "next";
import { notFoundOnTenant } from "@/lib/tenants/server";
import { CookiesSida } from "./CookiesSida";

export const metadata: Metadata = {
  title: "Cookies — Snajp",
  description: "Snajp.se använder en enda cookie, och den är strikt nödvändig. Ingen analys, ingen marknadsföring.",
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
 */
export default async function Page() {
  await notFoundOnTenant();

  return <CookiesSida />;
}
