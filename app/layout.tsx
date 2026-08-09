import type { Metadata } from "next";
import "./globals.css";
import { fontVariables } from "@/lib/fonts";
import { LocaleProvider } from "@/lib/i18n";
import { paletteToCss } from "@/lib/tenants";
import { getCurrentTenant } from "@/lib/tenants/server";

export async function generateMetadata(): Promise<Metadata> {
  const tenant = await getCurrentTenant();

  if (tenant) {
    return {
      title: `${tenant.name} — ${tenant.tagline}`,
      description: tenant.tagline
    };
  }

  return {
    title: "Snajp, AI för leads och kundtjänst",
    description:
      "Snajp skriver säljmejlen och svarar på kundmejlen. Två verktyg, en arbetsyta. Testa båda direkt i webbläsaren.",
    metadataBase: new URL("https://snajp.se")
  };
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const tenant = await getCurrentTenant();

  return (
    <html lang="sv" className={fontVariables}>
      <head>
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
      </body>
    </html>
  );
}
