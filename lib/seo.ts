import type { Metadata } from "next";
import { KANONISK_ORIGIN, kanoniskUrl } from "@/lib/kanonisk";
import { PAKET, PER_MANAD, PRIS_PREFIX, PRIS_SAKNAS, VALUTA, formateraPris, type Paket } from "@/lib/pricing";
import { TEAM } from "@/lib/team";

/**
 * Sökmotortexten och den strukturerade datan för Snajps publika sidor.
 *
 * ## Metadata ur ett ställe
 *
 * Varje sida satte tidigare `title`, `description` och `canonical` för hand,
 * och ingen satte Open Graph. En länk till /leads i Slack eller LinkedIn visade
 * därför ingen bild och sajtens allmänna text i stället för sidans.
 *
 * Delningskortet (`DELNING`) står bara i layouten. En sida som sätter egen
 * `openGraph` ersätter hela objektet och tappar bilden, så `sidmeta` sätter
 * ingen: Next fyller i kortets titel och beskrivning ur sidans egna
 * (`inheritFromMetadata` i next/dist/lib/metadata/resolve-metadata.js), och
 * Twitter-kortet ur Open Graph.
 *
 * Titeln skrivs hel på varje sida, utan mall i layouten. En mall
 * ("%s | Snajp") hade lagt till åtta tecken på sidor vars titel redan är
 * avvägd mot de cirka 60 tecken Google visar, och INV-SEO-001 mäter längden
 * på det som faktiskt står.
 *
 * ## JSON-LD
 *
 * Schemat beskriver bara det som går att belägga: bolagsnamnet, grundarna ur
 * lib/team.ts, orterna och priserna ur lib/pricing.ts. Inga betyg och inga
 * recensioner, eftersom vi inte har några (DESIGN.md, Honest-proof rule), och
 * inget organisationsnummer förrän lib/bolag.ts har ett.
 */

/**
 * Delningskortet för Snajps egna sidor, satt en gång i app/layout.tsx.
 * Bilden är statisk och utan priser, se scripts/generera_og.py.
 */
export const DELNING: Pick<Metadata, "openGraph" | "twitter"> = {
  openGraph: {
    type: "website",
    locale: "sv_SE",
    siteName: "Snajp",
    images: [{ url: "/og/snajp.jpg", width: 1200, height: 630, alt: "Snajp" }]
  },
  twitter: { card: "summary_large_image" }
};

export function sidmeta({
  vag,
  titel,
  beskrivning
}: Readonly<{ vag: string; titel: string; beskrivning: string }>): Metadata {
  return { title: titel, description: beskrivning, alternates: { canonical: vag } };
}

type Nod = Record<string, unknown>;

const ORG_ID = `${KANONISK_ORIGIN}/#organisation`;

export function organisation(kontaktMejl: string): Nod {
  return {
    "@type": "Organization",
    "@id": ORG_ID,
    name: "Snajp",
    url: KANONISK_ORIGIN,
    logo: kanoniskUrl("/icons/icon-512.png"),
    email: kontaktMejl,
    description:
      "Snajp bygger AI-agenter för svenska företag: Iris, en AI-SDR som hittar och skriver till nya B2B-kunder, och en supportagent som svarar kunder på svenska i mejl och chatt.",
    founder: TEAM.map((medlem) => ({ "@type": "Person", name: medlem.namn })),
    location: ["Göteborg", "Umeå"].map((ort) => ({
      "@type": "Place",
      address: { "@type": "PostalAddress", addressLocality: ort, addressCountry: "SE" }
    })),
    areaServed: { "@type": "Country", name: "Sverige" },
    knowsLanguage: ["sv", "en"]
  };
}

export function webbplats(): Nod {
  return {
    "@type": "WebSite",
    "@id": `${KANONISK_ORIGIN}/#webbplats`,
    url: KANONISK_ORIGIN,
    name: "Snajp",
    inLanguage: "sv-SE",
    publisher: { "@id": ORG_ID }
  };
}

/**
 * Produkterna i schemat: produktsidan och en beskrivning. Här och inte i
 * sidorna, så att alla sidor som nämner en produkt pekar på samma @id och
 * samma text. Duo har ingen egen sida och bor på startsidan.
 */
export const PRODUKTER: Record<Paket["id"], { vag: string; beskrivning: string }> = {
  leads: {
    vag: "/leads",
    beskrivning:
      "Iris, Snajps AI-SDR för svensk B2B: urval ur bolagsregistret, research på bolagets egen webbplats och ett personligt säljmejl på svenska som en människa godkänner."
  },
  support: {
    vag: "/support",
    beskrivning:
      "Snajp Support, en AI-agent för kundtjänst som svarar på svenska och engelska i mejlinkorgen och i chatten på kundens hemsida, ur kundens egen kunskapsbas."
  },
  duo: {
    vag: "/",
    beskrivning: "Snajp Duo, leadsagenten Iris och supportagenten i samma arbetsyta med delad kunddata."
  }
};

/** En produkt som programvara med sitt ingångspris. */
export function produkt(id: Paket["id"]): Nod {
  const paket = PAKET.find((p) => p.id === id);
  if (!paket) throw new Error(`Unknown package: ${id}`);
  const { vag, beskrivning } = PRODUKTER[id];
  return {
    "@type": "SoftwareApplication",
    "@id": `${kanoniskUrl(vag)}#produkt-${id}`,
    name: paket.namn,
    url: kanoniskUrl(vag),
    description: beskrivning,
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    inLanguage: ["sv-SE", "en"],
    publisher: { "@id": ORG_ID },
    ...(paket.prisPerManad === null
      ? {}
      : {
          offers: {
            "@type": "Offer",
            price: paket.prisPerManad,
            priceCurrency: VALUTA,
            priceSpecification: {
              "@type": "UnitPriceSpecification",
              price: paket.prisPerManad,
              priceCurrency: VALUTA,
              unitText: "MON",
              valueAddedTaxIncluded: false
            },
            availability: "https://schema.org/InStock",
            areaServed: { "@type": "Country", name: "Sverige" }
          }
        })
  };
}

export function faqSida(poster: readonly { fraga: string; svar: string }[]): Nod {
  return {
    "@type": "FAQPage",
    inLanguage: "sv-SE",
    mainEntity: poster.map((p) => ({
      "@type": "Question",
      name: p.fraga,
      acceptedAnswer: { "@type": "Answer", text: p.svar }
    }))
  };
}

export function brodsmulor(steg: readonly { namn: string; vag: string }[]): Nod {
  return {
    "@type": "BreadcrumbList",
    itemListElement: steg.map((s, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: s.namn,
      item: kanoniskUrl(s.vag)
    }))
  };
}

/** Flera noder i ett skript, så att @id-referenserna löses inom samma graf. */
export function graf(...noder: Nod[]): Nod {
  return { "@context": "https://schema.org", "@graph": noder };
}

/** "4 490 kr" för ett paket, eller null när priset inte är satt. */
export function paketpris(id: Paket["id"]): string | null {
  const belopp = PAKET.find((p) => p.id === id)?.prisPerManad ?? null;
  return belopp === null ? null : formateraPris(belopp);
}

/**
 * Prisets mening i en sökbeskrivning: "Från 4 490 kr/mån."
 *
 * Priset i en Google-träff ska följa prislistan av sig självt (Anton
 * 2026-11-05: "se till att priserna automatiskt uppdateras i länkarna").
 * Därför skrivs inget belopp i någon sidas metadata, bara det här anropet, och
 * INV-SEO-001 fäller en handskriven kronsumma i sidfilerna. Sökmotorn ser det
 * nya priset när den hämtar sidan igen; scripts/indexnow.py säger till Bing
 * direkt efter en release.
 */
export function prisrad(id: Paket["id"]): string {
  const pris = paketpris(id);
  return pris ? `${versal(PRIS_PREFIX.sv)} ${pris}${PER_MANAD.sv}.` : `${PRIS_SAKNAS.sv}.`;
}

/** Första bokstaven versal, för en fras ur lib/pricing.ts som inleder en mening. */
export function versal(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
