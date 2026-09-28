/**
 * Branschlistan i onboardingen — kundens EGEN bransch, inte målgruppens.
 *
 * Skillnaden är inte pedanteri: `business_contexts.industries` är
 * leads-agentens MÅLGRUPPSFILTER (vilka branscher Iris ska leta bolag i),
 * och kundens egen bransch hör inte dit — en HLR-utbildare säljer till
 * industri och bygg, inte till andra HLR-utbildare. Den egna branschen
 * skrivs därför som en rad i affärskontextens produkttext, där varje agent
 * läser den som kontext (ordförråd, ton, självbeskrivning), aldrig som
 * filter.
 *
 * Listan är medvetet kort och vardaglig — SNI-koder är för SCB, inte för
 * ett formulär klockan fyra på eftermiddagen. "Annat" finns för att en
 * lista utan utväg tvingar fram ett felval, och felvalet ser sedan ut som
 * ett faktum.
 */

export const BRANSCHER = [
  "Bygg & hantverk",
  "Industri & tillverkning",
  "IT & mjukvara",
  "E-handel & detaljhandel",
  "Utbildning",
  "Vård & omsorg",
  "Hotell & restaurang",
  "Transport & logistik",
  "Fastighet",
  "Ekonomi & juridik",
  "Marknadsföring & media",
  "Konsulttjänster",
  "Offentlig sektor & föreningar",
  "Annat"
] as const;

export type Bransch = (typeof BRANSCHER)[number];

export function arBransch(varde: string): varde is Bransch {
  return (BRANSCHER as readonly string[]).includes(varde);
}
