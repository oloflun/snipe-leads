import type { Metadata, Viewport } from "next";
import "./globals.css";
import { fontVariables } from "@/lib/fonts";

export const metadata: Metadata = {
  title: {
    default: "Snajp Support",
    template: "%s — Snajp Support"
  },
  description:
    "Supportagenten sorterar kundmejlen, föreslår svar ur er kunskapsbas och lämnar sändknappen till dig.",
  icons: {
    icon: [{ url: "/snajp-symbol-black.svg", type: "image/svg+xml" }]
  },
  // Fristående utvecklingsyta — ska inte indexeras förrän den har en riktig
  // domän och ett beslut om lansering.
  robots: { index: false, follow: false }
};

export const viewport: Viewport = {
  themeColor: "#f6f3ed",
  initialScale: 1,
  width: "device-width"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // Portalens skal (meny + providers) bor i app/(portal)/layout.tsx —
  // inloggningssidan renderas utan det.
  return (
    <html lang="sv" className={fontVariables}>
      <body>{children}</body>
    </html>
  );
}
