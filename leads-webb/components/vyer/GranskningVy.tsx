"use client";

import { Check, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { BAS, type KoPost } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Granskningskön — sajtens viktigaste handling. Varje utkast visas i sin
 * helhet med Godkänn/Avvisa; ett godkännande släpper det till schemaläggaren
 * (backendens språk- och tidsgrindar körs EN gång till vid utskick, så ett
 * ja här går aldrig förbi dem).
 */
export function GranskningVy() {
  const [poster, setPoster] = useState<KoPost[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [pagar, setPagar] = useState<string | null>(null);

  async function hamta() {
    setFel(null);
    try {
      const svar = await fetch(`${BAS}/leads/queue`).then((s) =>
        readJson<{ items: KoPost[] }>(s)
      );
      setPoster(svar?.items ?? []);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setPoster([]);
    }
  }

  useEffect(() => {
    void hamta();
  }, []);

  async function avgor(id: string, handling: "approve" | "reject") {
    setPagar(id);
    setFel(null);
    try {
      const svar = await fetch(`${BAS}/leads/queue/${id}/${handling}`, { method: "POST" });
      await readJson(svar);
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Granskning"
        beskrivning="Utkasten agenten skrivit, i väntan på ditt ja eller nej. Godkända utkast går till schemaläggaren — ingenting skickas i samma sekund du klickar."
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {poster === null ? (
        <SkeletonRows />
      ) : poster.length === 0 ? (
        <EmptyState
          title="Granskningskön är tom"
          body="När agenten skrivit ett utkast till ett kvalificerat bolag hamnar det här, och ingenting skickas förrän du godkänt det."
        />
      ) : (
        <div className="space-y-8">
          {poster.map((post) => (
            <article key={post.id} className="border-y border-ink/15 py-5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                <div className="min-w-0">
                  <h2 className="truncate text-[1.0625rem] font-semibold text-ink">
                    {post.subject || "Utan ämnesrad"}
                  </h2>
                  {post.prospect_email ? (
                    <p className="mt-0.5 text-[0.875rem] text-ink/55">
                      Till: {post.prospect_email}
                    </p>
                  ) : null}
                </div>
                <div className="flex shrink-0 items-center gap-2">
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
              </div>
              {post.body ? (
                <p className="mt-3 max-w-[72ch] whitespace-pre-wrap text-[0.9375rem] leading-7 text-ink/80">
                  {post.body}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
