"use client";

import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { bolagsraden, dataskyddKontakt, utanPlatshallare, UNDERLEVERANTORER } from "@/lib/bolag";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Integritetspolicyn på svenska och engelska (Antons beslut 2026-10-02). Vad
 * som ska granskas innan publicering står i page.tsx. Den engelska texten är
 * en översättning av den svenska, inte en egen lydelse.
 *
 * Underleverantörernas ändamål och region kommer ur lib/bolag.ts och är än så
 * länge bara svenska.
 */
const T = {
  rubrik: { sv: "Integritetspolicy", en: "Privacy policy" },
  ingress: {
    sv: "Den här sidan beskriver hur vi behandlar personuppgifter när du besöker snajp.se, skapar ett konto eller på annat sätt är i kontakt med oss.",
    en: "This page describes how we process personal data when you visit snajp.se, create an account or are otherwise in contact with us."
  },
  innehall: { sv: "Innehåll", en: "Contents" },
  ansvarig: { sv: "Vem är personuppgiftsansvarig", en: "Who is the data controller" },
  uppgifter: { sv: "Vilka uppgifter vi behandlar och varför", en: "What data we process and why" },
  kallor: { sv: "Varifrån uppgifterna kommer", en: "Where the data comes from" },
  sprakmodell: { sv: "Att texten bearbetas av en språkmodell", en: "Text is processed by a language model" },
  underleverantorer: { sv: "Vilka vi delar uppgifter med", en: "Who we share data with" },
  lagring: { sv: "Hur länge vi sparar uppgifter", en: "How long we keep data" },
  rattigheter: { sv: "Dina rättigheter", en: "Your rights" },
  cookies: { sv: "Cookies", en: "Cookies" },
  ansvarigText: {
    sv: "är personuppgiftsansvarig för behandlingen av personuppgifter som sker när du besöker snajp.se, registrerar ett konto eller på annat sätt är i kontakt med oss.",
    en: "is the data controller for the processing of personal data that takes place when you visit snajp.se, register an account or are otherwise in contact with us."
  },
  kontakt: { sv: "Kontakt i dataskyddsfrågor:", en: "Contact for data protection matters:" },
  konto: { sv: "Kontouppgifter", en: "Account details" },
  kontoText: {
    sv: "Namn och e-postadress när du skapar ett konto eller bjuds in till en arbetsyta. Rättslig grund: fullgörande av avtal.",
    en: "Name and email address when you create an account or are invited to a workspace. Legal basis: performance of a contract."
  },
  kunddata: { sv: "Kunddata i produkten", en: "Customer data in the product" },
  kunddataText: {
    sv: "Om ditt företag använder Snajps supportagent behandlar vi, på ert uppdrag och enligt separat personuppgiftsbiträdesavtal, de personuppgifter som finns i er kundtjänstinkorg: avsändarens namn, e-postadress och meddelandeinnehåll. Vi är då personuppgiftsbiträde, inte personuppgiftsansvarig — det är ni. Se personuppgiftsbiträdesavtalet för detaljer.",
    en: "If your company uses Snajp's support agent, we process, on your behalf and under a separate data processing agreement (personuppgiftsbiträdesavtal), the personal data in your customer service inbox: the sender's name, email address and message content. We are then a data processor, not the data controller; you are. See the data processing agreement for details."
  },
  utskick: { sv: "Utskick vi själva gör", en: "Mailings we send ourselves" },
  utskickText: {
    sv: "Om vi kontaktar er som potentiell kund använder vi allmänt tillgängliga företagsuppgifter. Rättslig grund: berättigat intresse. Du kan alltid avregistrera dig via länken i mejlet, och avregistreringen gäller omedelbart och för alla framtida utskick.",
    en: "If we contact you as a potential customer, we use publicly available company information. Legal basis: legitimate interest. You can always unsubscribe through the link in the email, and the unsubscribe applies immediately and to all future mailings."
  },
  foretagsRubrik: { sv: "Företagsuppgifter", en: "Company information" },
  foretagsText: {
    sv: " — bolagsnamn, bransch, storlek, adress och offentliga kontaktvägar — hämtas från bolagets egen webbplats, deras platsannonser och pressmeddelanden, samt från offentliga register. Sådana uppgifter är inte personuppgifter så länge de rör organisationen och inte en enskild person.",
    en: " (company name, industry, size, address and public contact channels) is collected from the company's own website, its job ads and press releases, and from public registers. Such information is not personal data as long as it concerns the organisation and not an individual person."
  },
  yrkesRubrik: { sv: "Personuppgifter i yrkesroll", en: "Personal data in a professional role" },
  yrkesText: {
    sv: " — namn, titel och en företagsadress till en kontaktperson — förekommer när en sådan uppgift är publicerad av bolaget självt, till exempel på en kontaktsida. Rättslig grund är berättigat intresse för B2B-kontakt, och intresseavvägningen bygger på att uppgiften rör personen i egenskap av yrkesutövare, att den redan är publicerad av arbetsgivaren, och att varje utskick bär en avregistreringslänk som fungerar med ett klick.",
    en: " (name, title and a business address for a contact person) occurs when such information has been published by the company itself, for example on a contact page. The legal basis is legitimate interest in B2B contact, and the balancing of interests rests on the data concerning the person in their professional capacity, on it already being published by the employer, and on every mailing carrying an unsubscribe link that works with one click."
  },
  sociala: {
    sv: "Vi hämtar inte uppgifter från sociala medier, och vi köper inte listor med privata profiler. Hittar agenten inte tillräckligt om ett bolag lämnar den fältet tomt i stället för att fylla det med en gissning.",
    en: "We do not collect data from social media, and we do not buy lists of private profiles. If the agent cannot find enough about a company, it leaves the field empty instead of filling it with a guess."
  },
  avregistrering: {
    sv: "En avregistrering gäller omedelbart och för alla framtida utskick, och den registreras oavsett om avsändaren är knuten till en arbetsyta hos oss eller inte.",
    en: "An unsubscribe applies immediately and to all future mailings, and it is recorded whether or not the sender is linked to a workspace with us."
  },
  modell1: {
    sv: "Snajp bygger på en språkmodell. Det betyder att den text agenten arbetar med — kundmejlet som kommer in, och det svar som föreslås — skickas till vår modelleverantör för bearbetning. Vi säger det rakt ut därför att det är det som gör produkten till en produkt, och därför att en kund som upptäcker det senare har hittat något vi valde att inte nämna.",
    en: "Snajp is built on a language model. This means that the text the agent works with (the incoming customer email and the suggested reply) is sent to our model provider for processing. We say this plainly because it is what makes the product a product, and because a customer who finds out later has found something we chose not to mention."
  },
  modell2: {
    sv: "Leverantören behandlar texten för vår räkning och enligt avtal. Vilka leverantörer det gäller, och vad respektive avtal säger om hur uppgifterna får användas, står nedan.",
    en: "The provider processes the text on our behalf and under contract. Which providers this concerns, and what each contract says about how the data may be used, is set out below."
  },
  foljande: {
    sv: "Vi använder följande underleverantörer för att driva tjänsten:",
    en: "We use the following sub-processors to run the service:"
  },
  isolering: {
    sv: "Ingen kunds data delas med en annan kund. Varje arbetsyta ligger i en egen avgränsning i databasen, och avgränsningen är en spärr i databasen — inte en inställning i koden.",
    en: "No customer's data is shared with another customer. Each workspace is kept separate in the database, and that separation is enforced by the database itself, not by a setting in the code."
  },
  lagring1: { sv: "Vi sparar uppgifterna i", en: "We keep the data for" },
  manader: { sv: "24 månader", en: "24 months" },
  lagring2: {
    sv: ", räknat från den senaste behandlingen, och därefter gallras de. Samma tid gäller samtliga kategorier ovan. Gallringen är automatiserad och loggas. Kontakta oss om du vill veta vad som gäller just ditt ärende.",
    en: ", counted from the most recent processing, after which it is deleted. The same period applies to all the categories above. Deletion is automated and logged. Contact us if you want to know what applies to your particular case."
  },
  ratt1: {
    sv: "Du har rätt att begära tillgång till, rättelse av och radering av dina uppgifter, samt att invända mot behandling som sker med stöd av berättigat intresse. Kontakta oss på",
    en: "You have the right to request access to, rectification of and erasure of your data, and to object to processing based on legitimate interest. Contact us at"
  },
  ratt2: {
    sv: ". Du har också rätt att klaga till Integritetsskyddsmyndigheten,",
    en: ". You also have the right to lodge a complaint with the Swedish Authority for Privacy Protection (Integritetsskyddsmyndigheten),"
  },
  cookieText: {
    sv: "Snajp.se sätter en enda cookie, och den är strikt nödvändig. Läs mer på",
    en: "Snajp.se sets a single cookie, and it is strictly necessary. Read more on the"
  },
  cookieLank: { sv: "cookiesidan", en: "cookie page" }
} satisfies Record<string, Localized>;

export function IntegritetspolicySida() {
  const { text } = useLocale();
  const kontakt = dataskyddKontakt(KONTAKT_MEJL);

  return (
    <JuridiskSida rubrik={text(T.rubrik)} ingress={text(T.ingress)}>
      {/* Innehållsförteckning. Inline och inte i marginalen: JuridiskSida
          sätter 68 tecken och delas med villkors- och cookiesidan, så en
          sidokolumn hade byggts om för tre sidor för att tjäna en. Länkarna
          gör samma nytta — de gör dokumentet navigerbart och varje avsnitt
          adresserbart, så `/integritetspolicy#lagring` går att klistra in i
          ett svar till en inköpares jurist. */}
      <nav aria-label={text(T.innehall)} className="not-prose">
        <h2 id="innehall">{text(T.innehall)}</h2>
        <ul>
          <li><a href="#ansvarig">{text(T.ansvarig)}</a></li>
          <li><a href="#uppgifter">{text(T.uppgifter)}</a></li>
          <li><a href="#kallor">{text(T.kallor)}</a></li>
          <li><a href="#sprakmodell">{text(T.sprakmodell)}</a></li>
          <li><a href="#underleverantorer">{text(T.underleverantorer)}</a></li>
          <li><a href="#lagring">{text(T.lagring)}</a></li>
          <li><a href="#rattigheter">{text(T.rattigheter)}</a></li>
          <li><a href="#cookies">{text(T.cookies)}</a></li>
        </ul>
      </nav>

      <h2 id="ansvarig">{text(T.ansvarig)}</h2>
      {/* Raden byggs av det som är ifyllt. Org.nr och postadress är ännu
          platshållare och utelämnas därför helt — de stod tidigare som
          "[XXXXXX-XXXX]" mitt i meningen om vem som bär ansvaret, vilket är
          den sämsta tänkbara platsen för en text som ser påhittad ut. */}
      <p>
        {bolagsraden(", ")} {text(T.ansvarigText)}
      </p>
      <p>
        {text(T.kontakt)} <a href={`mailto:${kontakt}`}>{kontakt}</a>
      </p>

      <h2 id="uppgifter">{text(T.uppgifter)}</h2>

      <h3>{text(T.konto)}</h3>
      <p>{text(T.kontoText)}</p>

      <h3>{text(T.kunddata)}</h3>
      <p>{text(T.kunddataText)}</p>

      <h3>{text(T.utskick)}</h3>
      <p>{text(T.utskickText)}</p>

      <h2 id="kallor">{text(T.kallor)}</h2>
      <p>
        <strong>{text(T.foretagsRubrik)}</strong>
        {text(T.foretagsText)}
      </p>
      <p>
        <strong>{text(T.yrkesRubrik)}</strong>
        {text(T.yrkesText)}
      </p>
      <p>{text(T.sociala)}</p>
      <p>{text(T.avregistrering)}</p>

      <h2 id="sprakmodell">{text(T.sprakmodell)}</h2>
      <p>{text(T.modell1)}</p>
      {/* HÄR STOD TIDIGARE att leverantören "inte tränar på texten". Det togs
          bort 2026-08-24 och ska inte skrivas tillbaka utan att någon läst
          det faktiska avtalet: påståendet beror helt på vilken nivå hos
          leverantören vi kör på, och gratisnivåer tillåter typiskt just det
          vi lovade bort. Ett löfte i en integritetspolicy är bindande — det
          är den ena texten på hela sajten som inte får vara optimistisk.
          Se docs/JURIDIK_ATGARDER.md, P0.1c. */}
      <p>{text(T.modell2)}</p>

      <h2 id="underleverantorer">{text(T.underleverantorer)}</h2>
      <p>{text(T.foljande)}</p>
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
      <p>{text(T.isolering)}</p>

      <h2 id="lagring">{text(T.lagring)}</h2>
      <p>
        {/* Retentionsperioden är beslutad: 24 månader, samma tid för samtliga
            kategorier. Se P1.1 i docs/JURIDIK_ATGARDER.md och
            gallringsfunktionen i supabase/migrations/048_gallring.sql —
            gallringsjobbets period ska stämma med talet som står här. */}
        {text(T.lagring1)} <strong>{text(T.manader)}</strong>
        {text(T.lagring2)}
      </p>

      <h2 id="rattigheter">{text(T.rattigheter)}</h2>
      <p>
        {text(T.ratt1)} <a href={`mailto:${kontakt}`}>{kontakt}</a>
        {text(T.ratt2)} <a href="https://imy.se">imy.se</a>.
      </p>

      <h2 id="cookies">{text(T.cookies)}</h2>
      <p>
        {text(T.cookieText)} <Link href="/cookies">{text(T.cookieLank)}</Link>.
      </p>
    </JuridiskSida>
  );
}
