import type { MetadataRoute } from "next";
import { arProduktion } from "@/lib/miljo";

/**
 * robots.txt — och det viktiga är vad den säger i ANDRA miljöer än produktion.
 *
 * `web-development-6c85.up.railway.app` är en spegel av produktionen med
 * riktiga kunders ärenden bakom inloggningen. Fram till 2026-08-24 hade den
 * ingen robots.txt alls: `/robots.txt` gav 404-sidans HTML. En fullständig
 * kopia av sajten låg alltså öppen för indexering.
 *
 * `dynamic = "force-dynamic"` är inte pedanteri. Utan den prerenderas filen
 * vid bygget, och miljövariabeln som avgör utfallet läses då EN gång — vilket
 * fungerar så länge varje miljö bygger sitt eget artefakt, men slutar fungera
 * i samma sekund någon återanvänder ett bygge mellan miljöer. Det är precis
 * den sortens tyst antagande som den här sessionen redan snubblat på tre
 * gånger.
 *
 * Notera vad robots.txt INTE gör: den tar inte bort något som redan hunnit
 * indexeras. Det gör `noindex`-taggen i app/layout.tsx, som sätts av samma
 * villkor. De två hör ihop — ta inte bort den ena.
 */
export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  if (!arProduktion()) {
    return { rules: [{ userAgent: "*", disallow: "/" }] };
  }

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Den inloggade ytan hör inte hemma i ett index ens i produktion.
        // Grinden som RÄKNAS är proxyn och layouternas kontroller — det här
        // är städning, inte skydd.
        disallow: ["/dashboard", "/settings", "/admin", "/onboarding", "/avregistrera", "/api"]
      }
    ]
    // Ingen `sitemap:`-rad: app/sitemap.ts finns inte. En robots.txt som
    // pekar på en sitemap som svarar 404 är sämre än ingen rad alls — den
    // säger åt sökmotorn att hämta något som inte finns, varje gång.
  };
}
