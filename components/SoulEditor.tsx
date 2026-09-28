"use client";

import { useCallback, useEffect, useState } from "react";
import { Rad, Radlista, btnPrimary, meta, rubrikPanel } from "@/components/ui";
import { cn } from "@/lib/utils";

const MAX_CHARS = 4000;
const ENDPOINT = "/api/snajp-support/leads/soul";

type LoadState = "loading" | "ready" | "error";

/**
 * Kundens röstdokument (SOUL).
 *
 * Texten härifrån hamnar i agentens ANVÄNDARmeddelande, wrappad som
 * opålitligt innehåll — aldrig i systemprompten (INV-SEC-009). Det betyder
 * att kunden kan styra ton och röst men inte reglerna, och det är avsiktligt:
 * hjälptexten nedan ber om hur ni låter, inte om regler, så att ingen skriver
 * en instruktion och undrar varför den ignoreras.
 */
export function SoulEditor() {
  const [content, setContent] = useState("");
  const [saved, setSaved] = useState("");
  const [state, setState] = useState<LoadState>("loading");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(ENDPOINT)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((data: { content?: string }) => {
        if (cancelled) return;
        setContent(data.content ?? "");
        setSaved(data.content ?? "");
        setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const save = useCallback(async () => {
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(ENDPOINT, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content })
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setSaved(content);
      setMessage("Sparat. Gäller från nästa mejl och svar.");
    } catch {
      setMessage("Kunde inte spara. Försök igen.");
    } finally {
      setBusy(false);
    }
  }, [content]);

  const over = content.length > MAX_CHARS;
  const dirty = content !== saved;

  if (state === "loading") {
    return <div className="h-56 animate-pulse rounded-card bg-ink/[0.055] md:h-80" aria-busy="true" />;
  }
  if (state === "error") {
    return (
      <p role="alert" className="text-[0.9375rem] text-danger">
        Kunde inte hämta röstdokumentet.
      </p>
    );
  }

  return (
    <Radlista ariaLabel="Röstdokument">
      {/* EN mening hjälptext, vid fältet. Den stod tidigare som ingress under
          sidrubriken; platshållaren visar sedan HUR, och exempel undervisar
          bättre än ett stycke som beskriver exemplen. */}
      <Rad className="grid gap-3">
        <div>
          <label htmlFor="soul-text" className={cn(rubrikPanel, "block")}>
            Röstdokument
          </label>
          <p id="soul-hjalp" className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
            Beskriv hur ni låter. Båda agenterna skriver så, i utskick och i svar.
          </p>
        </div>
        <textarea
          id="soul-text"
          value={content}
          onChange={(event) => {
            setContent(event.target.value);
            // Kvittensen gäller det som sparades, inte det som står nu. Utan
            // den här raden stod "Sparat." kvar bredvid "för långt, korta ner"
            // så fort man skrev vidare — två motsägande besked samtidigt
            // (sett i skärmdump, inte i koden).
            setMessage(null);
          }}
          rows={8}
          aria-describedby="soul-hjalp soul-count"
          /* Höjden är responsiv i CSS, inte via rows: en fast rows={16} gav
             450px textarea även på 375px-skärm, vilket sköt Spara-knappen
             92px under viken (uppmätt). Den primära åtgärden ska inte kräva
             att man scrollar förbi en mestadels tom ruta.

             max-w-[68ch] och md:h-80 av samma skäl fast åt andra hållet:
             utan bredduttaget blev fältet 1006px brett på 1440px-skärm, vilket
             är ~90 tecken per rad (uppmätt) mot 45-75 som går att läsa
             bekvämt. Och 416px höjd gav en ruta som var tre fjärdedelar tom —
             ett tomt fält läser som trasigt, inte som inbjudande. */
          className="focus-ring h-56 w-full max-w-[68ch] resize-y rounded-input border border-ink/15 bg-paper px-3 py-2.5 font-sans text-[16px] leading-6 md:h-80"
          placeholder={
            "Vi säger du, aldrig ni.\n" +
            "Korta meningar. Inga utropstecken.\n" +
            "Vi säger 'hör av dig', inte 'tveka inte att kontakta oss'.\n" +
            "Vi skriver 'order', inte 'beställning'."
          }
        />

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={save}
            disabled={busy || over || !dirty}
            className={btnPrimary}
          >
            {busy ? "Sparar…" : "Spara"}
          </button>
          {/* text-warning, inte text-ochre: ochre är en accent på 2.17:1 mot
              paper (uppmätt) och underkänd för text. Färgen är dessutom aldrig
              ensam bärare här, meningen står utskriven. */}
          <span id="soul-count" className={over ? "num text-[0.8125rem] text-warning" : cn(meta, "num")}>
            {content.length} / {MAX_CHARS} tecken
            {over ? ". För långt, korta ner innan du sparar." : ""}
          </span>
          {message ? (
            <span role="status" className="text-[0.9375rem] text-ink-muted">
              {message}
            </span>
          ) : null}
        </div>
      </Rad>
    </Radlista>
  );
}
