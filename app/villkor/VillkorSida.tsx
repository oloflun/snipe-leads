"use client";

import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { BOLAG } from "@/lib/bolag";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Användarvillkoren på svenska och engelska. Varför avsnitten om pris och
 * ansvarsbegränsning står oskrivna men synliga förklaras i page.tsx. Den
 * engelska texten är en översättning av den svenska, inte en egen lydelse.
 */
const T = {
  rubrik: { sv: "Användarvillkor", en: "Terms of service" },
  tjansten: { sv: "Tjänsten", en: "The service" },
  tjanstenText: {
    sv: "Snajp levererar en eller flera agenter enligt vad Kunden tecknat: supportagenten, som läser och besvarar inkommande kundmejl; leadsagenten, som tar fram prospekt och skriver utgående mejl; och, i förekommande fall, kvittohanteraren, som läser av kvitton ur Kundens kopplade mejlkonto och uppladdade filer.",
    en: "Snajp provides one or more agents according to what the Customer has subscribed to: the support agent, which reads and answers incoming customer emails; the leads agent, which finds prospects and writes outbound emails; and, where applicable, the receipt handler, which reads receipts from the Customer's connected email account and uploaded files."
  },
  kundensAnsvar: { sv: "Kundens ansvar", en: "The Customer's responsibilities" },
  ansvar1: {
    sv: "Kunden ansvarar för att de uppgifter som matas in i tjänsten — till exempel den kundtjänstinkorg som kopplas in — får behandlas av Snajp enligt gällande rätt, och för att informera sina egna kunder och besökare om detta på sin egen webbplats.",
    en: "The Customer is responsible for ensuring that the data entered into the service, for example the customer service inbox that is connected, may be processed by Snajp under applicable law, and for informing its own customers and visitors about this on its own website."
  },
  ansvar2: {
    sv: "Kunden ansvarar även för att arkivera räkenskapsinformation i enlighet med bokföringslagen. Snajps kvittohanterare lagrar inte originalunderlag som kvitton, fakturor eller mejl, och ersätter inte Kundens egen arkiveringsskyldighet.",
    en: "The Customer is also responsible for archiving accounting records in accordance with the Swedish Bookkeeping Act (bokföringslagen). Snajp's receipt handler does not store original records such as receipts, invoices or emails, and does not replace the Customer's own obligation to archive them."
  },
  ansvar3: {
    sv: "Kunden ansvarar för att informera sina egna kunder om att inkommande ärenden behandlas med hjälp av AI, i enlighet med artikel 13 i dataskyddsförordningen. Snajp tillhandahåller en textmall för detta, men ansvaret för att texten finns på Kundens webbplats och stämmer med Kundens verksamhet är Kundens.",
    en: "The Customer is responsible for informing its own customers that incoming cases are processed with the help of AI, in accordance with Article 13 of the General Data Protection Regulation (dataskyddsförordningen). Snajp provides a text template for this, but the responsibility for the text being on the Customer's website and matching the Customer's business lies with the Customer."
  },
  autonomiRubrik: {
    sv: "Autonominivån är Kundens val och Kundens ansvar.",
    en: "The level of autonomy is the Customer's choice and the Customer's responsibility."
  },
  autonomi: {
    sv: "Snajps supportagent levereras med mänsklig granskning påslagen för samtliga ärendekategorier. Kunden kan ställa om enskilda kategorier till automatiskt svar. Gör Kunden det upphör den mänskliga inblandningen för de kategorierna, och Kunden ansvarar för att bedöma vad det innebär enligt artikel 22 i dataskyddsförordningen.",
    en: "Snajp's support agent is delivered with human review switched on for all case categories. The Customer can switch individual categories to automatic replies. If the Customer does so, human involvement ends for those categories, and the Customer is responsible for assessing what that means under Article 22 of the General Data Protection Regulation."
  },
  utskick: {
    sv: "Utgående mejl från leadsagenten skickas i Kundens namn. Snajp kontrollerar i kod att varje utskick bär Kundens fullständiga företagsnamn, organisationsnummer, postadress och en fungerande avregistreringslänk, och blockerar utskick som saknar något av det. Kunden ansvarar för att de uppgifter vi identifierar Kunden med är korrekta.",
    en: "Outbound emails from the leads agent are sent in the Customer's name. Snajp checks in code that every email carries the Customer's full company name, company registration number, postal address and a working unsubscribe link, and blocks any email that lacks one of these. The Customer is responsible for the details we identify the Customer by being correct."
  },
  // Preliminär lydelse 2026-10-08 (Antons godkännande), ej juridiskt granskad:
  // webbpoolen, app/leads/webbpool.py och INV-SEC-008.
  bolagsdata: {
    sv: "Offentliga uppgifter om bolag (namn, organisationsnummer, webbplats, ort, län och bransch) och Snajps egen bedömning av ett bolags publika webbplats är inte Kundens data. Snajp får använda dem för egna ändamål, även i tjänster till andra kunder. Det gäller aldrig personuppgifter, Kundens utkast, anteckningar eller status, och aldrig uppgiften om att just Kunden har bearbetat ett visst bolag.",
    en: "Public information about companies (name, company registration number, website, town, county and industry) and Snajp's own assessment of a company's public website is not Customer data. Snajp may use it for its own purposes, including in services to other customers. This never covers personal data, the Customer's drafts, notes or status, nor the fact that the Customer in particular has worked with a given company."
  },
  pub: { sv: "Personuppgiftsbehandling", en: "Processing of personal data" },
  pubText: {
    sv: "I den mån Snajp behandlar personuppgifter för Kundens räkning gäller det separata personuppgiftsbiträdesavtalet, som är en integrerad del av detta avtal. Där framgår också vilka underleverantörer som anlitas. Snajps behandling som personuppgiftsansvarig beskrivs i",
    en: "To the extent Snajp processes personal data on the Customer's behalf, the separate data processing agreement (personuppgiftsbiträdesavtal) applies, and it forms an integral part of this agreement. It also lists the sub-processors used. Snajp's processing as data controller is described in the"
  },
  policyLank: { sv: "integritetspolicyn", en: "privacy policy" },
  pris: { sv: "Pris och betalning", en: "Price and payment" },
  pris1: {
    sv: "Det här avsnittet är inte fastställt. Priserna framgår av",
    en: "This section has not been settled. Prices are shown in the"
  },
  prislistan: { sv: "prislistan", en: "price list" },
  pris2: {
    sv: ", men betalningsvillkor, indexering och vad som gäller vid utebliven betalning är inte reglerat här. Skriv till oss på",
    en: ", but payment terms, indexation and what applies in case of non-payment are not governed here. Write to us at"
  },
  innanAvtal: { sv: "innan avtal tecknas.", en: "before entering into a contract." },
  ansvarsbegransning: { sv: "Ansvarsbegränsning", en: "Limitation of liability" },
  ansvarsbegransningText: {
    sv: "Det här avsnittet är inte fastställt. Klausulen avgör vad ett fel kostar, och vi skriver den inte själva — den ska formuleras av jurist. Tills dess finns ingen avtalad ansvarsbegränsning. Skriv till oss på",
    en: "This section has not been settled. The clause decides what an error costs, and we do not write it ourselves; it is to be drafted by a lawyer. Until then there is no agreed limitation of liability. Write to us at"
  },
  uppsagning: { sv: "Uppsägning och vad som händer med data", en: "Termination and what happens to data" },
  uppsagning1: {
    sv: "Uppsägningstiden är inte fastställd i de här villkoren. Bindningstiden är noll månader, vilket inte är samma sak — skriv till oss på",
    en: "The notice period is not set in these terms. The minimum term is zero months, which is not the same thing. Write to us at"
  },
  uppsagning2: {
    sv: "Vid avtalets upphörande raderas eller återlämnas Kundens personuppgifter enligt personuppgiftsbiträdesavtalets klausul om radering och återlämning, inom den tid som anges där. Se även avsnittet om lagringstider i",
    en: "When the agreement ends, the Customer's personal data is deleted or returned under the deletion and return clause of the data processing agreement, within the time stated there. See also the section on retention periods in the"
  },
  distans: { sv: "Distansavtal och ångerrätt", en: "Distance contracts and right of withdrawal" },
  distans1: {
    sv: "Avtalet ingås på distans. Vad det innebär — och varför distansavtalslagens ångerrätt inte gäller företagsavtal — beskrivs på sidan",
    en: "The agreement is concluded at a distance. What that means, and why the right of withdrawal under the Swedish Distance Contracts Act (distansavtalslagen) does not apply to business contracts, is described on the page"
  },
  distans2: {
    sv: ", som är en del av förhandsinformationen vid registreringen.",
    en: ", which is part of the information given in advance at sign-up."
  },
  lag: { sv: "Tillämplig lag", en: "Governing law" },
  lagText: { sv: "Svensk rätt gäller.", en: "Swedish law applies." }
} satisfies Record<string, Localized>;

function ingress(namn: string): Localized {
  return {
    sv: `Dessa villkor gäller mellan ${namn} ("Snajp") och det företag ("Kunden") som registrerar ett konto eller tecknar avtal om Snajps tjänster.`,
    en: `These terms apply between ${namn} ("Snajp") and the company ("the Customer") that registers an account or enters into an agreement for Snajp's services.`
  };
}

export function VillkorSida() {
  const { text } = useLocale();
  const mejl = <a href={`mailto:${KONTAKT_MEJL}`}>{KONTAKT_MEJL}</a>;

  return (
    <JuridiskSida rubrik={text(T.rubrik)} ingress={text(ingress(BOLAG.namn))}>
      <h2>{text(T.tjansten)}</h2>
      <p>{text(T.tjanstenText)}</p>

      <h2>{text(T.kundensAnsvar)}</h2>
      <p>{text(T.ansvar1)}</p>
      <p>{text(T.ansvar2)}</p>
      <p>{text(T.ansvar3)}</p>
      <p>
        <strong>{text(T.autonomiRubrik)}</strong> {text(T.autonomi)}
      </p>
      <p>{text(T.utskick)}</p>
      <p>{text(T.bolagsdata)}</p>

      <h2>{text(T.pub)}</h2>
      <p>
        {text(T.pubText)} <Link href="/integritetspolicy">{text(T.policyLank)}</Link>.
      </p>

      <h2>{text(T.pris)}</h2>
      <p>
        {text(T.pris1)} <Link href="/#priser">{text(T.prislistan)}</Link>
        {text(T.pris2)} {mejl} {text(T.innanAvtal)}
      </p>

      <h2>{text(T.ansvarsbegransning)}</h2>
      <p>
        {text(T.ansvarsbegransningText)} {mejl} {text(T.innanAvtal)}
      </p>

      <h2>{text(T.uppsagning)}</h2>
      <p>
        {text(T.uppsagning1)} {mejl} {text(T.innanAvtal)}
      </p>
      <p>
        {text(T.uppsagning2)} <Link href="/integritetspolicy">{text(T.policyLank)}</Link>.
      </p>

      <h2>{text(T.distans)}</h2>
      <p>
        {text(T.distans1)} <Link href="/angerratt">{text(T.distans)}</Link>
        {text(T.distans2)}
      </p>

      <h2>{text(T.lag)}</h2>
      <p>{text(T.lagText)}</p>
    </JuridiskSida>
  );
}
