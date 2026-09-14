"use client";

import { AlertTriangle, Check, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, SkeletonRows } from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { readJsonBody } from "@/lib/http/json";

/**
 * Agentens lärande — förslagen och kundens domar, på ett ställe.
 *
 * ## Varför ytan finns
 *
 * Backenden persisterar sedan 2026-08-26 det agenterna lär sig som FÖRSLAG
 * (agent_suggestions): supportens KB-artikelutkast ur ärenden där
 * kunskapsbasen inte räckte, och leads marknadsinsikter ur researchvarv.
 * Agenten skriver aldrig själv i underlaget (INV-LEARN-001) — den här vyn ÄR
 * människan i den loopen. Godkänn på ett kb_article-förslag skapar artikeln
 * (i backendens endpoint, inte här); godkänn på en marknadsinsikt markerar
 * den läst — själva ICP-ändringen gör du i Målgrupp-inställningarna med
 * insiktens text som underlag.
 *
 * Feedbacklistan därunder är read-only: domarna lämnas där körningarna syns,
 * listan här visar vad som samlats.
 */

type Forslag = {
  id: string;
  agent_type: string;
  kind: string;
  title: string;
  content:
    | {
        title?: string;
        content?: string;
        category?: string;
        gap?: string;
        icp_adjustment?: string;
        evidence?: string[];
      }
    | string;
  status: string;
  created_at: string;
};

type Feedbackrad = {
  id: string;
  run_id: string;
  verdict: string;
  comment: string | null;
  corrected_output: string | null;
  created_at: string;
};

type Lage =
  | { fas: "laddar" }
  | { fas: "ejAktiverad" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; forslag: Forslag[]; feedback: Feedbackrad[] };

const KIND_ETIKETT: Record<string, string> = {
  kb_article: "KB-artikel",
  marknadsinsikt: "Marknadsinsikt"
};

const VERDICT_ETIKETT: Record<string, string> = {
  good: "Bra",
  bad: "Fel",
  needs_review: "Granska"
};

function nar(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("sv-SE", { day: "numeric", month: "short" });
}

type ForslagsInnehall = {
  title?: string;
  content?: string;
  category?: string;
  gap?: string;
  icp_adjustment?: string;
  evidence?: string[];
};

function safeParse(s: string): ForslagsInnehall {
  try {
    return JSON.parse(s) as ForslagsInnehall;
  } catch {
    return {};
  }
}

function innehall(f: Forslag): { rubrik: string; brodtext: string; belagg: string[] } {
  // jsonb kan nå klienten som sträng beroende på proxyled — tåla båda.
  const c: ForslagsInnehall = typeof f.content === "string" ? safeParse(f.content) : f.content;
  if (f.kind === "kb_article") {
    return {
      rubrik: c.title ?? f.title,
      brodtext: c.content ?? "",
      belagg: []
    };
  }
  return {
    rubrik: f.title,
    brodtext: [c.gap, c.icp_adjustment].filter(Boolean).join("\n\n"),
    belagg: Array.isArray(c.evidence) ? c.evidence : []
  };
}

export function AgentLarande() {
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });
  const [arbetar, setArbetar] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    setLage({ fas: "laddar" });
    try {
      const [fRes, fbRes] = await Promise.all([
        fetch("/api/snajp-support/agent/forslag?status=ny", { cache: "no-store" }),
        fetch("/api/snajp-support/agent/feedback", { cache: "no-store" })
      ]);
      if (fRes.status === 409) {
        const kropp = await readJsonBody<unknown>(fRes).catch(() => null);
        if (arEjAktiverad(fRes.status, kropp)) {
          setLage({ fas: "ejAktiverad" });
          return;
        }
      }
      if (!fRes.ok) {
        setLage({
          fas: "fel",
          meddelande:
            fRes.status >= 500
              ? "Tjänsten svarar inte just nu. Den vaknar ur viloläge och kan ta upp till en minut."
              : `Kunde inte hämta förslagen (status ${fRes.status}).`
        });
        return;
      }
      const forslag = await readJsonBody<{ suggestions?: Forslag[] }>(fRes);
      const feedback = fbRes.ok
        ? await readJsonBody<{ feedback?: Feedbackrad[] }>(fbRes).catch(() => null)
        : null;
      setLage({
        fas: "klar",
        forslag: forslag?.suggestions ?? [],
        feedback: feedback?.feedback ?? []
      });
    } catch (error) {
      setLage({
        fas: "fel",
        meddelande: error instanceof Error ? error.message : "Kunde inte nå servern."
      });
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  const avgor = useCallback(
    async (id: string, handling: "godkann" | "avfard") => {
      setArbetar(id);
      try {
        const response = await fetch(`/api/snajp-support/agent/forslag/${id}/${handling}`, {
          method: "POST"
        });
        if (!response.ok) {
          setLage({
            fas: "fel",
            meddelande: `Kunde inte ${handling === "godkann" ? "godkänna" : "avfärda"} förslaget (status ${response.status}).`
          });
          return;
        }
        await hamta();
      } finally {
        setArbetar(null);
      }
    },
    [hamta]
  );

  if (lage.fas === "laddar") return <SkeletonRows />;
  if (lage.fas === "ejAktiverad") return <EjAktiverad yta="Lärande" />;

  if (lage.fas === "fel") {
    return (
      <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ochre" aria-hidden />
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">Lärandet kunde inte hämtas</p>
          <p className="mt-1 text-sm text-ink/70">{lage.meddelande}</p>
          <button
            type="button"
            onClick={() => void hamta()}
            className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
          >
            Försök igen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-12">
      <section>
        <h2 className="kicker text-mineral">Väntar på ditt beslut</h2>
        {lage.forslag.length === 0 ? (
          <div className="mt-3">
            <EmptyState
              title="Inga förslag just nu"
              body="När supportagenten ser en kunskapslucka eller leads-agenten lär sig något om marknaden hamnar förslaget här. Ingenting skrivs in i din kunskapsbas eller målgrupp utan ditt godkännande."
            />
          </div>
        ) : (
          <ul className="mt-3 divide-y divide-ink/15 border-y border-ink/15">
            {lage.forslag.map((f) => {
              const { rubrik, brodtext, belagg } = innehall(f);
              return (
                <li key={f.id} className="py-5">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <p className="text-[1.0625rem] font-semibold tracking-[-0.01em]">{rubrik}</p>
                    <span className="kicker shrink-0 text-mineral">
                      {KIND_ETIKETT[f.kind] ?? f.kind} · {f.agent_type} · {nar(f.created_at)}
                    </span>
                  </div>
                  {brodtext ? (
                    <p className="mt-2 max-w-[75ch] whitespace-pre-line text-[15px] leading-6 text-ink/78">
                      {brodtext}
                    </p>
                  ) : null}
                  {belagg.length > 0 ? (
                    <ul className="mt-2 max-w-[75ch] space-y-1">
                      {belagg.map((b) => (
                        <li key={b} className="text-[13px] leading-5 text-ink/55">
                          ”{b}”
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      disabled={arbetar === f.id}
                      onClick={() => void avgor(f.id, "godkann")}
                      className="focus-ring inline-flex min-h-9 items-center gap-1.5 rounded-input bg-ink px-3 text-[13px] font-medium text-paper disabled:opacity-50"
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden />
                      {f.kind === "kb_article" ? "Godkänn — skapa artikeln" : "Godkänn"}
                    </button>
                    <button
                      type="button"
                      disabled={arbetar === f.id}
                      onClick={() => void avgor(f.id, "avfard")}
                      className="focus-ring inline-flex min-h-9 items-center gap-1.5 rounded-input bg-paper2 px-3 text-[13px] font-medium disabled:opacity-50"
                    >
                      <X className="h-3.5 w-3.5" aria-hidden />
                      Avfärda
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section>
        <h2 className="kicker text-mineral">Domar från teamet</h2>
        {lage.feedback.length === 0 ? (
          <p className="mt-3 max-w-[75ch] text-[15px] leading-6 text-ink/60">
            Inga domar ännu. När någon i teamet markerar en körning som bra
            eller fel samlas den här — och en rättad text är det starkaste
            underlaget agenterna kan lära sig av.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-ink/15 border-y border-ink/15">
            {lage.feedback.map((r) => (
              <li key={r.id} className="py-4">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <p className="text-[15px] font-semibold">
                    {VERDICT_ETIKETT[r.verdict] ?? r.verdict}
                    {r.comment ? (
                      <span className="ml-2 font-normal text-ink/70">{r.comment}</span>
                    ) : null}
                  </p>
                  <span className="kicker shrink-0 text-mineral">{nar(r.created_at)}</span>
                </div>
                {r.corrected_output ? (
                  <p className="mt-2 max-w-[75ch] whitespace-pre-line text-[14px] leading-6 text-ink/70">
                    Rättad text: {r.corrected_output}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
