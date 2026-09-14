import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { fontVariables } from "@/lib/fonts";
import { PeriodProvider } from "@/lib/period";
import { ProfilProvider } from "@/lib/profil";

export const metadata: Metadata = {
  title: {
    default: "Snajp Bokföring",
    template: "%s — Snajp Bokföring"
  },
  description:
    "Bokföringsagenten läser dina kvitton och fakturor, räknar moms och resultat, och svarar på frågor om siffrorna.",
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
  return (
    <html lang="sv" className={fontVariables}>
      <body>
        <PeriodProvider>
          <ProfilProvider>
            <div className="flex min-h-dvh">
              <Sidebar />
              <main className="min-w-0 flex-1">
                <div className="mx-auto max-w-[1060px] px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
                  {children}
                </div>
              </main>
            </div>
          </ProfilProvider>
        </PeriodProvider>
      </body>
    </html>
  );
}
