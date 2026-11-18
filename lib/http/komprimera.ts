import "server-only";

/**
 * Proxyns svar från route handlers, med komprimeringen åt Next.
 *
 * ## Historik
 *
 * Funktionen gzippade JSON-svar själv sedan 2026-10-09: Next komprimerade då
 * sidor och statiska filer men inte route handlers, och Railways edge
 * komprimerar ingenting. Leads-fliken hämtade 364 KB körningar okomprimerat.
 *
 * Från next 16.4.6 komprimerar Next även route handlers, och gör det ovanpå en
 * kropp som redan bär `Content-Encoding: gzip`. Uppmätt i development
 * 2026-11-18: stora svar genom /api/snajp-support/* kom dubbelt gzippade,
 * webbläsaren packade upp en gång och vyerna visade "Oväntat svar från
 * servern (status 200)". Ett svar på 752 byte, under den gamla 1 KB-gränsen
 * här, kom gzippat av Next ensam, så det är Next som komprimerar.
 *
 * Funktionen lämnar därför svaret orört. Den står kvar som det enda stället
 * beslutet bor, så att anropsställena inte behöver ändras om det ändras igen.
 * Server actions och serverkomponenter läser proxyns svar själva och berörs
 * inte.
 */
export async function komprimera(_request: Request, svar: Response): Promise<Response> {
  return svar;
}
