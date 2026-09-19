"use client";

import { Globe, Loader2, Plus, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { BAS, kategori, type KbArtikel } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Kunskapsbasen — det agenten får svara ur. Grundningsregeln i backenden
 * gör att ett ärende utan täckning i basen eskaleras i stället för att
 * gissas, så varje artikel här är ett ärende till som agenten kan ta själv.
 *
 * Skanningen (POST /api/kb/skanna, app/kb_skanning.py) läser kundens egen
 * sajt och föreslår artiklar. Ingenting sparas förrän kunden valt: de
 * förkryssade utkasten går genom samma POST /api/kb som en handskriven artikel.
 */

type Utkast = {
  title: string;
  content: string;
  category: string;
  source_url: string;
  confidence: number;
  varningar: string[];
};

type Skanning = {
  webbplats: string;
  sidor: number;
  artiklar: Utkast[];
};

type Jobbsvar = { status: string; result?: Skanning | null; error?: string | null };

const INPUT =
  "focus-ring h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] placeholder:text-ink-subtle";

/** Förkryssat bara när modellen var säker och siffergrinden inte flaggade. */
function forvald(u: Utkast) {
  return u.confidence >= 0.5 && u.varningar.length === 0;
}

function sokvag(url: string) {
  try {
    const u = new URL(url);
    return u.pathname === "/" ? u.host : u.pathname;
  } catch {
    return url;
  }
}

export function KunskapsbasVy() {
  const [artiklar, setArtiklar] = useState<KbArtikel[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  const [webbplats, setWebbplats] = useState("");
  const [skannar, setSkannar] = useState(false);
  const [skanning, setSkanning] = useState<Skanning | null>(null);
  const [valda, setValda] = useState<Set<number>>(new Set());
  const [sparar, setSparar] = useState(false);
  const avbruten = useRef(false);

  const [titel, setTitel] = useState("");
  const [innehall, setInnehall] = useState("");
  const [sparat, setSparat] = useState(false);

  const [bekrafta, setBekrafta] = useState<string | null>(null);

  async function hamta() {
    try {
      const svar = await fetch(`${BAS}/kb`).then((s) => readJson<{ articles: KbArtikel[] }>(s));
      setArtiklar(svar?.articles ?? []);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setArtiklar([]);
    }
  }

  useEffect(() => {
    avbruten.current = false;
    void hamta();
    return () => {
      avbruten.current = true;
    };
  }, []);

  async function skanna(e: React.FormEvent) {
    e.preventDefault();
    if (!webbplats.trim() || skannar) return;
    setSkannar(true);
    setFel(null);
    setSkanning(null);
    try {
      const start = await fetch(`${BAS}/kb/skanna`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ webbplats: webbplats.trim() })
      }).then((s) => readJson<{ job_id: string }>(s));
      if (!start?.job_id) throw new Error("Skanningen startade inte.");

      // Hämtningen tar runt en halv minut, utkasten lika länge till.
      // Jobbet auto-failas i backenden efter fem minuter, så slingan har ett tak.
      for (let i = 0; i < 150 && !avbruten.current; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const jobb = await fetch(`${BAS}/jobs/${start.job_id}`).then((s) => readJson<Jobbsvar>(s));
        if (jobb?.status === "completed" && jobb.result) {
          setSkanning(jobb.result);
          setValda(
            new Set(jobb.result.artiklar.flatMap((u, index) => (forvald(u) ? [index] : [])))
          );
          return;
        }
        if (jobb?.status === "failed") throw new Error(jobb.error || "Skanningen misslyckades.");
      }
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setSkannar(false);
    }
  }

  async function sparaArtiklar(nya: { title: string; content: string; category?: string }[]) {
    const svar = await fetch(`${BAS}/kb`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ articles: nya })
    });
    await readJson(svar);
  }

  async function laggTillValda() {
    if (!skanning) return;
    const nya = skanning.artiklar
      .filter((_, index) => valda.has(index))
      .map(({ title, content, category }) => ({ title, content, category }));
    if (!nya.length) return;
    setSparar(true);
    setFel(null);
    try {
      // POST /api/kb tar högst 50 per anrop; skanningen ger högst 40.
      await sparaArtiklar(nya);
      setSkanning(null);
      setValda(new Set());
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setSparar(false);
    }
  }

  async function laggTill(e: React.FormEvent) {
    e.preventDefault();
    if (!titel.trim() || !innehall.trim()) return;
    setSparar(true);
    setFel(null);
    setSparat(false);
    try {
      await sparaArtiklar([{ title: titel.trim(), content: innehall.trim() }]);
      setTitel("");
      setInnehall("");
      setSparat(true);
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setSparar(false);
    }
  }

  async function taBort(id: string) {
    setFel(null);
    try {
      await readJson(await fetch(`${BAS}/kb/${encodeURIComponent(id)}`, { method: "DELETE" }));
      setBekrafta(null);
      setArtiklar((nu) => nu?.filter((a) => a.id !== id) ?? nu);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }

  function vaxla(index: number) {
    setValda((nu) => {
      const ny = new Set(nu);
      if (ny.has(index)) ny.delete(index);
      else ny.add(index);
      return ny;
    });
  }

  return (
    <div className="space-y-10">
      <PageHeader rubrik="Kunskapsbas" />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      <section className="max-w-[42rem]">
        <h2 className="font-display text-[1.25rem]">Skanna webbplats</h2>
        <form onSubmit={skanna} className="mt-3 flex flex-col gap-2 sm:flex-row">
          <label className="min-w-0 flex-1">
            <span className="sr-only">Webbplats</span>
            <input
              value={webbplats}
              onChange={(e) => setWebbplats(e.target.value)}
              placeholder="bolaget.se"
              inputMode="url"
              autoComplete="url"
              disabled={skannar}
              className={INPUT}
            />
          </label>
          <button type="submit" disabled={skannar || !webbplats.trim()} className={cn(btnPrimary, "shrink-0")}>
            {skannar ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Globe className="h-4 w-4" aria-hidden />
            )}
            {skannar ? "Skannar…" : "Skanna"}
          </button>
        </form>

        {skanning ? (
          <div className="mt-5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-[0.875rem] text-ink-muted">
                {skanning.artiklar.length} förslag från {skanning.sidor} sidor
              </p>
              {skanning.artiklar.length ? (
                <button
                  type="button"
                  className="focus-ring rounded-[4px] text-[0.875rem] font-medium text-ink underline-offset-4 hover:underline"
                  onClick={() =>
                    setValda(
                      valda.size === skanning.artiklar.length
                        ? new Set()
                        : new Set(skanning.artiklar.map((_, i) => i))
                    )
                  }
                >
                  {valda.size === skanning.artiklar.length ? "Avmarkera alla" : "Markera alla"}
                </button>
              ) : null}
            </div>

            {skanning.artiklar.length ? (
              <ul className="mt-2 divide-y divide-ink/12 border-y border-ink/15">
                {skanning.artiklar.map((u, index) => (
                  <li key={`${u.source_url}-${index}`} className="flex gap-3 py-3">
                    <input
                      type="checkbox"
                      checked={valda.has(index)}
                      onChange={() => vaxla(index)}
                      aria-label={`Lägg till ${u.title}`}
                      className="mt-1 h-4 w-4 shrink-0 accent-ink"
                    />
                    <details className="group min-w-0 flex-1">
                      <summary className="focus-ring flex cursor-pointer list-none flex-wrap items-baseline gap-x-3 gap-y-1 rounded-[4px]">
                        <span className="min-w-0 flex-1 text-[0.9375rem] font-medium">{u.title}</span>
                        <span className="hidden text-[0.8125rem] text-ink-subtle sm:inline">{sokvag(u.source_url)}</span>
                      </summary>
                      <p className="mt-2 max-w-[72ch] whitespace-pre-wrap text-[0.9375rem] leading-6 text-ink-muted">
                        {u.content}
                      </p>
                    </details>
                    {u.varningar.length ? (
                      <span className="shrink-0" title={u.varningar.join(" ")}>
                        <Badge tone="warn">Kontrollera</Badge>
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-2">
                <EmptyState title="Inga förslag hittades" />
              </div>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              {skanning.artiklar.length ? (
                <button
                  type="button"
                  onClick={laggTillValda}
                  disabled={sparar || valda.size === 0}
                  className={btnPrimary}
                >
                  {sparar ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Plus className="h-4 w-4" aria-hidden />}
                  Lägg till {valda.size}
                </button>
              ) : null}
              <button type="button" onClick={() => setSkanning(null)} className={btnSecondary}>
                Stäng
              </button>
            </div>
          </div>
        ) : null}
      </section>

      <section className="max-w-[42rem]">
        <details className="group" open={artiklar?.length === 0 ? true : undefined}>
          <summary className="focus-ring cursor-pointer list-none rounded-[4px] font-display text-[1.25rem]">
            Skriv en artikel
          </summary>
          <form onSubmit={laggTill} className="mt-3 space-y-4 border-y border-ink/15 py-5">
            <label className="block">
              <span className="text-[0.875rem] font-medium text-ink">Rubrik</span>
              <input
                value={titel}
                onChange={(e) => setTitel(e.target.value)}
                placeholder="Öppettider och leveranstid"
                className={cn(INPUT, "mt-1.5")}
              />
            </label>
            <label className="block">
              <span className="text-[0.875rem] font-medium text-ink">Innehåll</span>
              <textarea
                value={innehall}
                onChange={(e) => setInnehall(e.target.value)}
                rows={4}
                className="focus-ring mt-1.5 w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6 placeholder:text-ink-subtle"
              />
            </label>
            <div className="flex items-center gap-3">
              <button type="submit" disabled={sparar} className={cn(btnPrimary)}>
                {sparar ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Plus className="h-4 w-4" aria-hidden />
                )}
                Lägg till
              </button>
              {sparat ? (
                <span role="status" className="text-[0.875rem] text-moss">
                  Tillagd.
                </span>
              ) : null}
            </div>
          </form>
        </details>
      </section>

      <section>
        <h2 className="font-display text-[1.25rem]">
          {artiklar ? `${artiklar.length} artiklar` : "Artiklar"}
        </h2>
        {artiklar === null ? (
          <div className="mt-3">
            <SkeletonRows />
          </div>
        ) : artiklar.length === 0 ? (
          <div className="mt-3">
            <EmptyState title="Kunskapsbasen är tom" />
          </div>
        ) : (
          <div className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
            {artiklar.map((artikel, i) => (
              <div key={artikel.id ?? i} className="flex items-start gap-3 py-3">
                <details className="group min-w-0 flex-1">
                  <summary className="focus-ring flex cursor-pointer list-none flex-wrap items-baseline gap-x-4 rounded-[4px]">
                    <span className="min-w-0 flex-1 text-[0.9375rem] font-medium sm:truncate">
                      {artikel.title || "Utan rubrik"}
                    </span>
                    {artikel.category ? (
                      <span className="hidden sm:inline-flex">
                        <Badge tone="neutral">{kategori(artikel.category)}</Badge>
                      </span>
                    ) : null}
                  </summary>
                  {artikel.content ? (
                    <p className="mt-2 max-w-[72ch] whitespace-pre-wrap text-[0.9375rem] leading-6 text-ink-muted">
                      {artikel.content}
                    </p>
                  ) : null}
                </details>
                {artikel.id ? (
                  bekrafta === artikel.id ? (
                    <span className="flex shrink-0 gap-1.5">
                      <button
                        type="button"
                        onClick={() => void taBort(artikel.id!)}
                        className={cn(btnPrimary, btnLiten, "!bg-danger hover:!bg-danger/90")}
                      >
                        Ta bort
                      </button>
                      <button type="button" onClick={() => setBekrafta(null)} className={cn(btnSecondary, btnLiten)}>
                        Behåll
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setBekrafta(artikel.id!)}
                      aria-label={`Ta bort ${artikel.title || "artikeln"}`}
                      className="focus-ring shrink-0 rounded-[4px] p-1.5 text-ink-subtle hover:text-danger"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </button>
                  )
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
