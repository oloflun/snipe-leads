"use client";

import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";

/**
 * Löftet, direkt under hjältebilden.
 *
 * ## Varför sektionen numera vet vilken produkt sidan visar
 *
 * Den här texten var EN text som renderades på både /leads och /support, och
 * den beskrev kundtjänst: "sorterar inkorgen", "kundtjänstinkorg", "svarar ur
 * er kunskapsbas". På leads-sidan lovade alltså rubriken en säljare medan
 * första löftet under den beskrev en supportagent. Sektionen tar nu emot
 * `product` och har en uppsättning texter per produkt. Lägger man till en text
 * här hör den hemma i EN av de två, aldrig i båda.
 *
 * ## Varför siffran står som ett spann och med ett förbehåll
 *
 * Kunden gav "50–70 % av det repetitiva jobbet". Den siffran är ett estimat,
 * inte en uppmätt effekt hos en befintlig kund — och en procentsats utan
 * förbehåll läses som ett garanterat resultat. Blir utfallet 30 % hos den
 * första kunden är det vi som har lovat för mycket, i skrift, på förstasidan.
 * Därför står "räknar vi med" i hjältetexten på supportsidan.
 *
 * ## Varför kontrollen upprepas
 *
 * "Ni har sista ordet" står både i rubriken och som en egen punkt. Det är
 * avsiktligt: invändningen mot en AI som skriver i kundens namn ska mötas
 * innan läsaren hinner formulera den, inte längre ner på sidan.
 */

type ProduktCopy = {
  rubrik: Localized;
  lede: Localized;
  punkter: { sv: string[][]; en: string[][] };
};

const leads: ProduktCopy = {
  rubrik: {
    sv: "Leads som kommer till dig – du har alltid sista ordet.",
    en: "Leads that come to you, and you always have the final say."
  },
  lede: {
    sv: "Leads-agenten letar prospekt baserat på er produkt och gör en behovsanalys som den senare använder för att skapa professionella utgående mail.",
    en: "The leads agent finds prospects based on your product and works out what they need, then uses that analysis to write professional outgoing emails."
  },
  punkter: {
    sv: [
      ["Hittar rätt bolag", "Agenterna letar prospekt utifrån er produkt och gör en behovsanalys innan en enda rad skrivs."],
      ["Personliga, professionella mail", "Behovsanalysen och ert erbjudande går in i mejlet. Ni får ett utkast att ändra i, inte en mall att fylla i."],
      ["Ni har sista ordet", "Inget går ut utan att ni bestämt det. Mailen granskas alltid av en människa innan de skickas."]
    ],
    en: [
      ["Finds the right companies", "The agents look for prospects based on your product and work out the need before a single line is written."],
      ["Personal, professional emails", "The analysis and your offer go into the email. You get a draft to edit, not a template to fill in."],
      ["You have the final say", "Nothing goes out unless you decide it does. Every email is reviewed by a person before it is sent."]
    ]
  }
};

const support: ProduktCopy = {
  rubrik: {
    sv: "AI som sorterar och svarar, men ni har alltid kontrollen",
    en: "AI that sorts and answers, while you stay in control"
  },
  lede: {
    sv: "Mejlen sorteras automatiskt i rätt fack och får färdiga, korrekta svar ur er egen kunskapsbas. Ni läser igenom och godkänner innan något går ut.",
    en: "Emails are sorted into the right category and get complete, accurate replies from your own knowledge base. You read them through and approve before anything goes out."
  },
  punkter: {
    sv: [
      ["Sorteras automatiskt", "Varje mejl hamnar i rätt fack: garanti, leverans, betalning, teknisk support. Ni slutar sortera för hand."],
      ["Färdiga, korrekta svar", "Agenterna svarar utifrån ER kunskapsbas, inte ur en allmän modell. Saknas svaret säger de det i stället för att gissa. Om de mot förmodan inte kan ge ett svar, så eskalerar de och skickar vidare."],
      ["Ni har sista ordet", "Inget går ut utan att ni bestämt det. Mailen granskas alltid av en människa innan de skickas."]
    ],
    en: [
      ["Sorted automatically", "Every email lands in the right category: warranty, delivery, payment, technical support. No more manual triage."],
      ["Complete, accurate replies", "The agents answer from YOUR knowledge base, not from a general model. If the answer is missing they say so instead of guessing. Should they still be unable to answer, they escalate and hand the case on."],
      ["You have the final say", "Nothing goes out unless you decide it does. Every email is reviewed by a person before it is sent."]
    ]
  }
};

const perProdukt: Record<ProductKey, ProduktCopy> = { leads, support };

export function UspSection({ product }: Readonly<{ product: ProductKey }>) {
  const { locale, text } = useLocale();
  const copy = perProdukt[product];
  const punkter = copy.punkter[locale];

  return (
    <section
      id="loftet"
      aria-labelledby="loftet-rubrik"
      className="border-t border-ink/15 bg-paper"
    >
      <div className="mx-auto max-w-[1480px] px-6 py-20 md:px-10 md:py-28">
        <h2
          id="loftet-rubrik"
          className="max-w-[22ch] font-display text-[clamp(2rem,4.6vw,3.5rem)] font-semibold leading-[1.03] tracking-[-0.03em]"
        >
          {text(copy.rubrik)}
        </h2>

        <p className="mt-6 max-w-[58ch] text-[1.125rem] leading-[1.65] text-ink/80">
          {text(copy.lede)}
        </p>

        <div className="mt-14 grid gap-8 md:grid-cols-3 md:gap-10">
          {punkter.map(([rubrik, brod]) => (
            <div key={rubrik} className="border-t border-ink/15 pt-5">
              {/* Inget "01" här. Numreringen var gul, satt över varje rubrik
                  och läste som en ordningsföljd punkterna inte har. */}
              <h3 className="text-[1.0625rem] font-semibold tracking-[-0.01em]">{rubrik}</h3>
              <p className="mt-2 max-w-[42ch] text-[0.9375rem] leading-[1.6] text-ink/70">
                {brod}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
