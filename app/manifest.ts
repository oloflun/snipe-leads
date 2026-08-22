import type { MetadataRoute } from "next";

/**
 * PWA-manifestet. Gör arbetsytan installerbar på hemskärmen.
 *
 * ## Varför `start_url` är /dashboard och inte /
 *
 * Den som installerat appen är inloggad kund, inte besökare. Startsidan är
 * marknadsföring — att öppna appen och mötas av "Boka demo" är att skicka
 * kunden fel varje gång. Är sessionen slut skickar `/dashboard` vidare till
 * inloggningen ändå, vilket är rätt beteende.
 *
 * ## Varför ikonerna ligger som filer och inte genereras här
 *
 * `snipe_logo.svg` är 1206×728. En kvadratisk beskärning kapar märket, så
 * ikonerna byggs med marginal av `scripts/generera_ikoner.mjs` — se den filen
 * för marginalerna och varför iOS får en egen.
 *
 * `purpose: "maskable"` på den egna filen och inte på samma rad som "any":
 * en ikon som deklareras som båda används av Android som maskerbar och beskärs
 * då till en cirkel, vilket kapar en ikon som inte har säkerhetszonen.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Snajp",
    short_name: "Snajp",
    description: "Leads och kundtjänst i samma arbetsyta.",
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    lang: "sv",
    // Ur app/globals.css (--paper respektive --ink), konverterade från OKLCH.
    // theme_color färgar systemfältet, background_color splashskärmen.
    background_color: "#f6f3ed",
    theme_color: "#f6f3ed",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      {
        src: "/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable"
      }
    ]
  };
}
