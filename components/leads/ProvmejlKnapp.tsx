"use client";

import { Loader2, Mail } from "lucide-react";
import { useId, useState } from "react";
import { btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Skicka provmejl (Sebbe 2026-10-09: "vi vill se hur utskicken ser ut").
 *
 * Skickar utkastet, eller ett redan skickat mejl, till kundens EGEN adress
 * så som leadet får det: HTML-delen med signaturens logotyp, avsändaren och
 * svarsadressen. Backend: POST /api/leads/provmejl
 * (snajp-support/app/leads/provmejl.py). Adresserna kommer ur
 * GET /api/leads/provmejl/mottagare: kopplade brevlådor, signaturens e-post
 * och faktureringsmejlet. Någon annan adress går inte att välja, så knappen
 * är aldrig en väg förbi sändspärrarna. Kön, leadet och Skickat rörs inte.
 */

const T = {
  knapp: { sv: "Skicka provmejl", en: "Send test email" },
  till: { sv: "Skicka provet till", en: "Send the test to" },
  skicka: { sv: "Skicka", en: "Send" },
  avbryt: { sv: "Avbryt", en: "Cancel" },
  laddar: { sv: "Hämtar era adresser …", en: "Loading your addresses …" },
  inga: {
    sv: "Det finns ingen egen adress att skicka provet till. Koppla en brevlåda eller fyll i e-post i signaturen under Inställningar.",
    en: "There is no address of your own to send the test to. Connect a mailbox or add an email to the signature under Settings."
  },
  forklaring: {
    sv: "Provet går bara till er, precis som leadet skulle få det. Utkastet och leadet påverkas inte.",
    en: "The test only goes to you, exactly as the lead would receive it. The draft and the lead are not affected."
  },
  utanFot: {
    sv: "Obs: sidfoten med organisationsnummer och adress saknas, så det riktiga utskicket stoppas. Fyll i dem under Kunder & Data.",
    en: "Note: the footer with company number and address is missing, so the real send is blocked. Add them under Customers & Data."
  },
  ejEgen: {
    sv: "Provmejl går bara till era egna adresser.",
    en: "Test emails can only go to your own addresses."
  },
  avstangt: {
    sv: "Utskick är inte påslagna i den här miljön, så provet kan inte levereras.",
    en: "Sending is not switched on in this environment, so the test cannot be delivered."
  },
  saknas: { sv: "Mejlet finns inte längre.", en: "The email no longer exists." }
} satisfies Record<string, Localized>;

let adresser: Promise<string[]> | null = null;

/** Adresserna hämtas en gång per sidvisning och delas av alla knappar. */
function hamtaAdresser(): Promise<string[]> {
  adresser ??= fetch("/api/snajp-support/leads/provmejl/mottagare")
    .then(async (r) => (r.ok ? ((await readJsonBody<{ mottagare?: string[] }>(r))?.mottagare ?? []) : []))
    .catch(() => [])
    .then((lista) => {
      if (lista.length === 0) adresser = null;
      return lista;
    });
  return adresser;
}

export function ProvmejlKnapp({
  queueItemId,
  messageId,
  fore,
  className
}: Readonly<{
  queueItemId?: string | null;
  messageId?: string | null;
  /** Körs före sändningen, t.ex. för att spara en osparad redigering.
   *  false avbryter. */
  fore?: () => Promise<boolean>;
  className?: string;
}>) {
  const { text } = useLocale();
  const id = useId();
  const [oppen, setOppen] = useState(false);
  const [lista, setLista] = useState<string[] | null>(null);
  const [vald, setVald] = useState("");
  const [skickar, setSkickar] = useState(false);
  const [besked, setBesked] = useState<{ ton: "ok" | "fel"; text: Localized; extra?: Localized } | null>(null);

  if (!queueItemId && !messageId) return null;

  async function oppna() {
    setOppen(true);
    setBesked(null);
    const hamtade = await hamtaAdresser();
    setLista(hamtade);
    setVald((v) => v || hamtade[0] || "");
  }

  async function skicka() {
    if (!vald) return;
    setSkickar(true);
    setBesked(null);
    try {
      if (fore && !(await fore())) return;
      const response = await fetch("/api/snajp-support/leads/provmejl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ till: vald, queue_item_id: queueItemId ?? null, message_id: messageId ?? null })
      });
      const svar = await readJsonBody<{ till?: string; saknar_fot?: boolean; detail?: unknown }>(response);
      if (response.ok) {
        const till = svar?.till ?? vald;
        setBesked({
          ton: "ok",
          text: { sv: `Provmejlet är skickat till ${till}.`, en: `The test email was sent to ${till}.` },
          extra: svar?.saknar_fot ? T.utanFot : undefined
        });
        setOppen(false);
        return;
      }
      const detalj = typeof svar?.detail === "string" ? svar.detail : `status ${response.status}`;
      const fel: Localized =
        response.status === 403
          ? T.ejEgen
          : response.status === 503
            ? T.avstangt
            : response.status === 404
              ? T.saknas
              : { sv: `Provmejlet kunde inte skickas (${detalj}).`, en: `The test email could not be sent (${detalj}).` };
      setBesked({ ton: "fel", text: fel });
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setBesked({ ton: "fel", text: { sv: m, en: m } });
    } finally {
      setSkickar(false);
    }
  }

  return (
    <div className={cn("min-w-0", className)}>
      {oppen ? (
        <div className="rounded-card border border-ink/12 bg-paper px-3 py-3">
          {lista === null ? (
            <p className="flex items-center gap-2 text-[0.8125rem] text-ink-muted">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              {text(T.laddar)}
            </p>
          ) : lista.length === 0 ? (
            <p className="text-[0.8125rem] text-ink-muted">{text(T.inga)}</p>
          ) : (
            <div className="flex flex-wrap items-end gap-2">
              <label htmlFor={id} className="flex min-w-0 flex-col gap-1 text-[0.8125rem] text-ink-muted">
                {text(T.till)}
                <select
                  id={id}
                  value={vald}
                  onChange={(e) => setVald(e.target.value)}
                  className="focus-ring min-h-9 max-w-full rounded-input border border-ink/20 bg-paper px-2 text-[0.875rem] text-ink"
                >
                  {lista.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={skickar || !vald}
                onClick={() => void skicka()}
                className={cn(btnPrimary, btnLiten)}
              >
                {skickar ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Mail className="h-4 w-4" aria-hidden />}
                {text(T.skicka)}
              </button>
              <button type="button" disabled={skickar} onClick={() => setOppen(false)} className={cn(btnSecondary, btnLiten)}>
                {text(T.avbryt)}
              </button>
            </div>
          )}
          <p className="mt-2 text-[0.75rem] text-ink-subtle">{text(T.forklaring)}</p>
        </div>
      ) : (
        <button type="button" onClick={() => void oppna()} className={cn(btnSecondary, btnLiten)}>
          <Mail className="h-4 w-4" aria-hidden />
          {text(T.knapp)}
        </button>
      )}
      {besked ? (
        <p
          role={besked.ton === "fel" ? "alert" : "status"}
          className={cn("mt-2 text-[0.8125rem]", besked.ton === "fel" ? "text-danger" : "text-ink-muted")}
        >
          {text(besked.text)}
          {besked.extra ? <span className="mt-1 block text-ink">{text(besked.extra)}</span> : null}
        </p>
      ) : null}
    </div>
  );
}
