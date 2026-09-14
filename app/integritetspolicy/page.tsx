import type { Metadata } from "next";
import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { bolagsraden, dataskyddKontakt, utanPlatshallare, UNDERLEVERANTORER } from "@/lib/bolag";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
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
/* TODO: juridiskt granskad text krävs innan publicering.
    Sidan har rättslig betydelse och är skriven av en agent, inte av en
    jurist. Kontrollera särskilt tre saker, i den ordningen:
      1. Underleverantörernas dataregion och avtalsnivå (lib/bolag.ts —
         fälten är platshållare och UTELÄMNAS i vyn tills de fylls i).
      2. Påståendet om modelleverantörens träning: det STÅR INTE här, och
         får inte skrivas tillbaka utan att någon läst avtalet.
         Se docs/JURIDIK_ATGARDER.md, P0.1c.
      3. Gallringstiden 24 månader mot det gallringsjobbet faktiskt kör
         (supabase/migrations/048_gallring.sql). Två tal som glidit isär är
         värre än inget tal alls.
    Den gula utkastrutan är BORTTAGEN UR VYN på begäran 2026-08-25 och ska
    inte skrivas tillbaka. Den här markeringen är för utvecklaren, inte för
    besökaren. */
export default async function Page() {
  await notFoundOnTenant();

  return (
    <JuridiskSida
      rubrik="Integritetspolicy"
      ingress="Den här sidan beskriver hur vi behandlar personuppgifter när du besöker snajp.se, skapar ett konto eller på annat sätt är i kontakt med oss."
    >
      {/* Innehållsförteckning. Inline och inte i marginalen: JuridiskSida
          sätter 68 tecken och delas med villkors- och cookiesidan, så en
          sidokolumn hade byggts om för tre sidor för att tjäna en. Länkarna
          gör samma nytta — de gör dokumentet navigerbart och varje avsnitt
          adresserbart, så `/integritetspolicy#lagring` går att klistra in i
          ett svar till en inköpares jurist. */}
      <nav aria-label="Innehåll" className="not-prose">
        <h2 id="innehall">Innehåll</h2>
        <ul>
          <li><a href="#ansvarig">Vem är personuppgiftsansvarig</a></li>
          <li><a href="#uppgifter">Vilka uppgifter vi behandlar och varför</a></li>
          <li><a href="#kallor">Varifrån uppgifterna kommer</a></li>
          <li><a href="#sprakmodell">Att texten bearbetas av en språkmodell</a></li>
          <li><a href="#underleverantorer">Vilka vi delar uppgifter med</a></li>
          <li><a href="#lagring">Hur länge vi sparar uppgifter</a></li>
          <li><a href="#rattigheter">Dina rättigheter</a></li>
          <li><a href="#cookies">Cookies</a></li>
        </ul>
      </nav>

      <h2 id="ansvarig">Vem är personuppgiftsansvarig</h2>
      {/* Raden byggs av det som är ifyllt. Org.nr och postadress är ännu
          platshållare och utelämnas därför helt — de stod tidigare som
          "[XXXXXX-XXXX]" mitt i meningen om vem som bär ansvaret, vilket är
          den sämsta tänkbara platsen för en text som ser påhittad ut. */}
      <p>
        {bolagsraden(", ")} är personuppgiftsansvarig för behandlingen av personuppgifter som
        sker när du besöker snajp.se, registrerar ett konto eller på annat sätt är i kontakt
        med oss.
      </p>
      <p>
        Kontakt i dataskyddsfrågor:{" "}
        <a href={`mailto:${dataskyddKontakt(KONTAKT_MEJL)}`}>{dataskyddKontakt(KONTAKT_MEJL)}</a>
      </p>

      <h2 id="uppgifter">Vilka uppgifter vi behandlar och varför</h2>

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

      <h2 id="kallor">Varifrån uppgifterna kommer</h2>
      <p>
        <strong>Företagsuppgifter</strong> — bolagsnamn, bransch, storlek, adress och offentliga
        kontaktvägar — hämtas från bolagets egen webbplats, deras platsannonser och
        pressmeddelanden, samt från offentliga register. Sådana uppgifter är inte personuppgifter
        så länge de rör organisationen och inte en enskild person.
      </p>
      <p>
        <strong>Personuppgifter i yrkesroll</strong> — namn, titel och en företagsadress till en
        kontaktperson — förekommer när en sådan uppgift är publicerad av bolaget självt, till
        exempel på en kontaktsida. Rättslig grund är berättigat intresse för B2B-kontakt, och
        intresseavvägningen bygger på att uppgiften rör personen i egenskap av yrkesutövare, att
        den redan är publicerad av arbetsgivaren, och att varje utskick bär en avregistreringslänk
        som fungerar med ett klick.
      </p>
      <p>
        Vi hämtar inte uppgifter från sociala medier, och vi köper inte listor med privata
        profiler. Hittar agenten inte tillräckligt om ett bolag lämnar den fältet tomt i stället
        för att fylla det med en gissning.
      </p>
      <p>
        En avregistrering gäller omedelbart och för alla framtida utskick, och den registreras
        oavsett om avsändaren är knuten till en arbetsyta hos oss eller inte.
      </p>

      <h2 id="sprakmodell">Att texten bearbetas av en språkmodell</h2>
      <p>
        Snajp bygger på en språkmodell. Det betyder att den text agenten arbetar med — kundmejlet
        som kommer in, och det svar som föreslås — skickas till vår modelleverantör för bearbetning.
        Vi säger det rakt ut därför att det är det som gör produkten till en produkt, och därför att
        en kund som upptäcker det senare har hittat något vi valde att inte nämna.
      </p>
      {/* HÄR STOD TIDIGARE att leverantören "inte tränar på texten". Det togs
          bort 2026-08-24 och ska inte skrivas tillbaka utan att någon läst
          det faktiska avtalet: påståendet beror helt på vilken nivå hos
          leverantören vi kör på, och gratisnivåer tillåter typiskt just det
          vi lovade bort. Ett löfte i en integritetspolicy är bindande — det
          är den ena texten på hela sajten som inte får vara optimistisk.
          Se docs/JURIDIK_ATGARDER.md, P0.1c. */}
      <p>
        Leverantören behandlar texten för vår räkning och enligt avtal. Vilka leverantörer det
        gäller, och vad respektive avtal säger om hur uppgifterna får användas, står nedan.
      </p>

      <h2 id="underleverantorer">Vilka vi delar uppgifter med</h2>
      <p>Vi använder följande underleverantörer för att driva tjänsten:</p>
      <ul>
        {/* `region` utelämnas när den är en platshållare. Fälten innehåller
            interna anvisningar — "Ange dataregion OCH avtalsnivå … se
            docs/JURIDIK_ATGARDER.md, P0.1c" — och de stod ordagrant i en
            publik juridisk handling. Att inte ange region är en lucka; att
            publicera vår egen att-göra-lista är något annat. */}
        {UNDERLEVERANTORER.map((leverantor) => (
          <li key={leverantor.namn}>
            <strong>{leverantor.namn}</strong> — {leverantor.andamal}
            {utanPlatshallare(leverantor.region) ? ` ${leverantor.region}` : null}
          </li>
        ))}
      </ul>
      <p>
        Ingen kunds data delas med en annan kund. Varje arbetsyta ligger i en egen avgränsning i
        databasen, och avgränsningen är en spärr i databasen — inte en inställning i koden.
      </p>

      <h2 id="lagring">Hur länge vi sparar uppgifter</h2>
      <p>
        {/* Retentionsperioden är beslutad: 24 månader, samma tid för samtliga
            kategorier. Se P1.1 i docs/JURIDIK_ATGARDER.md och
            gallringsfunktionen i supabase/migrations/048_gallring.sql —
            gallringsjobbets period ska stämma med talet som står här. */}
        Vi sparar uppgifterna i <strong>24 månader</strong>, räknat från den senaste behandlingen,
        och därefter gallras de. Samma tid gäller samtliga kategorier ovan. Gallringen är
        automatiserad och loggas. Kontakta oss om du vill veta vad som gäller just ditt ärende.
      </p>

      <h2 id="rattigheter">Dina rättigheter</h2>
      <p>
        Du har rätt att begära tillgång till, rättelse av och radering av dina uppgifter, samt att
        invända mot behandling som sker med stöd av berättigat intresse. Kontakta oss på{" "}
        <a href={`mailto:${dataskyddKontakt(KONTAKT_MEJL)}`}>{dataskyddKontakt(KONTAKT_MEJL)}</a>. Du
        har också rätt att klaga till
        Integritetsskyddsmyndigheten, <a href="https://imy.se">imy.se</a>.
      </p>

      <h2 id="cookies">Cookies</h2>
      <p>
        Snajp.se sätter en enda cookie, och den är strikt nödvändig. Läs mer på{" "}
        <Link href="/cookies">cookiesidan</Link>.
      </p>
    </JuridiskSida>
  );
}
