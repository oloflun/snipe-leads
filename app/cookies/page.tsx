import type { Metadata } from "next";
import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { notFoundOnTenant } from "@/lib/tenants/server";
import { TEMA_COOKIE } from "@/lib/tema";

export const metadata: Metadata = {
  title: "Cookies — Snajp",
  description: "Snajp.se använder en enda cookie, och den är strikt nödvändig. Ingen analys, ingen marknadsföring.",
  alternates: { canonical: "/cookies" }
};

/**
 * Cookie-namnet importeras ur lib/tema.ts i stället för att skrivas av.
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

  return (
    <JuridiskSida
      rubrik="Cookies"
      ingress="Snajp.se använder en cookie. Den kommer ihåg om du valt ljust eller mörkt tema."
    >
      <h2>Cookien vi sätter</h2>
      <ul>
        <li>
          <strong>{TEMA_COOKIE}</strong> — sparar ditt val av ljust eller mörkt tema. Strikt
          nödvändig för sidans funktion och sätts inte förrän du gjort ett aktivt val. Innehåller
          bara ordet för det tema du valt, ingenting om dig.
        </li>
      </ul>

      <h2>Cookies vi inte sätter</h2>
      <p>
        Vi använder inga analyscookies och inga marknadsföringscookies på snajp.se. Vi mäter inte
        ditt beteende på sidan, och vi delar ingenting med annonsnätverk.
      </p>
      <p>
        Ändras det kommer den här sidan att uppdateras och en samtyckesruta att visas innan någon
        sådan cookie sätts — inte efteråt.
      </p>

      <h2>Om du är inloggad</h2>
      <p>
        Inne i arbetsytan används dessutom en sessionscookie för att hålla dig inloggad. Den är
        också strikt nödvändig: utan den kan vi inte veta att det är du som är inloggad mellan två
        sidladdningar. Se <Link href="/integritetspolicy">integritetspolicyn</Link> för hur
        kontouppgifter behandlas.
      </p>
    </JuridiskSida>
  );
}
