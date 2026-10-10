"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { Rad, Radlista, Tomt, btnPrimary, btnSecondary, etikett, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { UTFALL_ETIKETT, datumFormat, leadsAnrop, type Handelse, type Utfall } from "@/lib/leads/suite";
import { STATUS_ETIKETT } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Prospektets tidslinje (Fas 10, Leads Suite F6): statusbyten, mejl ut och
 * in, anteckningar och uppgifter, nyast först. Backenden komponerar listan
 * (`GET /leads/prospects/{id}/tidslinje`); här skrivs anteckningar och
 * uppgifter, och en uppgift bockas av med kryssrutan. Demon visar en tom
 * tidslinje och anropar ingenting.
 */

const T = {
  tidslinje: { sv: "Tidslinje", en: "Timeline" },
  hamtar: { sv: "Hämtar tidslinjen…", en: "Loading the timeline…" },
  hamtaFel: { sv: "Tidslinjen kunde inte hämtas.", en: "The timeline could not be loaded." },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  tom: { sv: "Inget har hänt med bolaget än.", en: "Nothing has happened with this company yet." },
  demo: {
    sv: "Här samlas statusbyten, mejl, anteckningar och uppgifter för bolaget. I demon är tidslinjen tom.",
    en: "Status changes, emails, notes and tasks for the company gather here. In the demo the timeline is empty."
  },
  svaraIInkorgen: { sv: "Svara under Att göra", en: "Reply under To do" },
  anteckning: { sv: "Anteckning", en: "Note" },
  sparaAnteckning: { sv: "Spara anteckning", en: "Save note" },
  uppgift: { sv: "Uppgift", en: "Task" },
  forfaller: { sv: "Förfaller", en: "Due" },
  laggTillUppgift: { sv: "Lägg till uppgift", en: "Add task" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  klar: { sv: "Klar", en: "Done" }
} satisfies Record<string, Localized>;

const TYP_ETIKETT: Record<Handelse["typ"], Localized> = {
  skapad: { sv: "Skapad", en: "Created" },
  status: { sv: "Status", en: "Status" },
  mejl_ut: { sv: "Mejl ut", en: "Email out" },
  mejl_in: { sv: "Mejl in", en: "Email in" },
  anteckning: { sv: "Anteckning", en: "Note" },
  uppgift: { sv: "Uppgift", en: "Task" },
  samtal: { sv: "Samtal", en: "Call" }
};

const faltKlass = "focus-ring min-h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] text-ink";

export function Tidslinje({ prospectId, demo = false }: Readonly<{ prospectId: string; demo?: boolean }>) {
  const { locale, text } = useLocale();
  // Leadsmejlen ligger i Att göra sedan Snajp Suite; vägen följer ytan (/admin).
  const vag = useArbetsvag();
  const [handelser, setHandelser] = useState<Handelse[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [skrivFel, setSkrivFel] = useState<string | null>(null);
  const [anteckning, setAnteckning] = useState("");
  const [titel, setTitel] = useState("");
  const [datum, setDatum] = useState("");
  const [sparar, setSparar] = useState<"anteckning" | "uppgift" | null>(null);

  const hamta = useCallback(async () => {
    if (demo) return;
    try {
      const svar = await leadsAnrop<{ handelser?: Handelse[] }>(`/leads/prospects/${prospectId}/tidslinje`);
      setHandelser(svar.handelser ?? []);
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }, [prospectId, demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  async function skriv(vad: "anteckning" | "uppgift", vag: string, kropp: unknown, nollstall: () => void) {
    setSparar(vad);
    setSkrivFel(null);
    try {
      await leadsAnrop(vag, { method: "POST", body: JSON.stringify(kropp) });
      nollstall();
      await hamta();
    } catch (orsak) {
      setSkrivFel(felmeddelande(orsak));
    } finally {
      setSparar(null);
    }
  }

  async function bocka(id: string, klar: boolean) {
    setHandelser((h) => h?.map((x) => (x.typ === "uppgift" && x.id === id ? { ...x, klar } : x)) ?? null);
    setSkrivFel(null);
    try {
      await leadsAnrop(`/leads/uppgifter/${id}`, { method: "PATCH", body: JSON.stringify({ klar }) });
    } catch (orsak) {
      setHandelser((h) => h?.map((x) => (x.typ === "uppgift" && x.id === id ? { ...x, klar: !klar } : x)) ?? null);
      setSkrivFel(felmeddelande(orsak));
    }
  }

  function rubrik(h: Handelse): string {
    // Samtalets rubrik är utfallets nyckel (app/api/leads_suite.py).
    if (h.typ === "samtal") return h.rubrik in UTFALL_ETIKETT ? text(UTFALL_ETIKETT[h.rubrik as Utfall]) : h.rubrik;
    if (h.typ !== "status") return h.rubrik;
    // Backenden skickar råa statusnycklar, "fran → till".
    return h.rubrik
      .split("→")
      .map((del) => {
        const nyckel = del.trim();
        return STATUS_ETIKETT[nyckel] ? text(STATUS_ETIKETT[nyckel]) : nyckel;
      })
      .join(" → ");
  }

  const nar = (iso: string) =>
    new Date(iso).toLocaleString(datumFormat(locale), { dateStyle: "medium", timeStyle: "short" });

  return (
    <section aria-labelledby={`tidslinje-${prospectId}`}>
      <h3 id={`tidslinje-${prospectId}`} className={rubrikPanel}>
        {text(T.tidslinje)}
      </h3>

      {demo ? (
        <div className="mt-3">
          <Tomt>{text(T.demo)}</Tomt>
        </div>
      ) : (
        <>
          <form
            className="mt-4 space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              const t = anteckning.trim();
              if (t) void skriv("anteckning", `/leads/prospects/${prospectId}/anteckningar`, { text: t }, () => setAnteckning(""));
            }}
          >
            <label className={cn(etikett, "flex flex-col gap-1")}>
              {text(T.anteckning)}
              <textarea
                value={anteckning}
                onChange={(e) => setAnteckning(e.target.value)}
                maxLength={4000}
                rows={3}
                className={cn(faltKlass, "py-2")}
              />
            </label>
            <button type="submit" disabled={sparar !== null || !anteckning.trim()} className={btnSecondary}>
              {sparar === "anteckning" ? text(T.sparar) : text(T.sparaAnteckning)}
            </button>
          </form>

          <form
            className="mt-5 flex flex-wrap items-end gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              const t = titel.trim();
              if (t)
                void skriv("uppgift", `/leads/prospects/${prospectId}/uppgifter`, { titel: t, forfaller: datum || null }, () => {
                  setTitel("");
                  setDatum("");
                });
            }}
          >
            <label className={cn(etikett, "flex min-w-[180px] flex-1 flex-col gap-1")}>
              {text(T.uppgift)}
              <input value={titel} onChange={(e) => setTitel(e.target.value)} maxLength={200} className={faltKlass} />
            </label>
            <label className={cn(etikett, "flex flex-col gap-1")}>
              {text(T.forfaller)}
              <input type="date" value={datum} onChange={(e) => setDatum(e.target.value)} className={faltKlass} />
            </label>
            <button type="submit" disabled={sparar !== null || !titel.trim()} className={btnSecondary}>
              {sparar === "uppgift" ? text(T.sparar) : text(T.laggTillUppgift)}
            </button>
          </form>

          {skrivFel ? (
            <p role="alert" className="mt-3 text-[15px] text-danger">
              {skrivFel}
            </p>
          ) : null}

          <div className="mt-6">
            {fel ? (
              <div>
                <p role="alert" className="text-[15px] text-danger">
                  {text(T.hamtaFel)} {fel}
                </p>
                <button type="button" onClick={() => void hamta()} className={cn(btnPrimary, "mt-3")}>
                  {text(T.forsokIgen)}
                </button>
              </div>
            ) : handelser === null ? (
              <p className={meta}>{text(T.hamtar)}</p>
            ) : handelser.length === 0 ? (
              <Tomt>{text(T.tom)}</Tomt>
            ) : (
              <>
                {handelser.some((h) => h.typ === "mejl_in") ? (
                  <Link
                    href={vag("/dashboard/att-gora")}
                    className="focus-ring mb-3 inline-flex min-h-11 items-center rounded-input text-[15px] font-medium underline underline-offset-4"
                  >
                    {text(T.svaraIInkorgen)}
                  </Link>
                ) : null}
                <Radlista ariaLabel={text(T.tidslinje)}>
                  {handelser.map((h, i) => (
                    <Rad key={`${h.typ}-${h.id ?? i}-${h.nar}`}>
                      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                        <span className={etikett}>{text(TYP_ETIKETT[h.typ])}</span>
                        <time dateTime={h.nar} className={meta}>
                          {nar(h.nar)}
                        </time>
                      </div>
                      {h.typ === "uppgift" && h.id ? (
                        <label className="mt-1 flex min-h-11 cursor-pointer items-center gap-3">
                          <input
                            type="checkbox"
                            checked={Boolean(h.klar)}
                            onChange={(e) => void bocka(h.id!, e.target.checked)}
                            className="focus-ring h-5 w-5 shrink-0 accent-ink"
                          />
                          <span className={cn("font-medium", h.klar && "text-ink-muted line-through")}>{h.rubrik}</span>
                          {h.klar ? <span className="sr-only">{text(T.klar)}</span> : null}
                        </label>
                      ) : rubrik(h) ? (
                        <p className="mt-1 break-words font-medium">{rubrik(h)}</p>
                      ) : null}
                      {h.text ? (
                        <p className="mt-1 whitespace-pre-line break-words text-[15px] text-ink-muted">
                          {h.typ === "uppgift"
                            ? `${text(T.forfaller)} ${new Date(`${h.text}T00:00:00`).toLocaleDateString(datumFormat(locale), { day: "numeric", month: "short" })}`
                            : h.text}
                        </p>
                      ) : null}
                    </Rad>
                  ))}
                </Radlista>
              </>
            )}
          </div>
        </>
      )}
    </section>
  );
}
