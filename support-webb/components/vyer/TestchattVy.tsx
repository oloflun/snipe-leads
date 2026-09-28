"use client";

import { Loader2, Send } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { BAS, type Jobb } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Testchatten: skriv ett låtsas-kundmejl och se exakt vad agenten hade
 * svarat, mot din riktiga kunskapsbas. Körningen är märkt test i loggen
 * (is_test) och skickar ingenting till någon kund.
 */

type Rad = { roll: "kund" | "agent"; text: string };

const POLL_MS = 3000;
const MAX_POLL = 40;

export function TestchattVy() {
  const [rader, setRader] = useState<Rad[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  async function skicka(e: React.FormEvent) {
    e.preventDefault();
    const meddelande = text.trim();
    if (!meddelande || busy) return;
    setBusy(true);
    setFel(null);
    setRader((f) => [...f, { roll: "kund", text: meddelande }]);
    setText("");

    try {
      const start = await fetch(`${BAS}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: meddelande, is_test: true })
      }).then((s) => readJson<{ job_id?: string }>(s));
      if (!start?.job_id) throw new Error("Agenten tog inte emot meddelandet.");

      for (let i = 0; i < MAX_POLL; i += 1) {
        const jobb = await fetch(`${BAS}/jobs/${start.job_id}`).then((s) => readJson<Jobb>(s));
        if (jobb?.status === "completed") {
          const svar = jobb.result?.reply;
          if (typeof svar !== "string" || !svar.trim()) {
            throw new Error("Agenten blev klar utan läsbart svar.");
          }
          setRader((f) => [...f, { roll: "agent", text: svar }]);
          setBusy(false);
          return;
        }
        if (jobb?.status === "failed") {
          throw new Error(jobb.error || "Agenten föll utan besked.");
        }
        await new Promise((klar) => setTimeout(klar, POLL_MS));
      }
      throw new Error("Agenten svarade inte i tid — prova igen om en stund.");
    } catch (orsak) {
      setRader((f) => f.slice(0, -1));
      setText(meddelande);
      setFel(felmeddelande(orsak));
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100dvh-5rem)] flex-col space-y-6">
      <PageHeader rubrik="Testchatt" />

      <div className="thin-scrollbar flex min-h-[18rem] flex-1 flex-col gap-3 overflow-y-auto rounded-panel border border-ink/15 bg-paper2/40 px-4 py-4">
        {rader.length === 0 ? (
          <p className="my-auto text-center text-[0.875rem] text-ink-subtle">Skriv en kundfråga nedan.</p>
        ) : null}
        {rader.map((rad, i) => (
          <div
            key={i}
            className={cn(
              "max-w-[46rem] rounded-card px-3.5 py-2.5 text-[0.9375rem] leading-6",
              rad.roll === "kund"
                ? "ml-auto bg-ink text-paper"
                : "border border-ink/15 bg-paper text-ink/85"
            )}
          >
            <p className="whitespace-pre-wrap">{rad.text}</p>
          </div>
        ))}
        {busy ? (
          <p className="flex items-center gap-2 text-[0.8125rem] text-mineral">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            Agenten skriver …
          </p>
        ) : null}
      </div>

      <form onSubmit={skicka}>
        <div className="flex items-center gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Skriv ett kundmejl på låtsas"
            className="focus-ring h-11 min-w-0 flex-1 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
          />
          <button
            type="submit"
            aria-label="Skicka"
            disabled={busy || !text.trim()}
            className="focus-ring inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-input bg-ink text-paper transition-colors hover:bg-ink2 disabled:opacity-40"
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
    </div>
  );
}
