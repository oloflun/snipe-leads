"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";
import { createDemoLeadsFetch } from "@/lib/demo/leads-controls";
import { felmeddelande, readJsonBody } from "@/lib/http/json";

/**
 * Kundens kontroller över leads-agenten: hur långt den får gå, vem den ska
 * leta efter, och vad som väntar på godkännande.
 *
 * Operate mode. Ruled ledger, inte kort. Inga modaler — en granskningskö är
 * exakt det fall där en modal gör arbetet långsammare: man godkänner tio
 * utkast i rad, och tio modaler är tjugo extra klick.
 *
 * Gränsen mot SOUL skrivs ut i UI:t, inte bara i koden: SOUL styr ton, ICP
 * styr urval. Utan den raden hamnar urvalskriterier i röstdokumentet.
 */

type Autonomy = "draft" | "first_contact" | "meeting";

type Config = {
  autonomy: Autonomy;
  autonomy_description: string;
  autonomy_levels: { value: Autonomy; description: string }[];
  icp: {
    industries: string[];
    exclude_industries: string[];
    geography: string[];
    roles: string[];
    must_have: string[];
    deal_breakers: string[];
    company_size: { min: number | null; max: number | null };
  };
};

type QueueItem = {
  id: string;
  subject?: string | null;
  body?: string | null;
  prospect_email?: string | null;
  scheduled_at?: string | null;
};

const AUTONOMY_LABEL: Record<Autonomy, string> = {
  draft: "Bara utkast",
  first_contact: "Första kontakten",
  meeting: "Till bokat möte"
};

const ICP_FIELDS: { key: keyof Config["icp"]; label: string; hint: string }[] = [
  { key: "industries", label: "Branscher", hint: "Bygg, tillverkning, logistik" },
  { key: "exclude_industries", label: "Undvik branscher", hint: "Bemanning, spel" },
  { key: "geography", label: "Stad, län, region", hint: "Göteborg, Skåne, Västra Götaland" },
  { key: "roles", label: "Roller", hint: "VD, inköpschef, platschef" },
  { key: "must_have", label: "Krävs", hint: "Egen produktion, växer" },
  { key: "deal_breakers", label: "Diskvalificerar", hint: "Under 10 anställda" }
];

function asList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * `demo` byter ut backend-anropen mot exempeldata i webbläsaren. Se
 * lib/demo/leads-controls.ts för skälet — grinden mot den riktiga backenden
 * står kvar orörd, det är indatan som byts.
 */
export function LeadsControls({ demo = false }: Readonly<{ demo?: boolean }>) {
  const [config, setConfig] = useState<Config | null>(null);
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // En instans per monterad vy, så att ändringar i demon består mellan anrop.
  const demoFetch = useRef<ReturnType<typeof createDemoLeadsFetch> | null>(null);
  if (demo && !demoFetch.current) {
    demoFetch.current = createDemoLeadsFetch();
  }

  /** Samma signatur som fetch, så anropsplatserna nedan är identiska i båda lägena. */
  const call = useCallback(
    (path: string, init?: RequestInit): Promise<Response> =>
      demo && demoFetch.current ? demoFetch.current(path, init) : fetch(path, init),
    [demo]
  );

  const load = useCallback(async () => {
    setError(null);
    try {
      const [configResponse, queueResponse] = await Promise.all([
        call("/api/snajp-support/leads/config", { cache: "no-store" }),
        call("/api/snajp-support/leads/queue", { cache: "no-store" })
      ]);
      if (!configResponse.ok) {
        const body = await readJsonBody<{ error?: string }>(configResponse).catch(() => null);
        throw new Error(
          body?.error ?? `Kunde inte hämta inställningarna (${configResponse.status}).`
        );
      }
      const laddadConfig = await readJsonBody<Config>(configResponse);
      if (laddadConfig) {
        setConfig(laddadConfig);
      }
      // Kön är inte kritisk för vyn — en trasig kropp ska inte fälla
      // inställningarna som redan lästs.
      const koSvar = queueResponse.ok
        ? await readJsonBody<{ items?: QueueItem[] }>(queueResponse).catch(() => null)
        : null;
      setQueue(koSvar?.items ?? []);
    } catch (cause) {
      setError(felmeddelande(cause));
      setQueue([]);
    }
  }, [call]);

  useEffect(() => {
    void load();
  }, [load]);

  function save(patch: Record<string, unknown>) {
    setError(null);
    setMessage(null);
    startTransition(async () => {
      // call() är fetch och kastar vid nätverksfel. Utan fångsten dog
      // transitionen tyst — knappen kom tillbaka och ingenting sa varför.
      try {
        const response = await call("/api/snajp-support/leads/config", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(patch)
        });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          setError(body.error ?? `Sparningen misslyckades (${response.status}).`);
          return;
        }
        setMessage("Sparat.");
        await load();
      } catch (cause) {
        setError(felmeddelande(cause));
      }
    });
  }

  function decide(itemId: string, action: "approve" | "reject") {
    setError(null);
    setMessage(null);
    startTransition(async () => {
      try {
        const response = await call(`/api/snajp-support/leads/queue/${itemId}/${action}`, {
          method: "POST"
        });
        if (!response.ok) {
          setError(`Åtgärden misslyckades (${response.status}).`);
          return;
        }
        await load();
      } catch (cause) {
        setError(felmeddelande(cause));
      }
    });
  }

  if (!config) {
    // Ett fel är INTE ett laddningstillstånd. Skelettet låg kvar och pulserade
    // under felmeddelandet, så ytan såg samtidigt ut att ladda och ha
    // misslyckats — och skelettet lovar dessutom innehåll som aldrig kommer.
    // Sett i pixlar vid 375px.
    if (error) {
      return (
        <p role="alert" className="break-words border-t border-ink/15 pt-6 text-[14px] text-danger">
          {error}
        </p>
      );
    }
    return (
      <div className="grid gap-px">
        {[0, 1, 2, 3].map((row) => (
          <div key={row} className="h-16 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-12">
      <section>
        <h3 className="kicker text-mineral">Hur långt agenterna får gå</h3>

        <div className="mt-5 flex min-w-0 flex-wrap gap-3">
          {config.autonomy_levels.map((level) => (
            <button
              key={level.value}
              type="button"
              disabled={isPending}
              aria-pressed={config.autonomy === level.value}
              onClick={() => save({ autonomy: level.value })}
              className={
                config.autonomy === level.value
                  ? "border border-ochre bg-ochre/10 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-ink disabled:opacity-60"
                  : "border border-ink/15 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-mineral transition hover:border-ochre hover:text-ochre disabled:opacity-60"
              }
            >
              {AUTONOMY_LABEL[level.value]}
            </button>
          ))}
        </div>

        {/* Raden som säger vad valet BETYDER. Utan den är det tre ord som
            låter lika, och kunden väljer det som låter mest kapabelt. */}
        <p className="mt-4 max-w-[64ch] text-[15px] leading-7">{config.autonomy_description}</p>
      </section>

      <section className="border-t border-ink/15 pt-8">
        <h3 className="kicker text-mineral">Målgrupp</h3>
        <p className="mt-3 max-w-[64ch] text-[15px] leading-7 text-mineral">
          <strong className="font-semibold text-ink">Er röst styr tonen, målgruppen styr urvalet.</strong>{" "}
          Det här avgör vilka bolag agenterna bearbetar — inte hur de låter. Skriv
          med komma emellan.
        </p>

        <form
          className="mt-6 grid gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            save({
              icp: {
                ...Object.fromEntries(
                  ICP_FIELDS.map((field) => [field.key, asList(String(form.get(field.key) ?? ""))])
                ),
                company_size: {
                  min: form.get("size_min") ? Number(form.get("size_min")) : null,
                  max: form.get("size_max") ? Number(form.get("size_max")) : null
                }
              }
            });
          }}
        >
          {ICP_FIELDS.map((field) => (
            <label key={field.key} className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
              <span className="kicker col-span-12 text-mineral md:col-span-3">{field.label}</span>
              <input
                name={field.key}
                defaultValue={(config.icp[field.key] as string[]).join(", ")}
                placeholder={field.hint}
                className="col-span-12 mt-3 h-12 min-w-0 border border-ink/15 bg-paper2/70 px-4 outline-none focus:border-ochre md:col-span-9 md:mt-0"
              />
            </label>
          ))}

          <div className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
            <span className="kicker col-span-12 text-mineral md:col-span-3">Anställda</span>
            <div className="col-span-12 mt-3 flex min-w-0 flex-wrap items-center gap-3 md:col-span-9 md:mt-0">
              <input
                name="size_min"
                type="number"
                min={0}
                defaultValue={config.icp.company_size.min ?? ""}
                placeholder="från"
                className="h-12 w-28 min-w-0 border border-ink/15 bg-paper2/70 px-4 outline-none focus:border-ochre"
              />
              <span className="text-mineral" aria-hidden>
                –
              </span>
              <input
                name="size_max"
                type="number"
                min={0}
                defaultValue={config.icp.company_size.max ?? ""}
                placeholder="till"
                className="h-12 w-28 min-w-0 border border-ink/15 bg-paper2/70 px-4 outline-none focus:border-ochre"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isPending}
              className="h-12 bg-ink px-5 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink disabled:opacity-60"
            >
              {isPending ? "Sparar..." : "Spara målgrupp"}
            </button>
          </div>
        </form>
      </section>

      <section className="border-t border-ink/15 pt-8">
        <h3 className="kicker text-mineral">Väntar på dig</h3>

        {queue === null ? (
          <div className="mt-5 h-16 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
        ) : queue.length === 0 ? (
          <p className="mt-5 border-t border-ink/15 pt-5 text-[15px] text-mineral">
            Inget väntar på granskning just nu.
          </p>
        ) : (
          <ul className="mt-5">
            {queue.map((item) => (
              <li key={item.id} className="min-w-0 border-t border-ink/15 py-5">
                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                  <span className="min-w-0 break-words text-[17px]">
                    {item.subject || "Utan ämnesrad"}
                  </span>
                  <span className="kicker shrink-0 text-mineral">
                    {item.prospect_email ?? "okänd mottagare"}
                  </span>
                </div>

                {item.body ? (
                  <p className="mt-3 max-w-[70ch] whitespace-pre-line text-[15px] leading-7 text-ink/75">
                    {item.body}
                  </p>
                ) : null}

                {/* Inline, inte i en modal. Man godkänner tio i rad. */}
                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    type="button"
                    disabled={isPending}
                    onClick={() => decide(item.id, "approve")}
                    className="border border-ink px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] transition hover:bg-ink hover:text-paper disabled:opacity-60"
                  >
                    Godkänn
                  </button>
                  <button
                    type="button"
                    disabled={isPending}
                    onClick={() => decide(item.id, "reject")}
                    className="border border-ink/15 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-mineral transition hover:border-danger hover:text-danger disabled:opacity-60"
                  >
                    Avvisa
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {error ? (
        <p role="alert" className="break-words text-[14px] text-danger">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="break-words text-[14px] text-moss">
          {message}
        </p>
      ) : null}
    </div>
  );
}
