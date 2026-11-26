"use client";

import { useEffect, useState } from "react";
import { Eraser, History, Pencil, Plus, RotateCcw, Trash2, type LucideIcon } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Objektikon, type Ton } from "@/components/crm/app/kit";
import { CrmFel, SYSTEMNAMN, crmAnrop, type Handelse } from "@/lib/crm/api";
import { faltetikett, uppraknat } from "@/lib/crm/felkoder";
import { useLocale, type Localized } from "@/lib/i18n";

const TYP: Record<Handelse["type"], { ikon: LucideIcon; ton: Ton; text: Localized }> = {
  created: { ikon: Plus, ton: "mossa", text: { sv: "Skapades", en: "Created" } },
  updated: { ikon: Pencil, ton: "bla", text: { sv: "Ändrades", en: "Changed" } },
  deleted: { ikon: Trash2, ton: "mineral", text: { sv: "Raderades", en: "Deleted" } },
  restored: { ikon: RotateCcw, ton: "ockra", text: { sv: "Återställdes", en: "Restored" } },
  purged: { ikon: Eraser, ton: "mineral", text: { sv: "Tömdes ur papperskorgen", en: "Emptied from the trash" } }
};

const KALLA: Record<string, Localized> = {
  api: { sv: "API", en: "API" },
  app: { sv: "Appen", en: "The app" },
  synk: { sv: "Synk", en: "Sync" },
  system: { sv: "Systemet", en: "The system" }
};

/** "Telefon och Ort ändrades": fälten med panelens etiketter. Loggen bär namnen, aldrig värdena. */
function vad(h: Handelse, text: (l: Localized) => string): string {
  if (h.type !== "updated" || h.fields.length === 0) return text(TYP[h.type]?.text ?? { sv: h.type, en: h.type });
  const falt = h.fields.map((f) => text(faltetikett(f)));
  const lista = uppraknat(falt, text({ sv: "och", en: "and" }));
  return text({ sv: `${lista} ändrades`, en: `${lista} changed` });
}

/** Varifrån: Synk från anslutningen, API, Appen eller Systemet. */
function varifran(h: Handelse, text: (l: Localized) => string): string {
  const kalla = h.source ? (KALLA[h.source] ?? { sv: h.source, en: h.source }) : { sv: "Okänd källa", en: "Unknown source" };
  if (h.source === "synk" && h.actor?.startsWith("anslutning:")) {
    const namn = h.actor.slice("anslutning:".length);
    const visat = SYSTEMNAMN[namn] ?? namn;
    return text({ sv: `Synk från ${visat}`, en: `Sync from ${visat}` });
  }
  return text(kalla);
}

/**
 * Postens historik som en tidslinje (Twentys Timeline, i panelens form): en rad
 * per händelse med vad som hände, varifrån och när, nyast först. Hämtas från
 * `GET /v1/companies/{id}/history` eller `/v1/people/{id}/history`, och igen
 * när posten ändrats (`andrad`), så att en sparad ändring syns direkt.
 */
export function Historik({ objekt, id, andrad }: Readonly<{ objekt: "companies" | "people" | "deals"; id: string; andrad?: string | null }>) {
  const { text } = useLocale();
  const [handelser, setHandelser] = useState<Handelse[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [omgang, setOmgang] = useState(0);

  useEffect(() => {
    let aktuell = true;
    setFel(null);
    crmAnrop<{ data: Handelse[] }>(`/v1/${objekt}/${encodeURIComponent(id)}/history?limit=100`)
      .then((s) => aktuell && setHandelser(s.data))
      .catch((e) => aktuell && setFel(e));
    return () => {
      aktuell = false;
    };
  }, [objekt, id, andrad, omgang]);

  if (fel && !handelser) {
    return (
      <div className="flex flex-col items-start gap-3 py-2">
        <Text color="secondary">
          {text(fel instanceof CrmFel ? fel.text : { sv: "Historiken gick inte att hämta.", en: "The history could not be loaded." })}
        </Text>
        <Button size="sm" variant="secondary" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => setOmgang((n) => n + 1)} />
      </div>
    );
  }

  if (!handelser) {
    return (
      <div className="flex flex-col gap-5 py-1" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar historiken", en: "Loading the history" })}>
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="flex items-start gap-3">
            <Skeleton width={24} height={24} radius={2} index={i} />
            <span className="flex flex-1 flex-col gap-2 pt-1">
              <Skeleton width={`${45 + ((i * 17) % 35)}%`} height={10} radius="rounded" index={i} />
              <Skeleton width="30%" height={8} radius="rounded" index={i} />
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (handelser.length === 0) {
    return (
      <EmptyState
        isCompact
        icon={<Icon icon={History} size="lg" color="secondary" />}
        title={text({ sv: "Ingen händelse än", en: "No events yet" })}
        description={text({
          sv: "Varje ändring av posten syns här: vilka fält som ändrades, varifrån och när.",
          en: "Every change to the record shows here: which fields changed, where from and when."
        })}
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <ol className="crm-tidslinje" aria-label={text({ sv: "Historik, nyast först", en: "History, newest first" })}>
        {handelser.map((h) => {
          const typ = TYP[h.type] ?? TYP.updated;
          return (
            <li key={h.seq} className="crm-tidslinje-rad">
              <span className="crm-tidslinje-ikon">
                <Objektikon ikon={typ.ikon} ton={typ.ton} storlek={24} />
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-0.5 pb-4">
                <span className="text-[0.875rem] text-ink">{vad(h, text)}</span>
                <span className="flex flex-wrap items-center gap-x-1.5 text-[0.8125rem] text-ink-muted">
                  <span>{varifran(h, text)}</span>
                  {h.at ? (
                    <>
                      <span aria-hidden>·</span>
                      <Timestamp value={h.at} format="relative" />
                    </>
                  ) : null}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
      <Text type="supporting" color="secondary">
        {text({
          sv: "Historiken visar vilka fält som ändrades. Värdena står i postens uppgifter.",
          en: "The history shows which fields changed. The values are in the record's details."
        })}
      </Text>
    </div>
  );
}
