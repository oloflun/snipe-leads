"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, SkeletonRows } from "@/components/ui";
import { BAS, type LeadsConfig } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";

/**
 * Målgruppen och autonomin, som de faktiskt är inställda. LÄSVY med flit:
 * ändringar görs i Snajp-webbens arbetsyta där hela kontrollpanelen bor —
 * två redigeringsytor för samma inställningar blir två sanningar.
 */
export function InstallningarVy() {
  const [config, setConfig] = useState<LeadsConfig | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [laddad, setLaddad] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const svar = await fetch(`${BAS}/leads/config`).then((s) => readJson<LeadsConfig>(s));
        setConfig(svar);
      } catch (orsak) {
        setFel(felmeddelande(orsak));
      }
      setLaddad(true);
    })();
  }, []);

  const icp = (config?.icp ?? {}) as Record<string, unknown>;
  const icpRader = Object.entries(icp).filter(
    ([, varde]) =>
      varde !== null &&
      varde !== "" &&
      !(Array.isArray(varde) && varde.length === 0)
  );

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Inställningar"
        beskrivning="Målgruppen agenten letar efter och hur självständigt den får arbeta. Ändringar görs i arbetsytan på Snajp-webben — här ser du vad som gäller."
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {!laddad ? (
        <SkeletonRows />
      ) : config ? (
        <>
          <section className="max-w-[42rem]">
            <h2 className="font-display text-[1.25rem]">Autonomi</h2>
            <div className="mt-3 border-y border-ink/15 py-4">
              <Badge tone="neutral">{config.autonomy || "okänd"}</Badge>
              {config.autonomy_description ? (
                <p className="mt-2 max-w-[62ch] text-[0.9375rem] leading-6 text-ink/62">
                  {config.autonomy_description}
                </p>
              ) : null}
            </div>
          </section>

          <section className="max-w-[42rem]">
            <h2 className="font-display text-[1.25rem]">Målgrupp</h2>
            {icpRader.length ? (
              <dl className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
                {icpRader.map(([nyckel, varde]) => (
                  <div key={nyckel} className="flex flex-wrap items-baseline gap-x-6 py-3">
                    <dt className="w-40 shrink-0 text-[0.875rem] text-ink/55">{nyckel}</dt>
                    <dd className="min-w-0 flex-1 break-words text-[0.9375rem]">
                      {Array.isArray(varde) ? varde.join(", ") : String(varde)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="mt-3 border-y border-ink/15 py-4 text-[0.9375rem] text-ink/55">
                Ingen målgrupp ifylld ännu — fyll i den i arbetsytan på
                Snajp-webben så vet agenten vad den ska leta efter.
              </p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
