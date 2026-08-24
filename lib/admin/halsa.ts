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
 * Kostnad per miljon tokens, SEK. Grov uppskattning för en billig modell
 * (DeepSeek-klassen), in- och utgående sammanslaget.
 *
 * ÄNDRA DEN HÄR när ni vet det faktiska utfallet från leverantörsfakturan.
 * Tills dess är varje marginal nedan en kvalificerad gissning, och UI:t säger
 * det rakt ut i stället för att presentera den som ett mätvärde.
 */
export const TOKENKOSTNAD_PER_MILJON_SEK = 12;

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
  /** Kort mening som förklarar utfallet. Visas bredvid symbolen. */
  motivering: string;
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
  return ((tokensIn + tokensUt) / 1_000_000) * TOKENKOSTNAD_PER_MILJON_SEK;
}

function dagarSedan(iso: string | null): number | null {
  if (!iso) return null;
  const då = new Date(iso).getTime();
  if (Number.isNaN(då)) return null;
  return Math.floor((Date.now() - då) / 86_400_000);
}

export function bedomKund(input: {
  produkter: readonly string[];
  tokensIn: number;
  tokensUt: number;
  korningar: number;
  arenden: number;
  senasteAktivitet: string | null;
}): KundEkonomi {
  const paket = paketForProdukter(input.produkter);
  const intakt = paket?.prisPerManad ?? 0;
  const kostnad = tokenkostnad(input.tokensIn, input.tokensUt);
  const marginal = intakt > 0 ? (intakt - kostnad) / intakt : null;

  const dagar = dagarSedan(input.senasteAktivitet);
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
        ? `Ingen aktivitet på ${dagar} dagar. Hör av er innan de gör det.`
        : "Har inte börjat använda tjänsten. Uppstarten är inte klar."
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
      motivering:
        "Ingen produkt kopplad till arbetsytan, så det finns ingen intäkt att räkna marginal på."
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
      motivering: `Använder tjänsten och kostar ${formateraPris(Math.round(kostnad))} av ${formateraPris(intakt)}.`
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
      motivering: `Hög användning: ${formateraPris(Math.round(kostnad))} av ${formateraPris(intakt)} går åt. Håll ett öga.`
    };
  }

  return {
    intakt,
    kostnad,
    marginal,
    halsa: "dalig",
    symbol: "🙁",
    paketNamn: paket?.namn ?? null,
    motivering: `Kostnaden äter upp intäkten (${formateraPris(Math.round(kostnad))} av ${formateraPris(intakt)}). Se över paket eller volym.`
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
