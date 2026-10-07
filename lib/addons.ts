import type { Localized } from "@/lib/i18n";

/**
 * Tilläggstjänster (migration 022).
 *
 * Skilt från `products`: en produkt är en agent kunden köpt och avgör vilka
 * vyer som finns. Ett tillägg är något den agenten får göra extra.
 *
 * Låsta som default och **synliga som upsell**. Ett tillägg som bara är
 * osynligt säljer ingenting — den som inte vet att bildanalys finns kommer
 * aldrig fråga efter den. Därför renderas låsta tillägg som ruled kort med
 * förklaring och en "Hör av dig"-CTA, inte som en gråad meny.
 */

export const addonKeys = [
  "inbox",
  "vision",
  "kb_autoingest",
  "multilang",
  "own_domain",
  "reports",
  // Leadslistor: databasens check-villkor uppdateras i migration 060 —
  // den migrationen är spegeln av den här raden. Glider de isär vägrar
  // databasen nyckeln som UI:t erbjuder.
  "leadlists"
] as const;

export type AddonKey = (typeof addonKeys)[number];

export function isAddonKey(value: string): value is AddonKey {
  return (addonKeys as readonly string[]).includes(value);
}

export type AddonSpec = {
  key: AddonKey;
  name: Localized;
  /** Vad kunden får. Skrivet för kunden, inte för oss. */
  what: Localized;
  /** Varför det inte ingår. Ett tillägg utan skäl läser som godtycke. */
  why: Localized;
};

export const addonCatalog: readonly AddonSpec[] = [
  {
    key: "inbox",
    name: { sv: "Kopplad inkorg", en: "Connected inbox" },
    what: { sv: "Din riktiga IMAP-inkorg kopplas in och agenterna svarar på mejl, inte bara i chatten.", en: "Your real IMAP inbox is connected and the agents answer email, not just chat." },
    why: { sv: "Kräver att vi hanterar era inloggningsuppgifter och sätter upp en inkorgsrutin per kund.", en: "It requires us to handle your login details and set up an inbox routine per customer." }
  },
  {
    key: "vision",
    name: { sv: "Bildanalys", en: "Image analysis" },
    what: { sv: "Kunder kan bifoga foton, till exempel en skadad vara eller en felkod på en display, och agenterna läser bilden.", en: "Customers can attach photos, such as a damaged item or an error code on a display, and the agents read the image." },
    why: { sv: "Egen modellkostnad per bild, och den körs som en separat tjänst vid sidan av samtalet.", en: "Its own model cost per image, and it runs as a separate service alongside the conversation." }
  },
  {
    key: "kb_autoingest",
    name: { sv: "Synkad kunskapsbas", en: "Synced knowledge base" },
    what: { sv: "Kunskapsbasen hämtas från er egen sajt och hålls uppdaterad när ni ändrar där.", en: "The knowledge base is fetched from your own site and kept up to date when you change it there." },
    why: { sv: "Löpande hämtning i stället för en engångsinläsning. Det är drift, inte uppsättning.", en: "Ongoing fetching instead of a one-time import. That is operations, not setup." }
  },
  {
    key: "multilang",
    name: { sv: "Engelsk agent", en: "English agent" },
    what: { sv: "En engelsk agent vid sidan av den svenska, med samma kunskapsbas och samma röst.", en: "An English agent alongside the Swedish one, with the same knowledge base and the same voice." },
    why: { sv: "Två språkversioner av varje instruktion, och en språkgrind som måste stämma i båda.", en: "Two language versions of every instruction, and a language gate that must hold in both." }
  },
  {
    key: "own_domain",
    name: { sv: "Egen domän", en: "Own domain" },
    what: { sv: "Chatten ligger på er egen adress i stället för på snajp.se.", en: "The chat lives on your own address instead of snajp.se." },
    why: { sv: "DNS och certifikat sätts upp per kund och måste förnyas.", en: "DNS and certificates are set up per customer and must be renewed." }
  },
  {
    key: "reports",
    name: { sv: "Månadsrapport", en: "Monthly report" },
    what: { sv: "Ärendevolym, vad frågorna handlade om, och hur ofta agenterna lämnade över till en människa.", en: "Case volume, what the questions were about, and how often the agents handed over to a human." },
    why: { sv: "Egen datavy som räknas fram separat. Den ingår inte i den löpande driften.", en: "A separate data view calculated on its own. It is not part of ongoing operations." }
  },
  {
    key: "leadlists",
    name: { sv: "Leadslistor", en: "Lead lists" },
    what: { sv: "Agenten bygger färdiga, granskningsbara leadslistor: verifierade svenska B2B-bolag med kontaktväg, källa och signal per rad, exporterbara som CSV. I tillägget ingår också en säljlista där ni håller ordning på bolagen ni ringt.", en: "The agent builds finished, reviewable lead lists: verified Swedish B2B companies with a contact path, source and signal per row, exportable as CSV. The add-on also includes a sales list where you keep track of the companies you have called." },
    why: { sv: "Volymkörningar med egen kvot och egen granskning. Det är ett eget arbetsflöde vid sidan av de riktade utskicken.", en: "Volume runs with their own quota and their own review. It is a separate workflow alongside the targeted outreach." }
  }
];

export function addonSpec(key: AddonKey): AddonSpec {
  const found = addonCatalog.find((spec) => spec.key === key);
  if (!found) {
    // Kan bara hända om katalogen och addonKeys glider isär, vilket check-
    // villkoret i 022 hindrar på databassidan men inte här.
    throw new Error(`Okänt tillägg: ${key}`);
  }
  return found;
}
