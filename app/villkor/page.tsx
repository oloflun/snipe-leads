import type { Metadata } from "next";
import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { BOLAG } from "@/lib/bolag";
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
 * Avsnitten "Pris och betalning" och "Ansvarsbegränsning" står tomma med
 * flit. Ansvarsbegränsning är den klausul som avgör vad ett fel kostar oss,
 * och den ska skrivas av en jurist — inte formuleras av den som byggde
 * produkten och vill tro att den fungerar.
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
      <p>
        <strong>[Fylls i: vad som ingår i respektive nivå, tillgänglighetsåtagande och vad som
        uttryckligen inte ingår.]</strong>
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
        <strong>[Fylls i: prismodell, betalningsvillkor, indexering och vad som händer vid utebliven
        betalning.]</strong>
      </p>

      <h2>Ansvarsbegränsning</h2>
      <p>
        <strong>[Fylls i av jurist. Skriv inte den här klausulen själv.]</strong>
      </p>

      <h2>Uppsägning och vad som händer med data</h2>
      <p>
        <strong>[Fylls i: uppsägningstid.]</strong> Vid avtalets upphörande raderas eller återlämnas
        Kundens personuppgifter enligt personuppgiftsbiträdesavtalets klausul om radering och
        återlämning, inom den tid som anges där. Se även avsnittet om lagringstider i{" "}
        <Link href="/integritetspolicy">integritetspolicyn</Link>.
      </p>

      <h2>Tillämplig lag</h2>
      <p>
        Svensk rätt gäller. <strong>[Fylls i: tvistlösning — allmän domstol eller skiljeförfarande,
        och på vilken ort.]</strong>
      </p>
    </JuridiskSida>
  );
}
