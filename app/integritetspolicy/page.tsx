import type { Metadata } from "next";
import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { BOLAG, DATASKYDD_MEJL, UNDERLEVERANTORER } from "@/lib/bolag";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Integritetspolicy — Snajp",
  description:
    "Så behandlar Snajp personuppgifter: vilka uppgifter, varför, vilka underleverantörer som är inblandade och vilka rättigheter du har.",
  alternates: { canonical: "/integritetspolicy" }
};

/**
 * OBS: `notFoundOnTenant` — sidan är SNAJPS policy, inte kundens. På kundens
 * domän hade den beskrivit fel personuppgiftsansvarig för fel behandling.
 * Samma grind som app/support/page.tsx använder.
 */
export default async function Page() {
  await notFoundOnTenant();

  return (
    <JuridiskSida
      rubrik="Integritetspolicy"
      ingress="Den här sidan beskriver hur vi behandlar personuppgifter när du besöker snajp.se, skapar ett konto eller på annat sätt är i kontakt med oss."
    >
      <h2>Vem är personuppgiftsansvarig</h2>
      <p>
        {BOLAG.namn}, org.nr {BOLAG.orgnr}, {BOLAG.postadress}, är personuppgiftsansvarig för
        behandlingen av personuppgifter som sker när du besöker snajp.se, registrerar ett konto
        eller på annat sätt är i kontakt med oss.
      </p>
      <p>
        Kontakt i dataskyddsfrågor: <a href={`mailto:${DATASKYDD_MEJL}`}>{DATASKYDD_MEJL}</a>
      </p>

      <h2>Vilka uppgifter vi behandlar och varför</h2>

      <h3>Kontouppgifter</h3>
      <p>
        Namn och e-postadress när du skapar ett konto eller bjuds in till en arbetsyta. Rättslig
        grund: fullgörande av avtal.
      </p>

      <h3>Kunddata i produkten</h3>
      <p>
        Om ditt företag använder Snajps supportagent behandlar vi, på ert uppdrag och enligt separat
        personuppgiftsbiträdesavtal, de personuppgifter som finns i er kundtjänstinkorg: avsändarens
        namn, e-postadress och meddelandeinnehåll. Vi är då personuppgiftsbiträde, inte
        personuppgiftsansvarig — det är ni. Se personuppgiftsbiträdesavtalet för detaljer.
      </p>

      <h3>Utskick vi själva gör</h3>
      <p>
        Om vi kontaktar er som potentiell kund använder vi allmänt tillgängliga företagsuppgifter.
        Rättslig grund: berättigat intresse. Du kan alltid avregistrera dig via länken i mejlet, och
        avregistreringen gäller omedelbart och för alla framtida utskick.
      </p>

      <h2>Att texten bearbetas av en språkmodell</h2>
      <p>
        Snajp bygger på en språkmodell. Det betyder att den text agenten arbetar med — kundmejlet
        som kommer in, och det svar som föreslås — skickas till vår modelleverantör för bearbetning.
        Vi säger det rakt ut därför att det är det som gör produkten till en produkt, och därför att
        en kund som upptäcker det senare har hittat något vi valde att inte nämna.
      </p>
      <p>
        Leverantören behandlar texten för vår räkning, enligt avtal, och använder den inte för att
        träna sina modeller. Vilka leverantörer det gäller står nedan.
      </p>

      <h2>Vilka vi delar uppgifter med</h2>
      <p>Vi använder följande underleverantörer för att driva tjänsten:</p>
      <ul>
        {UNDERLEVERANTORER.map((leverantor) => (
          <li key={leverantor.namn}>
            <strong>{leverantor.namn}</strong> — {leverantor.andamal} {leverantor.region}
          </li>
        ))}
      </ul>
      <p>
        Ingen kunds data delas med en annan kund. Varje arbetsyta ligger i en egen avgränsning i
        databasen, och avgränsningen är en spärr i databasen — inte en inställning i koden.
      </p>

      <h2>Hur länge vi sparar uppgifter</h2>
      <p>
        {/* Fylls i när retentionsperioden är beslutad. Se P1.1 i
            docs/JURIDIK_ATGARDER.md och gallringsfunktionen i
            supabase/migrations/048_gallring.sql — mekanismen finns, talet är
            ett affärsbeslut som inte ska gissas här. */}
        <strong>[Fylls i: konkret lagringstid per kategori.]</strong> Gallringen är automatiserad och
        loggas, men perioden är ännu inte fastställd. Kontakta oss om du vill veta vad som gäller
        just nu.
      </p>

      <h2>Dina rättigheter</h2>
      <p>
        Du har rätt att begära tillgång till, rättelse av och radering av dina uppgifter, samt att
        invända mot behandling som sker med stöd av berättigat intresse. Kontakta oss på{" "}
        <a href={`mailto:${DATASKYDD_MEJL}`}>{DATASKYDD_MEJL}</a>. Du har också rätt att klaga till
        Integritetsskyddsmyndigheten, <a href="https://imy.se">imy.se</a>.
      </p>

      <h2>Cookies</h2>
      <p>
        Snajp.se sätter en enda cookie, och den är strikt nödvändig. Läs mer på{" "}
        <Link href="/cookies">cookiesidan</Link>.
      </p>
    </JuridiskSida>
  );
}
