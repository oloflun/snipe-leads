// SERVER-ONLY. Översätter företagsprofilen från onboarding till något
// kundservice-agenten faktiskt kan svara utifrån.
//
// Utan det här startar varje ny kund med default-prompten och en TOM
// kunskapsbas — och eftersom grundningsregeln kräver stöd i kunskapsbasen
// eskalerar agenten då varenda fråga. Kunden ser en agent som aldrig svarar.
//
// Två saker synkas:
//   1. Tenantens systemprompt — vem bolaget är och vilken ton som gäller.
//   2. KB-artiklar för garanti, villkor, leverans och retur — de fyra frågor
//      som dominerar inkommande kundmail.
//
// Email studio rörs inte: den läser business_contexts som förut.

import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";

const SNAJP_SUPPORT_URL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8000";

export type CompanyProfile = {
  companyName?: string | null;
  product?: string | null;
  targetAudience?: string | null;
  tone?: string | null;
  guarantee?: string | null;
  terms?: string | null;
  delivery?: string | null;
  returnsPolicy?: string | null;
  supportEmail?: string | null;
};

export type SyncResult = {
  synced: boolean;
  articles: number;
  skipped: string[];
  error?: string;
};

function clean(value: string | null | undefined): string {
  return (value ?? "").trim();
}

/**
 * Företagsbeskrivningen som läggs i tenantens systemprompt.
 *
 * Medvetet BARA identitet och ton — inga siffror, villkor eller löften. Sådant
 * hör hemma i kunskapsbasen, där grundningsregeln kan kräva träff innan agenten
 * påstår något. Text i prompten kan agenten återge utan källa, och då är vi
 * tillbaka i att den hittar på villkor.
 */
export function buildSystemPromptExtra(profile: CompanyProfile): string {
  const lines: string[] = [];
  const name = clean(profile.companyName);
  const product = clean(profile.product);
  const audience = clean(profile.targetAudience);

  if (product) {
    lines.push(`${name || "Bolaget"} säljer ${product}.`);
  }
  if (audience) {
    lines.push(`Kunderna är främst ${audience}.`);
  }
  if (clean(profile.supportEmail)) {
    lines.push(
      `Ärenden som lämnas över till en människa hanteras av ${clean(profile.supportEmail)}.`
    );
  }
  lines.push(
    "Svara utifrån bolagets egna villkor i kunskapsbasen. Saknas underlag: " +
      "lämna över till en kollega i stället för att gissa."
  );
  return lines.join(" ");
}

/** De fyra facken som dominerar inkommande kundmail. Tomma fält hoppas över. */
export function buildKbArticles(profile: CompanyProfile): {
  title: string;
  content: string;
  category: string;
}[] {
  const candidates = [
    { title: "Garanti", content: clean(profile.guarantee), category: "garanti" },
    { title: "Köp- och betalningsvillkor", content: clean(profile.terms), category: "betalning" },
    { title: "Leverans och frakt", content: clean(profile.delivery), category: "leverans" },
    {
      title: "Retur och reklamation",
      content: clean(profile.returnsPolicy),
      category: "retur_reklamation"
    }
  ];
  // Backendens KB-validering kräver minst 10 tecken. Kortare svar är ändå inte
  // användbart underlag för ett kundsvar.
  return candidates.filter((article) => article.content.length >= 10);
}

async function call(path: string, apiKey: string, init: RequestInit = {}) {
  return fetch(`${SNAJP_SUPPORT_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey, ...(init.headers ?? {}) },
    cache: "no-store"
  });
}

/**
 * Synkar profilen till den inloggade organisationens tenant.
 *
 * Idempotent: artiklar matchas på rubrik och uppdateras i stället för att
 * dubbleras, så att en kund som justerar sina villkor får dem ändrade — inte
 * två motstridiga versioner i kunskapsbasen, vilket vore värre än inget.
 */
export async function syncCompanyProfileToSnajp(profile: CompanyProfile): Promise<SyncResult> {
  let apiKey: string;
  try {
    apiKey = (await requireSnajpTenant()).apiKey;
  } catch (error) {
    const message =
      error instanceof SnajpTenantError ? error.message : "Kunde inte nå arbetsytan.";
    return { synced: false, articles: 0, skipped: [], error: message };
  }

  try {
    const tenantResponse = await call("/api/tenant", apiKey, {
      method: "PUT",
      body: JSON.stringify({
        company_name: clean(profile.companyName) || undefined,
        tone: clean(profile.tone) || undefined,
        system_prompt_extra: buildSystemPromptExtra(profile)
      })
    });
    if (!tenantResponse.ok) {
      return {
        synced: false,
        articles: 0,
        skipped: [],
        error: `Kunde inte spara agentens profil (${tenantResponse.status}).`
      };
    }

    const wanted = buildKbArticles(profile);
    if (wanted.length === 0) {
      return { synced: true, articles: 0, skipped: [] };
    }

    const existingResponse = await call("/api/kb", apiKey);
    const existing: { id: string; title: string }[] = existingResponse.ok
      ? ((await existingResponse.json()).articles ?? [])
      : [];
    const byTitle = new Map(existing.map((a) => [a.title, a.id]));

    let written = 0;
    const skipped: string[] = [];
    const fresh: typeof wanted = [];

    for (const article of wanted) {
      const id = byTitle.get(article.title);
      if (id) {
        const updated = await call(`/api/kb/${id}`, apiKey, {
          method: "PUT",
          body: JSON.stringify({ content: article.content, category: article.category })
        });
        updated.ok ? (written += 1) : skipped.push(article.title);
      } else {
        fresh.push(article);
      }
    }

    if (fresh.length > 0) {
      const created = await call("/api/kb", apiKey, {
        method: "POST",
        body: JSON.stringify({ articles: fresh })
      });
      if (created.ok) {
        written += fresh.length;
      } else {
        skipped.push(...fresh.map((a) => a.title));
      }
    }

    return { synced: true, articles: written, skipped };
  } catch (error) {
    return {
      synced: false,
      articles: 0,
      skipped: [],
      error: error instanceof Error ? error.message : "Okänt fel vid synk."
    };
  }
}
