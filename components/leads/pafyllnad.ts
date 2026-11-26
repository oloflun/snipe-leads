import type { Localized } from "@/lib/i18n";

/**
 * Skälet till ett påfyllt lead (Antons regel 2026-11-24) på kundens språk.
 * Backenden sparar en kod i prospects.pafylld_skal (snajp-support
 * app/leads/korning.py: pafyllnadsskal och utanfor_ursprung); här blir den
 * text. Aldrig webbrevisionens fält. En okänd kod (en äldre rad i klartext)
 * visas som den står.
 */
const GRUPP: Record<string, Localized> = {
  a: { sv: "under er tröskel för träffsäkerhet", en: "below your accuracy threshold" },
  b: {
    sv: "kopplingen till det ni säljer kunde inte beläggas, men alla krav är uppfyllda",
    en: "the link to what you sell could not be confirmed, but every requirement is met",
  },
  c: {
    sv: "ett krav kunde inte styrkas i källmaterialet",
    en: "one requirement could not be confirmed in the sources",
  },
  d: { sv: "ett önskemål uppfylls inte", en: "one preference is not met" },
  ovrigt: {
    sv: "närmast att klara bedömningen bland de bortvalda",
    en: "closest to passing among the companies left out",
  },
  nej: {
    sv: "uppfyller inte alla krav, men var närmast målgruppen av de bolag som fanns kvar",
    en: "does not meet every requirement, but was closest to your target group among the companies left",
  },
};

const ENHET: Record<string, Localized> = {
  anstallda: { sv: "anställda", en: "employees" },
  omsattning: { sv: "kr i omsättning", en: "SEK in revenue" },
};

function tal(varde: string, locale: "sv-SE" | "en-GB"): string {
  const n = Number(varde);
  return Number.isFinite(n) ? n.toLocaleString(locale) : varde;
}

export function pafyllnadSkal(kod: string | null | undefined): Localized | null {
  if (!kod) return null;
  const delar = kod.split(":");
  if (delar[0] === "a" && delar.length === 3) {
    return {
      sv: `under er tröskel för träffsäkerhet, ${delar[1]} av ${delar[2]} krävda`,
      en: `below your accuracy threshold, ${delar[1]} of ${delar[2]} required`,
    };
  }
  if (delar[0] === "storlek" && delar.length === 5 && ENHET[delar[1]]) {
    const [, falt, riktning, varde, grans] = delar;
    const enhet = ENHET[falt];
    const max = riktning === "max";
    return {
      sv: `storleken vidgad: ${tal(varde, "sv-SE")} ${enhet.sv}, er gräns är ${max ? "högst" : "minst"} ${tal(grans, "sv-SE")}`,
      en: `size widened: ${tal(varde, "en-GB")} ${enhet.en}, your limit is ${max ? "at most" : "at least"} ${tal(grans, "en-GB")}`,
    };
  }
  return GRUPP[kod] ?? { sv: kod, en: kod };
}
