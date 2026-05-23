import type { Metadata } from "next";
import "./globals.css";
import { LocaleProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "Snipra - svensk AI-driven outbound automation",
  description:
    "Snipra hjälper svenska B2B-team att hitta rätt företag, analysera signaler och skicka lågmält personliga säljmejl.",
  metadataBase: new URL("https://snipra.se")
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="sv">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,300..700,30..100&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="noise">
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
