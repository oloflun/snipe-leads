"use client";

import { useCallback, useEffect, useState } from "react";

const MAX_CHARS = 4000;
const ENDPOINT = "/api/snajp-support/leads/soul";

type LoadState = "loading" | "ready" | "error";

/**
 * Kundens röstdokument (SOUL).
 *
 * Texten härifrån hamnar i agentens ANVÄNDARmeddelande, wrappad som
 * opålitligt innehåll — aldrig i systemprompten (INV-SEC-009). Det betyder
 * att kunden kan styra ton och röst men inte reglerna, och det är avsiktligt:
 * hjälptexten nedan säger det rakt ut så att ingen skriver en instruktion och
 * undrar varför den ignoreras.
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

  if (state === "loading") return <p className="text-mineral">Hämtar röstdokumentet…</p>;
  if (state === "error") return <p className="text-mineral">Kunde inte hämta röstdokumentet.</p>;

  return (
    <div className="grid gap-5">
      {/* Ingen brödtext och ingen rubrik här. PageShell säger vad sidan gör,
          och platshållaren i fältet visar HUR — exempel undervisar bättre än
          ett stycke som beskriver exemplen. */}
      <label className="grid gap-2">
        <span className="kicker text-mineral">Röstdokument</span>
        <textarea
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
          aria-label="Röstdokument"
          aria-describedby="soul-count"
          /* Höjden är responsiv i CSS, inte via rows: en fast rows={16} gav
             450px textarea även på 375px-skärm, vilket sköt Spara-knappen
             92px under viken (uppmätt). Den primära åtgärden ska inte kräva
             att man scrollar förbi en mestadels tom ruta.

             max-w-[68ch] och md:h-80 av samma skäl fast åt andra hållet:
             utan bredduttaget blev fältet 1006px brett på 1440px-skärm, vilket
             är ~90 tecken per rad (uppmätt) mot 45-75 som går att läsa
             bekvämt. Och 416px höjd gav en ruta som var tre fjärdedelar tom —
             ett tomt fält läser som trasigt, inte som inbjudande. */
          className="h-56 w-full max-w-[68ch] border border-rule bg-paper p-4 font-sans leading-relaxed md:h-80"
          placeholder={
            "Vi säger du, aldrig ni.\n" +
            "Korta meningar. Inga utropstecken.\n" +
            "Vi säger 'hör av dig', inte 'tveka inte att kontakta oss'.\n" +
            "Vi skriver 'order', inte 'beställning'."
          }
        />
      </label>

      <div className="flex flex-wrap items-center gap-4">
        {/* text-warning, inte text-ochre: ochre är en accent på 2.17:1 mot
            paper (uppmätt) och underkänd för 16px text. Färgen är dessutom
            aldrig ensam bärare här — meningen står utskriven. */}
        <span id="soul-count" className={over ? "text-warning" : "text-mineral"}>
          {content.length} / {MAX_CHARS} tecken
          {over ? " — för långt, korta ner innan du sparar" : ""}
        </span>
        <button
          type="button"
          onClick={save}
          disabled={busy || over || !dirty}
          className="border border-rule px-5 py-2 disabled:opacity-40"
        >
          {busy ? "Sparar…" : "Spara"}
        </button>
        {message ? <span className="text-mineral">{message}</span> : null}
      </div>
    </div>
  );
}
