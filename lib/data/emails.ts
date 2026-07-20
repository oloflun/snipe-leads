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
  source: "supabase" | "mock";
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

export async function loadEmailStudioData(): Promise<EmailStudioData> {
  const { getWorkspaceContext } = await import("@/lib/workspace");
  const context = await getWorkspaceContext();

  if (!context) {
    return mockStudioData();
  }

  const supabase = await import("@/lib/supabase/server").then((m) => m.createClient());
  const { data: emails, error } = await supabase
    .from("generated_emails")
    .select("id, subject, body, variant_length, variant_type, status, contact_id, campaign_id")
    .eq("workspace_id", context.workspace.id)
    .order("created_at", { ascending: false })
    .limit(1);

  if (error || !emails?.length) {
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
  };

  let contactName: string | null = null;
  if (row.contact_id) {
    const { data: contact } = await supabase
      .from("contacts")
      .select("full_name, company_id")
      .eq("id", row.contact_id)
      .maybeSingle();

    contactName = (contact as { full_name?: string } | null)?.full_name ?? null;
  }

  return {
    source: "supabase",
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

  const supabase = await import("@/lib/supabase/server").then((m) => m.createClient());
  const { error } = await supabase
    .from("generated_emails")
    .update({
      subject: input.subject,
      body: input.body,
      status: "draft"
    })
    .eq("id", input.emailId)
    .eq("workspace_id", context.workspace.id);

  if (error) {
    return { success: false, error: error.message };
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