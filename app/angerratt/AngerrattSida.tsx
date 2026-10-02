"use client";

import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { BOLAG } from "@/lib/bolag";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Sidan om distansavtal och ångerrätt, på svenska och engelska. Rättsläget och
 * varför texten säger det rakt ut står i page.tsx. Den engelska texten är en
 * översättning av den svenska; svenska lagnamn och SFS-nummer står kvar inom
 * parentes så att läsaren kan slå upp källan.
 */
const T = {
  rubrik: { sv: "Distansavtal och ångerrätt", en: "Distance contracts and right of withdrawal" },
  vadLagenAr: { sv: "Vad distansavtalslagen är", en: "What the Distance Contracts Act is" },
  lagen1: {
    sv: "Distansavtalslagen ger",
    en: "The Swedish Distance Contracts Act (distansavtalslagen) gives"
  },
  konsumenter: { sv: "konsumenter", en: "consumers" },
  lagen2: {
    sv: "ett särskilt skydd när avtal ingås på distans, till exempel via en webbplats: rätt till tydlig förhandsinformation och som huvudregel 14 dagars ångerrätt räknat från den dag avtalet ingicks. Med konsument menar lagen en fysisk person som handlar huvudsakligen för ändamål som ligger utanför näringsverksamhet.",
    en: "special protection when a contract is concluded at a distance, for example through a website: the right to clear information in advance and, as a main rule, a 14-day right of withdrawal counted from the day the contract was concluded. By consumer, the Act means a natural person acting mainly for purposes outside a business activity."
  },
  medSnajp: { sv: "Vad som gäller för avtal med Snajp", en: "What applies to contracts with Snajp" },
  foretag1: { sv: "Snajps tjänster riktar sig till", en: "Snajp's services are aimed at" },
  foretag: { sv: "företag", en: "businesses" },
  foretag2: {
    sv: ". Avtalet tecknas av en näringsidkare, för användning i näringsverksamhet, och vid registreringen anges organisationsnummer. För sådana företagsavtal gäller distansavtalslagen inte, och det finns därför",
    en: ". The contract is entered into by a trader, for use in a business activity, and a company registration number is given at sign-up. The Distance Contracts Act does not apply to such business contracts, and there is therefore"
  },
  ingenAngerratt: { sv: "ingen lagstadgad ångerrätt", en: "no statutory right of withdrawal" },
  foretag3: {
    sv: ". Det gäller även enskilda näringsidkare som tecknar avtalet för sin verksamhet.",
    en: ". This also applies to sole traders who enter into the contract for their business."
  },
  konsumentfallet: {
    sv: "Skulle en fysisk person ändå ha ingått avtalet huvudsakligen för privat bruk räknas den personen som konsument, och då gäller lagens ångerrätt: 14 dagar från avtalsdagen att ångra sig genom ett tydligt meddelande till oss, till exempel via e-post. Konsumentverkets standardformulär för ångerrätt går också bra att använda. Har tjänsten med konsumentens uttryckliga samtycke börjat utföras under ångerfristen kan ersättning för den utförda delen tas ut, och när tjänsten fullgjorts upphör ångerrätten.",
    en: "If a natural person has nevertheless entered into the contract mainly for private use, that person counts as a consumer, and the Act's right of withdrawal then applies: 14 days from the day of the contract to withdraw by sending us a clear statement, for example by email. The standard withdrawal form from the Swedish Consumer Agency (Konsumentverket) may also be used. If, with the consumer's express consent, performance of the service has begun during the withdrawal period, payment may be charged for the part already performed, and the right of withdrawal ends once the service has been fully performed."
  },
  istallet: {
    sv: "Vad som gäller i stället — oavsett ångerrätt",
    en: "What applies instead, regardless of the right of withdrawal"
  },
  medvetet: {
    sv: "Vi har medvetet byggt avtalet så att frågan sällan behöver ställas på sin spets:",
    en: "We have deliberately built the contract so that the question rarely needs to come to a head:"
  },
  gratisRubrik: { sv: "Två månader gratis.", en: "Two months free." },
  gratis: {
    sv: "Varje nytt konto börjar med en fri provperiod på två kalendermånader från kontoskapandet. Inga betalningsuppgifter lämnas vid registreringen, och vi hör av oss i god tid innan perioden tar slut.",
    en: "Every new account starts with a free trial of two calendar months from the day the account is created. No payment details are given at sign-up, and we will be in touch well before the period ends."
  },
  bindningRubrik: { sv: "Ingen bindningstid.", en: "No minimum term." },
  bindning: {
    sv: "Avtalet kan avslutas när som helst — under gratisperioden utan någon kostnad alls.",
    en: "The contract can be ended at any time, and during the free period at no cost at all."
  },
  faktureringRubrik: { sv: "Fakturering i efterhand.", en: "Invoicing in arrears." },
  fakturering: {
    sv: "Betalning sker mot faktura först efter gratisperioden. Det dras aldrig pengar automatiskt från något kort.",
    en: "Payment is made by invoice, and only after the free period. Money is never charged automatically to any card."
  },
  avsluta: {
    sv: "Vill ni avsluta, eller åberopa ångerrätt i konsumentfallet ovan, skriv till",
    en: "If you want to end the contract, or invoke the right of withdrawal in the consumer case above, write to"
  },
  ovriga: { sv: "Övriga villkor", en: "Other terms" },
  ovriga1: {
    sv: "Den här sidan är information enligt distansavtalslagen, inte hela avtalet. Avtalet i övrigt framgår av",
    en: "This page is information under the Distance Contracts Act, not the whole contract. The rest of the contract is set out in the"
  },
  villkorLank: { sv: "användarvillkoren", en: "terms of service" },
  ovriga2: { sv: ", och hur personuppgifter behandlas av", en: ", and how personal data is processed in the" },
  policyLank: { sv: "integritetspolicyn", en: "privacy policy" }
} satisfies Record<string, Localized>;

function ingress(namn: string): Localized {
  return {
    sv: `Så här förhåller sig avtal med ${namn} ("Snajp") till lagen om distansavtal och avtal utanför affärslokaler (2005:59), ofta kallad distansavtalslagen.`,
    en: `How contracts with ${namn} ("Snajp") relate to the Swedish Act on Distance Contracts and Off-Premises Contracts (lagen om distansavtal och avtal utanför affärslokaler, SFS 2005:59), often called the Distance Contracts Act (distansavtalslagen).`
  };
}

export function AngerrattSida() {
  const { text } = useLocale();

  return (
    <JuridiskSida rubrik={text(T.rubrik)} ingress={text(ingress(BOLAG.namn))}>
      <h2>{text(T.vadLagenAr)}</h2>
      <p>
        {text(T.lagen1)} <strong>{text(T.konsumenter)}</strong> {text(T.lagen2)}
      </p>

      <h2>{text(T.medSnajp)}</h2>
      <p>
        {text(T.foretag1)} <strong>{text(T.foretag)}</strong>
        {text(T.foretag2)} <strong>{text(T.ingenAngerratt)}</strong>
        {text(T.foretag3)}
      </p>
      <p>{text(T.konsumentfallet)}</p>

      <h2>{text(T.istallet)}</h2>
      <p>{text(T.medvetet)}</p>
      <ul>
        <li>
          <strong>{text(T.gratisRubrik)}</strong> {text(T.gratis)}
        </li>
        <li>
          <strong>{text(T.bindningRubrik)}</strong> {text(T.bindning)}
        </li>
        <li>
          <strong>{text(T.faktureringRubrik)}</strong> {text(T.fakturering)}
        </li>
      </ul>
      <p>
        {text(T.avsluta)} <a href={`mailto:${KONTAKT_MEJL}`}>{KONTAKT_MEJL}</a>.
      </p>

      <h2>{text(T.ovriga)}</h2>
      <p>
        {text(T.ovriga1)} <Link href="/villkor">{text(T.villkorLank)}</Link>
        {text(T.ovriga2)} <Link href="/integritetspolicy">{text(T.policyLank)}</Link>.
      </p>
    </JuridiskSida>
  );
}
