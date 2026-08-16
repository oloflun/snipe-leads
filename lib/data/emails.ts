import { emailVariants, findCompany, businessContext as mockBusinessContext } from "@/lib/mock-data";
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

function mockStudioData(locale: "sv" | "en" = "sv"): EmailStudioData {
  const variant = emailVariants[0];
  const company = findCompany(variant.companyId);

  return {
    source: "mock",
    businessContext: null,
    email: {
      id: variant.id,
      subject: variant.subject[locale],
      body: variant.body[locale],
      variantLength: variant.length,
      variantType: variant.type,
      status: "draft",
      companyId: variant.companyId,
      contactId: variant.contactId,
      companyName: company?.name ?? null,
      signal: company?.latestSignal[locale] ?? null,
      offer: mockBusinessContext.offer[locale],
      cta: mockBusinessContext.cta[locale],
      contactName: company?.contacts.find((c) => c.id === variant.contactId)?.fullName ?? null
    }
  };
}

/**
 * Public marketing surfaces always render example data, never a workspace's real
 * email. Deliberately synchronous and Supabase-free so /, /leads and /support stay
 * renderable with no session and no database.
 */
export function loadPublicEmailStudioData(locale: "sv" | "en" = "sv"): EmailStudioData {
  return mockStudioData(locale);
}

export async function loadEmailStudioData(): Promise<EmailStudioData> {
  const { getWorkspaceContext } = await import("@/lib/workspace");
  const context = await getWorkspaceContext();

  if (!context) {
    return mockStudioData();
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
    const mock = mockStudioData(context.workspace.locale === "en" ? "en" : "sv");

    if (context.businessContext) {
      return {
        ...mock,
        source: "mock",
        businessContext: context.businessContext
      };
    }

    return mock;
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