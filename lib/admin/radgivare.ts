import type { KundEkonomi } from "@/lib/admin/halsa";
import { MARGINAL_GRON, MARGINAL_ROD, TYST_EFTER_DAGAR, sammanfattaPortfolj } from "@/lib/admin/halsa";
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
 */

export type Svar = {
  text: string;
  /** Frågor som ligger nära, att erbjuda som knappar. */
  foljdfragor: string[];
};

export const EXEMPELFRAGOR = [
  "Hur går det totalt?",
  "Vilka kunder kräver åtgärd?",
  "Vem kostar mest?",
  "Vad tjänar vi per kund?",
  "Vilka är tysta?",
  "Vad händer om vi tappar största kunden?"
] as const;

const OKAND_FRAGA =
  "Den frågan kan jag inte räkna på. Jag svarar bara på det jag kan härleda ur " +
  "kundtabellen — intäkt, kostnad, marginal, användning och risk. Jag gissar inte, " +
  "eftersom ett nästan rätt tal om intäkter är värre än inget tal.";

function namnge(rader: Rad[]): string {
  return rader.map((r) => r.namn).join(", ");
}

export type Rad = { namn: string; ekonomi: KundEkonomi };

export function fragaRadgivaren(fraga: string, rader: Rad[]): Svar {
  const f = fraga.toLowerCase();
  const p = sammanfattaPortfolj(rader.map((r) => r.ekonomi));

  const traffar = (...ord: string[]) => ord.some((o) => f.includes(o));

  if (rader.length === 0) {
    return {
      text: "Det finns inga kunder att räkna på ännu. Tom lista är ett giltigt svar, inte ett fel.",
      foljdfragor: []
    };
  }

  // -- Helheten ------------------------------------------------------------
  if (traffar("totalt", "hur går det", "läget", "sammanfatt", "överblick")) {
    const marginal = p.marginal === null ? "—" : `${Math.round(p.marginal * 100)} %`;
    const problem = p.fordelning.dalig + p.fordelning.tyst;
    return {
      text:
        `${p.antalBetalande} av ${p.antalKunder} kunder betalar, tillsammans ` +
        `${formateraPris(p.mrr)} i månaden. Uppskattad tokenkostnad är ` +
        `${formateraPris(Math.round(p.kostnad))}, vilket ger ${marginal} marginal.\n\n` +
        (problem === 0
          ? "Ingen kund kräver en åtgärd just nu."
          : `${problem} kund(er) kräver en åtgärd: ${p.fordelning.dalig} med låg marginal och ` +
            `${p.fordelning.tyst} som inte använder tjänsten.`),
      foljdfragor: ["Vilka kunder kräver åtgärd?", "Vem kostar mest?"]
    };
  }

  // -- Åtgärdslistan -------------------------------------------------------
  if (traffar("åtgärd", "problem", "oroa", "risk", "dålig", "illa")) {
    const daliga = rader.filter((r) => r.ekonomi.halsa === "dalig");
    const tysta = rader.filter((r) => r.ekonomi.halsa === "tyst");
    if (daliga.length === 0 && tysta.length === 0) {
      return {
        text: "Ingen kund ligger under gränserna just nu. Alla använder tjänsten och betalar mer än de kostar.",
        foljdfragor: ["Hur går det totalt?"]
      };
    }
    const delar: string[] = [];
    if (daliga.length > 0) {
      delar.push(
        `LÅG MARGINAL (${daliga.length}): ${namnge(daliga)}. ` +
          `Kostnaden äter upp intäkten. Se över paket eller volymtak.`
      );
    }
    if (tysta.length > 0) {
      delar.push(
        `TYSTA (${tysta.length}): ${namnge(tysta)}. Ingen aktivitet på över ` +
          `${TYST_EFTER_DAGAR} dagar. De ser lönsamma ut just för att de inte används — ` +
          `hör av er innan de gör det.`
      );
    }
    return { text: delar.join("\n\n"), foljdfragor: ["Vem kostar mest?", "Hur går det totalt?"] };
  }

  // -- Kostnad -------------------------------------------------------------
  if (traffar("kostar mest", "dyrast", "kostnad", "tokens", "förbrukning")) {
    const sorterad = [...rader].sort((a, b) => b.ekonomi.kostnad - a.ekonomi.kostnad);
    const topp = sorterad.slice(0, 3);
    return {
      text:
        "Störst tokenkostnad:\n" +
        topp
          .map(
            (r, i) =>
              `${i + 1}. ${r.namn} — ${formateraPris(Math.round(r.ekonomi.kostnad))} av ` +
              `${formateraPris(r.ekonomi.intakt)} i intäkt` +
              (r.ekonomi.marginal !== null
                ? ` (${Math.round(r.ekonomi.marginal * 100)} % marginal)`
                : "")
          )
          .join("\n") +
        "\n\nTalen är uppskattningar, inte fakturor. Se fotnoten under tabellen.",
      foljdfragor: ["Vilka kunder kräver åtgärd?", "Vad tjänar vi per kund?"]
    };
  }

  // -- Intäkt per kund -----------------------------------------------------
  if (traffar("per kund", "tjänar vi", "intäkt", "mrr", "snitt")) {
    const snitt = p.antalBetalande > 0 ? p.mrr / p.antalBetalande : 0;
    const paketrader = PAKET.map((paket) => {
      const antal = rader.filter((r) => r.ekonomi.paketNamn === paket.namn).length;
      return `${paket.namn}: ${antal} st à ${formateraPris(paket.prisPerManad)}`;
    }).join("\n");
    return {
      text:
        `Snittintäkt per betalande kund är ${formateraPris(Math.round(snitt))} i månaden.\n\n` +
        `Fördelning:\n${paketrader}\n\n` +
        "Paketet härleds ur aktivitet, inte ur en produktkolumn — en kund som betalar utan " +
        "att använda visas därför fel här.",
      foljdfragor: ["Vad händer om vi tappar största kunden?", "Hur går det totalt?"]
    };
  }

  // -- Tysta ---------------------------------------------------------------
  if (traffar("tyst", "inaktiv", "använder inte", "slutat")) {
    const tysta = rader.filter((r) => r.ekonomi.halsa === "tyst");
    return {
      text:
        tysta.length === 0
          ? "Alla kunder har aktivitet. Ingen är tyst."
          : `${tysta.length} kund(er) utan aktivitet på över ${TYST_EFTER_DAGAR} dagar: ` +
            `${namnge(tysta)}.\n\nDe står för ${formateraPris(
              tysta.reduce((s, r) => s + r.ekonomi.intakt, 0)
            )} i månadsintäkt — alltså det belopp som är i farozonen.`,
      foljdfragor: ["Hur går det totalt?"]
    };
  }

  // -- Koncentrationsrisk --------------------------------------------------
  if (traffar("tappar", "säger upp", "churn", "störst", "beroende")) {
    const betalande = rader.filter((r) => r.ekonomi.intakt > 0);
    if (betalande.length === 0) {
      return { text: "Ingen kund har en intäkt att tappa ännu.", foljdfragor: [] };
    }
    const storst = [...betalande].sort((a, b) => b.ekonomi.intakt - a.ekonomi.intakt)[0];
    const andel = p.mrr > 0 ? storst.ekonomi.intakt / p.mrr : 0;
    return {
      text:
        `Största kunden är ${storst.namn} med ${formateraPris(storst.ekonomi.intakt)} i månaden, ` +
        `alltså ${Math.round(andel * 100)} % av intäkten.\n\n` +
        (andel >= 0.4
          ? "Det är en koncentrationsrisk. Tappar ni den kunden försvinner en betydande del " +
            "av intäkten på en gång."
          : "Ingen enskild kund dominerar intäkten."),
      foljdfragor: ["Vilka kunder kräver åtgärd?"]
    };
  }

  // -- Gränserna -----------------------------------------------------------
  if (traffar("gräns", "grön", "gul", "röd", "smiley", "symbol", "hur räknar")) {
    return {
      text:
        `Grönt 🙂 över ${Math.round(MARGINAL_GRON * 100)} % marginal, gult 😐 över ` +
        `${Math.round(MARGINAL_ROD * 100)} %, rött 🙁 under.\n\n` +
        `Tyst 😴 går FÖRE marginalen: en kund utan aktivitet på ${TYST_EFTER_DAGAR} dagar ` +
        "har låg tokenkostnad och alltså utmärkt marginal. Den hade lyst grönt precis innan " +
        "den sade upp sig, och det är det utfallet symbolen finns för att förhindra.",
      foljdfragor: ["Hur går det totalt?"]
    };
  }

  return { text: OKAND_FRAGA, foljdfragor: [...EXEMPELFRAGOR.slice(0, 3)] };
}
