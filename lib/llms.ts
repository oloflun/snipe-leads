import { kanoniskUrl } from "@/lib/kanonisk";
import { LANDNINGAR } from "@/lib/landningar";
import {
  BINDNING,
  EXTRA_MEJL_PRIS,
  EXTRA_PROSPEKT_PRIS,
  PAKET,
  PER_MANAD,
  PRIS_PREFIX,
  PRIS_SAKNAS,
  UPPSTARTSAVGIFT,
  formateraPris
} from "@/lib/pricing";
import { PRODUKTER, versal } from "@/lib/seo";
import { TEAM } from "@/lib/team";

/**
 * /llms.txt: sajten i klartext för AI-assistenter (formatet på llmstxt.org).
 *
 * ChatGPT, Perplexity och Claude som söker åt en användare läser hellre en
 * kort textfil än en sida som ritas av JavaScript. Filen säger vad Snajp är,
 * för vem, vad det kostar och var resten står. Byggd ur samma källor som
 * sajten (lib/pricing.ts, lib/landningar.ts), så att den inte kan säga något
 * annat än sidorna. Inga påståenden som inte står på sajten.
 */
export function llmsText(kontaktMejl: string): string {
  const paket = PAKET.map((p) => {
    const pris = p.prisPerManad === null ? PRIS_SAKNAS.sv.toLowerCase() : `${PRIS_PREFIX.sv} ${formateraPris(p.prisPerManad)}${PER_MANAD.sv}`;
    return `- ${p.namn}: ${pris}. ${p.beskrivning.sv} Ingår: ${p.ingar.map((r) => r.sv).join(", ")}.`;
  });
  const sida = (vag: string, namn: string, kort: string) => `- [${namn}](${kanoniskUrl(vag)}): ${kort}`;
  const grundare = new Intl.ListFormat("sv", { type: "conjunction" }).format(TEAM.map((m) => m.namn));

  return [
    "# Snajp",
    "",
    "> Snajp bygger AI-agenter för svenska B2B-företag. Iris är en svensk AI-SDR (leadsagent) som väljer ut bolag ur bolagsregistret, läser på om dem på deras egen webbplats och skriver ett personligt säljmejl på svenska. Snajp Support är en AI-agent för kundtjänst som svarar kunder på svenska och engelska i mejlinkorgen och i chatten på hemsidan, ur företagets egen kunskapsbas. Utvecklat i Göteborg och Umeå.",
    "",
    "Snajp builds AI agents for Swedish B2B companies: Iris, a Swedish AI SDR that finds and writes to new customers, and Snajp Support, an AI customer service agent that answers in Swedish and English by email and website chat.",
    "",
    "## Fakta",
    "",
    "- Språk: agenterna skriver och svarar på svenska och engelska.",
    "- En människa bestämmer hur mycket agenterna får göra själva. Iris kan köras med bara utkast, med rätt att skicka första mejlet eller fram till ett bokat möte; de tre första utskicken granskas alltid av en människa.",
    "- Supportagenten hittar inte på svar. Saknas underlag i kunskapsbasen lämnar den över till en människa. Återbetalningar, fakturafel, juridik, GDPR och arga kunder går alltid till en människa.",
    "- Leads hämtas ur öppna källor: bolagsregistret för urvalet, bolagens egna webbplatser, platsannonser och pressmeddelanden. Inga köpta listor, ingen LinkedIn-skrapning, inga privatpersoner och inga enskilda firmor.",
    "- Varje utskick har en avregistreringslänk. Den rättsliga grunden för B2B-prospektering är berättigat intresse enligt GDPR.",
    "- Data lagras inom EU, och varje kunds data är avskild på databasnivå.",
    `- Snajp grundades av ${grundare}.`,
    "",
    "## Priser (exklusive moms)",
    "",
    ...paket,
    `- Uppstart: ${formateraPris(UPPSTARTSAVGIFT)} engångs. ${versal(BINDNING.sv)}.`,
    `- Utöver paketets volym: ${formateraPris(EXTRA_PROSPEKT_PRIS)} per extra prospekt, ${formateraPris(EXTRA_MEJL_PRIS)} per extra mejl.`,
    "",
    "## Produkter",
    "",
    sida(PRODUKTER.leads.vag, "Snajp Leads", `${PRODUKTER.leads.beskrivning} Demon går att prova utan konto.`),
    sida(PRODUKTER.support.vag, "Snajp Support", `${PRODUKTER.support.beskrivning} Demon går att prova utan konto.`),
    "",
    "## Sidor",
    "",
    ...LANDNINGAR.map((p) => sida(p.vag, p.namn.sv, p.kort.sv)),
    "",
    "## Mer",
    "",
    sida("/faq", "Frågor och svar", "plattformen, data och källor, pris och avtal, dataskydd och uppstart."),
    sida("/vart-team", "Vårt team", "vilka som bygger Snajp och hur vi arbetar."),
    sida("/boka-demo", "Boka demo", "15 till 20 minuter mot era egna kunder eller ärenden."),
    sida("/integritetspolicy", "Integritetspolicy", "underleverantörer med namn och var behandlingen sker."),
    `- Kontakt: ${kontaktMejl}`,
    ""
  ].join("\n");
}
