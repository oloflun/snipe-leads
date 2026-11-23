"use client";

import { Search } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { faltTatt, meta } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { STATUS_ETIKETT } from "@/lib/prospekt";
import { leadsAnrop, relativTid } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Sök bolag (Antons beställning 2026-11-22): en sökruta i Leads sidhuvud
 * som hittar ett bolag bland ALLA leads, också de som fått mejl, svarat
 * eller arkiverats, och öppnar dess låda med profil, utkast och tidslinje.
 * Backend: GET /api/leads/sok (app/api/leads_uppfoljningar.py).
 *
 * En combobox enligt ARIA-mönstret: pilar flyttar markeringen, Enter
 * öppnar, Esc stänger.
 */

type Traff = {
  id: string;
  company_name: string | null;
  ort: string | null;
  contact_name: string | null;
  contact_email: string | null;
  orgnr: string | null;
  status: string | null;
  arkiverad: boolean;
  skickade: number;
  senast_skickat: string | null;
  thread_id: string | null;
  svarat: boolean;
};

export function BolagsSok({ onValj }: Readonly<{ onValj: (prospektId: string) => void }>) {
  const { text, locale } = useLocale();
  const listId = useId();
  const [fraga, setFraga] = useState("");
  const [traffar, setTraffar] = useState<Traff[] | null>(null);
  const [aktiv, setAktiv] = useState(0);
  const [oppen, setOppen] = useState(false);
  const [laddar, setLaddar] = useState(false);
  const yta = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = fraga.trim();
    if (q.length < 2) {
      setTraffar(null);
      return;
    }
    let avbruten = false;
    setLaddar(true);
    const id = window.setTimeout(async () => {
      try {
        const svar = await leadsAnrop<{ traffar: Traff[] }>(`/leads/sok?q=${encodeURIComponent(q)}`);
        if (!avbruten) {
          setTraffar(svar.traffar);
          setAktiv(0);
        }
      } catch {
        if (!avbruten) setTraffar([]);
      } finally {
        if (!avbruten) setLaddar(false);
      }
    }, 200);
    return () => {
      avbruten = true;
      window.clearTimeout(id);
    };
  }, [fraga]);

  useEffect(() => {
    if (!oppen) return;
    const stang = (e: MouseEvent) => {
      if (!yta.current?.contains(e.target as Node)) setOppen(false);
    };
    document.addEventListener("mousedown", stang);
    return () => document.removeEventListener("mousedown", stang);
  }, [oppen]);

  function valj(t: Traff) {
    setOppen(false);
    setFraga("");
    setTraffar(null);
    onValj(t.id);
  }

  const visa = oppen && fraga.trim().length >= 2;

  return (
    <div ref={yta} className="relative w-full sm:w-72">
      <label className="relative block">
        <span className="sr-only">{text({ sv: "Sök bolag", en: "Search companies" })}</span>
        <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
        <input
          type="search"
          role="combobox"
          aria-expanded={visa}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={visa && traffar?.[aktiv] ? `${listId}-${aktiv}` : undefined}
          value={fraga}
          placeholder={text({ sv: "Sök bolag, kontakt eller orgnr", en: "Search company, contact or org no." })}
          onChange={(e) => {
            setFraga(e.target.value);
            setOppen(true);
          }}
          onFocus={() => setOppen(true)}
          onKeyDown={(e) => {
            if (e.key === "Escape") setOppen(false);
            if (!traffar?.length) return;
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setAktiv((i) => (i + 1) % traffar.length);
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setAktiv((i) => (i - 1 + traffar.length) % traffar.length);
            } else if (e.key === "Enter" && traffar[aktiv]) {
              e.preventDefault();
              valj(traffar[aktiv]);
            }
          }}
          className={cn(faltTatt, "h-11 w-full pl-9")}
        />
      </label>
      {visa ? (
        <ul
          id={listId}
          role="listbox"
          aria-label={text({ sv: "Träffar", en: "Results" })}
          className="absolute left-0 right-0 top-full z-40 mt-1 max-h-[60dvh] overflow-y-auto rounded-card border border-ink/12 bg-paper p-1 shadow-lift sm:left-auto sm:w-[26rem]"
        >
          {traffar === null || laddar ? (
            <li className={cn(meta, "px-3 py-2.5")}>{text({ sv: "Söker…", en: "Searching…" })}</li>
          ) : traffar.length === 0 ? (
            <li className="px-3 py-2.5 text-[0.9375rem] text-ink-muted">{text({ sv: "Inga bolag hittades.", en: "No companies found." })}</li>
          ) : (
            traffar.map((t, i) => (
              <li
                key={t.id}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === aktiv}
                onMouseEnter={() => setAktiv(i)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  valj(t);
                }}
                className={cn("cursor-pointer rounded-input px-3 py-2.5", i === aktiv && "bg-paper2")}
              >
                <span className="flex items-baseline justify-between gap-3">
                  <span className="truncate text-[0.9375rem] font-medium text-ink">{t.company_name ?? t.contact_email}</span>
                  <span className="shrink-0 text-[0.8125rem] text-ink-muted">
                    {t.arkiverad
                      ? text({ sv: "Arkiverad", en: "Archived" })
                      : t.status && STATUS_ETIKETT[t.status]
                        ? text(STATUS_ETIKETT[t.status])
                        : null}
                  </span>
                </span>
                <span className={cn(meta, "block truncate")}>
                  {[t.ort, t.contact_name, t.orgnr].filter(Boolean).join(" · ")}
                  {t.skickade
                    ? ` · ${text({ sv: `${t.skickade} mejl, senast`, en: `${t.skickade} emails, last` })} ${relativTid(t.senast_skickat, locale)}`
                    : ""}
                  {t.svarat ? ` · ${text({ sv: "har svarat", en: "has replied" })}` : ""}
                </span>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
