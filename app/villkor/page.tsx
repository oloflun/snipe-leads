import type { Metadata } from "next";
import { notFoundOnTenant } from "@/lib/tenants/server";
import { VillkorSida } from "./VillkorSida";

export const metadata: Metadata = {
  title: "Användarvillkor — Snajp",
  description:
    "Villkoren mellan Snajp och det företag som tecknar avtal om supportagenten, leadsagenten eller kvittohanteraren.",
  alternates: { canonical: "/villkor" }
};

/**
 * SaaS-avtalet mellan oss och kunden. Ska INTE förväxlas med de
 * konsumentvillkor kunden har mot sina egna slutkunder — de skriver de själva,
 * på sin egen sajt, och vi tar inte ansvar för dem.
 *
 * ## Hålen i avtalet är utskrivna, inte gömda (2026-08-25)
 *
 * "Pris och betalning" och "Ansvarsbegränsning" är fortfarande oskrivna.
 * Tidigare stod det `[Fylls i: …]` i dem, vilket läste som ett trasigt bygge
 * sedan utkastrutan togs bort; nu står en mening riktad till LÄSAREN i stället.
 *
 * Avsnitten är INTE dolda, och det är ett val. Utan avtalad ansvarsbegränsning
 * gäller svensk rätts utgångspunkt — alltså oreglerat ansvar för oss — och en
 * dold rubrik hade fått dokumentet att se färdigt ut medan risken var
 * oförändrad. Rubriken är det enda som påminner om att klausulen saknas.
 *
 * Ansvarsbegränsningen ska skrivas av jurist, inte av den som byggde produkten
 * och vill tro att den fungerar. Formulera den inte här.
 *
 * Texten bor i VillkorSida.tsx på svenska och engelska (Antons beslut
 * 2026-10-02); den engelska är en översättning av den svenska.
 */
export default async function Page() {
  await notFoundOnTenant();

  return <VillkorSida />;
}
