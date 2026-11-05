import type { Localized } from "@/lib/i18n";
import type { Paket } from "@/lib/pricing";

/**
 * Registret över sökordssidorna: adress, produkt, namn och en mening om vad
 * sidan svarar på.
 *
 * ## Varför sidorna finns (Anton 2026-11-05)
 *
 * På "snajp" var vi etta med flera sidlänkar. På varje sökord som beskriver
 * verksamheten ("svensk AI-SDR", "B2B-leads", "supportchatt") syntes vi inte
 * alls, inte ens på sista sidan. Sajten hade tre produktadresser, ingen av dem
 * med sökordet i rubriken och ingen med en H1. En sökmotor kan inte ranka en
 * sida för en fråga som sidan aldrig ställer.
 *
 * Varje post är EN fråga med EN avsikt. Två sidor som svarar på samma fråga
 * konkurrerar med varandra, och åtta tunna kopior av samma sida är precis vad
 * Googles regler om doorway-sidor fäller. Innehållet bor i lib/landningssidor.ts
 * och är skrivet per sida; den här filen är bara registret.
 *
 * ## Varför registret är en egen fil
 *
 * Sidfoten, sitemapen och llms.txt läser listan. Sidfoten är en klient-
 * komponent, och hade den importerat innehållsfilen hade varje besökare laddat
 * ned åtta sidors text på båda språken för att rita åtta länkar.
 *
 * Ordningen är sidfotens ordning: leads först, sedan support, sist översikten.
 */

export type LandningsPost = {
  /** Adressen. Mappen under app/ heter likadant, se INV-SEO-001. */
  vag: string;
  /** Paketet sidan säljer: dess pris, schema och knappar. Duo är båda agenterna. */
  produkt: Paket["id"];
  /** Länktexten i sidfoten och brödsmulan. Samma ord som sidans sökord. */
  namn: Localized;
  /** En mening om vad sidan svarar på. Används i "Läs vidare" och llms.txt. */
  kort: Localized;
};

export const LANDNINGAR = [
  {
    vag: "/svensk-ai-sdr",
    produkt: "leads",
    namn: { sv: "Svensk AI-SDR", en: "Swedish AI SDR" },
    kort: {
      sv: "Iris hittar rätt bolag, läser på om dem och skriver säljmejlet på svenska.",
      en: "Iris finds the right companies, reads up on them and writes the sales email in Swedish."
    }
  },
  {
    vag: "/b2b-leads",
    produkt: "leads",
    namn: { sv: "Svenska B2B-leads", en: "Swedish B2B leads" },
    kort: {
      sv: "Svenska bolag utvalda efter er målgrupp, med kontaktväg, research och ett färdigt mejl.",
      en: "Swedish companies chosen for your target market, with a way in, research and a finished email."
    }
  },
  {
    vag: "/b2b-prospektering",
    produkt: "leads",
    namn: { sv: "B2B-prospektering", en: "B2B prospecting" },
    kort: {
      sv: "Så prospekterar svenska företag utan att skriva varje mejl själva, och vilka regler som gäller.",
      en: "How Swedish companies prospect without writing every email themselves, and which rules apply."
    }
  },
  {
    vag: "/leads-i-inkorgen",
    produkt: "leads",
    namn: { sv: "Svenska leads i inkorgen", en: "Swedish leads in your inbox" },
    kort: {
      sv: "Nya bolag och färdiga utkast samlas på ett ställe, och svaren hamnar i samma tråd.",
      en: "New companies and finished drafts gather in one place, and the replies land in the same thread."
    }
  },
  {
    vag: "/support-pa-svenska",
    produkt: "support",
    namn: { sv: "Support på svenska", en: "Support in Swedish" },
    kort: {
      sv: "En AI-agent för kundtjänst som svarar era kunder på svenska ur er egen kunskapsbas.",
      en: "An AI customer service agent that answers your customers in Swedish from your own knowledge base."
    }
  },
  {
    vag: "/supportchatt",
    produkt: "support",
    namn: { sv: "Supportchatt till hemsidan", en: "Support chat for your website" },
    kort: {
      sv: "En svensk AI-chatt på er webbplats, inlagd med en rad kod och i era färger.",
      en: "A Swedish AI chat on your website, added with one line of code and in your colours."
    }
  },
  {
    vag: "/ai-supportagent",
    produkt: "support",
    namn: { sv: "AI-supportagent", en: "AI support agent" },
    kort: {
      sv: "Supportagenten sorterar kundmejlen, skriver svaren och lämnar över det som kräver en människa.",
      en: "The support agent sorts customer emails, writes the replies and hands over what needs a person."
    }
  },
  {
    vag: "/ai-agenter",
    produkt: "duo",
    namn: { sv: "AI-agenter för företag", en: "AI agents for business" },
    kort: {
      sv: "Snajps två AI-agenter: en som hittar nya kunder och en som svarar dem ni redan har.",
      en: "Snajp's two AI agents: one that finds new customers and one that answers the ones you have."
    }
  }
] as const satisfies readonly LandningsPost[];

/** En sökordssidas adress. En felstavad adress fäller tsc, inte bara ett test. */
export type LandningsVag = (typeof LANDNINGAR)[number]["vag"];

export function landningsPost(vag: LandningsVag): LandningsPost {
  // `find` kan inte missa: vag är en av registrets egna adresser.
  return LANDNINGAR.find((p) => p.vag === vag)!;
}

/**
 * Produktsidan som en sökordssida hör till, för brödsmulan och sidfotens
 * rubriker. Duo har ingen egen produktsida: dess sidor hör till Snajp direkt.
 */
export const FAMILJ: Record<"leads" | "support", { namn: Localized; vag: string }> = {
  leads: { namn: { sv: "Leads", en: "Leads" }, vag: "/leads" },
  support: { namn: { sv: "Support", en: "Support" }, vag: "/support" }
};

/**
 * Brödsmulan från startsidan till sidan. Den synliga brödsmulan och
 * BreadcrumbList i schemat läser båda den här, så att de inte kan säga olika.
 */
export function smulspar(vag: LandningsVag): { namn: Localized; vag: string }[] {
  const post = landningsPost(vag);
  const familj = post.produkt === "duo" ? [] : [FAMILJ[post.produkt]];
  return [{ namn: { sv: "Snajp", en: "Snajp" }, vag: "/" }, ...familj, { namn: post.namn, vag }];
}
