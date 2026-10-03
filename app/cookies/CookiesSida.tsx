"use client";

import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { useLocale, type Localized } from "@/lib/i18n";
import { TEMA_COOKIE } from "@/lib/tema";

/**
 * Cookiesidans text på svenska och engelska. Sidan (page.tsx) är en
 * serverkomponent för tenant-grindens skull; språkvalet bor i klienten.
 * Den engelska texten är en översättning av den svenska, inte en egen lydelse.
 */
const T = {
  rubrik: { sv: "Cookies", en: "Cookies" },
  ingress: {
    sv: "Snajp.se använder en cookie. Den kommer ihåg om du valt ljust eller mörkt tema.",
    en: "Snajp.se uses one cookie. It remembers whether you chose the light or dark theme."
  },
  vi_satter: { sv: "Cookien vi sätter", en: "The cookie we set" },
  tema: {
    sv: " — sparar ditt val av ljust eller mörkt tema. Strikt nödvändig för sidans funktion och sätts inte förrän du gjort ett aktivt val. Innehåller bara ordet för det tema du valt, ingenting om dig.",
    en: ": stores your choice of light or dark theme. Strictly necessary for the site to work, and not set until you have made an active choice. It contains only the name of the theme you chose, nothing about you."
  },
  inte_satter: { sv: "Cookies vi inte sätter", en: "Cookies we do not set" },
  ingen_analys: {
    sv: "Vi använder inga analyscookies och inga marknadsföringscookies på snajp.se. Vi mäter inte ditt beteende på sidan, och vi delar ingenting med annonsnätverk.",
    en: "We use no analytics cookies and no marketing cookies on snajp.se. We do not measure your behaviour on the site, and we share nothing with ad networks."
  },
  andras: {
    sv: "Ändras det kommer den här sidan att uppdateras och en samtyckesruta att visas innan någon sådan cookie sätts — inte efteråt.",
    en: "If that changes, this page will be updated and a consent prompt will be shown before any such cookie is set, not afterwards."
  },
  inloggad: { sv: "Om du är inloggad", en: "If you are signed in" },
  session: {
    sv: "Inne i arbetsytan används dessutom en sessionscookie för att hålla dig inloggad. Den är också strikt nödvändig: utan den kan vi inte veta att det är du som är inloggad mellan två sidladdningar. Se",
    en: "Inside the workspace, a session cookie is also used to keep you signed in. It is also strictly necessary: without it we cannot know that it is you who is signed in between two page loads. See the"
  },
  policyLank: { sv: "integritetspolicyn", en: "privacy policy" },
  sessionSlut: {
    sv: "för hur kontouppgifter behandlas.",
    en: "for how account details are processed."
  }
} satisfies Record<string, Localized>;

export function CookiesSida() {
  const { text } = useLocale();

  return (
    <JuridiskSida rubrik={text(T.rubrik)} ingress={text(T.ingress)}>
      <h2>{text(T.vi_satter)}</h2>
      <ul>
        <li>
          <strong>{TEMA_COOKIE}</strong>
          {text(T.tema)}
        </li>
      </ul>

      <h2>{text(T.inte_satter)}</h2>
      <p>{text(T.ingen_analys)}</p>
      <p>{text(T.andras)}</p>

      <h2>{text(T.inloggad)}</h2>
      <p>
        {text(T.session)} <Link href="/integritetspolicy">{text(T.policyLank)}</Link>{" "}
        {text(T.sessionSlut)}
      </p>
    </JuridiskSida>
  );
}
