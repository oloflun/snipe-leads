"use client";

import { Loader2, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, EmptyState, SkeletonRows, btnPrimary } from "@/components/ui";
import { BAS, type KbArtikel } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Kunskapsbasen — det agenten får svara ur. Grundningsregeln i backenden
 * gör att ett ärende utan täckning i basen eskaleras i stället för att
 * gissas, så varje artikel här är ett ärende till som agenten kan ta själv.
 */
export function KunskapsbasVy() {
  const [artiklar, setArtiklar] = useState<KbArtikel[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [titel, setTitel] = useState("");
  const [innehall, setInnehall] = useState("");
  const [sparar, setSparar] = useState(false);
  const [sparat, setSparat] = useState(false);

  async function hamta() {
    try {
      const svar = await fetch(`${BAS}/kb`).then((s) =>
        readJson<{ articles: KbArtikel[] }>(s)
      );
      setArtiklar(svar?.articles ?? []);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setArtiklar([]);
    }
  }

  useEffect(() => {
    void hamta();
  }, []);

  async function laggTill(e: React.FormEvent) {
    e.preventDefault();
    if (!titel.trim() || !innehall.trim()) return;
    setSparar(true);
    setFel(null);
    setSparat(false);
    try {
      const svar = await fetch(`${BAS}/kb`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ articles: [{ title: titel.trim(), content: innehall.trim() }] })
      });
      await readJson(svar);
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

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik="Kunskapsbas"
        beskrivning="Det agenten får svara ur. Ärenden utan täckning här eskaleras till dig i stället för att gissas — varje artikel är ett ärende till som agenten kan ta själv."
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      <section className="max-w-[42rem]">
        <h2 className="font-display text-[1.25rem]">Lägg till en artikel</h2>
        <form onSubmit={laggTill} className="mt-3 space-y-4 border-y border-ink/15 py-5">
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">Rubrik</span>
            <input
              value={titel}
              onChange={(e) => setTitel(e.target.value)}
              placeholder="Öppettider och leveranstid"
              className="focus-ring mt-1.5 h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] placeholder:text-ink/35"
            />
          </label>
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">Innehåll</span>
            <textarea
              value={innehall}
              onChange={(e) => setInnehall(e.target.value)}
              rows={4}
              placeholder="Skriv som ni skulle svarat en kund — agenten formulerar utifrån det här."
              className="focus-ring mt-1.5 w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6 placeholder:text-ink/35"
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
            <EmptyState
              title="Kunskapsbasen är tom"
              body="Lägg till era vanligaste svar ovan, så kan agenten börja föreslå svar ur dem."
            />
          </div>
        ) : (
          <div className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
            {artiklar.map((artikel, i) => (
              <details key={artikel.id ?? i} className="group py-3">
                <summary className="focus-ring flex cursor-pointer list-none flex-wrap items-baseline gap-x-4 rounded-[4px]">
                  <span className="min-w-0 flex-1 truncate text-[0.9375rem] font-medium">
                    {artikel.title || "Utan rubrik"}
                  </span>
                  {artikel.category ? <Badge tone="neutral">{artikel.category}</Badge> : null}
                </summary>
                {artikel.content ? (
                  <p className="mt-2 max-w-[72ch] whitespace-pre-wrap text-[0.9375rem] leading-6 text-ink/70">
                    {artikel.content}
                  </p>
                ) : null}
              </details>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
