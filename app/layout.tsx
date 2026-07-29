import type { Metadata } from "next";
import "./globals.css";
import { fontVariables } from "@/lib/fonts";
import { LocaleProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "Snajp, AI för leads och kundtjänst",
  description:
    "Snajp skriver säljmejlen och svarar på kundmejlen. Två verktyg, en arbetsyta. Testa båda direkt i webbläsaren.",
  metadataBase: new URL("https://snajp.se")
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="sv" className={fontVariables}>
      <body>
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
