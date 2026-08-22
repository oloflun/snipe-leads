import type { Metadata, Viewport } from "next";
import "./globals.css";
import { fontVariables } from "@/lib/fonts";
import { LocaleProvider } from "@/lib/i18n";
import { paletteToCss } from "@/lib/tenants";
import { getCurrentTenant } from "@/lib/tenants/server";
import { InstalleraApp } from "@/components/InstalleraApp";

export async function generateMetadata(): Promise<Metadata> {
  const tenant = await getCurrentTenant();

  if (tenant) {
    // INGET manifest och inga appikoner på kundens domän. Enligt TENANTS.md ska
    // Snajps egna ytor aldrig synas där — och ett manifest som heter "Snajp"
    // hade erbjudit kundens besökare att installera VÅR app från kundens sajt.
    return {
      title: `${tenant.name} — ${tenant.tagline}`,
      description: tenant.tagline
    };
  }

  return {
    title: "Snajp, AI för leads och kundtjänst",
    description:
      "Snajp skriver säljmejlen och svarar på kundmejlen. Två verktyg, en arbetsyta. Testa båda direkt i webbläsaren.",
    metadataBase: new URL("https://snajp.se"),
    manifest: "/manifest.webmanifest",
    icons: {
      icon: [
        { url: "/snipe_logo.svg", type: "image/svg+xml" },
        { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }
      ],
      apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }]
    },
    appleWebApp: {
      capable: true,
      // Namnet under ikonen på iOS hemskärm. Utan det tar Safari <title>,
      // alltså "Snajp, AI för leads och kundtjänst" — som kapas till "Snajp,
      // AI f…" och ser trasigt ut.
      title: "Snajp",
      // `default` och inte `black-translucent`: den senare låter sidan rita
      // under statusfältet, vilket kräver att VARJE sidhuvud kompenserar för
      // det. Ett missat sidhuvud lägger uret ovanpå en rubrik.
      statusBarStyle: "default"
    }
  };
}

/**
 * Skild från generateMetadata eftersom viewport är sin egen export i Next.
 *
 * `viewportFit: "cover"` låter sidan använda hela skärmen på en iPhone med
 * notch — och är förutsättningen för att `env(safe-area-inset-*)` ska ge något
 * annat än noll. Utan den är säkerhetsmarginalerna i AppShell och
 * ImpersonationBanner tysta nollor.
 */
export const viewport: Viewport = {
  themeColor: "#f6f3ed",
  viewportFit: "cover",
  // Nypa-zoom ska INTE stängas av. `maximumScale: 1` är det vanligaste sättet
  // att göra en webbapp otillgänglig för den som behöver förstora text.
  initialScale: 1,
  width: "device-width"
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const tenant = await getCurrentTenant();

  return (
    <html lang="sv" className={fontVariables}>
      <head>
        {/* Next 16 skriver `mobile-web-app-capable` — den moderna taggen, som
            iOS läser från 16.4. Den apple-prefixade är den ENDA som äldre iOS
            förstår, och utan den öppnas appen från hemskärmen i ett vanligt
            Safari-fönster med adressfält i stället för i helskärm. Den står
            därför här och inte i metadata-objektet, som inte längre kan skriva
            den. Tas bort den dag vi slutar bry oss om iOS < 16.4. */}
        {tenant ? null : <meta name="apple-mobile-web-app-capable" content="yes" />}
        {/* Här låg tidigare en <noscript>-override som tvingade .rise synlig,
            eftersom .rise startade på opacity 0 och en utebliven observer gav
            en blank sida. Den behövs inte längre: sedan 2026-08-10 döljer
            globals.css bara .rise medan <html> bär `reveal-armed`, som
            useReveal sätter och äger. Utan JS armeras aldrig sidan, och allt
            är synligt. Borttagen i stället för kvarlämnad, för död kod som ser
            bärande ut är precis vad nästa person snubblar på. */}
        {/* Kundens palett skriver över :root. Komponenterna läser redan dessa
            variabler, så en ny kund kräver ingen komponentändring alls. */}
        {tenant ? <style>{paletteToCss(tenant.palette)}</style> : null}
      </head>
      <body>
        <LocaleProvider>{children}</LocaleProvider>
        {/* Inte på kundens domän. Där är vi supportchatten på deras sajt, och
            en ruta som ber besökaren installera VÅR app hör inte hemma. */}
        {tenant ? null : <InstalleraApp />}
      </body>
    </html>
  );
}
