"use client";

import { Check, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { Rad, Radlista, SkeletonRows, Tomt, btnLiten, btnPrimary, btnSecondary, meta, rubrikPanel } from "@/components/ui";
import type { EmailStudioData } from "@/lib/data/emails";
import { EXEMPELBOLAG } from "@/lib/demo/iris-exempel";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

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

function tillStudioData(post: KöItem): EmailStudioData {
  return {
    source: "database",
    businessContext: null,
    email: {
      id: post.id,
      subject: post.subject || "Utan ämnesrad",
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
  const [poster, setPoster] = useState<KöItem[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
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
      if (!response.ok) throw new Error(`Kön kunde inte hämtas (status ${response.status}).`);
      setPoster(svar?.items ?? []);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
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
      if (!response.ok) throw new Error(`Åtgärden misslyckades (status ${response.status}).`);
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  return (
    <div>
      {/* Ingen egen demorad: skalets demobanner säger redan att allt är
          exempeldata och att inget skickas. */}

      {fel ? (
        <p role="alert" className="mb-5 max-w-[70ch] text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}

      {poster === null ? (
        <SkeletonRows />
      ) : poster.length === 0 ? (
        <Tomt>Inga utkast väntar på granskning.</Tomt>
      ) : (
        <Radlista ariaLabel="Utkast som väntar på granskning">
          {poster.map((post) => {
            const öppen = oppen === post.id;
            return (
              <Rad key={post.id}>
                <button
                  type="button"
                  onClick={() => setOppen(öppen ? null : post.id)}
                  aria-expanded={öppen}
                  className="focus-ring block w-full rounded-input text-left"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                    <div className="min-w-0">
                      <h2 className={cn(rubrikPanel, "truncate")}>
                        {post.subject || "Utan ämnesrad"}
                      </h2>
                      <p className={cn(meta, "mt-0.5")}>
                        {[post.company_name, post.prospect_email].filter(Boolean).join(" · ") || "Okänd mottagare"}
                      </p>
                    </div>
                    <span className="shrink-0 text-[0.8125rem] font-medium text-warning">
                      {öppen ? "Dölj utkastet" : "Öppna utkastet"}
                    </span>
                  </div>
                </button>

                {/* Två rader i listan (regel 3), hela texten i editorn när
                    posten öppnas. Radbrytningarna slås ihop här med flit:
                    med pre-wrap hade de två raderna ofta varit "Hej Anna,"
                    och en tomrad. */}
                {!öppen && post.body ? (
                  <p className="mt-3 line-clamp-2 max-w-[72ch] text-[0.9375rem] leading-6 text-ink-muted">
                    {post.body}
                  </p>
                ) : null}

                {öppen ? (
                  <div className="mt-4">
                    <EmailStudioEditor data={tillStudioData(post)} compact />
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
                    Godkänn
                  </button>
                  <button
                    type="button"
                    disabled={pagar !== null}
                    onClick={() => void avgor(post.id, "reject")}
                    className={cn(btnSecondary, btnLiten)}
                  >
                    <X className="h-4 w-4" aria-hidden />
                    Avvisa
                  </button>
                </div>
              </Rad>
            );
          })}
        </Radlista>
      )}

      {demo && Object.keys(besked).length > 0 ? (
        <p role="status" className="mt-6 text-[0.9375rem] text-ink-muted">
          {`${Object.entries(besked)
            .map(([id, val]) => `${EXEMPELBOLAG.find((b) => b.id === id)?.companyName ?? id}: ${val === "approve" ? "godkänt" : "avvisat"}`)
            .join(" · ")}. Inget av det här skickades.`}
        </p>
      ) : null}
    </div>
  );
}
