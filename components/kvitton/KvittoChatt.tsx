"use client";

import { Loader2, Send, ShieldAlert, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Kvitto-assistenten — chatten över kvittodatan.
 *
 * Samma skelett som den gamla bokföringsassistenten: anropet går via
 * `/api/snajp-support/kvitton/chat`, backenden hämtar siffrorna med verktyg
 * och beloppsgrinden (INV-BOOK-003) fäller varje svar med ett tal som inte
 * hämtats. Ett fällt svar MÄRKS i gränssnittet i stället för att se ut som
 * vilket svar som helst.
 *
 * Filbilagor går INTE via chatten här — uppladdningen har en egen knapp i
 * arbetsytan, och en väg in är lättare att lita på än två.
 */

const BAS = "/api/snajp-support/kvitton";

type Rad = {
  roll: "kund" | "assistent";
  text: string;
  grundad?: boolean;
};

const FORSLAG = [
  "Hur mycket har vi lagt på resor den här månaden?",
  "Vilka kvitton behöver granskas?",
  "Hur mycket ingående moms finns i kvittona?"
];

const NATFEL = [
  "Kunde inte nå assistenten. Försök igen.",
  "Anropet kom inte fram. Försök igen."
];

const SVARSFEL = [
  "Inget svar den här gången. Försök igen.",
  "Något gick fel. Skicka frågan igen."
];

function slumpad(texter: string[]): string {
  return texter[Math.floor(Math.random() * texter.length)];
}

export function KvittoChatt() {
  const [rader, setRader] = useState<Rad[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const slutRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (rader.length) slutRef.current?.scrollIntoView({ block: "nearest" });
  }, [rader, busy]);

  async function skicka(fraga?: string) {
    const meddelande = (fraga ?? text).trim();
    if (!meddelande) return;

    setBusy(true);
    setFel(null);

    const historik = rader.map((r) => ({ roll: r.roll, text: r.text }));
    setRader((f) => [...f, { roll: "kund", text: meddelande }]);
    setText("");

    const aterstall = (feltext: string) => {
      setRader((f) => f.slice(0, -1));
      setText(meddelande);
      setFel(feltext);
    };

    try {
      const svar = await fetch(`${BAS}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ meddelande, historik })
      });
      const data = await svar.json().catch(() => null);
      if (!svar.ok) {
        aterstall(
          typeof data?.error === "string"
            ? data.error
            : typeof data?.detail === "string"
              ? data.detail
              : slumpad(SVARSFEL)
        );
        return;
      }
      if (typeof data?.reply !== "string" || !data.reply.trim()) {
        console.error("KvittoChatt: 200-svar utan reply-fält:", data);
        aterstall(slumpad(SVARSFEL));
        return;
      }
      setRader((f) => [
        ...f,
        { roll: "assistent", text: data.reply, grundad: data.grundad !== false }
      ]);
    } catch (orsak) {
      console.error("KvittoChatt:", orsak);
      aterstall(slumpad(NATFEL));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col rounded-panel border border-ink/15 bg-paper2/40">
      <header className="flex items-center gap-2 border-b border-ink/15 px-4 py-3">
        <Sparkles className="h-4 w-4 shrink-0 text-warning" aria-hidden />
        <h2 className="text-[0.9375rem] font-semibold text-ink">Kvitto-assistenten</h2>
      </header>

      <div className="flex min-h-[16rem] flex-col gap-3 overflow-y-auto px-4 py-4 lg:max-h-[26rem]">
        {rader.length === 0 ? (
          <div className="grid gap-2">
            {FORSLAG.map((f) => (
              <button
                key={f}
                type="button"
                disabled={busy}
                onClick={() => void skicka(f)}
                className="focus-ring rounded-input border border-ink/15 bg-paper px-3 py-2 text-left text-[0.8125rem] text-ink-muted hover:border-ink/35 hover:text-ink"
              >
                {f}
              </button>
            ))}
          </div>
        ) : null}

        {rader.map((rad, i) => (
          <div
            key={i}
            className={cn(
              "max-w-[92%] rounded-card px-3.5 py-2.5 text-[0.875rem] leading-6",
              rad.roll === "kund"
                ? "ml-auto bg-ink text-paper"
                : "border border-ink/15 bg-paper text-ink-muted"
            )}
          >
            <p className="whitespace-pre-wrap">{rad.text}</p>
            {rad.roll === "assistent" && rad.grundad === false ? (
              <p className="mt-2 flex items-start gap-1.5 border-t border-warning/30 pt-2 text-[0.75rem] leading-5 text-warning">
                <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                Stoppat av beloppskontrollen: en siffra gick inte att härleda.
              </p>
            ) : null}
          </div>
        ))}

        {busy ? (
          <p className="flex items-center gap-2 text-[0.8125rem] text-mineral">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            Hämtar siffrorna…
          </p>
        ) : null}
        <div ref={slutRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void skicka();
        }}
        className="border-t border-ink/15 px-4 py-3"
      >
        <div className="flex items-center gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ställ en fråga"
            className="focus-ring h-10 min-w-0 flex-1 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
          />
          <button
            type="submit"
            aria-label="Skicka"
            disabled={busy || !text.trim()}
            className="focus-ring inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-input bg-ink text-paper hover:bg-ink2 disabled:opacity-40"
          >
            <Send className="h-4 w-4" aria-hidden />
          </button>
        </div>

        {fel ? (
          <p role="alert" className="mt-2 break-words text-[0.8125rem] text-danger">
            {fel}
          </p>
        ) : null}
      </form>
    </section>
  );
}
