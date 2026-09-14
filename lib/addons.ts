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
  name: string;
  /** Vad kunden får. Skrivet för kunden, inte för oss. */
  what: string;
  /** Varför det inte ingår. Ett tillägg utan skäl läser som godtycke. */
  why: string;
};

export const addonCatalog: readonly AddonSpec[] = [
  {
    key: "inbox",
    name: "Kopplad inkorg",
    what: "Din riktiga IMAP-inkorg kopplas in och agenterna svarar på mejl, inte bara i chatten.",
    why: "Kräver att vi hanterar era inloggningsuppgifter och sätter upp en inkorgsrutin per kund."
  },
  {
    key: "vision",
    name: "Bildanalys",
    what: "Kunder kan bifoga foton — en skadad vara, en felkod på en display — och agenterna läser bilden.",
    why: "Egen modellkostnad per bild, och den körs som en separat tjänst vid sidan av samtalet."
  },
  {
    key: "kb_autoingest",
    name: "Synkad kunskapsbas",
    what: "Kunskapsbasen hämtas från er egen sajt och hålls uppdaterad när ni ändrar där.",
    why: "Löpande hämtning i stället för en engångsinläsning — det är drift, inte uppsättning."
  },
  {
    key: "multilang",
    name: "Engelsk agent",
    what: "En engelsk agent vid sidan av den svenska, med samma kunskapsbas och samma röst.",
    why: "Två språkversioner av varje instruktion, och en språkgrind som måste stämma i båda."
  },
  {
    key: "own_domain",
    name: "Egen domän",
    what: "Chatten ligger på er egen adress i stället för på snajp.se.",
    why: "DNS och certifikat sätts upp per kund och måste förnyas."
  },
  {
    key: "reports",
    name: "Månadsrapport",
    what: "Ärendevolym, vad frågorna handlade om, och hur ofta agenterna lämnade över till en människa.",
    why: "Egen datavy som räknas fram separat — den ingår inte i den löpande driften."
  },
  {
    key: "leadlists",
    name: "Leadslistor",
    what: "Agenten bygger färdiga, granskningsbara leadslistor — verifierade svenska B2B-bolag med kontaktväg, källa och signal per rad, exporterbara som CSV.",
    why: "Volymkörningar med egen kvot och egen granskning — det är ett eget arbetsflöde vid sidan av de riktade utskicken."
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
