"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, SkeletonRows } from "@/components/ui";
import { BAS, type Regel } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";

/**
 * Hur agenten är riggad: reglerna per ärendekategori och de kopplade
 * inkorgarna. LÄSVY med flit — ändringar görs i Snajp-webbens arbetsyta,
 * två redigeringsytor för samma regler blir två sanningar.
 */

const LAGE: Record<string, { etikett: string; ton: "good" | "warn" | "neutral" }> = {
  auto: { etikett: "Svarar själv", ton: "good" },
  draft: { etikett: "Utkast till dig", ton: "neutral" },
  escalate: { etikett: "Eskalerar alltid", ton: "warn" }
};

type Mailbox = { address?: string | null; status?: string | null; kan_synka?: boolean };

export function InstallningarVy() {
  const [regler, setRegler] = useState<Regel[] | null>(null);
  const [inkorgar, setInkorgar] = useState<Mailbox[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [r, m] = await Promise.all([
          fetch(`${BAS}/rules`).then((s) => readJson<{ rules?: Regel[] } | Regel[]>(s)),
          fetch(`${BAS}/inbox/mailboxes`).then((s) =>
            readJson<{ mailboxes?: Mailbox[] } | Mailbox[]>(s)
          )
        ]);
        setRegler(Array.isArray(r) ? r : r?.rules ?? []);
        setInkorgar(Array.isArray(m) ? m : m?.mailboxes ?? []);
      } catch (orsak) {
        setFel(felmeddelande(orsak));
        setRegler([]);
        setInkorgar([]);
      }
    })();
  }, []);

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik="Inställningar"
        beskrivning="Ändras i arbetsytan på Snajp-webben."
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      <section className="max-w-[42rem]">
        <h2 className="font-display text-[1.25rem]">Regler per kategori</h2>
        {regler === null ? (
          <div className="mt-3">
            <SkeletonRows />
          </div>
        ) : regler.length === 0 ? (
          <p className="mt-3 border-y border-ink/15 py-4 text-[0.9375rem] text-ink-muted">
            Inga regler — allt blir utkast till dig.
          </p>
        ) : (
          <dl className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
            {regler.map((regel, i) => {
              const lage = LAGE[regel.mode ?? ""] ?? { etikett: regel.mode ?? "—", ton: "neutral" as const };
              return (
                <div key={regel.category ?? i} className="flex flex-wrap items-baseline justify-between gap-x-6 py-3">
                  <dt className="text-[0.9375rem]">{regel.category ?? "—"}</dt>
                  <dd>
                    <Badge tone={lage.ton}>{lage.etikett}</Badge>
                  </dd>
                </div>
              );
            })}
          </dl>
        )}
      </section>

      <section className="max-w-[42rem]">
        <h2 className="font-display text-[1.25rem]">Kopplade inkorgar</h2>
        {inkorgar === null ? (
          <div className="mt-3">
            <SkeletonRows />
          </div>
        ) : inkorgar.length === 0 ? (
          <p className="mt-3 border-y border-ink/15 py-4 text-[0.9375rem] text-ink-muted">
            Ingen inkorg kopplad.
          </p>
        ) : (
          <div className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
            {inkorgar.map((box, i) => (
              <div key={box.address ?? i} className="flex flex-wrap items-baseline justify-between gap-x-6 py-3">
                <span className="min-w-0 truncate text-[0.9375rem]">{box.address ?? "—"}</span>
                <Badge tone={box.kan_synka ? "good" : "neutral"}>
                  {box.kan_synka ? "Synkar" : box.status ?? "—"}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
