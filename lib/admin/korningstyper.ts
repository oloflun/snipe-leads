/**
 * Agenttyperna i Logg › Körningar: filtret, tabellens typnamn och
 * översiktens fördelning läser samma lista.
 *
 * "bookkeeping" saknades ända tills agenten fick en adminvy. Filtret är en
 * uppräkning, alltså en lista som glider: en ny agenttyp syns i tabellen men
 * går inte att filtrera på förrän någon lägger till den här.
 *
 * Namnen är produktens (railens Iris, Kundtjänst, Kvitton), inte agent_type-
 * koderna: en kod som etikett är en intern detalj på fel ställe. En okänd typ
 * visas som koden själv, i mono, så att ingen ny typ döljs bakom ett påhittat
 * namn. Andra kolumnen är en nyckel i ADMIN (lib/admin/sprak.ts).
 */
export const KORNINGSTYPER: [string, string][] = [
  ["", "filterAlla"],
  ["support", "railKundtjanst"],
  ["leads_research", "typIrisResearch"],
  ["leads_outreach", "typIrisUtskick"],
  // Samma typer som Kostnad per agent räknar (agentanvandning/page.tsx).
  ["leads_svar", "typIrisSvar"],
  ["leads_followup", "typIrisUppfoljning"],
  ["bookkeeping", "railKvitton"],
  ["demo", "typDemo"]
];

export const KORNINGSTYPNAMN = new Map(KORNINGSTYPER);

/** Iris är en familj av agenttyper (söksteget "leads" plus research, utskick, svar, uppföljning). */
export function arIris(agentType: string): boolean {
  return agentType === "leads" || agentType.startsWith("leads_");
}
