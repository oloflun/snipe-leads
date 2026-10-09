"use client";

import { Loader2, Send, Trash2, RefreshCw, X } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import { btnLiten, btnPrimary, btnSecondary, meta } from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export type Utskick = {
  id: string;
  bolag: string | null;
  mottagare: string | null;
  amne: string | null;
  /** Första meningen i mejlet, så att man ser vad som går ut (kritik 4). */
  utdrag?: string | null;
};

export type Bekraftelsetyp = "skicka" | "avvisa" | "ta-bort" | "skapa-om";

const TEXT: Record<Bekraftelsetyp, { rubrik: (n: number) => Localized; knapp: (n: number) => Localized; forklaring: Localized | null }> = {
  skicka: {
    rubrik: (n) => ({ sv: `${n} mejl godkänns och skickas till:`, en: `${n} ${n === 1 ? "email is" : "emails are"} approved and sent to:` }),
    knapp: (n) => ({ sv: `Skicka ${n} mejl`, en: `Send ${n} ${n === 1 ? "email" : "emails"}` }),
    forklaring: {
      sv: "Varje mejl går genom sändspärrarna; utanför vardagar 08–16 skickas det när fönstret öppnar.",
      en: "Every email passes the send guards; outside weekdays 08–16 it goes out when the window opens."
    }
  },
  avvisa: {
    rubrik: (n) => ({ sv: `${n} utkast avvisas och skickas aldrig:`, en: `${n} ${n === 1 ? "draft is" : "drafts are"} rejected and never sent:` }),
    knapp: (n) => ({ sv: `Avvisa ${n} utkast`, en: `Reject ${n} ${n === 1 ? "draft" : "drafts"}` }),
    forklaring: null
  },
  "ta-bort": {
    rubrik: (n) => ({ sv: `${n} ${n === 1 ? "lead" : "leads"} tas bort för gott:`, en: `${n} ${n === 1 ? "lead is" : "leads are"} deleted for good:` }),
    knapp: (n) => ({ sv: `Ta bort ${n} ${n === 1 ? "lead" : "leads"}`, en: `Delete ${n} ${n === 1 ? "lead" : "leads"}` }),
    forklaring: {
      sv: "Det går inte att ångra. Leads som redan fått mejl tas inte bort; arkivera dem i stället.",
      en: "This cannot be undone. Leads that have already been emailed are not deleted; archive them instead."
    }
  },
  "skapa-om": {
    rubrik: (n) => ({ sv: `Utkasten skrivs om för ${n} ${n === 1 ? "lead" : "leads"}:`, en: `The drafts are rewritten for ${n} ${n === 1 ? "lead" : "leads"}:` }),
    knapp: (n) => ({ sv: `Skriv om ${n} utkast`, en: `Rewrite ${n} drafts` }),
    forklaring: {
      sv: "Väntande och godkända utkast ersätts och skickas aldrig.",
      en: "Waiting and approved drafts are replaced and never sent."
    }
  }
};

/**
 * EN bekräftelse för varje massåtgärd, på sidan och aldrig i webbläsarens
 * confirm-ruta (impeccable-kritik 3 och 4, Sebbes val "en bekräftelse för
 * allt"): skicka, avvisa, ta bort och skriv om. Varje berört bolag står
 * listat, vid utskick med ämnesrad och mejlets första mening, och knappen
 * säger exakt vad som händer.
 *
 * Tillgänglig som en dialog utan att låsa sidan: den tar fokus när den
 * öppnas (och annonseras därmed), Esc stänger, och fokus går tillbaka till
 * knappen man kom från.
 */
export function BekraftaUtskick({
  poster,
  typ = "skicka",
  overhoppade = 0,
  upptagen = false,
  tillagg,
  onBekrafta,
  onAvbryt
}: Readonly<{
  poster: Utskick[];
  typ?: Bekraftelsetyp;
  /** Markerade som inte berörs (inget väntande utkast) och hoppas över. */
  overhoppade?: number;
  upptagen?: boolean;
  /** Ett val eller en upplysning som hör till åtgärden, före förklaringen. */
  tillagg?: React.ReactNode;
  onBekrafta: () => void;
  onAvbryt: () => void;
}>) {
  const { text } = useLocale();
  const n = poster.length;
  const t = TEXT[typ];
  const rubrikId = useId();
  const ref = useRef<HTMLElement>(null);
  const avbryt = useRef(onAvbryt);
  avbryt.current = onAvbryt;

  useEffect(() => {
    const forra = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    ref.current?.focus();
    return () => {
      // Tillbaka till knappen man kom från, om den finns kvar.
      if (forra && document.contains(forra)) forra.focus();
    };
  }, []);

  const Ikon = typ === "ta-bort" ? Trash2 : typ === "avvisa" ? X : typ === "skapa-om" ? RefreshCw : Send;
  return (
    <section
      ref={ref}
      role="alertdialog"
      aria-modal="false"
      aria-labelledby={rubrikId}
      tabIndex={-1}
      onKeyDown={(e) => {
        if (e.key === "Escape" && !upptagen) {
          e.stopPropagation();
          avbryt.current();
        }
      }}
      className="focus-ring rounded-input border border-ink/15 bg-paper2 px-4 py-3"
    >
      <p id={rubrikId} className="text-[0.9375rem] font-medium text-ink">
        {text(t.rubrik(n))}
      </p>
      <ul className="thin-scrollbar mt-2 max-h-72 divide-y divide-ink/10 overflow-y-auto border-y border-ink/10">
        {poster.map((p) => (
          <li key={p.id} className="py-2">
            <p className="text-[0.875rem] font-medium text-ink">
              {p.bolag ?? p.mottagare ?? text({ sv: "Okänd mottagare", en: "Unknown recipient" })}
              {p.mottagare && p.bolag ? <span className="font-normal text-ink-muted"> · {p.mottagare}</span> : null}
            </p>
            {p.amne ? <p className={cn(meta, "truncate")}>{p.amne}</p> : null}
            {p.utdrag ? <p className={cn(meta, "line-clamp-2 max-w-[70ch]")}>{p.utdrag}</p> : null}
          </li>
        ))}
      </ul>
      {overhoppade > 0 ? (
        <p className={cn(meta, "mt-2")}>
          {text({
            sv: `${overhoppade} av de markerade berörs inte och hoppas över.`,
            en: `${overhoppade} of the selected are not affected and are skipped.`
          })}
        </p>
      ) : null}
      {tillagg}
      {t.forklaring ? <p className={cn(meta, "mt-2")}>{text(t.forklaring)}</p> : null}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={upptagen || n === 0}
          onClick={onBekrafta}
          // Ta bort: sekundär form med röd text, inte en röd platta (cn slår
          // inte ihop klasser, och en ink-knapp ska bära husets enda tunga ton).
          className={typ === "ta-bort" ? cn(btnSecondary, btnLiten, "border-danger/40 text-danger") : cn(btnPrimary, btnLiten)}
        >
          {upptagen ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Ikon className="h-4 w-4" aria-hidden />}
          {text(t.knapp(n))}
        </button>
        <button type="button" disabled={upptagen} onClick={onAvbryt} className={cn(btnSecondary, btnLiten)}>
          {text({ sv: "Avbryt", en: "Cancel" })}
        </button>
        <span className={meta}>{text({ sv: "Esc stänger", en: "Esc closes" })}</span>
      </div>
    </section>
  );
}

/** Mejlets första riktiga mening: hälsningsraden ("Hej," / "Hej Anna,") hoppas över. */
export function forstaMening(brodtext: string | null | undefined): string | null {
  const rader = String(brodtext ?? "")
    .split("\n")
    .map((r) => r.trim())
    .filter(Boolean);
  const rad = rader.find((r) => !/^(hej|hejsan|hallå|god (morgon|dag)|hi|hello)\b[^.!?]*,?$/i.test(r));
  if (!rad) return null;
  return rad.length > 180 ? `${rad.slice(0, 177)}…` : rad;
}
