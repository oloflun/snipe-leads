import type { MetadataRoute } from "next";

/**
 * PWA-manifestet. Gör arbetsytan installerbar på hemskärmen och skrivbordet.
 *
 * ## Varför `screenshots` inte är pynt
 *
 * Chrome på DESKTOP visar den riktiga installationsdialogen — apptitel,
 * beskrivning och förhandsbild — bara om manifestet har minst en skärmbild med
 * `form_factor: "wide"`. Saknas de erbjuder menyn "Skapa genväg…" i stället
 * för "Installera…", och en genväg öppnas i en vanlig webbläsarflik.
 *
 * Det är hela skillnaden mellan att installera en app och att spara ett
 * bokmärke, och det var precis det som hände: appen såg ut att "bara öppna ett
 * nytt fönster". Måtten nedan MÅSTE stämma med filernas faktiska pixlar —
 * en post med fel mått ignoreras tyst av Chrome.
 *
 * Bilderna genereras av `scripts/generera_butiksbilder.mjs`.
 *
 * ## Varför `orientation` är borta
 *
 * Den stod på `portrait`. På en telefon är det en rimlig låsning, på ett
 * skrivbord är det meningslöst — och en app som deklarerar sig som
 * porträttlåst är inte en skrivbordsapp. Utelämnad betyder "vad enheten än
 * har", vilket är rätt för båda.
 *
 * ## Varför `id` finns
 *
 * Utan `id` härleds appens identitet ur `start_url`. Den dag start_url ändras
 * blir det en ANNAN app för webbläsaren: den redan installerade ligger kvar
 * som en död ikon och en ny installeras bredvid. `id` fryser identiteten.
 *
 * ## Varför `start_url` är /dashboard och inte /
 *
 * Den som installerat appen är inloggad kund, inte besökare. Startsidan är
 * marknadsföring — att öppna appen och mötas av "Boka demo" är att skicka
 * kunden fel varje gång. Är sessionen slut skickar `/dashboard` vidare till
 * inloggningen, vilket är rätt beteende.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/?app=snajp",
    name: "Snajp — leads och kundtjänst",
    short_name: "Snajp",
    description:
      "Agenterna hittar bolagen, skriver mejlen och svarar kunderna. Du har alltid sista ordet.",
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    // Faller nedåt i tur och ordning. `window-controls-overlay` ger appen
    // titelraden på skrivbordet; stöds den inte används standalone.
    display_override: ["window-controls-overlay", "standalone", "minimal-ui"],
    lang: "sv",
    dir: "ltr",
    categories: ["business", "productivity"],
    // Ur app/globals.css (--paper respektive --ink), konverterade från OKLCH.
    // theme_color färgar systemfältet, background_color splashskärmen.
    background_color: "#f6f3ed",
    theme_color: "#f6f3ed",
    // Ett klick på en Snajp-länk ska hoppa till det redan öppna appfönstret
    // i stället för att öppna ett andra. Två fönster med samma arbetsyta är
    // hur man råkar godkänna samma utkast två gånger.
    launch_handler: { client_mode: "focus-existing" },
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      {
        // Egen fil och inte `purpose: "any maskable"` på samma rad: en ikon som
        // deklareras som båda används av Android som maskerbar och beskärs då
        // till en cirkel, vilket kapar en ikon utan säkerhetszon.
        src: "/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable"
      }
    ],
    screenshots: [
      {
        src: "/screenshots/wide-oversikt.png",
        sizes: "1280x800",
        type: "image/png",
        form_factor: "wide",
        label: "Översikten — läget i båda agenterna"
      },
      {
        src: "/screenshots/wide-analys.png",
        sizes: "1280x800",
        type: "image/png",
        form_factor: "wide",
        label: "Analys — skick, svar och ärenden per vecka"
      },
      {
        src: "/screenshots/wide-bolag.png",
        sizes: "1280x800",
        type: "image/png",
        form_factor: "wide",
        label: "Företag — bolagen agenten hittat, med signal och poäng"
      },
      {
        src: "/screenshots/narrow-oversikt.png",
        sizes: "390x664",
        type: "image/png",
        form_factor: "narrow",
        label: "Översikten i mobilen"
      },
      {
        src: "/screenshots/narrow-analys.png",
        sizes: "390x664",
        type: "image/png",
        form_factor: "narrow",
        label: "Analys i mobilen"
      }
    ],
    shortcuts: [
      {
        name: "Kundtjänst",
        short_name: "Kundtjänst",
        url: "/dashboard/support",
        icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }]
      },
      {
        name: "Leads",
        short_name: "Leads",
        url: "/dashboard/leads",
        icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }]
      },
      {
        name: "Email studio",
        short_name: "Mejl",
        url: "/dashboard/emails",
        icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }]
      }
    ]
  };
}
