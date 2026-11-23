/**
 * Testkunden som kundresan fylls i med. Ett påhittat bolag, uppenbart syntetiskt.
 *
 * Varje körning skapar ett nytt konto med egen adress (STAMP), så att körningar
 * efter varandra inte krockar. Inget här är en riktig kunds uppgifter.
 *
 *   KUND_EPOST   testanvändarens adress. Standard: en adress under example.com,
 *                som aldrig kan ta emot mejl.
 *   KUND_LOSEN   lösenordet. Standard: slumpas per körning och skrivs aldrig ut.
 *                Sätt den bara för ett konto som ska leva kvar.
 */
import { randomBytes } from "node:crypto";

const STAMP = process.env.STAMP ?? String(Date.now()).slice(-8);

export const kund = {
  stamp: STAMP,
  foretag: `E2E Testbolaget ${STAMP} AB`,
  kontakt: "E2E Testperson",
  // example.com är reserverad (RFC 2606): inget mejl dit kan nå en människa.
  epost: process.env.KUND_EPOST ?? `e2e-kund+${STAMP}@example.com`,
  losen: process.env.KUND_LOSEN ?? `E2e-${randomBytes(12).toString("base64url")}`,
  // Luhn-giltigt testnummer, samma som scripts/qa_ny_kund.mjs. Inget riktigt bolags.
  orgnr: "556677-8899",
  webbplats: `https://e2e-testbolaget-${STAMP}.example.com`,
  // Minst 120 tecken, annars skriver Iris inga utkast (business_context.py).
  produkt:
    "Vi säljer besiktning och service av lyftanordningar till industri och bygg, " +
    "med jour dygnet runt och egna certifierade tekniker. Texten är påhittad för testet.",
  bransch: "Industri & tillverkning",
  adress: "Testgatan 1",
  postnummer: "111 22",
  ort: "Stockholm",
  // Målgruppen lämnas bred: ett gissat filter hade smalnat av urvalet på fel grund.
  malgrupp: { branscher: "", orter: "", fokus: "Helst bolag med egen produktion." },
  kunskap: {
    rubrik: "Kontakt och öppettider",
    text:
      "E2E Testbolaget nås på vardagar mellan 08 och 17. Frågor om avtal och fakturor " +
      "besvaras av en medarbetare. Texten är påhittad för testet."
  }
} as const;

export type Testkund = typeof kund;
