import type { KundEkonomi } from "@/lib/admin/halsa";
import { MARGINAL_GRON, MARGINAL_ROD, TYST_EFTER_DAGAR, sammanfattaPortfolj } from "@/lib/admin/halsa";
import type { Locale } from "@/lib/i18n";
import { PAKET, formateraPris } from "@/lib/pricing";

/**
 * Rådgivaren ni frågar om siffrorna.
 *
 * ## Varför den RÄKNAR i stället för att fråga en modell
 *
 * Det uppenbara vore ett LLM-anrop. Två skäl att låta bli, och det andra är
 * det som avgjorde:
 *
 *  1. Det kräver en API-nyckel vi inte har satt, och en attrapp som låtsas
 *     svara är sämre än inget svar alls.
 *  2. **En modell som får en tabell och en fråga om marginal kommer att
 *     hallucinera ett tal.** Den kommer att låta säker, siffran kommer att se
 *     rimlig ut, och ingen kommer att kontrollera den. Frågorna här handlar om
 *     intäkter — det är den sämsta tänkbara platsen för ett svar som är nästan
 *     rätt.
 *
 * Svaren nedan räknas ur samma `KundEkonomi` som tabellen visar. De kan inte
 * säga emot vad du ser på skärmen, och de kan inte hitta på.
 *
 * ## Vad det kostar
 *
 * Den förstår bara frågor den känner igen. Det är en verklig begränsning, och
 * den erkänns i svaret i stället för att döljas bakom ett gissat svar — se
 * `OKAND_FRAGA`. Kopplas en riktig modell in senare bör den få de här
 * uträkningarna som VERKTYG, inte ersätta dem.
 *
 * ## Tvåspråkigheten
 *
 * Varje svar formuleras på båda språken, och NYCKELORDEN matchar båda oavsett
 * vilket språk gränssnittet står i. Skälet till det senare är att den som
 * ställer om till engelska ändå skriver "vilka är tysta?" ibland — en matchare
 * som bara förstår det valda språket hade svarat "den frågan kan jag inte
 * räkna på" på en fråga den mycket väl kan räkna på.
 */

export type Svar = {
  text: string;
  /** Frågor som ligger nära, att erbjuda som knappar. */
  foljdfragor: string[];
};

/** Frågeetiketterna. Nyckeln används internt; texten visas på knapparna. */
const FRAGOR = {
  totalt: { sv: "Hur går det totalt?", en: "How are we doing overall?" },
  atgard: { sv: "Vilka kunder kräver åtgärd?", en: "Which customers need attention?" },
  kostar: { sv: "Vem kostar mest?", en: "Who costs the most?" },
  perKund: { sv: "Vad tjänar vi per kund?", en: "What do we earn per customer?" },
  tysta: { sv: "Vilka är tysta?", en: "Which ones are dormant?" },
  storst: {
    sv: "Vad händer om vi tappar största kunden?",
    en: "What happens if we lose the largest customer?"
  }
} as const;

type Fraganyckel = keyof typeof FRAGOR;

export function exempelfragor(locale: Locale): string[] {
  return (Object.keys(FRAGOR) as Fraganyckel[]).map((k) => FRAGOR[k][locale]);
}

function foljd(locale: Locale, ...nycklar: Fraganyckel[]): string[] {
  return nycklar.map((n) => FRAGOR[n][locale]);
}

const OKAND_FRAGA = {
  sv:
    "Den frågan kan jag inte räkna på. Jag svarar bara på det jag kan härleda ur " +
    "kundtabellen — intäkt, kostnad, marginal, användning och risk. Jag gissar inte, " +
    "eftersom ett nästan rätt tal om intäkter är värre än inget tal.",
  en:
    "I cannot compute that one. I only answer what I can derive from the customer table — " +
    "revenue, cost, margin, usage and risk. I do not guess, because a nearly-right number " +
    "about revenue is worse than no number at all."
};

function namnge(rader: Rad[]): string {
  return rader.map((r) => r.namn).join(", ");
}

export type Rad = { namn: string; ekonomi: KundEkonomi };

export function fragaRadgivaren(fraga: string, rader: Rad[], locale: Locale = "sv"): Svar {
  const f = fraga.toLowerCase();
  const p = sammanfattaPortfolj(rader.map((r) => r.ekonomi));
  const sv = locale === "sv";

  const traffar = (...ord: string[]) => ord.some((o) => f.includes(o));

  if (rader.length === 0) {
    return {
      text: sv
        ? "Det finns inga kunder att räkna på ännu. Tom lista är ett giltigt svar, inte ett fel."
        : "There are no customers to compute on yet. An empty list is a valid answer, not a failure.",
      foljdfragor: []
    };
  }

  // -- Helheten ------------------------------------------------------------
  if (
    traffar("totalt", "hur går det", "läget", "sammanfatt", "överblick") ||
    traffar("overall", "how are we", "summary", "total", "doing")
  ) {
    const marginal = p.marginal === null ? "—" : `${Math.round(p.marginal * 100)} %`;
    const problem = p.fordelning.dalig + p.fordelning.tyst;
    return {
      text: sv
        ? `${p.antalBetalande} av ${p.antalKunder} kunder betalar, tillsammans ` +
          `${formateraPris(p.mrr)} i månaden. Uppskattad tokenkostnad är ` +
          `${formateraPris(Math.round(p.kostnad))}, vilket ger ${marginal} marginal.\n\n` +
          (problem === 0
            ? "Ingen kund kräver en åtgärd just nu."
            : `${problem} kund(er) kräver en åtgärd: ${p.fordelning.dalig} med låg marginal och ` +
              `${p.fordelning.tyst} som inte använder tjänsten.`)
        : `${p.antalBetalande} of ${p.antalKunder} customers pay, together ` +
          `${formateraPris(p.mrr)} per month. Estimated token cost is ` +
          `${formateraPris(Math.round(p.kostnad))}, giving a ${marginal} margin.\n\n` +
          (problem === 0
            ? "No customer needs attention right now."
            : `${problem} customer(s) need attention: ${p.fordelning.dalig} on a thin margin and ` +
              `${p.fordelning.tyst} not using the service.`),
      foljdfragor: foljd(locale, "atgard", "kostar")
    };
  }

  // -- Åtgärdslistan -------------------------------------------------------
  if (
    traffar("åtgärd", "problem", "oroa", "risk", "dålig", "illa") ||
    traffar("attention", "worry", "bad", "trouble", "act")
  ) {
    const daliga = rader.filter((r) => r.ekonomi.halsa === "dalig");
    const tysta = rader.filter((r) => r.ekonomi.halsa === "tyst");
    if (daliga.length === 0 && tysta.length === 0) {
      return {
        text: sv
          ? "Ingen kund ligger under gränserna just nu. Alla använder tjänsten och betalar mer än de kostar."
          : "No customer is below the thresholds right now. Everyone is using the service and paying more than they cost.",
        foljdfragor: foljd(locale, "totalt")
      };
    }
    const delar: string[] = [];
    if (daliga.length > 0) {
      delar.push(
        sv
          ? `LÅG MARGINAL (${daliga.length}): ${namnge(daliga)}. ` +
              `Kostnaden äter upp intäkten. Se över paket eller volymtak.`
          : `THIN MARGIN (${daliga.length}): ${namnge(daliga)}. ` +
              `Cost is eating the revenue. Review the plan or the volume cap.`
      );
    }
    if (tysta.length > 0) {
      delar.push(
        sv
          ? `TYSTA (${tysta.length}): ${namnge(tysta)}. Ingen aktivitet på över ` +
              `${TYST_EFTER_DAGAR} dagar. De ser lönsamma ut just för att de inte används — ` +
              `hör av er innan de gör det.`
          : `DORMANT (${tysta.length}): ${namnge(tysta)}. No activity for over ` +
              `${TYST_EFTER_DAGAR} days. They look profitable precisely because they are unused — ` +
              `reach out before they do.`
      );
    }
    return { text: delar.join("\n\n"), foljdfragor: foljd(locale, "kostar", "totalt") };
  }

  // -- Kostnad -------------------------------------------------------------
  if (
    traffar("kostar mest", "dyrast", "kostnad", "tokens", "förbrukning") ||
    traffar("costs the most", "most expensive", "cost", "consumption")
  ) {
    const sorterad = [...rader].sort((a, b) => b.ekonomi.kostnad - a.ekonomi.kostnad);
    const topp = sorterad.slice(0, 3);
    const lista = topp
      .map(
        (r, i) =>
          `${i + 1}. ${r.namn} — ${formateraPris(Math.round(r.ekonomi.kostnad))} ${
            sv ? "av" : "of"
          } ${formateraPris(r.ekonomi.intakt)} ${sv ? "i intäkt" : "in revenue"}` +
          (r.ekonomi.marginal !== null
            ? ` (${Math.round(r.ekonomi.marginal * 100)} % ${sv ? "marginal" : "margin"})`
            : "")
      )
      .join("\n");
    return {
      text: sv
        ? `Störst tokenkostnad:\n${lista}\n\n` +
          "Talen är uppskattningar, inte fakturor. Se fotnoten under tabellen."
        : `Highest token cost:\n${lista}\n\n` +
          "These are estimates, not invoices. See the footnote below the table.",
      foljdfragor: foljd(locale, "atgard", "perKund")
    };
  }

  // -- Intäkt per kund -----------------------------------------------------
  if (
    traffar("per kund", "tjänar vi", "intäkt", "mrr", "snitt") ||
    traffar("per customer", "we earn", "revenue", "average")
  ) {
    const snitt = p.antalBetalande > 0 ? p.mrr / p.antalBetalande : 0;
    const paketrader = PAKET.map((paket) => {
      const antal = rader.filter((r) => r.ekonomi.paketNamn === paket.namn).length;
      // Ett paket utan satt pris räknas inte in i en intäktsfördelning.
      // Att visa "0 kr" hade dragit ner snittet med ett tal som inte finns.
      const pris =
        paket.prisPerManad === null
          ? sv
            ? "pris ej satt"
            : "no price set"
          : formateraPris(paket.prisPerManad);
      return sv
        ? `${paket.namn}: ${antal} st à ${pris}`
        : `${paket.namn}: ${antal} at ${pris}`;
    }).join("\n");
    return {
      text: sv
        ? `Snittintäkt per betalande kund är ${formateraPris(Math.round(snitt))} i månaden.\n\n` +
          `Fördelning:\n${paketrader}\n\n` +
          "Paketet härleds ur aktivitet, inte ur en produktkolumn — en kund som betalar utan " +
          "att använda visas därför fel här."
        : `Average revenue per paying customer is ${formateraPris(Math.round(snitt))} per month.\n\n` +
          `Breakdown:\n${paketrader}\n\n` +
          "The plan is inferred from activity, not from a product column — a customer who pays " +
          "without using the service is therefore shown incorrectly here.",
      foljdfragor: foljd(locale, "storst", "totalt")
    };
  }

  // -- Tysta ---------------------------------------------------------------
  if (
    traffar("tyst", "inaktiv", "använder inte", "slutat") ||
    traffar("dormant", "inactive", "not using", "silent", "stopped")
  ) {
    const tysta = rader.filter((r) => r.ekonomi.halsa === "tyst");
    const risk = formateraPris(tysta.reduce((s, r) => s + r.ekonomi.intakt, 0));
    return {
      text:
        tysta.length === 0
          ? sv
            ? "Alla kunder har aktivitet. Ingen är tyst."
            : "Every customer has activity. None are dormant."
          : sv
            ? `${tysta.length} kund(er) utan aktivitet på över ${TYST_EFTER_DAGAR} dagar: ` +
              `${namnge(tysta)}.\n\nDe står för ${risk} i månadsintäkt — alltså det belopp ` +
              "som är i farozonen."
            : `${tysta.length} customer(s) with no activity for over ${TYST_EFTER_DAGAR} days: ` +
              `${namnge(tysta)}.\n\nThey account for ${risk} in monthly revenue — that is the ` +
              "amount at risk.",
      foljdfragor: foljd(locale, "totalt")
    };
  }

  // -- Koncentrationsrisk --------------------------------------------------
  if (
    traffar("tappar", "säger upp", "churn", "störst", "beroende") ||
    traffar("lose", "cancel", "largest", "biggest", "depend")
  ) {
    const betalande = rader.filter((r) => r.ekonomi.intakt > 0);
    if (betalande.length === 0) {
      return {
        text: sv
          ? "Ingen kund har en intäkt att tappa ännu."
          : "No customer has revenue to lose yet.",
        foljdfragor: []
      };
    }
    const storst = [...betalande].sort((a, b) => b.ekonomi.intakt - a.ekonomi.intakt)[0];
    const andel = p.mrr > 0 ? storst.ekonomi.intakt / p.mrr : 0;
    return {
      text: sv
        ? `Största kunden är ${storst.namn} med ${formateraPris(storst.ekonomi.intakt)} i månaden, ` +
          `alltså ${Math.round(andel * 100)} % av intäkten.\n\n` +
          (andel >= 0.4
            ? "Det är en koncentrationsrisk. Tappar ni den kunden försvinner en betydande del " +
              "av intäkten på en gång."
            : "Ingen enskild kund dominerar intäkten.")
        : `The largest customer is ${storst.namn} at ${formateraPris(storst.ekonomi.intakt)} per month, ` +
          `which is ${Math.round(andel * 100)} % of revenue.\n\n` +
          (andel >= 0.4
            ? "That is a concentration risk. Losing that customer would remove a significant " +
              "share of revenue at once."
            : "No single customer dominates the revenue."),
      foljdfragor: foljd(locale, "atgard")
    };
  }

  // -- Gränserna -----------------------------------------------------------
  if (
    traffar("gräns", "grön", "gul", "röd", "smiley", "symbol", "hur räknar") ||
    traffar("threshold", "green", "amber", "red", "how do you", "how is it calculated")
  ) {
    return {
      text: sv
        ? `Grönt 🙂 över ${Math.round(MARGINAL_GRON * 100)} % marginal, gult 😐 över ` +
          `${Math.round(MARGINAL_ROD * 100)} %, rött 🙁 under.\n\n` +
          `Tyst 😴 går FÖRE marginalen: en kund utan aktivitet på ${TYST_EFTER_DAGAR} dagar ` +
          "har låg tokenkostnad och alltså utmärkt marginal. Den hade lyst grönt precis innan " +
          "den sade upp sig, och det är det utfallet symbolen finns för att förhindra."
        : `Green 🙂 above ${Math.round(MARGINAL_GRON * 100)} % margin, amber 😐 above ` +
          `${Math.round(MARGINAL_ROD * 100)} %, red 🙁 below.\n\n` +
          `Dormant 😴 takes PRECEDENCE over margin: a customer with no activity for ` +
          `${TYST_EFTER_DAGAR} days has low token cost and therefore an excellent margin. They ` +
          "would have shown green right up until they cancelled, and that is the outcome the " +
          "symbol exists to prevent.",
      foljdfragor: foljd(locale, "totalt")
    };
  }

  return { text: OKAND_FRAGA[locale], foljdfragor: exempelfragor(locale).slice(0, 3) };
}
