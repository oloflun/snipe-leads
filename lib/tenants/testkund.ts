import type { Tenant } from "./types";
import { snajp } from "./snajp";

/**
 * Testarbetsytan — en delad tenant för konton som skapats med rutan
 * "Testarbetsyta" ikryssad i onboardingen.
 *
 * ## Varför den behövde finnas
 *
 * Onboardingen kan sedan 2026-08-18 hoppa över organisationsnumret, så en
 * testkund GÅR att skapa. Uppmätt mot dev-deployen 2026-08-19: den nyskapade
 * kunden mötte 409 på tre av sina egna ytor — Kontroll, Kundtjänst och Röst —
 * eftersom workspacet saknade `slug`, och en testkund som inte kan använda
 * produkten testar ingenting. Bypassen var alltså halvfärdig utan den här
 * filen.
 *
 * ## Varför EN delad tenant och inte en per testkund
 *
 * En tenant per testkund kräver en configfil, en rad i registret och en
 * miljövariabel — per kund. Det är en kodändring för att skapa ett testkonto,
 * vilket är precis den friktion bypassen fanns för att ta bort.
 *
 * Priset står utskrivet: testkunder DELAR ärenden, kunskapsbas och röstdokument
 * med varandra. Det är rätt avvägning för ett test och fel för en kund, och
 * därför får ingen riktig kund kopplas hit. `railway_link_testkund.py` vägrar
 * koppla en workspace som inte är märkt som testkund.
 *
 * ## Vad som INTE delas
 *
 * Tenanten är skild från `snajp`. En provkörning som en testkund startar får
 * inte hamna i vår egen inkorg — det var det första utkastet till den här
 * filen, och det gör vår egen tenants siffror obrukbara.
 */
export const testkund: Tenant = {
  slug: "testkund",
  name: "Testarbetsyta",
  tagline: "Delad tenant för testkonton — inte en riktig kund",
  website: "https://snajp.vercel.app",
  supportKeyEnv: "SNAJP_KEY_TESTKUND",

  logo: snajp.logo,
  // Snajps egna tokens. En testyta ska se ut som produkten, annars testar man
  // inte produkten.
  palette: snajp.palette,

  company: {
    legalName: "Testarbetsyta",
    // Avsiktligt ogiltigt format (kontrollsiffran stämmer inte, se lib/orgnr.ts)
    // så att det aldrig går att förväxla med ett riktigt organisationsnummer.
    orgNumber: "000000-0000",
    addresses: ["Testmiljö"],
    phones: [],
    email: "snajpsupport@gmail.com"
  },

  supportIntro:
    "Det här är en testarbetsyta. Svaren kommer från Snajps egen kunskapsbas och ska inte visas för en riktig kund.",
  supportPrompts: [
    "Vad kostar Snajp och vad ingår i paketen?",
    "Hur lång tid tar en uppstart innan agenterna kan svara?",
    "Var hämtar agenterna sina svar ifrån?"
  ]
};
