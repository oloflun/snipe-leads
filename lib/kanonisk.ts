/**
 * Sajtens kanoniska adress — ETT ställe, inte tre.
 *
 * ## Varför `www` och inte apex
 *
 * `snajp.se` är varumärkesadressen och vore det naturliga valet. Den går inte
 * att använda, och skälet är strukturellt snarare än en inställning någon
 * glömt:
 *
 *  * Railway pekas ut med en CNAME. En CNAME får enligt DNS-standarden inte
 *    samexistera med andra poster på samma namn, och apex MÅSTE ha NS och SOA.
 *    Apex kräver därför ALIAS/ANAME eller CNAME-flattening.
 *  * Loopia, där zonen ligger, har ingen av dem. Deras API sonderades
 *    2026-08-30 med sjutton tänkbara metodnamn — alla svarade `404 Unknown`.
 *
 * Alternativet var att flytta namnservrarna till Cloudflare, vars gratisplan
 * klarar flattening. Det valdes bort: en namnserverflytt kräver att varje post
 * återskapas, och MX:en för kontakt@snajp.se ligger på apex. Risken att tappa
 * inkommande mejl vägde tyngre än ett `www` i adressfältet.
 *
 * Apex omdirigerar därför till www med Loopias egen vidarebefordran.
 *
 * ## Vad som INTE ska härledas härifrån
 *
 * Mejladresser. `kontakt@snajp.se` och `integritet@snajp.se` ligger på apex —
 * MX-posten sitter där, och den flyttar inte med webbtrafiken. Se lib/bolag.ts.
 *
 * Kundernas egna adresser. En kund bor på `<slug>.snajp.se`, och
 * `tenantSlugFromHost` plockar sluggen ur värdnamnet. Den returnerar null för
 * `www`, vilket är varför den här adressen inte tolkas som en kund.
 */
export const KANONISK_ORIGIN = "https://www.snajp.se";

/** Absolut URL för en väg. `/leads` -> `https://www.snajp.se/leads`. */
export function kanoniskUrl(vag: string): string {
  return new URL(vag, KANONISK_ORIGIN).toString();
}
