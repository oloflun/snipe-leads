"use client";

/* design · pre-emit critique: P4 H4 E4 S4 R5 V3 — Operate-yta i det låsta systemet
   (DESIGN.md, Tier 0): samma ändringslista som adminens Agentinstruktioner. */

import { useEffect, useState } from "react";
import { Badge, btnLiten, btnPrimary, btnSecondary, etikett, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { leadsAnrop, relativTid } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Kundens egna önskemål till sin agent (fas 8, 2026-10-06).
 *
 * Kunden skriver feedback med egna ord, förhandsgranskar ändringarna med
 * skäl, godkänner, och kan återställa en tidigare version. Dokumentet läses i
 * användarposition, inslaget som opålitligt innehåll (INV-SEC-009): kunden
 * styr ton och fokus men kan inte upphäva reglerna. Backend:
 * `snajp-support/app/leads/onskemal.py`.
 */

type Agent = "leads" | "support";
type Andring = { typ: "lagg_till" | "ersatt" | "ta_bort"; befintlig?: string; ny?: string; skal?: string };
type Bakning = { dokument: string; andringar: Andring[]; sammanfattning?: string; varning?: string };
type Version = { id: string; created_at: string | null; content: string; feedback: string };
type Lage = { dokument: string; max_tecken: number; historik: Version[] };

const T = {
  rubrik: {
    leads: { sv: "Era önskemål till Iris", en: "Your instructions to Iris" },
    support: { sv: "Era önskemål till supportagenten", en: "Your instructions to the support agent" }
  },
  om: {
    sv: "Skriv med egna ord vad agenten ska göra annorlunda. Ni ser ändringarna innan de sparas. Önskemålen styr ton och fokus, inte reglerna för vad agenten får påstå.",
    en: "Write in your own words what the agent should do differently. You see the changes before they are saved. Your instructions steer tone and focus, not the rules on what the agent may claim."
  },
  nu: { sv: "Det agenten läser nu", en: "What the agent reads now" },
  tomt: { sv: "Inga önskemål sparade.", en: "No instructions saved." },
  feedback: { sv: "Er feedback", en: "Your feedback" },
  forhandsgranska: { sv: "Förhandsgranska", en: "Preview" },
  arbetar: { sv: "Arbetar…", en: "Working…" },
  andringar: { sv: "Ändringar", en: "Changes" },
  skal: { sv: "Skäl:", en: "Reason:" },
  typ: {
    lagg_till: { sv: "Läggs till", en: "Added" },
    ersatt: { sv: "Ersätts", en: "Replaced" },
    ta_bort: { sv: "Tas bort", en: "Removed" }
  },
  fore: { sv: "Före", en: "Before" },
  efter: { sv: "Efter", en: "After" },
  godkann: { sv: "Godkänn och spara", en: "Approve and save" },
  sparat: { sv: "Sparat. Gäller från nästa svar.", en: "Saved. Applies from the next reply." },
  historik: { sv: "Tidigare versioner", en: "Earlier versions" },
  aterstall: { sv: "Återställ", en: "Restore" },
  aterstalld: { sv: "Återställd. Gäller från nästa svar.", en: "Restored. Applies from the next reply." },
  aktiv: { sv: "Aktiv", en: "Active" },
  tecken: { sv: "tecken", en: "characters" }
} as const;

const TON = { lagg_till: "good", ersatt: "warn", ta_bort: "danger" } as const;

export function AgentOnskemal({ agent }: Readonly<{ agent: Agent }>) {
  const { locale, text } = useLocale();
  const [lage, setLage] = useState<Lage | null>(null);
  const [feedback, setFeedback] = useState("");
  const [bakning, setBakning] = useState<Bakning | null>(null);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [kvitto, setKvitto] = useState<Localized | null>(null);
  const bas = `/agent/onskemal/${agent}`;

  async function hamta() {
    try {
      setLage(await leadsAnrop<Lage>(bas));
    } catch (orsak) {
      setLage({ dokument: "", max_tecken: 4000, historik: [] });
      setFel(felmeddelande(orsak));
    }
  }

  useEffect(() => {
    void hamta();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hämtas om bara när agenten byts
  }, [agent]);

  async function kor(steg: () => Promise<void>) {
    setBusy(true);
    setFel(null);
    setKvitto(null);
    try {
      await steg();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setBusy(false);
    }
  }

  const forhandsgranska = () =>
    kor(async () => {
      setBakning(
        await leadsAnrop<Bakning>(`${bas}/forhandsgranska`, { method: "POST", body: JSON.stringify({ feedback }) })
      );
    });

  const spara = () =>
    kor(async () => {
      if (!bakning) return;
      await leadsAnrop(bas, { method: "PUT", body: JSON.stringify({ feedback, dokument: bakning.dokument }) });
      setFeedback("");
      setBakning(null);
      setKvitto(T.sparat);
      await hamta();
    });

  const aterstall = (id: string) =>
    kor(async () => {
      await leadsAnrop(`${bas}/aterstall/${id}`, { method: "POST" });
      setKvitto(T.aterstalld);
      await hamta();
    });

  if (!lage) return <div className="h-40 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />;
  const id = `onskemal-${agent}`;

  return (
    <section aria-labelledby={`${id}-rubrik`} className="grid gap-6">
      <div>
        <h2 id={`${id}-rubrik`} className={rubrikPanel}>
          {text(T.rubrik[agent])}
        </h2>
        <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">{text(T.om)}</p>
      </div>

      <div>
        <p className={etikett}>{text(T.nu)}</p>
        <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-input border border-ink/15 bg-paper2/50 p-4 text-[0.875rem] leading-6">
          {lage.dokument || text(T.tomt)}
        </pre>
      </div>

      <div>
        <label htmlFor={`${id}-feedback`} className={cn(etikett, "block")}>
          {text(T.feedback)}
        </label>
        <textarea
          id={`${id}-feedback`}
          value={feedback}
          maxLength={lage.max_tecken}
          rows={4}
          onChange={(e) => {
            setFeedback(e.target.value);
            setBakning(null);
          }}
          className="focus-ring mt-2 w-full resize-y rounded-input border border-ink/15 bg-paper p-3 text-[16px] leading-6"
        />
        <button
          type="button"
          onClick={() => void forhandsgranska()}
          disabled={busy || !feedback.trim()}
          className={cn(btnSecondary, "mt-3")}
        >
          {busy && !bakning ? text(T.arbetar) : text(T.forhandsgranska)}
        </button>
      </div>

      {bakning ? (
        <div>
          <p className={etikett}>{text(T.andringar)}</p>
          {bakning.sammanfattning ? (
            <p className="mt-2 max-w-[62ch] text-[0.9375rem] leading-6">{bakning.sammanfattning}</p>
          ) : null}
          <ol className="mt-3 divide-y divide-ink/12 border-y border-ink/12">
            {bakning.andringar.map((a, i) => (
              <li key={i} className="py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge tone={TON[a.typ]}>{text(T.typ[a.typ])}</Badge>
                  {a.skal ? (
                    <span className="text-[0.9375rem] text-ink-muted">
                      {text(T.skal)} {a.skal}
                    </span>
                  ) : null}
                </div>
                <div className="mt-2 grid gap-3 lg:grid-cols-2">
                  {a.typ !== "lagg_till" && a.befintlig ? (
                    <div className="min-w-0">
                      <p className={meta}>{text(T.fore)}</p>
                      <p className="mt-1 whitespace-pre-wrap break-words rounded-input bg-danger/[0.06] p-3 text-[0.875rem] leading-6 line-through decoration-danger/50">
                        {a.befintlig}
                      </p>
                    </div>
                  ) : null}
                  {a.typ !== "ta_bort" && a.ny ? (
                    <div className="min-w-0">
                      <p className={meta}>{text(T.efter)}</p>
                      <p className="mt-1 whitespace-pre-wrap break-words rounded-input bg-moss/[0.08] p-3 text-[0.875rem] leading-6">
                        {a.ny}
                      </p>
                    </div>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
          {bakning.varning ? (
            <p role="alert" className="mt-3 max-w-[62ch] text-[0.9375rem] leading-6 text-warning">
              {bakning.varning}
            </p>
          ) : null}
          <p className={cn(meta, "num mt-2")}>
            {bakning.dokument.length} / {lage.max_tecken} {text(T.tecken)}
          </p>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <button type="button" onClick={() => void spara()} disabled={busy || !bakning} className={btnPrimary}>
          {busy && bakning ? text(T.arbetar) : text(T.godkann)}
        </button>
        <span aria-live="polite" className="text-[0.9375rem] text-moss">
          {kvitto ? text(kvitto) : ""}
        </span>
        {fel ? (
          <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
            {fel}
          </p>
        ) : null}
      </div>

      {lage.historik.length ? (
        <div>
          <p className={etikett}>{text(T.historik)}</p>
          <ol className="mt-2 divide-y divide-ink/12 border-y border-ink/12">
            {lage.historik.map((v, i) => (
              <li key={v.id} className="flex flex-wrap items-start justify-between gap-3 py-3">
                <details className="min-w-0 flex-1">
                  <summary className="focus-ring cursor-pointer rounded-input text-[0.9375rem]">
                    <span className="num">{relativTid(v.created_at, locale)}</span>
                    {v.feedback ? <span className="ml-2 text-ink-muted">{v.feedback.slice(0, 80)}</span> : null}
                  </summary>
                  <pre className="mt-2 whitespace-pre-wrap text-[0.875rem] leading-6">{v.content || text(T.tomt)}</pre>
                </details>
                {i === 0 ? (
                  <Badge tone="good">{text(T.aktiv)}</Badge>
                ) : (
                  <button
                    type="button"
                    onClick={() => void aterstall(v.id)}
                    disabled={busy}
                    className={cn(btnSecondary, btnLiten)}
                  >
                    {text(T.aterstall)}
                  </button>
                )}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
