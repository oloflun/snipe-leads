"use client";

import { useCallback, useEffect, useState } from "react";

// Abonnemang och förbrukning för den inloggade organisationen.
//
// Siffrorna kommer från backendens ss_usage — samma källa som kvotkontrollen
// använder när den blockerar. Det som visas här är alltså det som faktiskt
// gäller, inte en separat uppskattning som kan hamna i otakt.

type Plan = {
  id: string;
  name: string;
  monthly_responses: number | null;
  description: string;
};

type Subscription = {
  plan: Plan;
  status: string;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
  stripe_customer_id: string | null;
  quota: {
    used: number;
    cap: number | null;
    remaining: number | null;
    ratio: number;
    warn: boolean;
    exceeded: boolean;
    degraded?: boolean;
  };
};

const STATUS_LABELS: Record<string, string> = {
  none: "Inget abonnemang",
  trialing: "Provperiod",
  active: "Aktivt",
  past_due: "Betalning misslyckades",
  canceled: "Avslutat",
  unpaid: "Obetalt",
  incomplete: "Ofullständigt"
};

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body?.error ?? `Något gick fel (${response.status}).`;
  } catch {
    return `Något gick fel (${response.status}).`;
  }
}

export function BillingPanel() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [subResponse, planResponse] = await Promise.all([
        fetch("/api/snajp-support/billing/subscription"),
        fetch("/api/snajp-support/billing/plans")
      ]);
      if (!subResponse.ok) {
        setError(await readError(subResponse));
        return;
      }
      setSubscription(await subResponse.json());
      if (planResponse.ok) {
        setPlans((await planResponse.json()).plans ?? []);
      }
      setError(null);
    } catch {
      setError("Kunde inte nå tjänsten. Försök igen om en stund.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function go(path: string, body?: unknown, label?: string) {
    setBusy(label ?? path);
    setError(null);
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined
      });
      if (!response.ok) {
        setError(await readError(response));
        return;
      }
      const { url } = await response.json();
      if (url) {
        window.location.href = url;
      }
    } catch {
      setError("Kunde inte starta betalflödet.");
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return <p className="text-[15px] text-ink/62">Hämtar abonnemang…</p>;
  }

  const quota = subscription?.quota;
  const cap = quota?.cap ?? null;
  const percent = cap ? Math.min(Math.round((quota!.used / cap) * 100), 100) : 0;

  return (
    <div className="grid gap-8">
      {error ? (
        <p className="border-l-2 border-ochre pl-4 text-[15px] leading-7 text-ink/80">{error}</p>
      ) : null}

      {subscription ? (
        <div className="border-t border-ink/15 pt-4">
          <p className="kicker text-mineral">Nuvarande nivå</p>
          <p className="mt-2 text-[22px]">{subscription.plan.name}</p>
          <p className="mt-1 text-[14px] text-ink/62">
            {STATUS_LABELS[subscription.status] ?? subscription.status}
            {subscription.cancel_at_period_end ? " · avslutas vid periodens slut" : ""}
          </p>

          <div className="mt-6">
            <p className="kicker text-mineral">AI-svar denna period</p>
            {cap === null ? (
              <p className="mt-2 text-[15px]">{quota?.used ?? 0} svar · obegränsat</p>
            ) : (
              <>
                <p className="mt-2 text-[15px]">
                  {quota?.used ?? 0} av {cap} svar
                </p>
                <div
                  className="mt-3 h-2 w-full max-w-md bg-ink/10"
                  role="progressbar"
                  aria-valuenow={percent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Förbrukning av månadens AI-svar"
                >
                  <div
                    className={`h-2 ${quota?.exceeded ? "bg-ochre" : "bg-ink"}`}
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </>
            )}

            {quota?.exceeded ? (
              <p className="mt-4 max-w-[60ch] border-l-2 border-ochre pl-4 text-[15px] leading-7">
                Kvoten är förbrukad. Agenten svarar inte automatiskt just nu — inkommande
                ärenden tas emot och lämnas över till er i stället. Uppgradera för att
                sätta igång den igen.
              </p>
            ) : quota?.warn ? (
              <p className="mt-4 max-w-[60ch] border-l-2 border-ochre pl-4 text-[15px] leading-7">
                Ni har använt {percent} % av månadens svar. Vid 100 % pausas de automatiska
                svaren tills nästa period, eller tills ni uppgraderar.
              </p>
            ) : null}

            {quota?.degraded ? (
              <p className="mt-4 text-[14px] text-ink/62">
                Förbrukningen kunde inte läsas just nu, så siffran kan vara inaktuell.
                Agenten fortsätter svara.
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="border-t border-ink/15 pt-4">
        <p className="kicker text-mineral">Byt nivå</p>
        <div className="mt-4 grid grid-cols-12 gap-x-8 gap-y-6">
          {plans.map((plan) => {
            const current = plan.id === subscription?.plan.id;
            return (
              <div key={plan.id} className="col-span-12 border-t border-ink/15 pt-4 md:col-span-4">
                <p className="text-[18px]">{plan.name}</p>
                <p className="mt-1 text-[14px] text-ink/62">
                  {plan.monthly_responses === null
                    ? "Obegränsat"
                    : `${plan.monthly_responses} AI-svar/månad`}
                </p>
                <p className="mt-2 text-[14px] leading-6 text-ink/62">{plan.description}</p>
                <button
                  type="button"
                  disabled={current || busy !== null}
                  onClick={() => go("/api/billing/checkout", { plan: plan.id }, plan.id)}
                  className="mt-4 inline-flex items-center border border-ink/15 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] transition hover:border-ochre hover:text-ochre disabled:opacity-40"
                >
                  {current ? "Nuvarande" : busy === plan.id ? "Öppnar…" : "Välj"}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {subscription?.stripe_customer_id ? (
        <div className="border-t border-ink/15 pt-4">
          <p className="kicker text-mineral">Fakturor och betalsätt</p>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => go("/api/billing/portal", undefined, "portal")}
            className="mt-4 inline-flex items-center gap-3 bg-ink px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink disabled:opacity-60"
          >
            {busy === "portal" ? "Öppnar…" : "Hantera abonnemang"}
            <span aria-hidden>↗</span>
          </button>
        </div>
      ) : null}
    </div>
  );
}
