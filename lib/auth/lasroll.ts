/**
 * Läsrollen (`viewer`) — extern läsbehörighet till en arbetsyta.
 *
 * Byggd för Livrustning-piloten: kundens kontaktperson ska kunna följa
 * agentens arbete (journalen, inkorgen, översikten) utan att kunna ändra
 * något och utan insyn i andra tenants. Tenant-isoleringen är samma som för
 * alla medlemmar (arbetsytan avgör allt); det läsrollen LÄGGER TILL är
 * skrivspärren.
 *
 * ## Var spärren sitter
 *
 * Två serverlägen, båda obligatoriska — UI:t som döljer knappar är hövlighet,
 * inte skydd:
 *
 *  1. `proxyAsTenant` (app/api/snajp-support/_auth.ts) vägrar alla
 *     icke-GET-anrop mot backenden. Det täcker kunskapsbasen, inkorgens
 *     åtgärder, testchatten, supportinställningarna och leads — varje
 *     inloggad backend-skrivning går genom den punkten.
 *  2. De sqlAsUser-baserade server actions som muterar arbetsytan
 *     (affärskontext, betalsätt, plan, notiser, agentinstruktioner …)
 *     frågar `arLasare()` innan de skriver.
 *
 * Rollen sätts via en inbjudan i Team-inställningarna (workspace_invites.role
 * = 'viewer'); triggern on_auth_user_created kopierar den till profiles.role
 * vid första inloggningen — ingen migration behövs, kolumnerna är text utan
 * check-villkor, och policy 032 (bara ägare bjuder in) gäller oförändrad.
 */

export const LASROLL = "viewer";

/** Vad en läsare möter vid ett skrivförsök. En mening, inte ett tekniskt fel. */
export const LASROLL_FEL =
  "Ditt konto har läsbehörighet — du kan följa allt, men inte ändra något.";

export function arLasare(
  context: { profile: { role?: string | null } } | null | undefined
): boolean {
  return (context?.profile?.role ?? "") === LASROLL;
}
