"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, SkeletonRows } from "@/components/ui";
import { Eskalering } from "@/components/vyer/Eskalering";
import { BAS, type LeadsConfig } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";

/**
 * Målgruppen och autonomin, som de faktiskt är inställda. LÄSVY med flit:
 * ändringar görs i Snajp-webbens arbetsyta där hela kontrollpanelen bor —
 * två redigeringsytor för samma inställningar blir två sanningar.
 */
/**
 * ICP-värdena är godtycklig JSON ur backendens config. `String(varde)` gav
 * "[object Object]" för nästlade objekt (t.ex. company_size: {min, max}) —
 * uppmätt i den lokala minneslägesbackenden 2026-09-16. Objekt plattas till
 * "nyckel: värde"-par i stället; ingenting hittas på, allt visas.
 */
function arTomt(varde: unknown): boolean {
  if (varde === null || varde === undefined || varde === "") return true;
  if (Array.isArray(varde)) return varde.every(arTomt);
  if (typeof varde === "object") return Object.values(varde).every(arTomt);
  return false;
}

function visaVarde(varde: unknown): string {
  if (Array.isArray(varde)) return varde.filter((v) => !arTomt(v)).map(visaVarde).join(", ");
  if (varde !== null && typeof varde === "object") {
    return Object.entries(varde as Record<string, unknown>)
      .filter(([, inre]) => !arTomt(inre))
      .map(([nyckel, inre]) => `${nyckel}: ${visaVarde(inre)}`)
      .join(", ");
  }
  return String(varde);
}

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
  // Ofyllda värden filtreras hela vägen ner: ett objekt vars fält alla är
  // null är lika tomt som null självt — "min: null, max: null" är brus, inte
  // en inställning (uppmätt i minneslägesbackenden 2026-09-16).
  const icpRader = Object.entries(icp).filter(([, varde]) => !arTomt(varde));

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Inställningar"
        beskrivning="Målgruppen Iris letar efter, hur självständigt hon får arbeta, och när hon ska lämna över till dig. Målgrupp och autonomi ändras i arbetsytan på Snajp-webben, eskaleringen ställer du in här."
      />

      <Eskalering />

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
                      {visaVarde(varde)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="mt-3 border-y border-ink/15 py-4 text-[0.9375rem] text-ink/55">
                Ingen målgrupp ifylld ännu. Fyll i den i arbetsytan på
                Snajp-webben så vet Iris vad hon ska leta efter.
              </p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
