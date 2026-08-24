import type { Metadata } from "next";
import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { BOLAG } from "@/lib/bolag";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Användarvillkor — Snajp",
  description:
    "Villkoren mellan Snajp och det företag som tecknar avtal om supportagenten, leadsagenten eller bokföringsagenten.",
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
 */
export default async function Page() {
  await notFoundOnTenant();

  return (
    <JuridiskSida
      rubrik="Användarvillkor"
      ingress={`Dessa villkor gäller mellan ${BOLAG.namn} ("Snajp") och det företag ("Kunden") som registrerar ett konto eller tecknar avtal om Snajps tjänster.`}
    >
      <h2>Tjänsten</h2>
      <p>
        Snajp levererar en eller flera agenter enligt vad Kunden tecknat: supportagenten, som läser
        och besvarar inkommande kundmejl; leadsagenten, som tar fram prospekt och skriver utgående
        mejl; och, i förekommande fall, bokföringsagenten.
      </p>

      <h2>Kundens ansvar</h2>
      <p>
        Kunden ansvarar för att de uppgifter som matas in i tjänsten — till exempel den
        kundtjänstinkorg som kopplas in — får behandlas av Snajp enligt gällande rätt, och för att
        informera sina egna kunder och besökare om detta på sin egen webbplats.
      </p>
      <p>
        Kunden ansvarar även för att arkivera räkenskapsinformation i enlighet med bokföringslagen.
        Snajps bokföringsagent lagrar inte originalunderlag som kvitton och fakturor, och ersätter
        inte Kundens egen arkiveringsskyldighet.
      </p>
      <p>
        Kunden ansvarar för att informera sina egna kunder om att inkommande ärenden behandlas
        med hjälp av AI, i enlighet med artikel 13 i dataskyddsförordningen. Snajp tillhandahåller
        en textmall för detta, men ansvaret för att texten finns på Kundens webbplats och stämmer
        med Kundens verksamhet är Kundens.
      </p>
      <p>
        <strong>Autonominivån är Kundens val och Kundens ansvar.</strong> Snajps supportagent
        levereras med mänsklig granskning påslagen för samtliga ärendekategorier. Kunden kan
        ställa om enskilda kategorier till automatiskt svar. Gör Kunden det upphör den mänskliga
        inblandningen för de kategorierna, och Kunden ansvarar för att bedöma vad det innebär
        enligt artikel 22 i dataskyddsförordningen.
      </p>
      <p>
        Utgående mejl från leadsagenten skickas i Kundens namn. Snajp kontrollerar i kod att varje
        utskick bär Kundens fullständiga företagsnamn, organisationsnummer, postadress och en
        fungerande avregistreringslänk, och blockerar utskick som saknar något av det. Kunden
        ansvarar för att de uppgifter vi identifierar Kunden med är korrekta.
      </p>

      <h2>Personuppgiftsbehandling</h2>
      <p>
        I den mån Snajp behandlar personuppgifter för Kundens räkning gäller det separata
        personuppgiftsbiträdesavtalet, som är en integrerad del av detta avtal. Där framgår också
        vilka underleverantörer som anlitas. Snajps behandling som personuppgiftsansvarig beskrivs i{" "}
        <Link href="/integritetspolicy">integritetspolicyn</Link>.
      </p>

      <h2>Pris och betalning</h2>
      <p>
        Det här avsnittet är inte fastställt. Priserna framgår av{" "}
        <Link href="/#priser">prislistan</Link>, men betalningsvillkor, indexering och vad som
        gäller vid utebliven betalning är inte reglerat här. Skriv till oss på{" "}
        <a href={`mailto:${KONTAKT_MEJL}`}>{KONTAKT_MEJL}</a> innan avtal tecknas.
      </p>

      <h2>Ansvarsbegränsning</h2>
      <p>
        Det här avsnittet är inte fastställt. Klausulen avgör vad ett fel kostar, och vi skriver
        den inte själva — den ska formuleras av jurist. Tills dess finns ingen avtalad
        ansvarsbegränsning. Skriv till oss på{" "}
        <a href={`mailto:${KONTAKT_MEJL}`}>{KONTAKT_MEJL}</a> innan avtal tecknas.
      </p>

      <h2>Uppsägning och vad som händer med data</h2>
      <p>
        Uppsägningstiden är inte fastställd i de här villkoren. Bindningstiden är noll månader,
        vilket inte är samma sak — skriv till oss på{" "}
        <a href={`mailto:${KONTAKT_MEJL}`}>{KONTAKT_MEJL}</a> innan avtal tecknas.
      </p>
      <p>
        Vid avtalets upphörande raderas eller återlämnas Kundens personuppgifter enligt
        personuppgiftsbiträdesavtalets klausul om radering och återlämning, inom den tid som
        anges där. Se även avsnittet om lagringstider i{" "}
        <Link href="/integritetspolicy">integritetspolicyn</Link>.
      </p>

      <h2>Tillämplig lag</h2>
      <p>Svensk rätt gäller.</p>
    </JuridiskSida>
  );
}
