import type { Localized } from "@/lib/i18n";
import { PAKET, formateraPris } from "@/lib/pricing";

/**
 * Kundhälsa: tjänar vi pengar på den här kunden, och används tjänsten?
 *
 * ## Varför två frågor och inte en
 *
 * En kund kan betala bra och inte använda något — då är intäkten hög men
 * relationen på väg att sägas upp. En annan kan använda mycket och kosta mer
 * än den betalar. Båda är problem, och de kräver motsatta åtgärder. En enda
 * "hälsosiffra" hade blandat ihop dem.
 *
 * ## ANTAGANDENA, som du måste kunna ifrågasätta
 *
 * Alla tal som inte kommer från `lib/pricing.ts` står nedan som namngivna
 * konstanter. De är UPPSKATTNINGAR, inte mätvärden, och det är hela skälet
 * till att de ligger här och inte utspridda i en komponent: när marginalen ser
 * fel ut ska frågan "vad antog vi?" gå att besvara på tio sekunder.
 */

/**
 * Kostnad per miljon tokens, SEK — leverantörens LISTPRIS för den modell som
 * faktiskt är konfigurerad, inte längre en gissning.
 *
 * ## Varför två tal och inte ett
 *
 * Det stod `TOKENKOSTNAD_PER_MILJON_SEK = 12` här, ett blandat tal för "en
 * billig modell (DeepSeek-klassen)". Två fel i det:
 *
 *  1. **DeepSeek körs inte.** Både `main` och `development` står på
 *     `LLM_PROVIDER=gemini`, `MODEL=gemini-3.6-flash` (avläst i Railway
 *     2026-08-29). DeepSeek är dessutom spärrad i varje miljö som bär
 *     kunddata — se CLAUDE.md. Talet beskrev en leverantör vi inte använder.
 *  2. **Utgående tokens kostar FEM gånger mer än ingående.** Ett blandat tal
 *     är därför fel åt olika håll beroende på hur svaren ser ut: en agent som
 *     läser mycket och skriver kort underskattas, en som skriver långa svar
 *     överskattas. `agent_runs` har `tokens_in` och `tokens_out` var för sig,
 *     så det finns ingen anledning att slå ihop dem.
 *
 * ## Var talen kommer ifrån
 *
 * Google, listpris för `gemini-3.6-flash`, betald nivå (hämtat 2026-08-29 från
 * ai.google.dev/gemini-api/docs/pricing): $0,75 per miljon ingående och $3,75
 * per miljon utgående. Växelkurs 9,5237 SEK/USD (ECB via frankfurter.dev,
 * 2026-08-28).
 *
 * ## VAD DE INTE ÄR: en faktura
 *
 * Det finns ingen. Båda miljöerna kör på Geminis GRATISNIVÅ — felloggen är
 * full av `generate_content_free_tier_requests, limit: 20`, och
 * `docs/JURIDIK_ATGARDER.md` har mätt samma sak
 * (`GenerateRequestsPerMinutePerProjectPerModel-FreeTier`). Fakturering är
 * inte påslagen på Google-projektet, så det verkliga utfallet i kronor är noll
 * — betalt i genomströmning (20 anrop/dygn) i stället för i pengar.
 *
 * Talen nedan är alltså vad det KOMMER att kosta den dag faktureringen slås på,
 * vilket juridikspåret säger att den måste. Att sätta 0 här hade gömt en
 * kostnad som är på väg, och att behålla 12 hade beskrivit fel leverantör.
 *
 * ## Fällan i januari
 *
 * Introduktionspriset gäller till och med 2026-12-31. Från 2027-01-01 DUBBLAS
 * båda talen (14,29 respektive 71,43 SEK). Sätt om dem då — marginalen faller
 * inte för att något gått sönder utan för att priset ändrades.
 */
export const TOKENKOSTNAD_IN_PER_MILJON_SEK = 7.14;
export const TOKENKOSTNAD_UT_PER_MILJON_SEK = 35.71;

/** Modellen talen gäller. Visas i fotnoten, så påståendet går att falsifiera. */
export const TOKENKOSTNAD_MODELL = "gemini-3.6-flash";

/** Marginal under detta är rött — kunden kostar nästan lika mycket som den ger. */
export const MARGINAL_ROD = 0.5;
/** Marginal över detta är grönt. Mellan dem: gult. */
export const MARGINAL_GRON = 0.8;

/** Ingen aktivitet på så här många dagar räknas som tyst, oavsett marginal. */
export const TYST_EFTER_DAGAR = 14;

export type Halsa = "bra" | "ok" | "dalig" | "tyst" | "okand";

export type KundEkonomi = {
  /** Månadsintäkt enligt paketet kunden har. */
  intakt: number;
  /** Uppskattad tokenkostnad för perioden. */
  kostnad: number;
  /** (intäkt − kostnad) / intäkt. Null när intäkten är noll. */
  marginal: number | null;
  halsa: Halsa;
  /**
   * Kort mening som förklarar utfallet. Visas bredvid symbolen.
   *
   * Tvåspråkig och inte en färdig sträng: motiveringen är den enda texten i
   * tabellen som räknas fram ur data, och hade den varit svensk hade EN/SV-
   * knappen bytt språk på allt utom just den mening som förklarar raden.
   */
  motivering: Localized;
  symbol: string;
  paketNamn: string | null;
};

/**
 * Vilket paket produkterna motsvarar. Alla tre = Trio, leads + kundtjänst = Duo.
 *
 * Ordningen är inte godtycklig: Trio måste prövas FÖRE Duo. Gjorde den inte
 * det matchade en trio-kund på `harLeads && harSupport` och räknades som Duo,
 * alltså 6 990 kr i stället för 9 990 — och felet syns bara som en marginal
 * som är för dålig, aldrig som ett fel.
 *
 * Bokföringen ensam gav tidigare null, vilket blev noll i intäkt för en
 * arbetsyta som betalar. Den har ett paket nu och matchas som ett.
 */
export function paketForProdukter(produkter: readonly string[]): (typeof PAKET)[number] | null {
  const harLeads = produkter.includes("leads");
  const harSupport = produkter.includes("support");
  const harBokforing = produkter.includes("bookkeeping");
  if (harLeads && harSupport && harBokforing) return PAKET.find((p) => p.id === "trio") ?? null;
  if (harLeads && harSupport) return PAKET.find((p) => p.id === "duo") ?? null;
  if (harLeads) return PAKET.find((p) => p.id === "leads") ?? null;
  if (harSupport) return PAKET.find((p) => p.id === "support") ?? null;
  if (harBokforing) return PAKET.find((p) => p.id === "bookkeeping") ?? null;
  return null;
}

export function tokenkostnad(tokensIn: number, tokensUt: number): number {
  return (
    (tokensIn / 1_000_000) * TOKENKOSTNAD_IN_PER_MILJON_SEK +
    (tokensUt / 1_000_000) * TOKENKOSTNAD_UT_PER_MILJON_SEK
  );
}

/**
 * `nu` skickas IN och läses inte här.
 *
 * Portfoljvy är en klientkomponent, och en klientkomponent renderas två gånger
 * — på servern och i webbläsaren. Ett `Date.now()` här hade gett två olika
 * svar, och därmed "Ingen aktivitet på 37 dagar" i den serverrenderade HTML:en
 * mot "38 dagar" efter hydreringen. Klockan läses en gång, på servern, och
 * skickas ned som ett tal.
 */
function dagarSedan(iso: string | null, nu: number): number | null {
  if (!iso) return null;
  const då = new Date(iso).getTime();
  if (Number.isNaN(då)) return null;
  return Math.floor((nu - då) / 86_400_000);
}

export function bedomKund(input: {
  produkter: readonly string[];
  tokensIn: number;
  tokensUt: number;
  korningar: number;
  arenden: number;
  senasteAktivitet: string | null;
  /** Millisekunder sedan epok, läst EN gång på servern. Se `dagarSedan`. */
  nu: number;
}): KundEkonomi {
  const paket = paketForProdukter(input.produkter);
  const intakt = paket?.prisPerManad ?? 0;
  const kostnad = tokenkostnad(input.tokensIn, input.tokensUt);
  const marginal = intakt > 0 ? (intakt - kostnad) / intakt : null;

  const dagar = dagarSedan(input.senasteAktivitet, input.nu);
  const anvander = input.korningar > 0 || input.arenden > 0;

  // TYST GÅR FÖRE MARGINAL, och det är hela poängen med två frågor. En kund
  // som inte använder tjänsten har per definition låg tokenkostnad och därmed
  // utmärkt marginal — den hade lyst grönt precis innan den sade upp sig.
  if (!anvander || (dagar !== null && dagar > TYST_EFTER_DAGAR)) {
    return {
      intakt,
      kostnad,
      marginal,
      halsa: "tyst",
      symbol: "😴",
      paketNamn: paket?.namn ?? null,
      motivering: anvander
        ? {
            sv: `Ingen aktivitet på ${dagar} dagar. Hör av er innan de gör det.`,
            en: `No activity for ${dagar} days. Reach out before they do.`
          }
        : {
            sv: "Har inte börjat använda tjänsten. Uppstarten är inte klar.",
            en: "Has not started using the service. Onboarding is unfinished."
          }
    };
  }

  if (marginal === null) {
    return {
      intakt,
      kostnad,
      marginal: null,
      halsa: "okand",
      symbol: "❔",
      paketNamn: null,
      motivering: {
        sv: "Ingen produkt kopplad till arbetsytan, så det finns ingen intäkt att räkna marginal på.",
        en: "No product linked to this workspace, so there is no revenue to measure margin against."
      }
    };
  }

  if (marginal >= MARGINAL_GRON) {
    return {
      intakt,
      kostnad,
      marginal,
      halsa: "bra",
      symbol: "🙂",
      paketNamn: paket?.namn ?? null,
      motivering: {
        sv: `Använder tjänsten och kostar ${formateraPris(Math.round(kostnad))} av ${formateraPris(intakt)}.`,
        en: `Actively using the service, costing ${formateraPris(Math.round(kostnad))} of ${formateraPris(intakt)}.`
      }
    };
  }

  if (marginal >= MARGINAL_ROD) {
    return {
      intakt,
      kostnad,
      marginal,
      halsa: "ok",
      symbol: "😐",
      paketNamn: paket?.namn ?? null,
      motivering: {
        sv: `Hög användning: ${formateraPris(Math.round(kostnad))} av ${formateraPris(intakt)} går åt. Håll ett öga.`,
        en: `Heavy usage: ${formateraPris(Math.round(kostnad))} of ${formateraPris(intakt)} consumed. Worth watching.`
      }
    };
  }

  return {
    intakt,
    kostnad,
    marginal,
    halsa: "dalig",
    symbol: "🙁",
    paketNamn: paket?.namn ?? null,
    motivering: {
      sv: `Kostnaden äter upp intäkten (${formateraPris(Math.round(kostnad))} av ${formateraPris(intakt)}). Se över paket eller volym.`,
      en: `Cost is eating the revenue (${formateraPris(Math.round(kostnad))} of ${formateraPris(intakt)}). Review the plan or the volume.`
    }
  };
}

export type Portfolj = {
  antalKunder: number;
  antalBetalande: number;
  mrr: number;
  kostnad: number;
  marginal: number | null;
  fordelning: Record<Halsa, number>;
};

export function sammanfattaPortfolj(kunder: KundEkonomi[]): Portfolj {
  const fordelning: Record<Halsa, number> = { bra: 0, ok: 0, dalig: 0, tyst: 0, okand: 0 };
  let mrr = 0;
  let kostnad = 0;
  let betalande = 0;

  for (const k of kunder) {
    fordelning[k.halsa] += 1;
    mrr += k.intakt;
    kostnad += k.kostnad;
    if (k.intakt > 0) betalande += 1;
  }

  return {
    antalKunder: kunder.length,
    antalBetalande: betalande,
    mrr,
    kostnad,
    marginal: mrr > 0 ? (mrr - kostnad) / mrr : null,
    fordelning
  };
}
