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
        {/* .rise starts at opacity 0 and is revealed by an IntersectionObserver.
            Without JavaScript that observer never runs and the page renders
            blank. This is the fallback, and it belongs next to the .rise rule in
            globals.css — neither survives alone. */}
        <noscript>
          <style>{`.rise{opacity:1!important;transform:none!important}`}</style>
        </noscript>
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
