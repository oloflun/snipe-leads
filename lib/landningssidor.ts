import type { ProduktYta } from "@/components/marketing/ProduktBilder";
import type { Localized } from "@/lib/i18n";
import { KANONISK_ORIGIN, kanoniskUrl } from "@/lib/kanonisk";
import { landningsPost, smulspar, type LandningsVag } from "@/lib/landningar";
import {
  BINDNING,
  BINDNINGSTID_MANADER,
  EXTRA_PROSPEKT_PRIS,
  PAKET,
  PRODUKTER_FOR_PAKET,
  UPPSTARTSAVGIFT,
  besparingPerManad,
  formateraPris,
  type Paket
} from "@/lib/pricing";
import { AI_SDR_VERKTYG, KONTROLLERAD, SUPPORTVERKTYG } from "@/lib/jamforelser";
import { brodsmulor, faqSida, graf, paketpris, produkt } from "@/lib/seo";
import { TEAM } from "@/lib/team";

/**
 * Innehållet på sökordssidorna, en post per adress i lib/landningar.ts.
 *
 * ## Vad som får stå här
 *
 * Bara det som går att belägga. Sakuppgifterna om Snajp kommer ur tre källor
 * och inga andra: Snajps egen kunskapsbas (snajp-support/app/tenants/snajp_kb.py,
 * som vår supportchatt svarar ur), lib/faq.ts och Antons regler för leads i
 * CLAUDE.md. Inga påhittade siffror eller kundcitat (DESIGN.md, Honest-proof
 * rule). Priser och volymer räknas ur lib/pricing.ts och skrivs aldrig in för hand.
 *
 * Andra leverantörer nämns bara på jämförelsesidorna och bara ur
 * lib/jamforelser.ts, där varje uppgift har en källa på leverantörens egen sajt
 * och ett kontrolldatum (docs/SEO-JAMFORELSER-KALLOR.md). Jämförande reklam
 * ska vara saklig och gå att kontrollera; därför står "Ej angivet" där
 * leverantören inte själv säger något, och sidan säger att Snajp är en av dem.
 *
 * Webbplatsbedömningen nämns inte. Den är hemlig utanför plattformsadmin och
 * webbyråkunderna (CLAUDE.md, beslut 2026-10-08), och en sökordssida är det
 * mest publika stället vi har.
 *
 * ## Hur texten är skriven
 *
 * Varje sida svarar på EN fråga, den som står i sökordet, och `kortSvar` är
 * svaret i ett stycke på 40 till 60 ord. Det är det stycke en AI-översikt eller
 * ChatGPT kan citera utan resten av sidan, så det ska stå på egna ben.
 * Svenskan är skriven med humanizer-svenska, engelskan med humanizer. Inga
 * tankstreck i någotdera språket.
 *
 * Varje svensk sträng står på sin `sv:`-rad: INV-COPY-001 läser raden, och en
 * fortsättningsrad med svenska bokstäver hade fällts som enspråkig.
 */

type Fraga = { fraga: Localized; svar: Localized };

export type Landning = {
  vag: LandningsVag;
  /** H1. `*ord*` är sidans enda markerade ord. */
  rubrik: Localized;
  ingress: Localized;
  kortSvar: Fraga;
  stegRubrik: Localized;
  steg: { rubrik: Localized; text: Localized }[];
  yta: { typ: ProduktYta; rubrik: Localized; text: Localized };
  granser: { rubrik: Localized; punkter: Localized[] };
  /**
   * Valfri. Första kolumnen är radens etikett; varje rad har lika många värden
   * som kolumner. Fler än fyra kolumner staplas till lg i stället för md.
   * `kallor` och `kontrollerad` krävs när tabellen namnger andra leverantörer.
   */
  jamforelse?: {
    rubrik: Localized;
    kolumner: Localized[];
    rader: Localized[][];
    kallor?: { namn: string; url: string }[];
    kontrollerad?: Localized;
  };
  fragor: Fraga[];
  relaterade: LandningsVag[];
};

function kr(id: Paket["id"]): string {
  const pris = paketpris(id);
  // Sidornas prismeningar påstår ett pris. Finns inget ska bygget falla här,
  // inte publicera "från null kr".
  if (!pris) throw new Error(`Package ${id} has no price, update lib/landningssidor.ts`);
  return pris;
}

/** En rad ur paketets "Ingår", så att volymerna bara står i lib/pricing.ts. */
function ingar(id: Paket["id"], ord: string): Localized {
  const rad = PAKET.find((p) => p.id === id)?.ingar.find((r) => r.sv.includes(ord));
  if (!rad) throw new Error(`Package ${id} has no included line with "${ord}"`);
  return rad;
}

const LEADS = kr("leads");
const SUPPORT = kr("support");
const DUO = kr("duo");
const UPPSTART = formateraPris(UPPSTARTSAVGIFT);
const EXTRA_PROSPEKT = formateraPris(EXTRA_PROSPEKT_PRIS);
const DUO_SPAR = formateraPris(besparingPerManad("duo"));
const PROSPEKT = ingar("leads", "prospekt");
const MEJL = ingar("leads", "mejl");
/** Bindningstiden som slutet på en mening: "och det finns ingen bindningstid". */
const BINDNING_GALLER: Localized =
  BINDNINGSTID_MANADER === 0
    ? { sv: `det finns ${BINDNING.sv}`, en: `there is ${BINDNING.en}` }
    : { sv: `${BINDNING.sv} gäller`, en: `${BINDNING.en} applies` };
const GRUNDARE: Localized = {
  sv: new Intl.ListFormat("sv", { type: "conjunction" }).format(TEAM.map((m) => m.namn)),
  en: new Intl.ListFormat("en", { type: "conjunction" }).format(TEAM.map((m) => m.namn))
};

const SVENSK_AI_SDR: Landning = {
  vag: "/svensk-ai-sdr",
  rubrik: { sv: "En svensk AI-SDR som skriver som *ni*.", en: "A Swedish AI SDR that writes like *you*." },
  ingress: {
    sv: "Iris är Snajps AI-SDR för svensk B2B. Hon väljer ut bolag som passar er, läser på om dem på deras egen webbplats och skriver ett första mejl på svenska som bygger på något hon faktiskt har hittat. Ni bestämmer hur mycket hon får skicka själv.",
    en: "Iris is Snajp's AI SDR for Swedish B2B. She picks out companies that fit you, reads up on them on their own website and writes a first email in Swedish built on something she actually found. You decide how much she may send on her own."
  },
  kortSvar: {
    fraga: { sv: "Vad är en AI-SDR?", en: "What is an AI SDR?" },
    svar: {
      sv: "En AI-SDR är en programvaruagent som gör en säljutvecklares förarbete. Den hittar företag som matchar er målgrupp, tar reda på vem som är rätt kontakt, skriver ett personligt första mejl och håller ordning på uppföljningen. En svensk AI-SDR gör samma sak med svenska bolagsdata, på svenska och efter de regler som gäller för B2B-kontakt i Sverige.",
      en: "An AI SDR is a software agent that does a sales development rep's groundwork. It finds companies that match your target market, works out the right contact, writes a personal first email and keeps the follow-up in order. A Swedish AI SDR does the same with Swedish company data, in Swedish, under the rules that apply to B2B contact in Sweden."
    }
  },
  stegRubrik: { sv: "Så arbetar Iris", en: "How Iris works" },
  steg: [
    {
      rubrik: { sv: "Urvalet", en: "The selection" },
      text: {
        sv: "Iris utgår från bolagsregistret och väljer företag efter bransch, ort, storlek och omsättning. Varje bolag prövas sedan mot er idealkundprofil innan något dyrare steg körs.",
        en: "Iris starts from the company register and selects companies by industry, location, size and turnover. Each one is then checked against your ideal customer profile before any costlier step runs."
      }
    },
    {
      rubrik: { sv: "Researchen", en: "The research" },
      text: {
        sv: "Hon läser bolagets egen webbplats: vad de gör, vem som är kontakt och vad som har hänt nyligen. En nyöppning, en rekrytering eller en ny tjänst blir ingången i mejlet.",
        en: "She reads the company's own website: what they do, who the contact is and what has happened lately. A new opening, a hire or a new service becomes the way into the email."
      }
    },
    {
      rubrik: { sv: "Mejlet", en: "The email" },
      text: {
        sv: "Utkastet är kort, på svenska och har en anledning att höra av sig just nu. Vill ni ändra något skriver ni om det med ett knapptryck, kortare eller mer personligt.",
        en: "The draft is short, in Swedish and has a reason to get in touch right now. If you want to change something, you rewrite it at the press of a button, shorter or more personal."
      }
    },
    {
      rubrik: { sv: "Uppföljningen", en: "The follow-up" },
      text: {
        sv: "Svarar mottagaren slutar uppföljningen direkt. Uppföljningsmejlen är utkast som en människa godkänner, och den som avregistrerar sig får inga fler utskick.",
        en: "When the recipient replies, the follow-up stops at once. Follow-up emails are drafts a person approves, and anyone who unsubscribes gets no further sends."
      }
    }
  ],
  yta: {
    typ: "irisUtkast",
    rubrik: { sv: "Ett utkast från Iris", en: "A draft from Iris" },
    text: {
      sv: "Ingången kommer ur researchen: här en rekrytering som bolaget själv har annonserat.",
      en: "The opening comes from the research: here a job ad the company posted itself."
    }
  },
  granser: {
    rubrik: { sv: "Det Iris inte gör", en: "What Iris does not do" },
    punkter: [
      { sv: "Köper inga listor och skrapar inte LinkedIn.", en: "Buys no lists and does not scrape LinkedIn." },
      { sv: "Skriver inte samma mejl till hundra bolag.", en: "Does not write the same email to a hundred companies." },
      { sv: "Mejlar inte HR-, ekonomi- eller jobbadresser.", en: "Does not email HR, finance or jobs addresses." },
      { sv: "Skickar ingenting ni inte har gett henne lov att skicka. De tre första utskicken granskas alltid av en människa.", en: "Sends nothing you have not allowed her to send. The first three sends are always reviewed by a person." }
    ]
  },
  jamforelse: {
    rubrik: { sv: "Tre andra sätt att få fler möten", en: "Three other ways to get more meetings" },
    kolumner: [
      { sv: "Sätt", en: "Option" },
      { sv: "Vad ni får", en: "What you get" },
      { sv: "Vad det kräver av er", en: "What it takes from you" }
    ],
    rader: [
      [
        { sv: "Anställa en säljutvecklare", en: "Hire a sales development rep" },
        { sv: "En person som lär sig er marknad", en: "A person who learns your market" },
        { sv: "Rekrytering, upplärning och en lön varje månad", en: "Recruitment, training and a salary every month" }
      ],
      [
        { sv: "Köpa en leadslista", en: "Buy a lead list" },
        { sv: "Namn och adresser", en: "Names and addresses" },
        { sv: "Att ni själva läser på och skriver varje mejl", en: "Reading up and writing every email yourselves" }
      ],
      [
        { sv: "Ett utländskt AI-verktyg", en: "A foreign AI tool" },
        { sv: "Volym, ofta med mallar skrivna för en annan marknad", en: "Volume, often with templates written for another market" },
        { sv: "Att svenska mejl och svenska regler fungerar ändå", en: "Making Swedish emails and Swedish rules work anyway" }
      ],
      [
        { sv: "Iris", en: "Iris" },
        { sv: "Utvalda svenska bolag med research och ett färdigt mejl", en: "Selected Swedish companies with research and a finished email" },
        { sv: `Att ni läser och godkänner. Från ${LEADS} i månaden, ${BINDNING.sv}.`, en: `Reading and approving. From ${LEADS} a month, ${BINDNING.en}.` }
      ]
    ]
  },
  fragor: [
    {
      fraga: { sv: "Skriver Iris på svenska?", en: "Does Iris write in Swedish?" },
      svar: {
        sv: "Ja. Iris är byggd för svensk B2B och skriver på svenska från början, inte översatt i efterhand. Hon skriver på engelska när mottagaren gör det.",
        en: "Yes. Iris is built for Swedish B2B and writes in Swedish from the start, not translated afterwards. She writes in English when the recipient does."
      }
    },
    {
      fraga: { sv: "Är en AI-SDR samma sak som en leadsagent?", en: "Is an AI SDR the same as a lead agent?" },
      svar: {
        sv: "I stort sett. Leadsagent är det ord som används i Sverige för en AI-agent som hittar nya kunder och skriver till dem, och AI-SDR är den engelska yrkestiteln för samma arbete. Ordet används också för chattbotar som fångar besökare på en hemsida; Iris är den första sorten och kontaktar bolag som ännu inte har hittat er.",
        en: "Largely, yes. Lead agent is the word used in Sweden for an AI agent that finds new customers and writes to them, and AI SDR is the English job title for the same work. The word is also used for chatbots that capture visitors on a website; Iris is the first kind and contacts companies that have not found you yet."
      }
    },
    {
      fraga: { sv: "Vad kostar en AI-SDR från Snajp?", en: "What does an AI SDR from Snajp cost?" },
      svar: {
        sv: `Snajp Leads kostar från ${LEADS} i månaden och innehåller ${PROSPEKT.sv} och ${MEJL.sv}. Uppstarten är en engångsavgift från ${UPPSTART}, och ${BINDNING_GALLER.sv}.`,
        en: `Snajp Leads costs from ${LEADS} a month and includes ${PROSPEKT.en} and ${MEJL.en}. Onboarding is a one-off fee from ${UPPSTART}, and ${BINDNING_GALLER.en}.`
      }
    },
    {
      fraga: { sv: "Får Iris skicka mejl själv?", en: "Can Iris send emails on her own?" },
      svar: {
        sv: "Om ni vill. Ni väljer mellan tre nivåer: bara utkast, att hon får skicka det första mejlet, eller att hon får föra dialogen fram till ett möte. Hon bokar aldrig en tid utan bekräftelse.",
        en: "If you want her to. You choose between three levels: drafts only, sending the first email, or carrying the conversation up to a meeting. She never books a time without confirmation."
      }
    },
    {
      fraga: { sv: "Ersätter Iris våra säljare?", en: "Does Iris replace our sales people?" },
      svar: {
        sv: "Nej. Iris gör förarbetet: urvalet, researchen och det första utkastet. Samtalet, mötet och affären är fortfarande era.",
        en: "No. Iris does the groundwork: the selection, the research and the first draft. The conversation, the meeting and the deal are still yours."
      }
    },
    {
      fraga: { sv: "Kan vi prova innan vi bestämmer oss?", en: "Can we try before we decide?" },
      svar: {
        sv: "Ja. Iris går att prova direkt i webbläsaren med exempeldata, utan konto. Vill ni se henne arbeta med era egna kunder bokar ni en demo på 15 till 20 minuter.",
        en: "Yes. You can try Iris straight in the browser with sample data, no account needed. To see her work with your own customers, book a 15 to 20 minute demo."
      }
    }
  ],
  relaterade: ["/jamfor-ai-sdr", "/b2b-leads", "/b2b-prospektering"]
};

const B2B_LEADS: Landning = {
  vag: "/b2b-leads",
  rubrik: { sv: "Svenska B2B-leads, *utvalda* innan de når er.", en: "Swedish B2B leads, *chosen* before they reach you." },
  ingress: {
    sv: "En lista med namn är inte ett lead. Snajp väljer ut svenska bolag som passar er, kontrollerar att det finns en väg in och levererar varje bolag med en kort research och ett färdigt mejl att godkänna.",
    en: "A list of names is not a lead. Snajp picks Swedish companies that fit you, checks that there is a way in, and delivers each company with a short piece of research and a finished email to approve."
  },
  kortSvar: {
    fraga: { sv: "Vad är ett B2B-lead?", en: "What is a B2B lead?" },
    svar: {
      sv: "Ett B2B-lead är ett företag som passar det ni säljer och som ni har en rimlig väg att nå. Det har rätt bransch och storlek, en kontaktuppgift som går fram och en anledning för er att höra av er. Hos Snajp räknas ett bolag som lead först när alla tre finns på plats.",
      en: "A B2B lead is a company that fits what you sell and that you have a reasonable way to reach. It has the right industry and size, a contact detail that gets through and a reason for you to get in touch. At Snajp a company counts as a lead only when all three are in place."
    }
  },
  stegRubrik: { sv: "Från register till lead", en: "From register to lead" },
  steg: [
    {
      rubrik: { sv: "Filtret", en: "The filter" },
      text: {
        sv: "Bolagsregistret väljer ut företagen på bransch, område, storlek och omsättning. Registret används för urvalet, inte som adressbok.",
        en: "The company register selects companies by industry, area, size and turnover. The register is used for the selection, not as an address book."
      }
    },
    {
      rubrik: { sv: "Bedömningen", en: "The assessment" },
      text: {
        sv: "Varje bolag prövas mot er idealkundprofil. Det som inte passar sorteras bort innan någon research körs, så att tiden går till rätt bolag.",
        en: "Each company is checked against your ideal customer profile. Whatever does not fit is sorted out before any research runs, so the time goes to the right companies."
      }
    },
    {
      rubrik: { sv: "Kontaktvägen", en: "The way in" },
      text: {
        sv: "Kontaktuppgiften hämtas från bolagets egen webbplats, i första hand en namngiven persons adress och annars bolagets egen. Har bolaget bara telefon hamnar det i en ringlista.",
        en: "The contact detail comes from the company's own website, a named person's address first and otherwise the company's own. If the company only has a phone number, it goes on a call list."
      }
    },
    {
      rubrik: { sv: "Leveransen", en: "The delivery" },
      text: {
        sv: "Leadet kommer med det Iris hittade om bolaget och ett utkast till mejl. Ni läser, justerar om ni vill och godkänner.",
        en: "The lead arrives with what Iris found about the company and a draft email. You read it, adjust it if you like and approve."
      }
    }
  ],
  yta: {
    typ: "irisLista",
    rubrik: { sv: "Bolagen Iris har valt ut", en: "The companies Iris picked" },
    text: {
      sv: "Varje bolag har en poäng mot er profil och skälet till att det är värt er tid.",
      en: "Each company has a score against your profile and the reason it is worth your time."
    }
  },
  granser: {
    rubrik: { sv: "Vad ett lead från Snajp inte är", en: "What a lead from Snajp is not" },
    punkter: [
      { sv: "En köpt adresslista.", en: "A bought address list." },
      { sv: "En privatperson. Uppgifterna gäller företag och yrkesroller.", en: "A private individual. The data concerns companies and professional roles." },
      { sv: "En gissning. Saknar Iris underlag fyller hon inte i det själv.", en: "A guess. When Iris lacks the facts, she does not fill them in herself." },
      { sv: "Ett kasserat bolag. Den som saknar webbplats eller mejl hamnar i en egen lista i stället.", en: "A discarded company. One without a website or email goes on a list of its own instead." }
    ]
  },
  jamforelse: {
    rubrik: { sv: "Köpa leads eller få dem utvalda", en: "Buying leads or having them chosen" },
    kolumner: [
      { sv: "", en: "" },
      { sv: "Köpt leadslista", en: "Bought lead list" },
      { sv: "Leads från Snajp", en: "Leads from Snajp" }
    ],
    rader: [
      [
        { sv: "Urvalet", en: "The selection" },
        { sv: "Bransch och ort", en: "Industry and location" },
        { sv: "Bransch och ort, prövat mot er profil", en: "Industry and location, checked against your profile" }
      ],
      [
        { sv: "Kontaktuppgiften", en: "The contact detail" },
        { sv: "Varierar mellan leverantörer", en: "Varies between suppliers" },
        { sv: "Från bolagets egen webbplats", en: "From the company's own website" }
      ],
      [
        { sv: "Ingången i mejlet", en: "The opening of the email" },
        { sv: "Ni letar själva", en: "You look for it yourselves" },
        { sv: "Något bolaget själv har publicerat", en: "Something the company published itself" }
      ],
      [
        { sv: "Mejlet", en: "The email" },
        { sv: "Ni skriver det", en: "You write it" },
        { sv: "Ett färdigt utkast på svenska", en: "A finished draft in Swedish" }
      ],
      [
        { sv: "När någon svarar", en: "When someone replies" },
        { sv: "Ni håller själva reda på det", en: "You keep track yourselves" },
        { sv: "Uppföljningen slutar av sig själv", en: "The follow-up stops by itself" }
      ]
    ]
  },
  fragor: [
    {
      fraga: { sv: "Var kommer era B2B-leads ifrån?", en: "Where do your B2B leads come from?" },
      svar: {
        sv: "Urvalet görs i bolagsregistret. Kontaktuppgifterna och researchen kommer från öppna källor: bolagens egna webbplatser, platsannonser och pressmeddelanden. Vi köper inga listor och skrapar inte LinkedIn.",
        en: "The selection is made in the company register. The contact details and research come from open sources: the companies' own websites, job ads and press releases. We buy no lists and do not scrape LinkedIn."
      }
    },
    {
      fraga: { sv: "Hur många leads får vi?", en: "How many leads do we get?" },
      svar: {
        sv: `Snajp Leads innehåller ${PROSPEKT.sv} och ${MEJL.sv}. Behöver ni fler kostar varje extra prospekt ${EXTRA_PROSPEKT}.`,
        en: `Snajp Leads includes ${PROSPEKT.en} and ${MEJL.en}. If you need more, each extra prospect costs ${EXTRA_PROSPEKT}.`
      }
    },
    {
      fraga: { sv: "Kan vi styra vilka bolag som väljs?", en: "Can we control which companies are chosen?" },
      svar: {
        sv: "Ja. Ni beskriver er målgrupp vid uppstarten: bransch, område, storlek och vad som gör ett bolag intressant för er. Iris använder den profilen i varje körning.",
        en: "Yes. You describe your target market at onboarding: industry, area, size and what makes a company interesting to you. Iris uses that profile in every run."
      }
    },
    {
      fraga: { sv: "Vad händer med bolag som saknar webbplats?", en: "What happens to companies without a website?" },
      svar: {
        sv: "De kastas inte. Har bolaget telefon och en namngiven vd i registret hamnar det i ringlistan, så att ni kan ringa i stället för att mejla.",
        en: "They are not thrown away. If the company has a phone number and a named managing director in the register, it goes on the call list so you can call instead of emailing."
      }
    }
  ],
  relaterade: ["/svensk-ai-sdr", "/leads-i-inkorgen", "/b2b-prospektering"]
};

const B2B_PROSPEKTERING: Landning = {
  vag: "/b2b-prospektering",
  rubrik: { sv: "B2B-prospektering för *svenska* företag.", en: "B2B prospecting for *Swedish* companies." },
  ingress: {
    sv: "Prospektering är att hitta företagen som borde vara era kunder och ge dem en anledning att svara. Det mesta av tiden går till förarbetet. Det är den delen Iris tar över, medan samtalet och affären stannar hos er.",
    en: "Prospecting is finding the companies that ought to be your customers and giving them a reason to reply. Most of the time goes into the groundwork. That is the part Iris takes over, while the conversation and the deal stay with you."
  },
  kortSvar: {
    fraga: { sv: "Vad är B2B-prospektering?", en: "What is B2B prospecting?" },
    svar: {
      sv: "B2B-prospektering är arbetet med att hitta och kontakta företag som kan bli kunder, innan de själva har hört av sig. Det består av fyra delar: urval, research, första kontakt och uppföljning. I Sverige sker kall B2B-kontakt ofta via mejl till företag, och mottagaren ska alltid kunna tacka nej med ett klick.",
      en: "B2B prospecting is the work of finding and contacting companies that could become customers before they have got in touch themselves. It has four parts: selection, research, first contact and follow-up. In Sweden, cold B2B contact often happens by email to companies, and the recipient must always be able to say no with one click."
    }
  },
  stegRubrik: { sv: "Prospektering i fyra steg", en: "Prospecting in four steps" },
  steg: [
    {
      rubrik: { sv: "Bestäm vem ni säljer till", en: "Decide who you sell to" },
      text: {
        sv: "Bransch, storlek, område och vad som gör ett bolag redo att köpa. Det blir er idealkundprofil, och den styr varje urval Iris gör.",
        en: "Industry, size, area and what makes a company ready to buy. That becomes your ideal customer profile, and it drives every selection Iris makes."
      }
    },
    {
      rubrik: { sv: "Läs på innan ni skriver", en: "Read up before you write" },
      text: {
        sv: "Ett mejl som visar att avsändaren vet vad bolaget gör har en chans. Iris läser webbplatsen och letar efter något aktuellt, som en rekrytering eller en ny tjänst.",
        en: "An email that shows the sender knows what the company does stands a chance. Iris reads the website and looks for something current, such as a hire or a new service."
      }
    },
    {
      rubrik: { sv: "Skriv kort, på svenska", en: "Write short, in Swedish" },
      text: {
        sv: "Ett första mejl ska gå att läsa på en halv minut och sluta med en enkel fråga. Iris håller utkasten korta och utan mallfraser.",
        en: "A first email should take half a minute to read and end with a simple question. Iris keeps the drafts short and free of template phrases."
      }
    },
    {
      rubrik: { sv: "Följ upp, och sluta i tid", en: "Follow up, and stop in time" },
      text: {
        sv: "En uppföljning ger mottagaren en andra chans att svara. Svarar hen, eller avregistrerar sig, slutar utskicken direkt.",
        en: "A follow-up gives the recipient a second chance to reply. If they reply, or unsubscribe, the sends stop at once."
      }
    }
  ],
  yta: {
    typ: "irisLista",
    rubrik: { sv: "Urvalet, färdigt att arbeta med", en: "The selection, ready to work with" },
    text: {
      sv: "Iris gör förarbetet. Ni väljer vilka bolag som får ett mejl.",
      en: "Iris does the groundwork. You choose which companies get an email."
    }
  },
  granser: {
    rubrik: { sv: "Regler som gäller i varje utskick", en: "Rules that apply to every send" },
    punkter: [
      { sv: "Bara företag och yrkesroller, aldrig privatpersoner.", en: "Companies and professional roles only, never private individuals." },
      { sv: "Enskilda firmor kontaktas inte.", en: "Sole traders are not contacted." },
      { sv: "Avregistrering med ett klick, och spärren gäller alla framtida utskick.", en: "One-click unsubscribe, and the block applies to every future send." },
      { sv: "Inga utskick till HR-, ekonomi- eller jobbadresser.", en: "No sends to HR, finance or jobs addresses." }
    ]
  },
  fragor: [
    {
      fraga: { sv: "Är kalla mejl till företag tillåtna i Sverige?", en: "Are cold emails to companies allowed in Sweden?" },
      svar: {
        sv: "Marknadsföringslagen kräver samtycke för reklam via mejl till privatpersoner, men inte till juridiska personer. Därför kontaktar Snajp företag och inte enskilda firmor. Personuppgifterna behandlas med stöd av berättigat intresse enligt GDPR, och varje utskick har en avregistreringslänk.",
        en: "The Swedish Marketing Act requires consent for email advertising to private individuals, but not to legal entities. That is why Snajp contacts companies and not sole traders. Personal data is processed on the basis of legitimate interest under the GDPR, and every send carries an unsubscribe link."
      }
    },
    {
      fraga: { sv: "Vilka företag passar Iris för?", en: "Which companies is Iris right for?" },
      svar: {
        sv: "Svenska företag som säljer till andra företag och har ett tydligt erbjudande, till exempel konsulter, byråer, programvarubolag och tjänsteföretag.",
        en: "Swedish companies that sell to other companies and have a clear offer, for example consultancies, agencies, software companies and service businesses."
      }
    },
    {
      fraga: { sv: "Hur lång tid tar det att komma igång?", en: "How long does it take to get started?" },
      svar: {
        sv: "Uppstarten tar en dag: ni beskriver målgruppen och erbjudandet, och vi sätter upp profilen. Sedan sköter Iris urvalet och researchen, och er tid går till att läsa och godkänna.",
        en: "Onboarding takes a day: you describe the target market and the offer, and we set up the profile. After that Iris handles the selection and research, and your time goes into reading and approving."
      }
    },
    {
      fraga: { sv: "Kan vi ringa i stället för att mejla?", en: "Can we call instead of emailing?" },
      svar: {
        sv: "Ja. Bolag som bara har telefon hamnar i en ringlista med antalet anställda angivet, och efter samtalet noterar ni utfallet: ej svar, återkom, ej intresserad eller möte bokat.",
        en: "Yes. Companies with only a phone number go on a call list with the headcount shown, and after the call you note the outcome: no answer, call back, not interested or meeting booked."
      }
    }
  ],
  relaterade: ["/svensk-ai-sdr", "/b2b-leads", "/leads-i-inkorgen"]
};

const LEADS_I_INKORGEN: Landning = {
  vag: "/leads-i-inkorgen",
  rubrik: { sv: "Svenska leads i inkorgen, med mejlet *skrivet*.", en: "Swedish leads in your inbox, with the email *written*." },
  ingress: {
    sv: "När Iris har kört står nya bolag och färdiga utkast i er granskningskö. Ni läser, godkänner och skickar. Svarar någon samlas hela konversationen på samma ställe, och uppföljningen till den personen slutar av sig själv.",
    en: "Once Iris has run, new companies and finished drafts are waiting in your review queue. You read, approve and send. When someone replies, the whole conversation gathers in one place and the follow-up to that person stops by itself."
  },
  kortSvar: {
    fraga: { sv: "Vad betyder det att få leads levererade?", en: "What does it mean to have leads delivered?" },
    svar: {
      sv: "Att få leads levererade betyder att någon annan gör urvalet och researchen, och att ni får färdiga bolag att arbeta med i stället för en lista att bearbeta. Hos Snajp kommer varje lead med en kort motivering och ett utkast till mejl, så att nästa steg är att läsa och godkänna.",
      en: "Having leads delivered means someone else does the selection and research, and you get companies ready to work with instead of a list to process. At Snajp each lead comes with a short reason and a draft email, so the next step is to read and approve."
    }
  },
  stegRubrik: { sv: "En vecka med Iris", en: "A week with Iris" },
  steg: [
    {
      rubrik: { sv: "Utkasten väntar", en: "The drafts are waiting" },
      text: {
        sv: "Nya bolag och deras utkast står i granskningskön, sorterade efter hur väl de passar er.",
        en: "New companies and their drafts sit in the review queue, sorted by how well they fit you."
      }
    },
    {
      rubrik: { sv: "Ni godkänner", en: "You approve" },
      text: {
        sv: "Läs, ändra med ett knapptryck och skicka. Ett bolag ni inte vill kontakta hoppar ni över.",
        en: "Read, change it at the press of a button and send. A company you do not want to contact, you skip."
      }
    },
    {
      rubrik: { sv: "Svaren samlas", en: "The replies gather" },
      text: {
        sv: "Under Skickat ser ni utskicket och svaret i samma tråd. Den som har svarat får inga fler automatiska uppföljningar.",
        en: "Under Sent you see the send and the reply in the same thread. Anyone who has replied gets no more automatic follow-ups."
      }
    },
    {
      rubrik: { sv: "Ringlistan bevakas", en: "The call list is watched" },
      text: {
        sv: "Bolag ni har ringt kommer tillbaka när det är dags: ej svar efter två arbetsdagar och återkom på det datum ni angav.",
        en: "Companies you have called come back when it is time: no answer after two working days, and call back on the date you set."
      }
    }
  ],
  yta: {
    typ: "irisUtkast",
    rubrik: { sv: "Utkastet, klart att godkänna", en: "The draft, ready to approve" },
    text: {
      sv: "Ni ser mottagaren, ämnesraden och hela texten innan något går ut.",
      en: "You see the recipient, the subject line and the full text before anything goes out."
    }
  },
  granser: {
    rubrik: { sv: "Ni behåller kontrollen", en: "You stay in control" },
    punkter: [
      { sv: "Inget går ut som ni inte har gett lov till.", en: "Nothing goes out that you have not allowed." },
      { sv: "Uppföljningar är alltid utkast som en människa godkänner.", en: "Follow-ups are always drafts a person approves." },
      { sv: "Ett avslutande utfall, som kontakta inte, stoppar alla utskick till bolaget.", en: "A closing outcome, such as do not contact, stops every send to the company." },
      { sv: "Varje utskick har en avregistreringslänk som fungerar med ett klick.", en: "Every send carries an unsubscribe link that works with one click." }
    ]
  },
  fragor: [
    {
      fraga: { sv: "Hamnar leadsen i vår vanliga mejlinkorg?", en: "Do the leads land in our normal email inbox?" },
      svar: {
        sv: "Leadsen och utkasten samlas i Snajp, i granskningskön, så att de inte drunknar bland annan post. Det är där ni godkänner, och där ni ser svaren i samma tråd som utskicket.",
        en: "The leads and drafts gather in Snajp, in the review queue, so they do not drown among other mail. That is where you approve, and where you see the replies in the same thread as the send."
      }
    },
    {
      fraga: { sv: "Hur ofta kommer det nya leads?", en: "How often do new leads arrive?" },
      svar: {
        sv: `Det styr ni själva inom paketets volym, som är ${PROSPEKT.sv}. Kör ni Iris varje vecka blir granskningen en fast rutin i stället för en hög som växer.`,
        en: `You decide that yourselves within the package volume, which is ${PROSPEKT.en}. Run Iris every week and reviewing becomes a fixed routine instead of a growing pile.`
      }
    },
    {
      fraga: { sv: "Vad händer när någon svarar?", en: "What happens when someone replies?" },
      svar: {
        sv: "Uppföljningen till den personen slutar direkt, och svaret visas tillsammans med utskicket under Skickat. Ett uppföljningsmejl är alltid ett utkast som ni godkänner.",
        en: "The follow-up to that person stops at once, and the reply appears together with the send under Sent. A follow-up email is always a draft you approve."
      }
    }
  ],
  relaterade: ["/svensk-ai-sdr", "/b2b-leads", "/b2b-prospektering"]
};

const SUPPORT_PA_SVENSKA: Landning = {
  vag: "/support-pa-svenska",
  rubrik: { sv: "Support som svarar på *svenska*.", en: "Support that replies in *Swedish*." },
  ingress: {
    sv: "Snajp Support är en AI-agent för kundtjänst. Den läser era inkommande mejl och chattar, förstår vad kunden vill och skriver svaret på svenska med era egna formuleringar. Det den saknar underlag för lämnar den till en människa.",
    en: "Snajp Support is an AI customer service agent. It reads your incoming emails and chats, understands what the customer wants and writes the reply in Swedish in your own words. Whatever it lacks the facts for, it hands to a person."
  },
  kortSvar: {
    fraga: { sv: "Vad är AI-support på svenska?", en: "What is AI support in Swedish?" },
    svar: {
      sv: "AI-support på svenska är en agent som svarar era kunder på svenska utifrån ert eget underlag: villkor, priser, leveranstider och svar ni redan har skrivit. Den hämtar formuleringarna ur er kunskapsbas i stället för att översätta från engelska, så svaret låter som ert bolag och inte som en allmän assistent.",
      en: "AI support in Swedish is an agent that answers your customers in Swedish from your own material: terms, prices, delivery times and replies you have already written. It takes its wording from your knowledge base instead of translating from English, so the reply sounds like your company and not a generic assistant."
    }
  },
  stegRubrik: { sv: "Så hanteras ett ärende", en: "How a case is handled" },
  steg: [
    {
      rubrik: { sv: "Agenten läser", en: "The agent reads" },
      text: {
        sv: "Varje nytt mejl eller chattmeddelande läses direkt. Agenten avgör vad det gäller, hur brådskande det är och vilken ton kunden har.",
        en: "Every new email or chat message is read at once. The agent works out what it is about, how urgent it is and what tone the customer has."
      }
    },
    {
      rubrik: { sv: "Ärendet sorteras", en: "The case is sorted" },
      text: {
        sv: "Det hamnar i rätt fack, till exempel order, retur, faktura eller offert. Det brådskande ligger inte längre under nio ärenden som kan vänta.",
        en: "It lands in the right category, such as order, return, invoice or quote. The urgent case no longer sits underneath nine that can wait."
      }
    },
    {
      rubrik: { sv: "Svaret skrivs", en: "The reply is written" },
      text: {
        sv: "Svaret kommer ur er kunskapsbas, på svenska eller engelska beroende på vad kunden skrev. Ni väljer per fack om agenten svarar själv eller lämnar ett utkast.",
        en: "The reply comes from your knowledge base, in Swedish or English depending on what the customer wrote. You choose per category whether the agent replies itself or leaves a draft."
      }
    },
    {
      rubrik: { sv: "Det svåra lämnas över", en: "The hard cases are handed over" },
      text: {
        sv: "Återbetalningar, fakturafel, juridik, GDPR och arga kunder går alltid till en människa, med hela historiken bifogad.",
        en: "Refunds, invoice errors, legal matters, GDPR and angry customers always go to a person, with the full history attached."
      }
    }
  ],
  yta: {
    typ: "inkorg",
    rubrik: { sv: "Inkorgen efter agenten", en: "The inbox after the agent" },
    text: {
      sv: "Ärendena är sorterade, och varje svar väntar på ert godkännande.",
      en: "The cases are sorted, and every reply is waiting for your approval."
    }
  },
  granser: {
    rubrik: { sv: "Vad agenten aldrig gör", en: "What the agent never does" },
    punkter: [
      { sv: "Hittar på ett svar den saknar underlag för.", en: "Makes up an answer it has no material for." },
      { sv: "Lovar pengar tillbaka eller fattar juridiska beslut.", en: "Promises money back or makes legal decisions." },
      { sv: "Döljer att den är en agent. Svaret är märkt.", en: "Hides that it is an agent. The reply is labelled." },
      { sv: "Svarar i sociala medier. Den arbetar i er mejlinkorg och i chatten på er hemsida.", en: "Replies on social media. It works in your email inbox and in the chat on your website." }
    ]
  },
  jamforelse: {
    rubrik: { sv: "Supportagent eller regelstyrd chatbot", en: "Support agent or rule-based chatbot" },
    kolumner: [
      { sv: "", en: "" },
      { sv: "Regelstyrd chatbot", en: "Rule-based chatbot" },
      { sv: "Snajp Support", en: "Snajp Support" }
    ],
    rader: [
      [
        { sv: "Svaren", en: "The answers" },
        { sv: "Förskrivna flöden som byggs för hand", en: "Pre-written flows built by hand" },
        { sv: "Skrivs ur er kunskapsbas för varje fråga", en: "Written from your knowledge base for each question" }
      ],
      [
        { sv: "När svaret saknas", en: "When the answer is missing" },
        { sv: "Ett standardsvar eller en återvändsgränd", en: "A stock reply or a dead end" },
        { sv: "Säger det rakt ut och lämnar över", en: "Says so plainly and hands over" }
      ],
      [
        { sv: "Kanaler", en: "Channels" },
        { sv: "Ofta bara chatten", en: "Often just the chat" },
        { sv: "Mejlinkorgen och chatten", en: "The email inbox and the chat" }
      ],
      [
        { sv: "Språk", en: "Language" },
        { sv: "Det språk flödet skrevs på", en: "The language the flow was written in" },
        { sv: "Svenska eller engelska, efter kunden", en: "Swedish or English, following the customer" }
      ]
    ]
  },
  fragor: [
    {
      fraga: { sv: "Svarar agenten på svenska även om kunskapsbasen är på engelska?", en: "Does the agent reply in Swedish even if the knowledge base is in English?" },
      svar: {
        sv: "Den svarar på det språk kunden skriver, svenska eller engelska, oavsett vilket språk kunskapsbasen har. Andra språk erbjuds inte.",
        en: "It replies in the language the customer writes, Swedish or English, whatever language the knowledge base is in. Other languages are not offered."
      }
    },
    {
      fraga: { sv: "Vilka kanaler hanterar den?", en: "Which channels does it handle?" },
      svar: {
        sv: "Två: er mejlinkorg och chatten på er hemsida. Sociala medier som Facebook, Instagram och WhatsApp hanteras inte.",
        en: "Two: your email inbox and the chat on your website. Social media such as Facebook, Instagram and WhatsApp are not handled."
      }
    },
    {
      fraga: { sv: "Hur kopplar vi in vår inkorg?", en: "How do we connect our inbox?" },
      svar: {
        sv: "Under Inställningar, till exempel en Gmail-inkorg med ett app-lösenord från mejlleverantören. Att koppla inkorgen och fylla kunskapsbasen tar en dag.",
        en: "Under Settings, for example a Gmail inbox with an app password from your email provider. Connecting the inbox and filling the knowledge base takes a day."
      }
    },
    {
      fraga: { sv: "Vad kostar AI-support från Snajp?", en: "What does AI support from Snajp cost?" },
      svar: {
        sv: `Snajp Support kostar från ${SUPPORT} i månaden med obegränsade chattar och e-posttriage. Uppstarten kostar från ${UPPSTART}, och ${BINDNING_GALLER.sv}.`,
        en: `Snajp Support costs from ${SUPPORT} a month with unlimited chats and email triage. Onboarding costs from ${UPPSTART}, and ${BINDNING_GALLER.en}.`
      }
    },
    {
      fraga: { sv: "Var lagras våra kunders mejl?", en: "Where are our customers' emails stored?" },
      svar: {
        sv: "Databasen ligger inom EU, och varje kunds data är avskild på databasnivå. Vilken AI-leverantör som behandlar texten står med namn i integritetspolicyn.",
        en: "The database is inside the EU, and each customer's data is isolated at database level. Which AI provider processes the text is named in the privacy policy."
      }
    }
  ],
  relaterade: ["/supportchatt", "/ai-supportagent", "/ai-agenter"]
};

const SUPPORTCHATT: Landning = {
  vag: "/supportchatt",
  rubrik: { sv: "Svensk supportchatt till er *hemsida*.", en: "A Swedish support chat for your *website*." },
  ingress: {
    sv: "Chatten läggs in på er webbplats med en rad kod och svarar besökarna dygnet runt på svenska, ur samma kunskapsbas som er mejlsupport. Den bär er logotyp och era färger, och den hittar inte på.",
    en: "The chat goes onto your website with one line of code and answers visitors around the clock in Swedish, from the same knowledge base as your email support. It carries your logo and your colours, and it does not make things up."
  },
  kortSvar: {
    fraga: { sv: "Vad är en supportagent för hemsidan?", en: "What is a support agent for a website?" },
    svar: {
      sv: "En supportagent för hemsidan är en chattruta som svarar besökarnas frågor direkt, utan att någon behöver bevaka den. Snajps supportagent svarar på svenska ur er egen kunskapsbas i stället för förskrivna flöden. Frågor den saknar underlag för lämnar den till er, i stället för att gissa.",
      en: "A support agent for a website is a chat box that answers visitors' questions straight away, without anyone having to watch it. Snajp's support agent answers in Swedish from your own knowledge base rather than pre-written flows. Questions it has no material for it passes to you instead of guessing."
    }
  },
  stegRubrik: { sv: "Från kodrad till svar", en: "From one line of code to an answer" },
  steg: [
    {
      rubrik: { sv: "Klistra in", en: "Paste it in" },
      text: {
        sv: "Ni lägger en rad kod sist på sidan. Den fungerar på alla webbplatser där ni kan lägga in ett skript, och ingen plugin behövs.",
        en: "You add one line of code at the end of the page. It works on any website where you can add a script, and no plugin is needed."
      }
    },
    {
      rubrik: { sv: "Er profil", en: "Your look" },
      text: {
        sv: "Panelen visar er logotyp och er accentfärg. Chatten kan bara visas på de domäner ni har godkänt.",
        en: "The panel shows your logo and your accent colour. The chat can only appear on the domains you have approved."
      }
    },
    {
      rubrik: { sv: "Svaren", en: "The answers" },
      text: {
        sv: "Besökaren frågar med egna ord och får svar ur kunskapsbasen, på svenska eller engelska.",
        en: "The visitor asks in their own words and gets an answer from the knowledge base, in Swedish or English."
      }
    },
    {
      rubrik: { sv: "Överlämningen", en: "The handover" },
      text: {
        sv: "Frågor om pengar tillbaka, fakturor eller juridik, och besökare som vill prata med en människa, lämnas över i stället för att besvaras.",
        en: "Questions about refunds, invoices or legal matters, and visitors who want to talk to a person, are handed over instead of answered."
      }
    }
  ],
  yta: {
    typ: "widget",
    rubrik: { sv: "Chatten på er egen sajt", en: "The chat on your own site" },
    text: {
      sv: "Stängd tills besökaren behöver den, och i era färger.",
      en: "Closed until the visitor needs it, and in your colours."
    }
  },
  granser: {
    rubrik: { sv: "Byggd för att inte störa er sajt", en: "Built not to get in the way of your site" },
    punkter: [
      { sv: "Felar skriptet händer ingenting på er sida.", en: "If the script fails, nothing happens on your page." },
      { sv: "Visas bara på de domäner ni har godkänt.", en: "Only appears on the domains you have approved." },
      { sv: "Ingen hemlig nyckel i koden på er webbplats.", en: "No secret key in the code on your website." },
      { sv: "Obegränsade chattar i paketet, utan pris per samtal.", en: "Unlimited chats in the package, with no price per conversation." }
    ]
  },
  fragor: [
    {
      fraga: { sv: "Hur installerar vi chatten?", en: "How do we install the chat?" },
      svar: {
        sv: "Ni klistrar in en rad kod som ni får av oss, sist i sidans kod. Ingen plugin och ingen app behövs.",
        en: "You paste in one line of code that we give you, at the end of the page's code. No plugin and no app is needed."
      }
    },
    {
      fraga: { sv: "Kan chatten svara på frågor om våra produkter?", en: "Can the chat answer questions about our products?" },
      svar: {
        sv: "Ja, så länge svaret finns i kunskapsbasen. Den byggs vid uppstarten av er webbplats, era villkor och det ni berättar för oss.",
        en: "Yes, as long as the answer is in the knowledge base. It is built at onboarding from your website, your terms and what you tell us."
      }
    },
    {
      fraga: { sv: "Vad händer när chatten inte vet svaret?", en: "What happens when the chat does not know the answer?" },
      svar: {
        sv: "Den säger att den inte har uppgiften, svarar på det den har stöd för och erbjuder att en kollega tar resten.",
        en: "It says it does not have the information, answers what it has support for and offers to have a colleague take the rest."
      }
    },
    {
      fraga: { sv: "Kostar varje chatt extra?", en: "Does each chat cost extra?" },
      svar: {
        sv: `Nej. Snajp Support har obegränsade chattar och kostar från ${SUPPORT} i månaden.`,
        en: `No. Snajp Support has unlimited chats and costs from ${SUPPORT} a month.`
      }
    },
    {
      fraga: { sv: "Märker besökaren att det är en AI?", en: "Can the visitor tell it is an AI?" },
      svar: {
        sv: "Ja. Svaren är märkta. Att dölja det skulle spara en sekund och kosta förtroendet.",
        en: "Yes. The replies are labelled. Hiding it would save a second and cost the trust."
      }
    },
    {
      fraga: { sv: "Är det samma supportagent i chatten och i mejlen?", en: "Is it the same support agent in the chat and in email?" },
      svar: {
        sv: "Ja. Supportagenten svarar i chatten på hemsidan och arbetar i mejlinkorgen: den sorterar kundmejlen, skriver svaren och lämnar över det som kräver en människa. Det är samma agent och samma kunskapsbas i båda kanalerna.",
        en: "Yes. The support agent answers in the chat on your website and works in the email inbox: it sorts customer email, writes the replies and hands over what needs a person. It is the same agent and the same knowledge base in both channels."
      }
    }
  ],
  relaterade: ["/jamfor-supportagenter", "/support-pa-svenska", "/ai-supportagent"]
};

const AI_SUPPORTAGENT: Landning = {
  vag: "/ai-supportagent",
  rubrik: { sv: "En AI-supportagent som vet sina *gränser*.", en: "An AI support agent that knows its *limits*." },
  ingress: {
    sv: "Snajp Support är en supportagent för företag som får många mejl med samma frågor. Den gör förarbetet i kundtjänsten: sorterar, prioriterar och skriver svar. Ni bestämmer per typ av ärende hur långt den får gå.",
    en: "Snajp Support is a support agent for companies that get a lot of email with the same questions. It does the groundwork in customer service: sorting, prioritising and writing replies. You decide per type of case how far it may go."
  },
  kortSvar: {
    fraga: { sv: "Vad gör en AI-supportagent?", en: "What does an AI support agent do?" },
    svar: {
      sv: "En AI-supportagent läser inkommande kundärenden, avgör vad de gäller och hur brådskande de är, och skriver ett svar ur företagets eget underlag. Den skiljer sig från en chatbot genom att den också arbetar i mejlinkorgen och lämnar över de ärenden den inte ska hantera själv.",
      en: "An AI support agent reads incoming customer cases, works out what they are about and how urgent they are, and writes a reply from the company's own material. It differs from a chatbot in that it also works in the email inbox and hands over the cases it should not handle on its own."
    }
  },
  stegRubrik: { sv: "Tre nivåer, valda per fack", en: "Three levels, chosen per category" },
  steg: [
    {
      rubrik: { sv: "Svarar själv", en: "Replies itself" },
      text: {
        sv: "För enkla frågor med ett tydligt svar i kunskapsbasen, som leveranstider och öppettider.",
        en: "For simple questions with a clear answer in the knowledge base, such as delivery times and opening hours."
      }
    },
    {
      rubrik: { sv: "Skriver ett utkast", en: "Writes a draft" },
      text: {
        sv: "Agenten skriver svaret, och ni godkänner med ett klick eller låter den skriva om.",
        en: "The agent writes the reply, and you approve with one click or have it rewrite."
      }
    },
    {
      rubrik: { sv: "Lämnar alltid över", en: "Always hands over" },
      text: {
        sv: "För ärenden som ska till en människa, hur säker agenten än är.",
        en: "For cases that should go to a person, however confident the agent is."
      }
    },
    {
      rubrik: { sv: "Ni ser varför", en: "You see why" },
      text: {
        sv: "Varje ärende visar vilket fack det hamnade i, hur säker agenten var och vilket svar den föreslår.",
        en: "Every case shows which category it landed in, how confident the agent was and which reply it proposes."
      }
    }
  ],
  yta: {
    typ: "inkorg",
    rubrik: { sv: "Kundtjänstinkorgen, sorterad", en: "The service inbox, sorted" },
    text: {
      sv: "Agenten sorterar, skriver utkastet och räknar fram offerten. Ni trycker godkänn.",
      en: "The agent sorts, drafts the reply and works out the quote. You press approve."
    }
  },
  granser: {
    rubrik: { sv: "Ärenden som alltid går till en människa", en: "Cases that always go to a person" },
    punkter: [
      { sv: "Pengar tillbaka och fakturafel.", en: "Refunds and invoice errors." },
      { sv: "Juridik, GDPR-begäranden och säkerhet.", en: "Legal matters, GDPR requests and security." },
      { sv: "En arg kund, en kund i kris eller en kund som ber om en människa.", en: "An angry customer, a customer in crisis or a customer asking for a person." },
      { sv: "Motstridiga uppgifter i underlaget. Agenten jämkar inte ihop dem.", en: "Conflicting information in the material. The agent does not paper over it." }
    ]
  },
  jamforelse: {
    rubrik: { sv: "Kundtjänsten med och utan agent", en: "Customer service with and without the agent" },
    kolumner: [
      { sv: "", en: "" },
      { sv: "Utan agent", en: "Without the agent" },
      { sv: "Med Snajp Support", en: "With Snajp Support" }
    ],
    rader: [
      [
        { sv: "Sorteringen", en: "Triage" },
        { sv: "Någon läser varje mejl först", en: "Someone reads every email first" },
        { sv: "Ärendet sorteras när det kommer in", en: "The case is sorted as it arrives" }
      ],
      [
        { sv: "Svaret", en: "The reply" },
        { sv: "Letas fram i gamla mejl och dokument", en: "Dug out of old emails and documents" },
        { sv: "Ett utkast ur kunskapsbasen", en: "A draft from the knowledge base" }
      ],
      [
        { sv: "Det svåra ärendet", en: "The hard case" },
        { sv: "Konkurrerar med de enkla om tiden", en: "Competes with the easy ones for time" },
        { sv: "Lämnas över med historiken bifogad", en: "Handed over with the history attached" }
      ]
    ]
  },
  fragor: [
    {
      fraga: { sv: "Vad är skillnaden mellan en supportagent och en chatbot?", en: "What is the difference between a support agent and a chatbot?" },
      svar: {
        sv: "En chatbot svarar i en chattruta. En supportagent arbetar även i mejlinkorgen, sorterar ärenden och skriver utkast som en människa kan godkänna. Snajp Support gör båda delarna.",
        en: "A chatbot answers in a chat box. A support agent also works in the email inbox, sorts cases and writes drafts a person can approve. Snajp Support does both."
      }
    },
    {
      fraga: { sv: "Passar den för företagssupport med B2B-kunder?", en: "Does it suit business support with B2B customers?" },
      svar: {
        sv: "Ja. Agenten svarar med den ton som står i er kunskapsbas, vare sig kunderna är företag eller privatpersoner, och offerter och fakturafrågor sorteras i egna fack.",
        en: "Yes. The agent replies in the tone set out in your knowledge base, whether your customers are businesses or individuals, and quotes and invoice questions are sorted into their own categories."
      }
    },
    {
      fraga: { sv: "Kan vi börja med bara utkast?", en: "Can we start with drafts only?" },
      svar: {
        sv: "Ja, och det är så vi rekommenderar att börja. Kör agenten i utkastläge ett par dagar och rätta det som blir fel, innan den får svara själv i något fack.",
        en: "Yes, and that is how we recommend starting. Run the agent in draft mode for a few days and correct what comes out wrong before it may reply itself in any category."
      }
    },
    {
      fraga: { sv: "Hur lång tid tar det att komma igång?", en: "How long does setup take?" },
      svar: {
        sv: "Att koppla inkorgen och fylla kunskapsbasen tar en dag. Det som tar tid är att komma överens om tonen, och det gör ni bäst genom att rätta agentens utkast de första dagarna.",
        en: "Connecting the inbox and filling the knowledge base takes a day. What takes time is agreeing on the tone, and that is best done by correcting the agent's drafts in the first few days."
      }
    }
  ],
  relaterade: ["/jamfor-supportagenter", "/support-pa-svenska", "/supportchatt"]
};

const AI_AGENTER: Landning = {
  vag: "/ai-agenter",
  rubrik: { sv: "AI-agenter för svenska företag, i en *arbetsyta*.", en: "AI agents for Swedish companies, in one *workspace*." },
  ingress: {
    sv: "Snajp har två AI-agenter. Iris hittar och skriver till nya kunder, och supportagenten svarar de kunder ni redan har. Båda arbetar på svenska, och båda vet vad de inte ska göra på egen hand.",
    en: "Snajp has two AI agents. Iris finds and writes to new customers, and the support agent answers the customers you already have. Both work in Swedish, and both know what they should not do on their own."
  },
  kortSvar: {
    fraga: { sv: "Vad är en AI-agent?", en: "What is an AI agent?" },
    svar: {
      sv: "En AI-agent är ett program som tar emot ett mål, planerar stegen dit och använder verktyg för att nå det. En chatbot svarar bara på det den får. En agent för företag behöver tydliga gränser: den ska veta vad den får göra själv och vad som ska till en människa.",
      en: "An AI agent is a program that takes a goal, plans the steps towards it and uses tools to get there. A chatbot only answers what it is given. An agent for business needs clear limits: it has to know what it may do on its own and what should go to a person."
    }
  },
  stegRubrik: { sv: "Två agenter, en arbetsyta", en: "Two agents, one workspace" },
  steg: [
    {
      rubrik: { sv: "Iris, leadsagenten", en: "Iris, the leads agent" },
      text: {
        sv: "Väljer ut svenska bolag som passar er, läser på om dem och skriver det första mejlet.",
        en: "Picks Swedish companies that fit you, reads up on them and writes the first email."
      }
    },
    {
      rubrik: { sv: "Supportagenten", en: "The support agent" },
      text: {
        sv: "Läser kundmejl och chattar, sorterar dem och svarar ur er kunskapsbas.",
        en: "Reads customer emails and chats, sorts them and answers from your knowledge base."
      }
    },
    {
      rubrik: { sv: "Delad kunddata", en: "Shared customer data" },
      text: {
        sv: "Med Snajp Duo delar agenterna kunddata i samma arbetsyta, så att nya leads och befintliga kundärenden finns på ett ställe.",
        en: "With Snajp Duo the agents share customer data in one workspace, so new leads and existing customer cases sit in one place."
      }
    },
    {
      rubrik: { sv: "Byggt i Sverige", en: "Built in Sweden" },
      text: {
        sv: "Snajp utvecklas i Göteborg och Umeå, och vi använder agenterna i vår egen verksamhet.",
        en: "Snajp is developed in Gothenburg and Umeå, and we use the agents in our own business."
      }
    }
  ],
  yta: {
    typ: "widget",
    rubrik: { sv: "Supportagenten på en kunds sajt", en: "The support agent on a customer's site" },
    text: {
      sv: "Samma agent svarar i chatten och i mejlinkorgen.",
      en: "The same agent answers in the chat and in the email inbox."
    }
  },
  granser: {
    rubrik: { sv: "Gemensamt för båda agenterna", en: "What both agents share" },
    punkter: [
      { sv: "De föreslår, och ni bestämmer hur mycket de får göra själva.", en: "They propose, and you decide how much they may do on their own." },
      { sv: "De svarar på svenska och engelska.", en: "They reply in Swedish and English." },
      { sv: "Varje kunds data är avskild på databasnivå och lagras inom EU.", en: "Each customer's data is isolated at database level and stored inside the EU." },
      { sv: "De hittar inte på. Saknas underlag säger de det.", en: "They do not make things up. When the material is missing, they say so." }
    ]
  },
  jamforelse: {
    rubrik: { sv: "Välj agent efter uppgift", en: "Choose an agent by task" },
    kolumner: [
      { sv: "", en: "" },
      { sv: "Iris (Snajp Leads)", en: "Iris (Snajp Leads)" },
      { sv: "Supportagenten (Snajp Support)", en: "Support agent (Snajp Support)" }
    ],
    rader: [
      [
        { sv: "Uppgiften", en: "The task" },
        { sv: "Hitta och kontakta nya kunder", en: "Find and contact new customers" },
        { sv: "Svara de kunder ni redan har", en: "Answer the customers you already have" }
      ],
      [
        { sv: "Arbetar i", en: "Works in" },
        { sv: "Granskningskön och utskicken", en: "The review queue and the sends" },
        { sv: "Mejlinkorgen och chatten på hemsidan", en: "The email inbox and the chat on your website" }
      ],
      [
        { sv: "Pris", en: "Price" },
        { sv: `Från ${LEADS} i månaden`, en: `From ${LEADS} a month` },
        { sv: `Från ${SUPPORT} i månaden`, en: `From ${SUPPORT} a month` }
      ]
    ]
  },
  fragor: [
    {
      fraga: { sv: "Vad är skillnaden mellan en AI-agent och en chatbot?", en: "What is the difference between an AI agent and a chatbot?" },
      svar: {
        sv: "En chatbot svarar på frågor. En AI-agent utför en uppgift i flera steg, som att välja ut bolag, läsa på om dem och skriva ett mejl, och lämnar över när uppgiften kräver en människa.",
        en: "A chatbot answers questions. An AI agent carries out a task in several steps, such as picking companies, reading up on them and writing an email, and hands over when the task needs a person."
      }
    },
    {
      fraga: { sv: "Kan vi använda båda agenterna?", en: "Can we use both agents?" },
      svar: {
        sv: `Ja. Snajp Duo ger er båda agenterna i samma arbetsyta med delad kunddata. Duo kostar från ${DUO} i månaden, ${DUO_SPAR} mindre än att köpa dem var för sig.`,
        en: `Yes. Snajp Duo gives you both agents in one workspace with shared customer data. Duo costs from ${DUO} a month, ${DUO_SPAR} less than buying them separately.`
      }
    },
    {
      fraga: { sv: "Tränas AI-modellen på vår data?", en: "Is the AI model trained on our data?" },
      svar: {
        sv: "Nej. Texten skickas till vår AI-leverantör för att svaret ska kunna skrivas, och leverantören tränar inte på den. Vilken leverantör det är står i integritetspolicyn.",
        en: "No. The text is sent to our AI provider so the reply can be written, and the provider does not train on it. Which provider it is is stated in the privacy policy."
      }
    },
    {
      fraga: { sv: "Vem står bakom Snajp?", en: "Who is behind Snajp?" },
      svar: {
        sv: `Snajp grundades av ${GRUNDARE.sv} och utvecklas i Göteborg och Umeå. Vi säljer till svensk B2B och använder produkten själva varje dag.`,
        en: `Snajp was founded by ${GRUNDARE.en} and is developed in Gothenburg and Umeå. We sell to Swedish B2B and use the product ourselves every day.`
      }
    }
  ],
  relaterade: ["/svensk-ai-sdr", "/support-pa-svenska", "/b2b-leads"]
};

/** Kontrolldagen som text, t.ex. "6 november 2026". UTC så att servern och webbläsaren skriver samma dag. */
const KONTROLL_DAG: Localized = {
  sv: new Date(`${KONTROLLERAD}T12:00:00Z`).toLocaleDateString("sv-SE", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }),
  en: new Date(`${KONTROLLERAD}T12:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })
};

const SA_HAR_VI_JAMFORT = (saljer: Localized): Landning["granser"] => ({
  rubrik: { sv: "Så har vi jämfört", en: "How we compared" },
  punkter: [
    { sv: `Bara leverantörernas egna sidor, kontrollerade ${KONTROLL_DAG.sv}.`, en: `Only the vendors' own pages, checked on ${KONTROLL_DAG.en}.` },
    { sv: "Det en leverantör inte själv skriver står som Ej angivet.", en: "What a vendor does not state itself is marked Not stated." },
    { sv: "Priserna är leverantörernas egna, i den valuta de anger.", en: "Prices are the vendors' own, in the currency they give." },
    saljer
  ]
});

const KONTROLL_FRAGA: Fraga = {
  fraga: { sv: "Hur ofta kontrolleras jämförelsen?", en: "How often is the comparison checked?" },
  svar: {
    sv: `Minst var tredje månad, senast ${KONTROLL_DAG.sv}. Har en leverantör ändrat något, eller har vi fel om någon, skriv till oss så rättar vi tabellen.`,
    en: `At least every three months, most recently on ${KONTROLL_DAG.en}. If a vendor has changed something, or we have got someone wrong, write to us and we will correct the table.`
  }
};

const JAMFOR_AI_SDR: Landning = {
  vag: "/jamfor-ai-sdr",
  rubrik: { sv: "AI-SDR i Sverige, *jämförda*.", en: "AI SDRs in Sweden, *compared*." },
  ingress: {
    sv: "Vi har läst varje leverantörs egna sidor och ställt upp det de själva säger om språk, godkännande, data och pris. Snajp säljer Iris, som står först. Det en leverantör inte skriver står som Ej angivet.",
    en: "We read each vendor's own pages and set out what they say themselves about language, approval, data and price. Snajp sells Iris, listed first. What a vendor does not state is marked Not stated."
  },
  kortSvar: {
    fraga: { sv: "Vilken AI-SDR passar ett svenskt företag?", en: "Which AI SDR suits a Swedish company?" },
    svar: {
      sv: `Den som skriver på svenska från början, låter en människa godkänna utskicken tills texterna håller, lagrar datan inom EU och har ett pris ni kan räkna hem. Tabellen nedan jämför ${AI_SDR_VERKTYG.length + 1} verktyg på de punkterna, hämtat ur varje leverantörs egna sidor. Snajp säljer ett av dem, Iris.`,
      en: `One that writes in Swedish from the start, lets a person approve the sends until the texts hold up, stores data in the EU and has a price you can earn back. The table below compares ${AI_SDR_VERKTYG.length + 1} tools on those points, taken from each vendor's own pages. Snajp sells one of them, Iris.`
    }
  },
  stegRubrik: { sv: "Fyra frågor att ställa", en: "Four questions to ask" },
  steg: [
    {
      rubrik: { sv: "Språket", en: "The language" },
      text: {
        sv: "Skrivs mejlet på svenska från början, eller översätts det i efterhand? Svenska köpare läser tilltalet och ordvalen först.",
        en: "Is the email written in Swedish from the start, or translated afterwards? Swedish buyers read the form of address and the word choice first."
      }
    },
    {
      rubrik: { sv: "Urvalet", en: "The selection" },
      text: {
        sv: "Var kommer bolagen ifrån? En köpt lista, LinkedIn och bolagsregistret ger olika träffar och har olika regler.",
        en: "Where do the companies come from? A bought list, LinkedIn and the company register give different hits and come with different rules."
      }
    },
    {
      rubrik: { sv: "Godkännandet", en: "The approval" },
      text: {
        sv: "Vem trycker på skicka? Börja med att en människa godkänner varje mejl, och släpp på när ni litar på texterna.",
        en: "Who presses send? Start with a person approving every email, and loosen it once you trust the texts."
      }
    },
    {
      rubrik: { sv: "Datan", en: "The data" },
      text: {
        sv: "Var lagras uppgifterna, och skriver leverantören ett personuppgiftsbiträdesavtal? Det avgör om ni kan använda verktyget enligt GDPR.",
        en: "Where is the data stored, and does the vendor sign a data processing agreement? That decides whether you can use the tool under GDPR."
      }
    }
  ],
  yta: {
    typ: "irisLista",
    rubrik: { sv: "Iris urval av nya bolag", en: "Iris's selection of new companies" },
    text: {
      sv: "Så ser urvalet ut i Snajp: bolag, skäl och ett utkast per rad.",
      en: "What the selection looks like in Snajp: company, reason and a draft per row."
    }
  },
  granser: SA_HAR_VI_JAMFORT({ sv: "Snajp säljer Iris. Läs tabellen med det i minnet.", en: "Snajp sells Iris. Read the table with that in mind." }),
  jamforelse: {
    rubrik: { sv: "AI-SDR och leadsagenter för svenska företag", en: "AI SDRs and lead agents for Swedish companies" },
    kolumner: [
      { sv: "Verktyg", en: "Tool" },
      { sv: "Vad det är", en: "What it is" },
      { sv: "Svenska", en: "Swedish" },
      { sv: "Godkännande", en: "Approval" },
      { sv: "Data", en: "Data" },
      { sv: "Pris", en: "Price" }
    ],
    rader: [
      [
        { sv: "Iris (Snajp)", en: "Iris (Snajp)" },
        { sv: "Svensk AI-SDR: urval ur bolagsregistret, research på bolagets egen sajt, mejl på svenska", en: "Swedish AI SDR: selection from the company register, research on the company's own site, email in Swedish" },
        { sv: "Ja, skriver på svenska från början", en: "Yes, writes in Swedish from the start" },
        { sv: "Ni väljer: utkast, första mejlet eller fram till möte; de tre första granskas alltid", en: "You choose: drafts, the first email or up to a meeting; the first three are always reviewed" },
        { sv: "Inom EU", en: "In the EU" },
        { sv: `Från ${LEADS}/mån, ${BINDNING.sv}`, en: `From ${LEADS} a month, ${BINDNING.en}` }
      ],
      ...AI_SDR_VERKTYG.map((v) => [{ sv: v.namn, en: v.namn }, v.vad, v.svenska, v.godkannande, v.data, v.pris])
    ],
    kallor: AI_SDR_VERKTYG.map((v) => ({ namn: v.namn, url: v.kalla })),
    kontrollerad: {
      sv: `Kontrollerat ${KONTROLL_DAG.sv} mot varje leverantörs egna sidor. Källor:`,
      en: `Checked on ${KONTROLL_DAG.en} against each vendor's own pages. Sources:`
    }
  },
  fragor: [
    {
      fraga: { sv: "Vilka verktyg kallas leadsagent men gör något annat?", en: "Which tools are called lead agents but do something else?" },
      svar: {
        sv: "Flera. Rebel är en kontaktdatabas och skickar inget själv. Kust IT:s KIT Lead Agent är en vägvisare i chatten på en hemsida. Finn från hirefinn.ai ringer upp inkommande leads. Leadsson säljer listor, och Franzens Leads säljer leads till B2C-företag. Därför står de inte i tabellen.",
        en: "Several. Rebel is a contact database and sends nothing itself. Kust IT's KIT Lead Agent is a guide in the chat on a website. Finn from hirefinn.ai calls inbound leads. Leadsson sells lists, and Franzens Leads sells leads to consumer businesses. That is why they are not in the table."
      }
    },
    {
      fraga: { sv: "Behöver en AI-SDR skriva på svenska?", en: "Does an AI SDR need to write in Swedish?" },
      svar: {
        sv: "Ja, om mottagarna är svenska. Fråga om utskicken skrivs på svenska eller översätts i efterhand; en översättning märks ofta på tilltal och ordval. Iris skriver på svenska från början och på engelska när mottagaren gör det.",
        en: "Yes, if the recipients are Swedish. Ask whether the sends are written in Swedish or translated afterwards; a translation often shows in the form of address and the word choice. Iris writes in Swedish from the start and in English when the recipient does."
      }
    },
    {
      fraga: { sv: "Får man skicka kalla säljmejl till företag i Sverige?", en: "Can you send cold sales emails to companies in Sweden?" },
      svar: {
        sv: "Till aktiebolag och andra juridiska personer, ja, om mejlet är relevant för mottagaren och har en tydlig avregistrering. Enskilda firmor räknas som privatpersoner och kräver samtycke, så Iris kontaktar dem inte.",
        en: "To limited companies and other legal persons, yes, if the email is relevant to the recipient and has a clear unsubscribe. Sole traders count as private individuals and require consent, so Iris does not contact them."
      }
    },
    {
      fraga: { sv: "Vad kostar en AI-SDR?", en: "What does an AI SDR cost?" },
      svar: {
        sv: `Prismodellerna skiljer sig: fast pris per månad, pris per kontakt eller ett projekt. I tabellen går spannet från under tusen kronor till flera tusen dollar i månaden. Iris kostar från ${LEADS} i månaden, och ${BINDNING_GALLER.sv}.`,
        en: `The pricing models differ: a fixed monthly price, a price per contact or a project. In the table the range runs from under a thousand kronor to several thousand dollars a month. Iris costs from ${LEADS} a month, and ${BINDNING_GALLER.en}.`
      }
    },
    KONTROLL_FRAGA
  ],
  relaterade: ["/svensk-ai-sdr", "/b2b-prospektering", "/b2b-leads"]
};

const JAMFOR_SUPPORTAGENTER: Landning = {
  vag: "/jamfor-supportagenter",
  rubrik: { sv: "Supportagenter i Sverige, *jämförda*.", en: "Support agents in Sweden, *compared*." },
  ingress: {
    sv: "Vi har läst varje leverantörs egna sidor och ställt upp det de själva säger om svenska svar, överlämning, data och pris. Snajp säljer Snajp Support, som står först. Det en leverantör inte skriver står som Ej angivet.",
    en: "We read each vendor's own pages and set out what they say themselves about Swedish answers, handover, data and price. Snajp sells Snajp Support, listed first. What a vendor does not state is marked Not stated."
  },
  kortSvar: {
    fraga: { sv: "Vilken supportagent passar ett svenskt företag?", en: "Which support agent suits a Swedish company?" },
    svar: {
      sv: `Den som svarar på svenska ur ert eget material, lämnar över till en människa när underlaget tar slut och lagrar kundernas meddelanden inom EU. Tabellen nedan jämför ${SUPPORTVERKTYG.length + 1} supportagenter och chattbotar på de punkterna och på pris, hämtat ur varje leverantörs egna sidor. Snajp säljer en av dem.`,
      en: `One that answers in Swedish from your own material, hands over to a person when the material runs out and stores your customers' messages in the EU. The table below compares ${SUPPORTVERKTYG.length + 1} support agents and chatbots on those points and on price, taken from each vendor's own pages. Snajp sells one of them.`
    }
  },
  stegRubrik: { sv: "Fyra frågor att ställa", en: "Four questions to ask" },
  steg: [
    {
      rubrik: { sv: "Underlaget", en: "The material" },
      text: {
        sv: "Svarar den bara ur ert eget material, eller fyller språkmodellen i luckorna själv?",
        en: "Does it answer only from your own material, or does the language model fill the gaps on its own?"
      }
    },
    {
      rubrik: { sv: "Språket", en: "The language" },
      text: {
        sv: "Svarar den på svenska i både chatten och mejlen, och står svenska i leverantörens språklista?",
        en: "Does it answer in Swedish in both the chat and email, and is Swedish on the vendor's language list?"
      }
    },
    {
      rubrik: { sv: "Överlämningen", en: "The handover" },
      text: {
        sv: "Vad händer när den inte vet? Ärendet ska gå vidare till en människa med hela tråden.",
        en: "What happens when it does not know? The case should go on to a person with the whole thread."
      }
    },
    {
      rubrik: { sv: "Datan och priset", en: "Data and price" },
      text: {
        sv: "Var lagras kundernas meddelanden, och betalar ni per agent, per löst ärende eller ett fast pris?",
        en: "Where are your customers' messages stored, and do you pay per agent, per resolution or a fixed price?"
      }
    }
  ],
  yta: {
    typ: "inkorg",
    rubrik: { sv: "Supportagenten i inkorgen", en: "The support agent in the inbox" },
    text: {
      sv: "Kundmejlen sorterade efter ämne och brådska, med svar att godkänna.",
      en: "Customer email sorted by topic and urgency, with replies to approve."
    }
  },
  granser: SA_HAR_VI_JAMFORT({ sv: "Snajp säljer Snajp Support. Läs tabellen med det i minnet.", en: "Snajp sells Snajp Support. Read the table with that in mind." }),
  jamforelse: {
    rubrik: { sv: "Supportagenter och chattbotar för svenska företag", en: "Support agents and chatbots for Swedish companies" },
    kolumner: [
      { sv: "Verktyg", en: "Tool" },
      { sv: "Vad det är", en: "What it is" },
      { sv: "Svenska", en: "Swedish" },
      { sv: "Överlämning", en: "Handover" },
      { sv: "Data", en: "Data" },
      { sv: "Pris", en: "Price" }
    ],
    rader: [
      [
        { sv: "Snajp Support", en: "Snajp Support" },
        { sv: "Supportagent i mejlinkorgen och i chatten på hemsidan, ur er kunskapsbas", en: "Support agent in the email inbox and the website chat, from your knowledge base" },
        { sv: "Ja, svenska och engelska", en: "Yes, Swedish and English" },
        { sv: "Ja; återbetalningar, fakturafel, juridik och arga kunder går alltid till en människa", en: "Yes; refunds, invoice errors, legal matters and angry customers always go to a person" },
        { sv: "Inom EU", en: "In the EU" },
        { sv: `Från ${SUPPORT}/mån, obegränsade chattar`, en: `From ${SUPPORT} a month, unlimited chats` }
      ],
      ...SUPPORTVERKTYG.map((v) => [{ sv: v.namn, en: v.namn }, v.vad, v.svenska, v.overlamning, v.data, v.pris])
    ],
    kallor: SUPPORTVERKTYG.map((v) => ({ namn: v.namn, url: v.kalla })),
    kontrollerad: {
      sv: `Kontrollerat ${KONTROLL_DAG.sv} mot varje leverantörs egna sidor. Källor:`,
      en: `Checked on ${KONTROLL_DAG.en} against each vendor's own pages. Sources:`
    }
  },
  fragor: [
    {
      fraga: { sv: "Vad skiljer en supportagent från en chattbot?", en: "How is a support agent different from a chatbot?" },
      svar: {
        sv: "En chattbot svarar i chatten på hemsidan. En supportagent arbetar också i mejlinkorgen: den sorterar kundmejlen, skriver svar ur ert underlag och lämnar över det den inte ska hantera. Flera av verktygen i tabellen gör båda.",
        en: "A chatbot answers in the chat on your website. A support agent also works in the email inbox: it sorts customer email, writes replies from your material and hands over what it should not handle. Several of the tools in the table do both."
      }
    },
    {
      fraga: { sv: "Svarar verktygen på svenska?", en: "Do the tools answer in Swedish?" },
      svar: {
        sv: "Zendesk, Intercom och Dstnys röstagent har svenska i sina språklistor. Flera andra stöder många språk utan att nämna svenska särskilt. Snajp Support svarar på svenska och engelska.",
        en: "Zendesk, Intercom and Dstny's voice agent have Swedish on their language lists. Several others support many languages without naming Swedish. Snajp Support answers in Swedish and English."
      }
    },
    {
      fraga: { sv: "Vad händer med kundernas meddelanden?", en: "What happens to your customers' messages?" },
      svar: {
        sv: "Det beror på verktyget, och tabellen visar var varje leverantör säger att datan lagras. Se också till att ni får ett personuppgiftsbiträdesavtal, eftersom kundmejl innehåller personuppgifter. Snajp lagrar datan inom EU.",
        en: "It depends on the tool, and the table shows where each vendor says the data is stored. Also make sure you get a data processing agreement, since customer email contains personal data. Snajp stores the data in the EU."
      }
    },
    {
      fraga: { sv: "Vad kostar en supportagent?", en: "What does a support agent cost?" },
      svar: {
        sv: `Tre modeller är vanligast: pris per agent och månad, pris per löst ärende eller ett fast månadspris. Snajp Support kostar från ${SUPPORT} i månaden med obegränsade chattar.`,
        en: `Three models are most common: a price per agent per month, a price per resolution or a fixed monthly price. Snajp Support costs from ${SUPPORT} a month with unlimited chats.`
      }
    },
    KONTROLL_FRAGA
  ],
  relaterade: ["/ai-supportagent", "/supportchatt", "/support-pa-svenska"]
};

/**
 * Sidans JSON-LD: brödsmulan, frågorna (det korta svaret först) och den
 * produkt sidan handlar om. Produktens @id är produktsidans, så att alla
 * sökordssidor pekar på samma produkt i stället för att skapa åtta.
 */
export function landningSchema(sida: Landning): Record<string, unknown> {
  const post = landningsPost(sida.vag);
  // Duo är båda agenterna: sidan handlar om paketet och om de två produkterna.
  const produkter = [...new Set([post.produkt, ...PRODUKTER_FOR_PAKET[post.produkt]])].map(produkt);
  return graf(
    {
      "@type": "WebPage",
      "@id": `${kanoniskUrl(sida.vag)}#sida`,
      url: kanoniskUrl(sida.vag),
      name: post.namn.sv,
      description: sida.kortSvar.svar.sv,
      inLanguage: "sv-SE",
      isPartOf: { "@id": `${KANONISK_ORIGIN}/#webbplats` },
      about: produkter.map((p) => ({ "@id": p["@id"] }))
    },
    brodsmulor(smulspar(sida.vag).map((s) => ({ namn: s.namn.sv, vag: s.vag }))),
    faqSida([sida.kortSvar, ...sida.fragor].map((f) => ({ fraga: f.fraga.sv, svar: f.svar.sv }))),
    ...produkter
  );
}

/**
 * Innehållet per adress. Typen kräver en post för varje adress i
 * lib/landningar.ts: en ny sida i registret utan innehåll fäller tsc.
 */
export const LANDNING: Record<LandningsVag, Landning> = {
  "/svensk-ai-sdr": SVENSK_AI_SDR,
  "/b2b-leads": B2B_LEADS,
  "/b2b-prospektering": B2B_PROSPEKTERING,
  "/leads-i-inkorgen": LEADS_I_INKORGEN,
  "/jamfor-ai-sdr": JAMFOR_AI_SDR,
  "/support-pa-svenska": SUPPORT_PA_SVENSKA,
  "/supportchatt": SUPPORTCHATT,
  "/ai-supportagent": AI_SUPPORTAGENT,
  "/jamfor-supportagenter": JAMFOR_SUPPORTAGENTER,
  "/ai-agenter": AI_AGENTER
};
