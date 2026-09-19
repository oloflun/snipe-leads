/**
 * Hälsningsraden i ett kallmejl: "Hej Karin," eller "Hej,".
 *
 * ## Varför en egen funktion
 *
 * Bugghistorien, uppmätt på /demo/leads 2026-09-18: exempelbolagens
 * `contact_name` var en ROLL ("Inköpschef"), inte ett namn, och den gamla
 * demogeneratorn skrev ändå `Hej ${context.contactName},` rakt av — kunden
 * fick "Hej Inköpschef," i varje utkast. En roll är inte ett namn, och att
 * hälsa på en roll avslöjar direkt att ingen läst vem mottagaren faktiskt är.
 *
 * Den riktiga (inloggade) utkasts-vägen bygger ALDRIG hälsningen i kod — den
 * är en hård regel i systemprompten (`EMAIL_STUDIO_SYSTEM_PROMPT`, regel 5):
 * modellen använder namnet under "Mejl-kontext → Kontakt" eller inleder utan
 * namn. Grep genom `snajp-support/app/leads/` (writer-flödet: leads_agent.py,
 * outreach_playbook.py, research_playbook.py, follow_up_generator.py) visar
 * ingen kodbyggd hälsning där heller — bara `sign_off()` i leads_agent.py,
 * som sätter AVSÄNDARENS namn sist i mejlet, ett annat problem. Den här
 * funktionen har alltså inget motsvarande ställe att porteras till i
 * Python idag; om ett sådant ställe tillkommer ska det använda samma regel.
 *
 * De enda kodställena som byggde en hälsning var demodata: den gamla
 * `simulateAction` i app/api/email-studio/route.ts (borttagen, se
 * lib/demo/iris-exempel.ts) och `PITCH()` i
 * snajp-support/app/leads/exempelbolag.py (skriver alltid "Hej!" utan namn,
 * så den bugen fanns aldrig där).
 */

/** Ord som avslöjar att strängen är en ROLL, inte ett namn. Gemener — jämförelsen gör om till gemener. */
const ROLLORD = [
  "chef",
  "vd",
  "cfo",
  "coo",
  "cto",
  "ceo",
  "inköp",
  "ekonomi",
  "hr",
  "kontakt",
  "info",
  "kundtjänst",
  "ordförande",
  "ägare",
  "grundare",
  "ansvarig"
];

/**
 * "Hej Karin," om `contactName` ser ut som ett personnamn, annars "Hej,".
 *
 * En roll/titel (Inköpschef, VD, Platschef, CFO, Ekonomichef, "Kontakt" …)
 * eller en helt gemen sträng (t.ex. en trasig import) räknas INTE som ett
 * namn. Bara förnamnet används i hälsningen, aldrig efternamnet — samma regel
 * som resten av produktens mejltext.
 */
export function halsning(contactName?: string | null): string {
  const namn = (contactName ?? "").trim();
  if (!namn) return "Hej,";

  // Helt gemen text ("inköpschef", ett rått importfält) är inte ett namn —
  // riktiga personnamn skrivs med versal begynnelsebokstav.
  if (namn === namn.toLowerCase()) return "Hej,";

  const gemen = namn.toLowerCase();
  if (ROLLORD.some((ord) => gemen.includes(ord))) return "Hej,";

  const fornamn = namn.split(/\s+/)[0];
  return fornamn ? `Hej ${fornamn},` : "Hej,";
}
