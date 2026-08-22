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
    companyName: data.email.companyName ?? undefined,
    signal: data.email.signal ?? undefined,
    offer: data.email.offer ?? data.businessContext?.offer ?? undefined,
    cta: data.email.cta ?? data.businessContext?.cta ?? undefined,
    contactName: data.email.contactName ?? undefined
  };
}