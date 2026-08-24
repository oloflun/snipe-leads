"use client";

import { Loader2, Paperclip, Send, ShieldAlert, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Bokföringsassistenten — en EGEN agent, inte kundtjänstagenten i ny hatt.
 *
 * ## Vad som är eget, och vad som bara delar adress
 *
 * Värt att säga rakt ut, eftersom URL:en lurar ögat: anropet går till
 * `/api/snajp-support/bookkeeping/chat`, men `snajp-support` är namnet på
 * BACKEND-TJÄNSTEN som alla agenter bor i — leads anropar
 * `/api/snajp-support/leads/...` på samma sätt. Det är en proxy-prefix, inte
 * kundtjänstagenten.
 *
 * Bakom den ligger `build_bookkeeping_chat_agent()` i
 * `app/agent/bookkeeping_agent.py`: egen systemprompt, egna verktyg
 * (`bookkeeping_chat_tools.py`), egen grind. Ingen rad delas med
 * `support_agent.py`, och ingen av dem importerar den andra.
 *
 * ## Vad den kan svara på, och vad den vägrar
 *
 * Den hämtar siffror med verktyg och formulerar svaret i ord. Varje krontal i
 * svaret måste komma från ett verktygsanrop i samma tur; en kontroll i
 * backenden (INV-BOOK-003, `bookkeeping/beloppsgrind.py`) fäller svaret annars
 * och kunden får en ärlig rad om att assistenten inte kunde härleda talet.
 *
 * Det syns i gränssnittet: ett fällt svar märks, i stället för att se ut som
 * vilket svar som helst. Att dölja det hade varit att dölja exakt den
 * information som gör resten av svaren trovärdiga.
 *
 * ## Filer går genom samma väg som panelen
 *
 * Kvittot laddas upp som en del av chattmeddelandet, och backenden läser det
 * med `ta_emot_underlag` — exakt samma funktion som uppladdningspanelen
 * anropar. Det blir alltså ett riktigt underlag med verifikat, inte en bild i
 * en chattlogg, och det dyker upp i listan till vänster.
 *
 * ## Varför meddelandeytan har en fast höjd
 *
 * Panelen är klistrad i sidokolumnen (`lg:sticky` i BookkeepingView). En yta
 * som växer med samtalet hade tryckt ut sin egen botten ur skärmen efter fem
 * turer, och då sitter inmatningsfältet utanför vyn — alltså precis det
 * klistringen skulle förhindra.
 */

const BAS = "/api/snajp-support/bookkeeping";

/** Speglar `LASBARA_MIMETYPER` i app/bookkeeping/underlag.py. */
const LASBARA = ".pdf,image/jpeg,image/png,image/webp,image/heic";

type Rad = {
  roll: "kund" | "assistent";
  text: string;
  /** False när INV-BOOK-003 fällde svaret. Bara meningsfullt för assistenten. */
  grundad?: boolean;
  /** Filnamnet, när turen bar ett underlag. */
  bilaga?: string;
};

const FORSLAG = [
  "Sammanfatta perioden",
  "Vilka underlag behöver granskas?",
  "Vilket konto hamnar drivmedel på?"
];

export function BokforingChatt() {
  const [rader, setRader] = useState<Rad[]>([]);
  const [text, setText] = useState("");
  const [fil, setFil] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const filRef = useRef<HTMLInputElement>(null);
  const slutRef = useRef<HTMLDivElement>(null);

  // Rullar till senaste svaret INUTI meddelandeytan. `block: "nearest"` och
  // inte "start": annars rycker hela sidan när panelen är klistrad.
  useEffect(() => {
    if (rader.length) slutRef.current?.scrollIntoView({ block: "nearest" });
  }, [rader, busy]);

  async function skicka(fraga?: string) {
    const meddelande = (fraga ?? text).trim();
    if (!meddelande && !fil) return;

    setBusy(true);
    setFel(null);

    const min: Rad = { roll: "kund", text: meddelande, bilaga: fil?.name };
    // Historiken skickas som den SÅG UT före den här turen. Backenden bär bara
    // text vidare — verktygssvar från en tidigare tur får inte grunda ett
    // belopp i den här, eftersom siffrorna kan ha ändrats sedan dess.
    const historik = rader.map((r) => ({ roll: r.roll, text: r.text }));
    setRader((f) => [...f, min]);
    setText("");

    try {
      let svar: Response;
      if (fil) {
        const kropp = new FormData();
        kropp.append("meddelande", meddelande);
        kropp.append("historik", JSON.stringify(historik));
        kropp.append("fil", fil);
        svar = await fetch(`${BAS}/chat`, { method: "POST", body: kropp });
      } else {
        svar = await fetch(`${BAS}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ meddelande, historik })
        });
      }

      const data = await svar.json().catch(() => null);
      if (!svar.ok) {
        // `error` FÖRE `detail`, och båda före den generiska texten.
        //
        // Proxyn svarar {"error": "..."} — bland annat med den begripliga
        // texten om att AI-leverantörens kvot är slut (se 505fa4c: "kvoten är
        // inte en krasch och ska inte se ut som en"). Backendens egna 422:or
        // svarar {"detail": "..."}.
        //
        // Utan `error` visade chatten "Assistenten svarade inte (429)" medan
        // servern precis förklarat exakt vad som hänt och vad kunden kan göra.
        // Uppmätt live 2026-08-24, med kvoten faktiskt slut.
        setFel(
          typeof data?.error === "string"
            ? data.error
            : typeof data?.detail === "string"
              ? data.detail
              : `Assistenten svarade inte (${svar.status}).`
        );
        return;
      }

      setRader((f) => [
        ...f,
        { roll: "assistent", text: data.reply, grundad: data.grundad !== false }
      ]);
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte nå assistenten.");
    } finally {
      setFil(null);
      if (filRef.current) filRef.current.value = "";
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col rounded-panel border border-ink/15 bg-paper2/40">
      <header className="flex items-center gap-2 border-b border-ink/15 px-4 py-3">
        <Sparkles className="h-4 w-4 shrink-0 text-ochre" aria-hidden />
        <h2 className="text-[0.9375rem] font-semibold text-ink">Bokföringsassistenten</h2>
      </header>

      <p className="px-4 pt-3 text-[0.8125rem] leading-5 text-ink/55">
        Fråga om en period, ett underlag eller ett konto. Den hämtar siffrorna ur
        din bokföring och räknar aldrig själv. Du kan också släppa ett kvitto här.
      </p>

      {/* Meddelandeytan. Fast höjd med egen rullning — se docstringen. */}
      <div className="flex min-h-[16rem] flex-col gap-3 overflow-y-auto px-4 py-4 lg:max-h-[26rem]">
        {rader.length === 0 ? (
          <div className="grid gap-2">
            {FORSLAG.map((f) => (
              <button
                key={f}
                type="button"
                disabled={busy}
                onClick={() => void skicka(f)}
                className="focus-ring rounded-input border border-ink/15 bg-paper px-3 py-2 text-left text-[0.8125rem] text-ink/70 hover:border-ink/35 hover:text-ink"
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
                : "border border-ink/15 bg-paper text-ink/85"
            )}
          >
            {rad.bilaga ? (
              <p
                className={cn(
                  "mb-1.5 flex items-center gap-1.5 text-[0.75rem]",
                  rad.roll === "kund" ? "text-paper/70" : "text-mineral"
                )}
              >
                <Paperclip className="h-3 w-3 shrink-0" aria-hidden />
                {rad.bilaga}
              </p>
            ) : null}
            <p className="whitespace-pre-wrap">{rad.text}</p>
            {rad.roll === "assistent" && rad.grundad === false ? (
              // Ett fällt svar MÄRKS. Se docstringen: att dölja grinden hade
              // dolt just det som gör de andra svaren trovärdiga.
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
        {fil ? (
          <p className="mb-2 flex items-center gap-2 text-[0.8125rem] text-ink/70">
            <Paperclip className="h-3.5 w-3.5 shrink-0" aria-hidden />
            <span className="min-w-0 truncate">{fil.name}</span>
            <button
              type="button"
              onClick={() => {
                setFil(null);
                if (filRef.current) filRef.current.value = "";
              }}
              aria-label="Ta bort bilagan"
              className="focus-ring rounded-input p-0.5 text-ink/45 hover:text-ink"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          </p>
        ) : null}

        <div className="flex items-center gap-2">
          <label
            title="Bifoga kvitto eller faktura"
            className="focus-ring inline-flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-input border border-ink/15 text-ink/60 hover:border-ink/35 hover:text-ink"
          >
            <Paperclip className="h-4 w-4" aria-hidden />
            <span className="sr-only">Bifoga underlag</span>
            <input
              ref={filRef}
              type="file"
              accept={LASBARA}
              onChange={(e) => setFil(e.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>

          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ställ en fråga"
            className="focus-ring h-10 min-w-0 flex-1 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
          />

          <button
            type="submit"
            aria-label="Skicka"
            disabled={busy || (!text.trim() && !fil)}
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
