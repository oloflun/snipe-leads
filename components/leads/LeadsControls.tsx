"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";
import { createDemoLeadsFetch } from "@/lib/demo/leads-controls";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { icpEtiketter } from "@/lib/leads/icpLabels";
import { useLocale, type Localized } from "@/lib/i18n";
import { btnLiten, btnPrimary, btnSecondary, etikett, meta, rubrikPanel, flik, flikAktiv, flikInaktiv, fliklista } from "@/components/ui";
import { cn } from "@/lib/utils";

/** Formulärfält i målgruppen: husets fält, inte de fyrkantiga plattorna i 48 px
 *  med spärrade mono-etiketter som stod här före 2026-10-03. */
const FALT =
  "focus-ring h-10 rounded-input border border-ink/15 bg-paper px-3 text-[1rem] text-ink outline-none hover:border-ink/30 [@media(pointer:fine)]:text-[0.9375rem]";

function somText(cause: unknown): Localized {
  const m = felmeddelande(cause);
  return { sv: m, en: m };
}

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

type Autonomy = "draft" | "first_contact" | "meeting" | "auto_send";

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

const AUTONOMY_LABEL: Record<Autonomy, Localized> = {
  draft: { sv: "Bara utkast", en: "Drafts only" },
  first_contact: { sv: "Första kontakten", en: "First contact" },
  meeting: { sv: "Till bokat möte", en: "Up to a booked meeting" },
  // Backenden returnerar redan nivån i autonomy_levels (se app/leads/autonomy.py
  // LEVELS), fjärde knappen renderade "undefined" som etikett innan den här
  // raden fanns. Grinden (kan_aktivera_auto_send) sitter i backendens PUT och
  // rörs inte här: knappen går fortfarande att trycka, men sparningen avvisas
  // med ett läsbart 422-fel om målgrupp, produktbeskrivning eller
  // avsändardomän saknas.
  auto_send: { sv: "Skickar automatiskt", en: "Sends automatically" }
};

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
 *
 * `visaKo` döljer "Väntar på dig"-kön. Iris › Inställningar visar kön i
 * Granskning i stället (se IrisGranskning.tsx) — dubblerad här blir den en
 * andra, äldre kö som glider isär från den riktiga.
 */
export function LeadsControls({
  demo = false,
  visaKo = true
}: Readonly<{ demo?: boolean; visaKo?: boolean }>) {
  const { locale, text } = useLocale();
  const etiketter = icpEtiketter(locale);
  const ICP_FIELDS: { key: keyof Config["icp"]; label: string; hint: string }[] = [
    { key: "industries", ...etiketter.industries },
    { key: "exclude_industries", ...etiketter.exclude_industries },
    { key: "geography", ...etiketter.geography },
    { key: "roles", ...etiketter.roles },
    { key: "must_have", ...etiketter.must_have },
    { key: "deal_breakers", ...etiketter.deal_breakers }
  ];
  const [config, setConfig] = useState<Config | null>(null);
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<Localized | null>(null);
  const [message, setMessage] = useState<Localized | null>(null);
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
        visaKo ? call("/api/snajp-support/leads/queue", { cache: "no-store" }) : null
      ]);
      if (!configResponse.ok) {
        const body = await readJsonBody<{ error?: string }>(configResponse).catch(() => null);
        setError(
          body?.error
            ? { sv: body.error, en: body.error }
            : {
                sv: `Kunde inte hämta inställningarna (${configResponse.status}).`,
                en: `Could not fetch the settings (${configResponse.status}).`
              }
        );
        setQueue([]);
        return;
      }
      const laddadConfig = await readJsonBody<Config>(configResponse);
      if (laddadConfig) {
        setConfig(laddadConfig);
      }
      // Kön är inte kritisk för vyn — en trasig kropp ska inte fälla
      // inställningarna som redan lästs. Utan visaKo hämtas den inte alls.
      const koSvar = queueResponse?.ok
        ? await readJsonBody<{ items?: QueueItem[] }>(queueResponse).catch(() => null)
        : null;
      setQueue(visaKo ? (koSvar?.items ?? []) : []);
    } catch (cause) {
      setError(somText(cause));
      setQueue([]);
    }
  }, [call, visaKo]);

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
          setError(
            body.error
              ? { sv: body.error, en: body.error }
              : {
                  sv: `Sparningen misslyckades (${response.status}).`,
                  en: `Saving failed (${response.status}).`
                }
          );
          return;
        }
        setMessage({ sv: "Sparat.", en: "Saved." });
        await load();
      } catch (cause) {
        setError(somText(cause));
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
          setError({
            sv: `Åtgärden misslyckades (${response.status}).`,
            en: `The action failed (${response.status}).`
          });
          return;
        }
        await load();
      } catch (cause) {
        setError(somText(cause));
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
          {text(error)}
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
        <h2 className={rubrikPanel}>{text({ sv: "Hur långt agenterna får gå", en: "How far the agents may go" })}</h2>

        <div className={cn("mt-3", fliklista)}>
          {config.autonomy_levels.map((level) => (
            <button
              key={level.value}
              type="button"
              disabled={isPending}
              aria-pressed={config.autonomy === level.value}
              onClick={() => save({ autonomy: level.value })}
              className={cn(flik, "disabled:opacity-60", config.autonomy === level.value ? flikAktiv : flikInaktiv)}
            >
              {text(AUTONOMY_LABEL[level.value])}
            </button>
          ))}
        </div>

        {/* Raden som säger vad valet BETYDER. Utan den är det tre ord som
            låter lika, och kunden väljer det som låter mest kapabelt. */}
        <p className="mt-4 max-w-[64ch] text-[0.9375rem] leading-7 text-ink-muted">{config.autonomy_description}</p>
      </section>

      <section className="border-t border-ink/15 pt-8">
        <h2 className={rubrikPanel}>{text({ sv: "Målgrupp", en: "Target group" })}</h2>
        <p className="mt-2 text-[0.9375rem] leading-7 text-ink-muted">
          {text({ sv: "Styr urvalet, inte tonen. Separera med komma.", en: "Steers the selection, not the tone. Separate with commas." })}
        </p>

        <form
          className="mt-5 grid gap-4"
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
            <label key={field.key} className="grid grid-cols-12 items-center gap-x-6 border-t border-ink/12 pt-4">
              <span className={cn(etikett, "col-span-12 md:col-span-3")}>{field.label}</span>
              <input
                name={field.key}
                defaultValue={(config.icp[field.key] as string[]).join(", ")}
                placeholder={field.hint}
                className={cn(FALT, "col-span-12 mt-2 min-w-0 md:col-span-9 md:mt-0")}
              />
            </label>
          ))}

          <div className="grid grid-cols-12 items-center gap-x-6 border-t border-ink/12 pt-4">
            <span className={cn(etikett, "col-span-12 md:col-span-3")}>{text({ sv: "Anställda", en: "Employees" })}</span>
            <div className="col-span-12 mt-3 flex min-w-0 flex-wrap items-center gap-3 md:col-span-9 md:mt-0">
              <input
                name="size_min"
                type="number"
                min={0}
                defaultValue={config.icp.company_size.min ?? ""}
                placeholder={text({ sv: "från", en: "from" })}
                className={cn(FALT, "w-28 min-w-0")}
              />
              <span className="text-mineral" aria-hidden>
                –
              </span>
              <input
                name="size_max"
                type="number"
                min={0}
                defaultValue={config.icp.company_size.max ?? ""}
                placeholder={text({ sv: "till", en: "to" })}
                className={cn(FALT, "w-28 min-w-0")}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isPending}
              className={btnPrimary}
            >
              {isPending ? text({ sv: "Sparar...", en: "Saving..." }) : text({ sv: "Spara målgrupp", en: "Save target group" })}
            </button>
          </div>
        </form>
      </section>

      {visaKo ? (
      <section className="border-t border-ink/15 pt-8">
        <h2 className={rubrikPanel}>{text({ sv: "Väntar på dig", en: "Waiting for you" })}</h2>

        {queue === null ? (
          <div className="mt-5 h-16 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
        ) : queue.length === 0 ? (
          <p className="mt-5 border-t border-ink/15 pt-5 text-[15px] text-mineral">
            {text({ sv: "Inget väntar på granskning.", en: "Nothing is waiting for review." })}
          </p>
        ) : (
          <ul className="mt-5">
            {queue.map((item) => (
              <li key={item.id} className="min-w-0 border-t border-ink/15 py-5">
                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                  <span className="min-w-0 break-words text-[17px]">
                    {item.subject || text({ sv: "Utan ämnesrad", en: "No subject line" })}
                  </span>
                  <span className={cn(meta, "shrink-0")}>
                    {item.prospect_email ?? text({ sv: "okänd mottagare", en: "unknown recipient" })}
                  </span>
                </div>

                {item.body ? (
                  <p className="mt-3 max-w-[70ch] whitespace-pre-line text-[15px] leading-7 text-ink-muted">
                    {item.body}
                  </p>
                ) : null}

                {/* Inline, inte i en modal. Man godkänner tio i rad. */}
                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    type="button"
                    disabled={isPending}
                    onClick={() => decide(item.id, "approve")}
                    className={cn(btnPrimary, btnLiten)}
                  >
                    {text({ sv: "Godkänn", en: "Approve" })}
                  </button>
                  <button
                    type="button"
                    disabled={isPending}
                    onClick={() => decide(item.id, "reject")}
                    className={cn(btnSecondary, btnLiten)}
                  >
                    {text({ sv: "Avvisa", en: "Reject" })}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
      ) : null}

      {error ? (
        <p role="alert" className="break-words text-[14px] text-danger">
          {text(error)}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="break-words text-[14px] text-moss">
          {text(message)}
        </p>
      ) : null}
    </div>
  );
}
