import type { BusinessContext } from "@/lib/database.types";

export type GeneratedEmailRecord = {
  id: string;
  subject: string;
  body: string;
  variantLength: string;
  variantType: string;
  status: string;
  companyId: string | null;
  contactId: string | null;
  companyName: string | null;
  signal: string | null;
  offer: string | null;
  cta: string | null;
  contactName: string | null;
};

export type EmailStudioData = {
  email: GeneratedEmailRecord;
  businessContext: BusinessContext | null;
  source: "database" | "mock";
};

/**
 * Exempelmejlet på marknadssidan.
 *
 * Står HÄR och inte i `emailVariants`: den listan matar också dashboardens
 * demoytor, och marknadssidans första intryck ska gå att byta utan att röra
 * demodatan i produkten. Fälten under `email` är samtidigt den kontext
 * Email Studio skickar med till varje åtgärdsknapp (kortare, skriv om,
 * personalisera ...) — tomma fält där ger en omskrivning som tappar bolaget,
 * signalen och erbjudandet, så de fylls i för hand i stället för att hämtas
 * ur en företagslista mejlet inte finns i.
 *
 * Avsändaren i exemplet är ett påhittat kundbolag (Safe-alarm), inte Snajp:
 * sidan visar vad agenten skriver ÅT en kund.
 */
const PUBLIKT_EXEMPELMEJL = {
  id: "email-etech-cold",
  subject: {
    sv: "Ny lokal i Göteborg och brandsäkerheten",
    en: "New premises in Gothenburg and fire safety"
  },
  body: {
    sv:
      "Hej David,\n\n" +
      "Jag såg att techbolaget E-Tech växlar upp med en ny lokal i Göteborg. " +
      "Det brukar vara ett läge där säkerheten blir en prioritering. Då vi på " +
      "Safe-alarm garanterar en säkerhet inom brandutrustning så vill vi gärna " +
      "höras vidare.\n\n" +
      "Vi skickar gärna en skräddarsydd offert.",
    en:
      "Hi David,\n\n" +
      "I saw that the tech company E-Tech is stepping up with new premises in " +
      "Gothenburg. That is usually the point where safety becomes a priority. " +
      "Since we at Safe-alarm guarantee safety in fire equipment, we would very " +
      "much like to talk further.\n\n" +
      "We would be glad to send a tailored quote."
  },
  companyName: "E-Tech",
  contactName: "David",
  signal: {
    sv: "Ny lokal i Göteborg och pågående expansion",
    en: "New premises in Gothenburg and an ongoing expansion"
  },
  offer: {
    sv: "Brandutrustning och säkerhetslösningar anpassade efter den nya lokalen",
    en: "Fire equipment and safety solutions fitted to the new premises"
  },
  cta: {
    sv: "Vill ni att vi skickar en skräddarsydd offert?",
    en: "Would you like us to send a tailored quote?"
  }
} as const;

/**
 * Knapparnas svar för exempelmejlet ovan, för en besökare utan inloggning
 * (app/api/email-studio/route.ts). Utan dem svarade varje knapp på startsidan
 * att demot bara fanns för andra exempelbolag (Anton 2026-10-19: "ta bort alla
 * tekniska referenser, endast korta motiveringar"). Motiveringen är en kort
 * mening på vanlig svenska eller engelska, utan metodnamn och fackord.
 * Översätt byter språk: från svenska ger den engelska versionen och tvärtom.
 */
type PubliktSvar = { new_version: string; explanation: string; subject_suggestions: string[] };
const PUBLIKA_SVAR: Record<"sv" | "en", Record<string, PubliktSvar>> = {
  sv: {
    shorter: {
      new_version:
        "Hej David,\n\n" +
        "E-Tech flyttar till en ny lokal i Göteborg. En flytt är ett bra tillfälle att få brandskyddet rätt från början.\n\n" +
        "Ska jag skicka ett förslag anpassat efter lokalen?",
      explanation: "Kortare: flytten, varför den spelar roll och en enkel fråga. Resten var utfyllnad.",
      subject_suggestions: ["Brandskyddet i nya lokalen"]
    },
    rewrite: {
      new_version:
        "Hej David,\n\n" +
        "När E-Tech flyttar in i den nya lokalen i Göteborg ska mycket på plats samtidigt. Brandskyddet är lätt att skjuta upp, men det är enklast att få rätt innan inredningen står på plats.\n\n" +
        "Vi på Safe-alarm går igenom lokalen och föreslår den utrustning som behövs, varken mer eller mindre.\n\n" +
        "Passar det att jag skickar ett förslag?",
      explanation: "Ny vinkel: mejlet börjar i Davids vardag under flytten och säger först sedan vad ni erbjuder.",
      subject_suggestions: ["Inför flytten till nya lokalen"]
    },
    improve: {
      new_version:
        "Hej David,\n\n" +
        "Jag såg att E-Tech flyttar till en ny lokal i Göteborg. Innan inredningen är på plats är det enklast att få brandskyddet rätt från början.\n\n" +
        "Vi på Safe-alarm tar fram ett förslag på brandutrustning anpassat efter just er lokal.\n\n" +
        "Vill du att jag skickar ett?",
      explanation: "Säger tydligare varför det är läge nu och slutar med en fråga som är lätt att svara ja på.",
      subject_suggestions: ["Brandskyddet i E-Techs nya lokal"]
    },
    personalize: {
      new_version:
        "Hej David,\n\n" +
        "Grattis till den nya lokalen i Göteborg. Ett techbolag har mycket värdefull utrustning på plats, och då handlar brandskyddet om mer än en brandsläckare vid dörren.\n\n" +
        "Vi på Safe-alarm anpassar utrustningen efter hur ni använder lokalen, från serverrummet till kontoren.\n\n" +
        "Vill du att jag tar fram ett förslag?",
      explanation: "Kopplad till att E-Tech är ett techbolag: utrustningen och serverrummet gör brandskyddet viktigare.",
      subject_suggestions: ["Brandskydd för en techlokal"]
    },
    translate: {
      new_version: PUBLIKT_EXEMPELMEJL.body.en,
      explanation: "Hela mejlet på engelska, med samma ton och innehåll.",
      subject_suggestions: [PUBLIKT_EXEMPELMEJL.subject.en]
    },
    ab_variants: {
      new_version:
        "Variant A (flytten):\n" +
        "Hej David,\n\n" +
        "E-Tech flyttar till en ny lokal i Göteborg. Det är det bästa tillfället att få brandskyddet rätt från början.\n\n" +
        "Vill du ha ett förslag anpassat efter lokalen?\n\n" +
        "Variant B (en fråga):\n" +
        "Hej David,\n\n" +
        "Har ni hunnit se över brandskyddet i nya lokalen, eller ligger det kvar på listan inför flytten?\n\n" +
        "Vi på Safe-alarm tar gärna fram ett förslag.",
      explanation: "Två vinklar: A utgår från flytten, B öppnar med en fråga. Skicka båda och se vilken som får flest svar.",
      subject_suggestions: ["Brandskyddet i nya lokalen (A)", "En fråga inför flytten (B)"]
    },
    followup: {
      new_version:
        "Hej David,\n\n" +
        "Jag hörde av mig om brandskyddet i er nya lokal. Ett förslag till: vi kan gå igenom lokalen på plats innan ni flyttar in, så att inget behöver göras om efteråt.\n\n" +
        "Passar det en dag nästa vecka?",
      explanation: "Uppföljningen tillför något nytt, en genomgång på plats, i stället för att bara påminna.",
      subject_suggestions: ["En genomgång innan ni flyttar in"]
    },
    analyze: {
      new_version: PUBLIKT_EXEMPELMEJL.body.sv,
      explanation:
        "6/10. Flytten är en bra anledning att höra av sig. Mittenmeningen säger vad ni gör men inte vad David får, och \"garanterar en säkerhet\" är ett löfte som är svårt att hålla. Avsluta med en fråga i stället för ett erbjudande.",
      subject_suggestions: []
    }
  },
  en: {
    shorter: {
      new_version:
        "Hi David,\n\n" +
        "E-Tech is moving to new premises in Gothenburg. A move is a good moment to get fire safety right from the start.\n\n" +
        "Shall I send a proposal fitted to the space?",
      explanation: "Shorter: the move, why it matters and a simple question. The rest was padding.",
      subject_suggestions: ["Fire safety in the new premises"]
    },
    rewrite: {
      new_version:
        "Hi David,\n\n" +
        "Moving E-Tech into new premises in Gothenburg means a lot has to fall into place at once. Fire safety is easy to put off, but it is simplest to get right before the fit-out is done.\n\n" +
        "At Safe-alarm we walk through the space and propose the equipment it needs, no more and no less.\n\n" +
        "Would it help if I sent a proposal?",
      explanation: "New angle: the email starts in David's day during the move and only then says what you offer.",
      subject_suggestions: ["Before the move to the new premises"]
    },
    improve: {
      new_version:
        "Hi David,\n\n" +
        "I saw that E-Tech is moving to new premises in Gothenburg. Before the fit-out is finished, it is easiest to get fire safety right from the start.\n\n" +
        "At Safe-alarm we put together a proposal for fire equipment fitted to your space.\n\n" +
        "Shall I send you one?",
      explanation: "Says more plainly why now is the moment and ends with a question that is easy to say yes to.",
      subject_suggestions: ["Fire safety in E-Tech's new premises"]
    },
    personalize: {
      new_version:
        "Hi David,\n\n" +
        "Congratulations on the new premises in Gothenburg. A tech company keeps a lot of valuable equipment on site, so fire safety is about more than an extinguisher by the door.\n\n" +
        "At Safe-alarm we fit the equipment to how you use the space, from the server room to the offices.\n\n" +
        "Shall I put together a proposal?",
      explanation: "Tied to E-Tech being a tech company: the equipment and the server room make fire safety matter more.",
      subject_suggestions: ["Fire safety for a tech space"]
    },
    translate: {
      new_version: PUBLIKT_EXEMPELMEJL.body.sv,
      explanation: "The whole email in Swedish, with the same tone and content.",
      subject_suggestions: [PUBLIKT_EXEMPELMEJL.subject.sv]
    },
    ab_variants: {
      new_version:
        "Variant A (the move):\n" +
        "Hi David,\n\n" +
        "E-Tech is moving to new premises in Gothenburg. It is the best moment to get fire safety right from the start.\n\n" +
        "Would you like a proposal fitted to the space?\n\n" +
        "Variant B (a question):\n" +
        "Hi David,\n\n" +
        "Have you had time to look at fire safety in the new premises, or is it still on the list before the move?\n\n" +
        "At Safe-alarm we would be glad to put together a proposal.",
      explanation: "Two angles: A starts from the move, B opens with a question. Send both and see which gets more replies.",
      subject_suggestions: ["Fire safety in the new premises (A)", "A question before the move (B)"]
    },
    followup: {
      new_version:
        "Hi David,\n\n" +
        "I got in touch about fire safety in your new premises. One more idea: we can walk through the space before you move in, so nothing has to be redone afterwards.\n\n" +
        "Would a day next week work?",
      explanation: "The follow-up adds something new, a walkthrough on site, instead of just a reminder.",
      subject_suggestions: ["A walkthrough before you move in"]
    },
    analyze: {
      new_version: PUBLIKT_EXEMPELMEJL.body.en,
      explanation:
        "6/10. The move is a good reason to get in touch. The middle sentence says what you do but not what David gets, and \"guarantee safety\" is a promise that is hard to keep. End with a question rather than an offer.",
      subject_suggestions: []
    }
  }
};

/** Svaret på en knapp för startsidans exempelmejl, eller undefined om mejlet inte är det. */
export function publiktExempelsvar(
  context: { companyName?: unknown } | null | undefined,
  action: string,
  locale: unknown
): PubliktSvar | undefined {
  if (context?.companyName !== PUBLIKT_EXEMPELMEJL.companyName) return undefined;
  const svar = PUBLIKA_SVAR[locale === "en" ? "en" : "sv"];
  return svar[action] ?? svar.improve;
}

/**
 * Public marketing surfaces always render example data, never a workspace's real
 * email. Deliberately synchronous and Supabase-free so /, /leads and /support stay
 * renderable with no session and no database.
 *
 * Mejlet är ALLTID `PUBLIKT_EXEMPELMEJL`, så det står som första exempel varje
 * gång sidan laddas — knapparna skriver sedan om det utan att ändra vad nästa
 * besökare möts av.
 */
export function loadPublicEmailStudioData(locale: "sv" | "en" = "sv"): EmailStudioData {
  return {
    source: "mock",
    businessContext: null,
    email: {
      id: PUBLIKT_EXEMPELMEJL.id,
      subject: PUBLIKT_EXEMPELMEJL.subject[locale],
      body: PUBLIKT_EXEMPELMEJL.body[locale],
      variantLength: "kort",
      variantType: "cold",
      status: "draft",
      companyId: null,
      contactId: null,
      companyName: PUBLIKT_EXEMPELMEJL.companyName,
      signal: PUBLIKT_EXEMPELMEJL.signal[locale],
      offer: PUBLIKT_EXEMPELMEJL.offer[locale],
      cta: PUBLIKT_EXEMPELMEJL.cta[locale],
      contactName: PUBLIKT_EXEMPELMEJL.contactName
    }
  };
}

export async function loadEmailStudioData(): Promise<EmailStudioData> {
  const { getWorkspaceContext } = await import("@/lib/workspace");
  const context = await getWorkspaceContext();

  if (!context) {
    // Ingen session: samma exempel som marknadssidan, av samma skäl som
    // nedan. Två olika exempelmejl i samma produkt är två saker att hålla
    // uppdaterade, och det ena hann bli inaktuellt.
    return loadPublicEmailStudioData();
  }

  const { sqlAsUser } = await import("@/lib/db");
  // Mejlet och kontaktnamnet i en fråga: kontakten hämtades förut i ett andra
  // anrop efter att raden kommit tillbaka, alltså ett tur och retur som alltid
  // följde på det första.
  let emails: Array<Record<string, unknown>> = [];
  try {
    emails = await sqlAsUser(
      context.user.id,
      `select ge.id, ge.subject, ge.body, ge.variant_length, ge.variant_type,
              ge.status, ge.contact_id, ge.campaign_id, c.full_name as contact_name
         from public.generated_emails ge
         left join public.contacts c on c.id = ge.contact_id
        where ge.workspace_id = $1
        order by ge.created_at desc
        limit 1`,
      [context.workspace.id]
    );
  } catch {
    emails = [];
  }

  if (!emails.length) {
    // Arbetsytan har inga utkast ännu.
    //
    // Här låg `mockStudioData()`, alltså mejlet om Byggkompaniet Syd och Elin
    // Nordin — ett annat, påhittat bolags säljmejl, omärkt, i kundens egen
    // Email Studio. En ny kund som öppnade fliken fick intrycket att agenterna
    // redan skrivit till någon.
    //
    // Nu samma exempel som webbplatsen visar, och `source: "mock"` bärs vidare
    // så att editorn kan SÄGA att det är ett exempel (se EmailStudioEditor).
    // Kundens affärskontext följer med när den finns, för då blir åtgärderna i
    // studion körda mot deras eget erbjudande och inte mot exemplets.
    const exempel = loadPublicEmailStudioData(context.workspace.locale === "en" ? "en" : "sv");

    return {
      ...exempel,
      businessContext: context.businessContext ?? null
    };
  }

  const row = emails[0] as {
    id: string;
    subject: string;
    body: string;
    variant_length: string;
    variant_type: string;
    status: string;
    contact_id: string | null;
    campaign_id: string | null;
    contact_name: string | null;
  };

  const contactName = row.contact_name ?? null;

  return {
    source: "database",
    businessContext: context.businessContext,
    email: {
      id: row.id,
      subject: row.subject,
      body: row.body,
      variantLength: row.variant_length,
      variantType: row.variant_type,
      status: row.status,
      companyId: null,
      contactId: row.contact_id,
      companyName: null,
      signal: null,
      offer: context.businessContext?.offer ?? null,
      cta: context.businessContext?.cta ?? null,
      contactName
    }
  };
}

export async function saveEmailDraft(input: {
  emailId: string;
  subject: string;
  body: string;
}): Promise<{ success: boolean; error?: string }> {
  const { getWorkspaceContext } = await import("@/lib/workspace");
  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Inte inloggad" };
  }

  const { sqlAsUser } = await import("@/lib/db");
  try {
    await sqlAsUser(
      context.user.id,
      `update public.generated_emails
          set subject = $1, body = $2, status = 'draft'
        where id = $3 and workspace_id = $4`,
      [input.subject, input.body, input.emailId, context.workspace.id]
    );
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  return { success: true };
}

export function toRefineContext(data: EmailStudioData) {
  return {
    // Skickas med så att /api/email-studio kan slå upp EXAKT vilket av de
    // sex exempelbolagen (lib/demo/iris-exempel.ts) ett anonymt anrop gäller
    // — stabilt även om kunden hunnit redigera bolagsnamnet i ämnesraden.
    companyId: data.email.companyId ?? undefined,
    companyName: data.email.companyName ?? undefined,
    signal: data.email.signal ?? undefined,
    offer: data.email.offer ?? data.businessContext?.offer ?? undefined,
    cta: data.email.cta ?? data.businessContext?.cta ?? undefined,
    contactName: data.email.contactName ?? undefined
  };
}