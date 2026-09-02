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

export const ICP_ETIKETTER: Record<IcpNyckel, { label: string; hint: string }> = {
  industries: { label: "Branscher", hint: "Bygg, tillverkning, logistik" },
  exclude_industries: { label: "Undvik branscher", hint: "Bemanning, spel" },
  // Etiketten säger "Stad" — därför städer i exemplet, inte län och regioner.
  geography: { label: "Stad", hint: "Göteborg, Umeå, Stockholm" },
  roles: { label: "Beslutsfattarroller", hint: "VD, inköpschef, platschef" },
  must_have: { label: "Signaler som krävs", hint: "Egen produktion, växer" },
  // Backend-nyckeln heter deal_breakers och rörs inte; kundens ord är "Egna kriterier".
  deal_breakers: { label: "Egna kriterier", hint: "Under 10 anställda" }
};
