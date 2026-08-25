import type { Tenant } from "./types";

/**
 * Snajp AB — vår EGEN arbetsyta, kopplad till ss_tenant `snajp`.
 *
 * Vi använder vår egen produkt. Det är därför den här configen finns: utan den
 * svarar `/chat/snajp` med "Ingen configfil för snajp i lib/tenants"
 * (TENANTS.md steg 4), och den som klickar på vår egen supportlänk möts av ett
 * internt felmeddelande.
 *
 * ## Varför tenanten heter något annat i databasen
 *
 * `ss_tenants.name` för slug `snajp` är "Hjärtstartare-piloten" — ett namn från
 * den första piloten, satt i migration 012. Det namnet står kvar i databasen
 * och ändras inte härifrån: kunskapsbasen, ärendena och agentens körningar
 * hänger på den raden, och att byta namn på den för kosmetikens skull är att
 * röra en identitet flera tabeller pekar på.
 *
 * Configen nedan är vad BESÖKAREN ser. De två får skilja sig, och avvikelsen
 * noteras här i stället för att jämkas ihop — samma disciplin som TENANTS.md
 * föreskriver för Livrustnings motstridiga garantitider.
 *
 * ## Paletten
 *
 * Snajps egen, alltså identisk med `globals.css`. Till skillnad från en kunds
 * config ska den här INTE avvika: det är vårt varumärke chatten bär, inte
 * någon annans.
 */
export const snajp: Tenant = {
  slug: "snajp",
  name: "Snajp",
  tagline: "Kundtjänst och leads som svarar utifrån era egna texter",
  website: "https://snajp.vercel.app",
  supportKeyEnv: "SNAJP_KEY_SNAJP",

  logo: {
    src: "/snajp-logo-v1-black.svg",
    width: 552,
    height: 159,
    alt: "Snajp",
    // Ljust fält. Logotypen är mörk ordbild och syns mot papper — motsatsen
    // till Livrustnings, som är vit och försvinner. Kontrollerat mot båda
    // bakgrunderna enligt kommentaren i types.ts.
    background: "light"
  },

  // Snajps egna tokens, samma värden som :root i globals.css.
  palette: {
    ink: "0.20 0.018 252",
    ink2: "0.28 0.018 252",
    paper: "0.965 0.008 88",
    paper2: "0.93 0.012 88",
    mineral: "0.55 0.015 252",
    seal: "0.38 0.030 235",
    ochre: "0.74 0.16 64",
    moss: "0.42 0.071 142",
    danger: "0.53 0.190 27"
  },

  company: {
    legalName: "Snajp",
    // PLATSHÅLLARE — ersätt med det riktiga numret innan en extern kund ser
    // den här sidfoten. Ett påhittat organisationsnummer i en avsändarsidfot
    // är ett lagbrott enligt marknadsföringslagen, inte ett skönhetsfel.
    // Formatet är avsiktligt ogiltigt så att det INTE går att förväxla med
    // ett riktigt nummer: kontrollsiffran stämmer inte (se lib/orgnr.ts).
    orgNumber: "000000-0000",
    addresses: ["Umeå, Sverige"],
    phones: [],
    email: "snajpsupport@gmail.com"
  },

  supportIntro:
    "Fråga om agenterna, vad de kan svara på, vad de kostar eller hur en uppstart går till.",
  supportPrompts: [
    "Vad kostar Snajp och vad ingår i paketen?",
    "Hur lång tid tar en uppstart innan agenterna kan svara?",
    "Var hämtar agenterna sina svar ifrån?",
    "Vad händer om agenterna inte vet svaret på en fråga?",
    "Kan vi testa innan vi bestämmer oss?"
  ]
};
