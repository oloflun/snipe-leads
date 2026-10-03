"use client";

import { useCallback, useEffect, useState } from "react";
import { EjAktiverad } from "@/components/EjAktiverad";
import { SkeletonRows, Tomt, btnSecondary, etikett, meta } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { LeadsFel, leadsAnrop, poangAv, type SuiteProspekt } from "@/lib/leads/suite";
import { STATUS_ETIKETT, STATUS_ORDNING, nivaEtikett } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Iris › Pipeline (Fas 10, Leads Suite F5): en kolumn per status. Ett kort
 * flyttas med dra och släpp eller med "Flytta till"-listan på kortet (för
 * tangentbord och skärmläsare); båda sparar med PATCH status, optimistiskt,
 * och återställs om sparningen faller. Spärrade bolag ligger bakom en växel.
 * I demon kommer korten ur demofixturen och flytten sparas aldrig.
 */

const T = {
  pipeline: { sv: "Pipeline", en: "Pipeline" },
  hamtaFel: { sv: "Bolagen kunde inte hämtas.", en: "The companies could not be loaded." },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  tomt: { sv: "Inga bolag ännu. Kör Iris så fylls pipelinen.", en: "No companies yet. Run Iris to fill the pipeline." },
  visaSparrade: { sv: "Visa spärrade", en: "Show blocked" },
  flyttaTill: { sv: "Flytta till", en: "Move to" },
  ingaKort: { sv: "Inga leads", en: "No leads" },
  flyttFel: { sv: "Flytten sparades inte", en: "The move was not saved" },
  flyttad: { sv: "flyttad till", en: "moved to" },
  poang: { sv: "poäng", en: "score" },
  demo: { sv: "Flytten sparas inte i demon.", en: "Moves are not saved in the demo." }
} satisfies Record<string, Localized>;

export function Pipeline({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { locale, text } = useLocale();
  const [prospekt, setProspekt] = useState<SuiteProspekt[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [ejAktiverad, setEjAktiverad] = useState(false);
  const [flyttFel, setFlyttFel] = useState<string | null>(null);
  const [flyttMeddelande, setFlyttMeddelande] = useState<string | null>(null);
  const [fokusId, setFokusId] = useState<string | null>(null);

  // Kortet byter kolumn och monteras om: fokus tillbaka till samma select EFTER
  // commit, annars hamnar tangentbordet på body (2.4.3).
  useEffect(() => {
    if (fokusId) document.getElementById(`pipeline-val-${fokusId}`)?.focus();
  }, [fokusId, prospekt]);
  const [visaSparrade, setVisaSparrade] = useState(false);
  const [over, setOver] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    setFel(null);
    if (demo) {
      const svar = demoOversiktSvar("/leads/prospects") as { prospects?: SuiteProspekt[] } | undefined;
      setProspekt(svar?.prospects ?? []);
      return;
    }
    try {
      const svar = await leadsAnrop<{ prospects?: SuiteProspekt[] }>("/leads/prospects");
      setProspekt(svar.prospects ?? []);
    } catch (orsak) {
      if (orsak instanceof LeadsFel && orsak.ejAktiverad) setEjAktiverad(true);
      else setFel(felmeddelande(orsak));
    }
  }, [demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  async function flytta(id: string, status: string) {
    const forra = prospekt?.find((p) => p.id === id)?.status;
    if (!forra || forra === status) return;
    setFlyttFel(null);
    setProspekt((rader) => rader?.map((p) => (p.id === id ? { ...p, status } : p)) ?? null);
    const namn = prospekt?.find((p) => p.id === id)?.company_name ?? "";
    setFlyttMeddelande(`${namn} ${text(T.flyttad)} ${text(STATUS_ETIKETT[status] ?? { sv: status, en: status })}`);
    setFokusId(id);
    if (demo) return;
    try {
      await leadsAnrop(`/leads/prospects/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    } catch (orsak) {
      setProspekt((rader) => rader?.map((p) => (p.id === id ? { ...p, status: forra } : p)) ?? null);
      setFlyttFel(`${text(T.flyttFel)}: ${felmeddelande(orsak)}`);
    }
  }

  if (ejAktiverad) return <EjAktiverad yta={text(T.pipeline)} />;
  if (fel) {
    return (
      <div>
        <p role="alert" className="text-[15px] text-danger">
          {text(T.hamtaFel)} {fel}
        </p>
        <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, "mt-4")}>
          {text(T.forsokIgen)}
        </button>
      </div>
    );
  }
  if (prospekt === null) return <SkeletonRows />;
  if (prospekt.length === 0) return <Tomt>{text(T.tomt)}</Tomt>;

  const kolumner = STATUS_ORDNING.filter((s) => visaSparrade || s !== "suppressed");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {demo ? <p className={meta}>{text(T.demo)}</p> : <span />}
        <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 text-[15px] text-ink-muted">
          <input
            type="checkbox"
            checked={visaSparrade}
            onChange={(e) => setVisaSparrade(e.target.checked)}
            className="focus-ring h-5 w-5 accent-ink"
          />
          {text(T.visaSparrade)}
        </label>
      </div>

      {flyttFel ? (
        <p role="alert" className="text-[15px] text-danger">
          {flyttFel}
        </p>
      ) : null}
      <p role="status" className="sr-only">
        {flyttMeddelande}
      </p>

      <div className="thin-scrollbar overflow-x-auto pb-2">
        <ol className="flex gap-4" aria-label={text(T.pipeline)}>
          {kolumner.map((status) => {
            const kort = prospekt.filter((p) => p.status === status);
            const rubrikId = `pipeline-${status}`;
            return (
              <li
                key={status}
                aria-labelledby={rubrikId}
                onDragOver={(e) => {
                  e.preventDefault();
                  setOver(status);
                }}
                onDragLeave={() => setOver((o) => (o === status ? null : o))}
                onDrop={(e) => {
                  e.preventDefault();
                  setOver(null);
                  const id = e.dataTransfer.getData("text/plain");
                  if (id) void flytta(id, status);
                }}
                className={cn(
                  "flex w-64 shrink-0 flex-col rounded-card border p-3 transition-colors",
                  over === status ? "border-ink/40 bg-ochre/10" : "border-ink/12 bg-paper2/40"
                )}
              >
                <h2 id={rubrikId} className={cn(etikett, "flex items-baseline justify-between gap-2 px-1")}>
                  <span>{text(STATUS_ETIKETT[status])}</span>
                  <span className="num tabular-nums">{kort.length}</span>
                </h2>
                {kort.length === 0 ? (
                  <p className={cn(meta, "mt-3 px-1")}>{text(T.ingaKort)}</p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {kort.map((p) => (
                      <li
                        key={p.id}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData("text/plain", p.id);
                          e.dataTransfer.effectAllowed = "move";
                        }}
                        className="cursor-grab rounded-input border border-ink/12 bg-paper p-3 active:cursor-grabbing"
                      >
                        <p className="break-words font-semibold leading-snug">{p.company_name}</p>
                        <p className={cn(meta, "mt-1")}>
                          {[p.niva ? nivaEtikett(p.niva, locale) : null, poangAv(p) ? `${poangAv(p)} ${text(T.poang)}` : null]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                        {p.contact_name ? <p className="mt-1 break-words text-[15px] text-ink-muted">{p.contact_name}</p> : null}
                        <label className="mt-2 block">
                          <span className="sr-only">
                            {text(T.flyttaTill)} ({p.company_name})
                          </span>
                          <select
                            id={`pipeline-val-${p.id}`}
                            value={p.status}
                            onChange={(e) => void flytta(p.id, e.target.value)}
                            className="focus-ring min-h-11 w-full rounded-input border border-ink/15 bg-paper px-2 text-[16px] text-ink"
                          >
                            {STATUS_ORDNING.map((s) => (
                              <option key={s} value={s}>
                                {s === p.status ? text(STATUS_ETIKETT[s]) : `${text(T.flyttaTill)}: ${text(STATUS_ETIKETT[s])}`}
                              </option>
                            ))}
                          </select>
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
