/**
 * Snajp CRM:s navigering som ett register (docs/crm/MIGRERING-FUNKTIONSLISTA.md
 * § Navigeringen i det nya gränssnittet).
 *
 * Sidofältet, kommandopaletten, strandningsskyddet och notisräknaren läser alla
 * härifrån, så att en ny vy läggs till på ETT ställe: steget som bygger vyn lägger
 * dess post här (eller slår om `byggd` till sant). Bara poster som gör något visas:
 * en post med `byggd: false` står i registret men syns ingenstans, och en grupp
 * utan synlig post syns inte heller.
 *
 * Vem som ser en post (`produkt`, `tillagg`, `roll`) är en ritregel, inte en
 * grind. Grindarna sitter i servern och i proxyn (Sekretess punkt 5 till 8).
 */
import type { LucideIcon } from "lucide-react";
import { OBJEKT, type Objekt, type Ton } from "@/components/crm/app/kit";
import type { AddonKey } from "@/lib/addons";
import type { Localized } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";

/** Sidofältets grupper, i den ordning de står. */
export type Navgrupp = "arbetsyta" | "iris" | "kundtjanst" | "kvitton" | "data" | "plattform";

export const NAVGRUPPER: { nyckel: Navgrupp; namn: Localized }[] = [
  { nyckel: "arbetsyta", namn: { sv: "Arbetsyta", en: "Workspace" } },
  { nyckel: "iris", namn: { sv: "Iris", en: "Iris" } },
  { nyckel: "kundtjanst", namn: { sv: "Kundtjänst", en: "Support" } },
  { nyckel: "kvitton", namn: { sv: "Kvitton", en: "Receipts" } },
  { nyckel: "data", namn: { sv: "Data", en: "Data" } },
  { nyckel: "plattform", namn: { sv: "Plattform", en: "Platform" } }
];

/** Talen som kan stå på en menypost. Skalet räknar dem (Notiser.tsx). */
export type Raknare = "leadsnotiser";

export type Navpost = {
  /** Postens nyckel, samma som vägen under `/crm`: `bolag`, `iris/leads`. */
  nyckel: string;
  grupp: Navgrupp;
  namn: Localized;
  ikon: LucideIcon;
  ton: Ton;
  /** Syns bara när arbetsytan har produkten (`products` i DashboardState). */
  produkt?: ProductKey;
  /** Syns bara när arbetsytan har tillägget (`addons`). */
  tillagg?: AddonKey;
  /** Syns bara för plattformsadmin. */
  roll?: "plattformsadmin";
  /** Falskt tills steget som bygger vyn slår på den. En post som inte gör något visas aldrig. */
  byggd: boolean;
  /** Ett tal på posten (ockra, som `crm-railtal`). */
  raknare?: Raknare;
};

/** De vyer som fanns före registret, med namn, ikon och ton ur verktygslådan (kit.tsx: OBJEKT). */
function fran(objekt: Objekt, grupp: Navgrupp): Navpost {
  const o = OBJEKT[objekt];
  return { nyckel: objekt, grupp, namn: o.namn, ikon: o.ikon, ton: o.ton, byggd: true };
}

export const NAVPOSTER: Navpost[] = [
  fran("oversikt", "arbetsyta"),
  fran("bolag", "arbetsyta"),
  fran("personer", "arbetsyta"),
  fran("affarer", "arbetsyta"),
  fran("uppgifter", "arbetsyta"),
  // Steg 4.2: Iris leads som lista och panel (components/crm/app/iris/LeadsVy.tsx).
  {
    nyckel: "iris/leads",
    grupp: "iris",
    namn: OBJEKT.leads.namn,
    ikon: OBJEKT.leads.ikon,
    ton: OBJEKT.leads.ton,
    produkt: "leads",
    byggd: true,
    raknare: "leadsnotiser"
  },
  // Steg 4.3: Iris utkast, att granska, skickas snart och skickat (components/crm/app/iris/UtkastVy.tsx).
  {
    nyckel: "iris/utkast",
    grupp: "iris",
    namn: OBJEKT.utkast.namn,
    ikon: OBJEKT.utkast.ikon,
    ton: OBJEKT.utkast.ton,
    produkt: "leads",
    byggd: true
  },
  // Steg 4.4: Iris körningar med förlopp, körningens sida och Kör Iris (components/crm/app/iris/KorningarVy.tsx).
  {
    nyckel: "iris/korningar",
    grupp: "iris",
    namn: OBJEKT.korningar.namn,
    ikon: OBJEKT.korningar.ikon,
    ton: OBJEKT.korningar.ton,
    produkt: "leads",
    byggd: true
  },
  fran("synk", "data"),
  fran("sparrar", "data"),
  fran("utvecklare", "data")
];

/** Det skalet vet om den som tittar: samma fält som `useDashboard()`. */
export type Navlage = {
  products: readonly ProductKey[];
  addons: readonly AddonKey[];
  isPlatformAdmin: boolean;
};

/** Får den som tittar se posten, bortsett från om den är byggd. */
export function narbar(post: Navpost, lage: Navlage): boolean {
  if (post.produkt && !lage.products.includes(post.produkt)) return false;
  if (post.tillagg && !lage.addons.includes(post.tillagg)) return false;
  if (post.roll === "plattformsadmin" && !lage.isPlatformAdmin) return false;
  return true;
}

/** Posterna som syns för den som tittar, i registrets ordning. */
export function synligaPoster(lage: Navlage): Navpost[] {
  return NAVPOSTER.filter((p) => p.byggd && narbar(p, lage));
}

/** Grupperna med sina synliga poster. En grupp utan synlig post är borta. */
export function synligaGrupper(lage: Navlage): { nyckel: Navgrupp; namn: Localized; poster: Navpost[] }[] {
  const poster = synligaPoster(lage);
  return NAVGRUPPER.map((g) => ({ ...g, poster: poster.filter((p) => p.grupp === g.nyckel) })).filter((g) => g.poster.length > 0);
}

/** Vägen under roten, utan roten och utan snedstreck i ändarna: `/crm/iris/leads` blir `iris/leads`. */
export function vagUnder(vag: string, bas: string): string {
  if (!vag.startsWith(bas)) return "";
  return vag.slice(bas.length).replace(/^\/+|\/+$/g, "");
}

/**
 * Posten adressen hör till: den längsta nyckeln som adressen börjar med, så att
 * `iris/leads/42` hör till `iris/leads`. Roten är översikten.
 */
export function postForVag(vag: string, bas: string): Navpost | undefined {
  const under = vagUnder(vag, bas) || "oversikt";
  let bast: Navpost | undefined;
  for (const p of NAVPOSTER) {
    if ((under === p.nyckel || under.startsWith(`${p.nyckel}/`)) && (!bast || p.nyckel.length > bast.nyckel.length)) bast = p;
  }
  return bast;
}

/** En post ur registret på nyckeln, byggd eller inte. */
export const navpost = (nyckel: string) => NAVPOSTER.find((p) => p.nyckel === nyckel);
