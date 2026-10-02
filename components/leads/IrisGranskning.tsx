"use client";

import { Check, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import type { EmailStudioData } from "@/lib/data/emails";
import { EXEMPELBOLAG } from "@/lib/demo/iris-exempel";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";

const UTAN_AMNE: Localized = { sv: "Utan ämnesrad", en: "No subject line" };

/**
 * Iris › Granskning — utkasten Iris skrivit, i väntan på ett ja eller nej.
 *
 * Portad från `leads-webb/components/vyer/GranskningVy.tsx` till huvudappens
 * API-konventioner: samma `/api/snajp-support/leads/queue` och
 * `/api/snajp-support/leads/queue/{id}/{approve|reject}` som
 * `components/leads/LeadsControls.tsx` redan anropar, inte leads-webbs egna
 * proxy/session. Godkännande släpper utkastet till schemaläggaren —
 * backendens språk- och tidsgrindar körs en gång till vid utskick, så ett ja
 * här går aldrig förbi dem.
 *
 * Ett klick på ett poständer öppnar samma editor som Iris › Bolag mejlutkast
 * gör (EmailStudioEditor), så granskningen är mer än en rå textrad.
 */

type KöItem = {
  id: string;
  subject?: string | null;
  body?: string | null;
  prospect_email?: string | null;
  company_name?: string | null;
};

function tillStudioData(post: KöItem, utanAmne: string): EmailStudioData {
  return {
    source: "database",
    businessContext: null,
    email: {
      id: post.id,
      subject: post.subject || utanAmne,
      body: post.body ?? "",
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: null,
      contactId: null,
      companyName: post.company_name ?? null,
      signal: null,
      offer: null,
      cta: null,
      contactName: null
    }
  };
}

/** Demons kö: de sex fixturbolagens utkast, oavsett vilken omgång som visas i Bolag. */
function demoKo(): KöItem[] {
  return EXEMPELBOLAG.map((b) => ({
    id: b.id,
    subject: b.draft.subject,
    body: b.draft.body,
    prospect_email: `${b.contactFirstName.toLowerCase()}@${b.website}`,
    company_name: b.companyName
  }));
}

export function IrisGranskning({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  const [poster, setPoster] = useState<KöItem[] | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  const [pagar, setPagar] = useState<string | null>(null);
  const [oppen, setOppen] = useState<string | null>(null);
  const [besked, setBesked] = useState<Record<string, "approve" | "reject">>({});

  async function hamta() {
    setFel(null);
    if (demo) {
      setPoster(demoKo());
      return;
    }
    try {
      const response = await fetch("/api/snajp-support/leads/queue", { cache: "no-store" });
      const svar = await readJsonBody<{ items?: KöItem[] }>(response);
      if (!response.ok) {
        setFel({
          sv: `Kön kunde inte hämtas (status ${response.status}).`,
          en: `The queue could not be fetched (status ${response.status}).`
        });
        setPoster([]);
        return;
      }
      setPoster(svar?.items ?? []);
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
      setPoster([]);
    }
  }

  useEffect(() => {
    void hamta();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo]);

  async function avgor(id: string, handling: "approve" | "reject") {
    setPagar(id);
    setFel(null);
    if (demo) {
      // Demon avgör bara lokalt state — inget skickas, se docstringen.
      await new Promise((r) => setTimeout(r, 250));
      setBesked((f) => ({ ...f, [id]: handling }));
      setPoster((f) => (f ? f.filter((p) => p.id !== id) : f));
      setPagar(null);
      return;
    }
    try {
      const response = await fetch(`/api/snajp-support/leads/queue/${id}/${handling}`, {
        method: "POST"
      });
      if (!response.ok) {
        setFel({
          sv: `Åtgärden misslyckades (status ${response.status}).`,
          en: `The action failed (status ${response.status}).`
        });
        return;
      }
      await hamta();
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
    } finally {
      setPagar(null);
    }
  }

  return (
    <div>
      {demo ? (
        <p className="mb-6 text-[13px] leading-6 text-ink-subtle">{text({ sv: "Exempelutkast.", en: "Example drafts." })}</p>
      ) : null}

      {fel ? (
        <p role="alert" className="mb-5 max-w-[70ch] text-[0.875rem] text-danger">
          {text(fel)}
        </p>
      ) : null}

      {poster === null ? (
        <SkeletonRows />
      ) : poster.length === 0 ? (
        <EmptyState title={text({ sv: "Granskningskön är tom", en: "The review queue is empty" })} />
      ) : (
        <div className="divide-y divide-ink/15 border-y border-ink/15">
          {poster.map((post) => {
            const öppen = oppen === post.id;
            return (
              <article key={post.id} className="py-5">
                <button
                  type="button"
                  onClick={() => setOppen(öppen ? null : post.id)}
                  aria-expanded={öppen}
                  className="focus-ring block w-full rounded-input text-left"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                    <div className="min-w-0">
                      <h2 className="truncate text-[1.0625rem] font-semibold text-ink">
                        {post.subject || text(UTAN_AMNE)}
                      </h2>
                      <p className="mt-0.5 text-[0.875rem] text-ink-subtle">
                        {[post.company_name, post.prospect_email].filter(Boolean).join(" · ") || text({ sv: "Okänd mottagare", en: "Unknown recipient" })}
                      </p>
                    </div>
                    <span className="shrink-0 text-[0.8125rem] font-medium text-warning">
                      {öppen ? text({ sv: "Dölj utkastet", en: "Hide draft" }) : text({ sv: "Öppna utkastet", en: "Open draft" })}
                    </span>
                  </div>
                </button>

                {!öppen && post.body ? (
                  <p className="mt-3 max-w-[72ch] whitespace-pre-wrap text-[0.9375rem] leading-7 text-ink-muted">
                    {post.body.length > 220 ? `${post.body.slice(0, 220)}…` : post.body}
                  </p>
                ) : null}

                {öppen ? (
                  <div className="mt-4">
                    <EmailStudioEditor data={tillStudioData(post, text(UTAN_AMNE))} compact />
                  </div>
                ) : null}

                <div className="mt-4 flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    disabled={pagar !== null}
                    onClick={() => void avgor(post.id, "approve")}
                    className={cn(btnPrimary, btnLiten)}
                  >
                    {pagar === post.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Check className="h-4 w-4" aria-hidden />
                    )}
                    {text({ sv: "Godkänn", en: "Approve" })}
                  </button>
                  <button
                    type="button"
                    disabled={pagar !== null}
                    onClick={() => void avgor(post.id, "reject")}
                    className={cn(btnSecondary, btnLiten)}
                  >
                    <X className="h-4 w-4" aria-hidden />
                    {text({ sv: "Avvisa", en: "Reject" })}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {demo && Object.keys(besked).length > 0 ? (
        <p role="status" className="mt-6 text-[13px] text-ink-subtle">
          {`${Object.entries(besked)
            .map(([id, val]) => `${EXEMPELBOLAG.find((b) => b.id === id)?.companyName ?? id}: ${val === "approve" ? text({ sv: "godkänt", en: "approved" }) : text({ sv: "avvisat", en: "rejected" })}`)
            .join(" · ")}.`}
        </p>
      ) : null}
    </div>
  );
}
