"use client";

import { Loader2, Send } from "lucide-react";
import { btnLiten, btnPrimary, btnSecondary, meta } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export type Utskick = { id: string; bolag: string | null; mottagare: string | null; amne: string | null };

/**
 * Bekräftelsen före ett massutskick, på sidan och inte i webbläsarens
 * confirm-ruta (impeccable-kritik 3, 2026-10-07: "Godkänna och skicka 6
 * utkast?" sa inte till VEM). Varje mottagare och ämnesrad står listad, och
 * knappen säger exakt hur många mejl som går. Sebbes val: massutskicket får
 * finnas utan att varje utkast öppnats, men aldrig utan mottagarlista.
 *
 * Används av alla tre massutskicken: Iris-listans "Skicka utkasten",
 * översiktens utkastruta och körningens "Leads och utkast".
 */
export function BekraftaUtskick({
  poster,
  overhoppade = 0,
  upptagen = false,
  onBekrafta,
  onAvbryt
}: Readonly<{
  poster: Utskick[];
  /** Markerade som inte har något väntande utkast och därför hoppas över. */
  overhoppade?: number;
  upptagen?: boolean;
  onBekrafta: () => void;
  onAvbryt: () => void;
}>) {
  const { text } = useLocale();
  const n = poster.length;
  return (
    <section
      role="region"
      aria-label={text({ sv: "Bekräfta utskick", en: "Confirm sending" })}
      className="rounded-input border border-ink/15 bg-paper2 px-4 py-3"
    >
      <p className="text-[0.9375rem] font-medium text-ink">
        {text({
          sv: `${n} mejl godkänns och skickas till:`,
          en: `${n} ${n === 1 ? "email is" : "emails are"} approved and sent to:`
        })}
      </p>
      <ul className="thin-scrollbar mt-2 max-h-64 divide-y divide-ink/10 overflow-y-auto border-y border-ink/10">
        {poster.map((p) => (
          <li key={p.id} className="py-2">
            <p className="text-[0.875rem] font-medium text-ink">
              {p.bolag ?? p.mottagare ?? text({ sv: "Okänd mottagare", en: "Unknown recipient" })}
              {p.mottagare && p.bolag ? <span className="font-normal text-ink-muted"> · {p.mottagare}</span> : null}
            </p>
            {p.amne ? <p className={cn(meta, "truncate")}>{p.amne}</p> : null}
          </li>
        ))}
      </ul>
      {overhoppade > 0 ? (
        <p className={cn(meta, "mt-2")}>
          {text({
            sv: `${overhoppade} av de markerade har inget utkast som väntar och hoppas över.`,
            en: `${overhoppade} of the selected have no draft waiting and are skipped.`
          })}
        </p>
      ) : null}
      <p className={cn(meta, "mt-2")}>
        {text({
          sv: "Varje mejl går genom sändspärrarna; utanför vardagar 08–16 skickas det när fönstret öppnar.",
          en: "Every email passes the send guards; outside weekdays 08–16 it goes out when the window opens."
        })}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button type="button" disabled={upptagen || n === 0} onClick={onBekrafta} className={cn(btnPrimary, btnLiten)}>
          {upptagen ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Send className="h-4 w-4" aria-hidden />}
          {text({ sv: `Skicka ${n} mejl`, en: `Send ${n} ${n === 1 ? "email" : "emails"}` })}
        </button>
        <button type="button" disabled={upptagen} onClick={onAvbryt} className={cn(btnSecondary, btnLiten)}>
          {text({ sv: "Avbryt", en: "Cancel" })}
        </button>
      </div>
    </section>
  );
}
