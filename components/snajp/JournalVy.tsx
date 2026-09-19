"use client";

import { Loader2, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { Badge } from "@/components/ui";
import {
  TOKENKOSTNAD_MODELL,
  tokenkostnad
} from "@/lib/admin/halsa";
import { readJsonBody } from "@/lib/http/json";

/**
 * Journalen: vad agenten gjort och vad det kostat — tenant-scopat.
 *
 * Byggd för Livrustning-piloten: kundens kontaktperson (läsrollen) ska kunna
 * följa körningar, eskaleringar och kostnad utan att någon av oss behöver
 * öppna /admin och ta en skärmdump. Datat kommer ur två tenant-scopade
 * endpoints — GET /api/usage (ny, journalens dagliga serie + budgetläget)
 * och GET /api/chattar (överlämningarna) — via den inloggade proxyn, alltså
 * med kundens egen nyckel och kundens egen isolering.
 *
 * Kostnaden är en UPPSKATTNING ur tokental och Vertex listpris
 * (lib/admin/halsa.ts), samma siffra som adminytans Agentanvändning — och
 * samma förbehåll: det här är inte en faktura.
 */

type Dagrad = {
  datum: string;
  korningar: number;
  korningar_test: number;
  tokens_in: number;
  tokens_out: number;
};

type UsageSvar = {
  dagar: Dagrad[];
  budget: { tak: number; forbrukat_24h: number };
};

type ChattRad = {
  customer_id: string;
  customer_name?: string | null;
  subject?: string | null;
  category?: string | null;
  channel?: string | null;
  overlamnad_at?: string | null;
  orsak_text?: string | null;
  aktiv?: boolean;
  is_test?: boolean;
};

class EjAktiveradFel extends Error {}

async function hamta<T>(path: string): Promise<T> {
  const response = await fetch(`/api/snajp-support${path}`, {
    headers: { "Content-Type": "application/json" }
  });
  const payload =
    (await readJsonBody<T & { offline?: boolean; error?: string }>(response)) ??
    ({} as T & { offline?: boolean; error?: string });
  if (payload.offline) {
    throw new Error(payload.error ?? "Tjänsten är inte tillgänglig just nu.");
  }
  if (!response.ok) {
    if (arEjAktiverad(response.status, payload)) throw new EjAktiveradFel();
    throw new Error(payload.error ?? "Okänt fel");
  }
  return payload;
}

function kr(varde: number): string {
  return `${varde.toFixed(2).replace(".", ",")} kr`;
}

function datumtid(varde: string | null | undefined): string {
  if (!varde) return "–";
  const d = new Date(varde);
  return Number.isNaN(d.getTime()) ? "–" : d.toLocaleString("sv-SE", { dateStyle: "short", timeStyle: "short" });
}

export function JournalVy() {
  const [usage, setUsage] = useState<UsageSvar | null>(null);
  const [chattar, setChattar] = useState<ChattRad[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ejAktiverad, setEjAktiverad] = useState(false);

  const ladda = useCallback(async () => {
    try {
      setError(null);
      const [u, c] = await Promise.all([
        hamta<UsageSvar>("/usage?days=30"),
        hamta<{ chattar: ChattRad[] }>("/chattar")
      ]);
      setUsage(u);
      setChattar(c.chattar ?? []);
    } catch (caught) {
      if (caught instanceof EjAktiveradFel) {
        setEjAktiverad(true);
        return;
      }
      setError(caught instanceof Error ? caught.message : "Kunde inte hämta journalen.");
    }
  }, []);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  if (ejAktiverad) {
    return <EjAktiverad yta="Journalen" />;
  }

  if (error) {
    return (
      <div className="rounded-[8px] border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-ink-muted">
        {error}
      </div>
    );
  }

  if (!usage || !chattar) {
    return (
      <div className="flex items-center gap-2 text-sm text-ink-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Hämtar journalen…
      </div>
    );
  }

  const totalTokensIn = usage.dagar.reduce((sum, d) => sum + d.tokens_in, 0);
  const totalTokensUt = usage.dagar.reduce((sum, d) => sum + d.tokens_out, 0);
  const totalKorningar = usage.dagar.reduce((sum, d) => sum + d.korningar + d.korningar_test, 0);
  const { tak, forbrukat_24h } = usage.budget;
  const budgetAndel = tak > 0 ? Math.min(1, forbrukat_24h / tak) : 0;

  return (
    <div className="space-y-8">
      {/* Nyckeltal — 30 dagar */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-card bg-paper p-5">
          <p className="kicker text-mineral">Körningar · 30 dagar</p>
          <p className="mt-2 font-display text-[1.75rem] leading-none">{totalKorningar}</p>
        </div>
        <div className="rounded-card bg-paper p-5">
          <p className="kicker text-mineral">Tokens · 30 dagar</p>
          <p className="mt-2 font-display text-[1.75rem] leading-none">
            {(totalTokensIn + totalTokensUt).toLocaleString("sv-SE")}
          </p>
        </div>
        <div className="rounded-card bg-paper p-5">
          <p className="kicker text-mineral">Uppskattad kostnad · 30 dagar</p>
          <p className="mt-2 font-display text-[1.75rem] leading-none">
            {kr(tokenkostnad(totalTokensIn, totalTokensUt))}
          </p>
          <p className="mt-2 text-xs leading-5 text-ink-subtle">
            Listpris {TOKENKOSTNAD_MODELL} — en uppskattning, inte en faktura.
          </p>
        </div>
      </div>

      {/* Budgetläget — visas bara när ett tak faktiskt är satt */}
      {tak > 0 ? (
        <div className="rounded-card bg-paper p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="kicker text-mineral">Dygnsbudget</p>
            <p className="text-sm text-ink-muted">
              {forbrukat_24h.toLocaleString("sv-SE")} av {tak.toLocaleString("sv-SE")} tokens
              senaste dygnet
            </p>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-ink/10">
            <div
              className={budgetAndel >= 0.8 ? "h-full rounded-full bg-danger" : "h-full rounded-full bg-moss"}
              style={{ width: `${Math.round(budgetAndel * 100)}%` }}
            />
          </div>
          {budgetAndel >= 0.8 ? (
            <p className="mt-2 text-xs leading-5 text-danger">
              Nära taket — vid 100 % pausar agenten tills fönstret rullat vidare.
            </p>
          ) : null}
        </div>
      ) : null}

      {/* Daglig serie */}
      <div>
        <h3 className="kicker text-mineral">Per dag</h3>
        {usage.dagar.length === 0 ? (
          <p className="mt-4 text-sm text-ink-muted">Inga körningar de senaste 30 dagarna.</p>
        ) : (
          <div className="mt-4 divide-y divide-ink/10 overflow-hidden rounded-card bg-paper">
            {usage.dagar.map((dag) => (
              <div
                key={dag.datum}
                className="grid grid-cols-12 items-baseline gap-x-3 px-4 py-3 text-sm"
              >
                <span className="col-span-4 font-mono text-xs text-ink-muted sm:col-span-3">
                  {dag.datum}
                </span>
                <span className="col-span-4 sm:col-span-3">
                  {dag.korningar} körningar
                  {dag.korningar_test > 0 ? (
                    <span className="text-ink-subtle"> (+{dag.korningar_test} test)</span>
                  ) : null}
                </span>
                <span className="col-span-4 text-right font-mono text-xs text-ink-muted sm:col-span-3">
                  {(dag.tokens_in + dag.tokens_out).toLocaleString("sv-SE")} tokens
                </span>
                <span className="col-span-12 text-right font-mono text-xs text-ink-muted sm:col-span-3">
                  {kr(tokenkostnad(dag.tokens_in, dag.tokens_out))}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Eskaleringar/överlämningar */}
      <div>
        <h3 className="kicker text-mineral">Överlämnade samtal</h3>
        {chattar.length === 0 ? (
          <p className="mt-4 text-sm text-ink-muted">
            Inga överlämningar — agenten har hanterat samtalen själv.
          </p>
        ) : (
          <div className="mt-4 divide-y divide-ink/10 overflow-hidden rounded-card bg-paper">
            {chattar.map((rad) => (
              <div
                key={rad.customer_id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-3 text-sm"
              >
                <ShieldAlert className="h-4 w-4 shrink-0 text-danger" aria-hidden />
                <span className="min-w-0 flex-1 truncate font-medium">
                  {rad.customer_name || rad.subject || "Okänd kund"}
                </span>
                {rad.orsak_text ? <Badge tone="neutral">{rad.orsak_text}</Badge> : null}
                {rad.channel ? <Badge tone="neutral">{rad.channel}</Badge> : null}
                {rad.is_test ? <span className="kicker text-mineral">Test</span> : null}
                <Badge tone={rad.aktiv ? "warn" : "good"}>
                  {rad.aktiv ? "Väntar på människa" : "Avslutad"}
                </Badge>
                <span className="font-mono text-xs text-ink-subtle">
                  {datumtid(rad.overlamnad_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
