/**
 * Pensionerad 2026-09-27 (plans/2026-09-27-appytor-enhetlighet.md, regel 4).
 *
 * Kortet "Gemensam översikt" bar en märkning med paket- och arbetsytans namn
 * (namnet står redan i railen), en ingress om sidan och två länkkort till
 * Leads och Kundtjänst (samma vägar som railen). Inget av det klarade regel 1
 * eller 4, och StartView renderar det inte längre; varje produktsektion bär
 * sina egna länkar där de används.
 *
 * Filen står kvar som en tom komponent i stället för att raderas, eftersom en
 * radering av en produktionsfil kräver Antons godkännande. Radera den, och
 * importen försvinner inte någonstans: ingen importerar den.
 */
export function DuoSummary() {
  return null;
}
