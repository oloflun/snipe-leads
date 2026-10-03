/**
 * ICP-fältens etiketter — EN källa för alla ytor som visar målgruppsfälten.
 *
 * Nyckeln är backendens fältnamn (`deal_breakers`, `geography` …) och får
 * ALDRIG ändras här — den går i API-anropen. Etiketten är det kunden ser, och
 * den ska vara densamma i körformuläret (LeadsRunForm), inställningarna
 * (LeadsControls), förhandsvisningen (/forhandsvisning/exempelbolag) och
 * bolagssidan. Innan den här filen fanns låg samma text hårdkodad på fyra
 * ställen och gled isär vid varje omformulering.
 *
 * `hint` är exempeltexten (placeholder) för fältet — inte en förklaring.
 */
export type IcpNyckel =
  | "industries"
  | "exclude_industries"
  | "geography"
  | "roles"
  | "must_have"
  | "deal_breakers";

export type IcpEtikett = { label: string; hint: string };

export const ICP_ETIKETTER: Record<IcpNyckel, IcpEtikett> = {
  industries: { label: "Branscher", hint: "Bygg, tillverkning, logistik" },
  exclude_industries: { label: "Undvik branscher", hint: "Bemanning, spel" },
  // Etiketten säger "Stad" — därför städer i exemplet, inte län och regioner.
  geography: { label: "Stad", hint: "Göteborg, Umeå, Stockholm" },
  roles: { label: "Beslutsfattarroller", hint: "VD, inköpschef, platschef" },
  must_have: { label: "Signaler som krävs", hint: "Egen produktion, växer" },
  // Backend-nyckeln heter deal_breakers och rörs inte; kundens ord är "Egna kriterier".
  deal_breakers: { label: "Egna kriterier", hint: "Under 10 anställda" }
};

const ICP_ETIKETTER_EN: Record<IcpNyckel, IcpEtikett> = {
  industries: { label: "Industries", hint: "Construction, manufacturing, logistics" },
  exclude_industries: { label: "Avoid industries", hint: "Staffing, gambling" },
  geography: { label: "City", hint: "Gothenburg, Umeå, Stockholm" },
  roles: { label: "Decision-maker roles", hint: "CEO, purchasing manager, site manager" },
  must_have: { label: "Required signals", hint: "Own production, growing" },
  deal_breakers: { label: "Own criteria", hint: "Fewer than 10 employees" }
};

/** Etiketterna på kundens språk (INV-COPY-001). `ICP_ETIKETTER` är den svenska
 *  tabellen och står kvar för ytor som inte bytt än. */
export function icpEtiketter(locale: "sv" | "en"): Record<IcpNyckel, IcpEtikett> {
  return locale === "en" ? ICP_ETIKETTER_EN : ICP_ETIKETTER;
}
