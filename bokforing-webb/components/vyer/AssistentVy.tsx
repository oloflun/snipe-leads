"use client";

import { Loader2, Paperclip, Send, ShieldAlert, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { BAS, LASBARA } from "@/lib/api";
import { profilSomKontext, useProfil } from "@/lib/profil";
import { cn } from "@/lib/utils";

/**
 * Assistenten — samma agent som i huvudappen (`build_bookkeeping_chat_agent`
 * i snajp-support), här som en hel flik i stället för en sidopanel.
 *
 * Tre saker är ärvda beslut därifrån och ska inte "förbättras" bort:
 *
 * 1. Varje krontal i ett svar måste komma från ett verktygsanrop i samma tur
 *    (INV-BOOK-003). Ett fällt svar MÄRKS i vyn — att dölja grinden hade dolt
 *    det som gör de andra svaren trovärdiga.
 * 2. Historiken skickas som den såg ut FÖRE turen, och vid fel läggs frågan
 *    och filen tillbaka så att ett nytt klick gör om exakt samma tur.
 * 3. Ett bifogat kvitto går genom samma väg som uppladdningspanelen
 *    (`ta_emot_underlag`) och blir ett riktigt underlag, inte en bild i en
 *    chattlogg.
 *
 * Företagsprofilen från Inställningar skickas som en märkt bakgrundsrad
 * FÖRST i historiken — synligt deklarerat under rubriken, inte insmuget.
 */

type Rad = {
  roll: "kund" | "assistent";
  text: string;
  grundad?: boolean;
  bilaga?: string;
};

const FORSLAG = [
  "Sammanfatta perioden",
  "Hur mycket moms ska jag betala?",
  "Vilka underlag behöver granskas?",
  "Vilket konto hamnar drivmedel på?"
];

const NATFEL = [
  "Jag når inte assistenten just nu. Kontrollera uppkopplingen och prova igen — det du skrev står kvar.",
  "Anropet kom inte fram. Vänta en liten stund och tryck på skicka igen, så gör vi ett nytt försök."
];

const SVARSFEL = [
  "Assistenten fick inte fram ett svar den här gången. Prova gärna igen om en liten stund — frågan står kvar.",
  "Något hakade upp sig när svaret skulle tas fram. Skicka frågan igen, eller formulera den på ett annat sätt."
];

function slumpad(texter: string[]): string {
  return texter[Math.floor(Math.random() * texter.length)];
}

export function AssistentVy() {
  const { profil } = useProfil();
  const [rader, setRader] = useState<Rad[]>([]);
  const [text, setText] = useState("");
  const [fil, setFil] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const filRef = useRef<HTMLInputElement>(null);
  const slutRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (rader.length) slutRef.current?.scrollIntoView({ block: "nearest" });
  }, [rader, busy]);

  const kontext = profilSomKontext(profil);

  async function skicka(fraga?: string) {
    const meddelande = (fraga ?? text).trim();
    if (!meddelande && !fil) return;

    setBusy(true);
    setFel(null);

    const min: Rad = { roll: "kund", text: meddelande, bilaga: fil?.name };
    const historik: Array<{ roll: string; text: string }> = [
      ...(kontext ? [{ roll: "kund", text: kontext }] : []),
      ...rader.map((r) => ({ roll: r.roll, text: r.text }))
    ];
    setRader((f) => [...f, min]);
    setText("");

    const aterstall = (feltext: string) => {
      setRader((f) => f.slice(0, -1));
      setText(meddelande);
      setFel(feltext);
    };

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
        console.error("AssistentVy: 200-svar utan reply-fält:", data);
        aterstall(slumpad(SVARSFEL));
        return;
      }

      setRader((f) => [
        ...f,
        { roll: "assistent", text: data.reply, grundad: data.grundad !== false }
      ]);
      setFil(null);
      if (filRef.current) filRef.current.value = "";
    } catch (orsak) {
      console.error("AssistentVy:", orsak);
      aterstall(slumpad(NATFEL));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100dvh-5rem)] flex-col space-y-6">
      <PageHeader
        rubrik="Assistent"
        beskrivning="Fråga om en period, ett underlag eller ett konto. Assistenten hämtar siffrorna ur din bokföring med verktyg och räknar aldrig själv — ett svar där en siffra inte kunde härledas märks tydligt."
      />

      <p className="text-[0.8125rem] leading-5 text-ink/50">
        {kontext ? (
          <>
            <Sparkles className="mr-1.5 inline h-3.5 w-3.5 text-ochre" aria-hidden />
            Assistenten känner till din företagsprofil från Inställningar
            {profil.foretagsnamn ? ` (${profil.foretagsnamn})` : ""} och riktar svaren efter den.
          </>
        ) : (
          <>
            Fyll i din företagsprofil under{" "}
            <Link href="/installningar" className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4">
              Inställningar
            </Link>{" "}
            — namn, organisationsnummer och webbplats — så känner assistenten till ditt företag.
          </>
        )}
      </p>

      {/* Meddelandeytan tar resten av höjden; formuläret står stilla under. */}
      <div className="thin-scrollbar flex min-h-[18rem] flex-1 flex-col gap-3 overflow-y-auto rounded-panel border border-ink/15 bg-paper2/40 px-4 py-4">
        {rader.length === 0 ? (
          <div className="my-auto">
            <p className="text-center text-[0.875rem] text-ink/50">Börja med en av de här, eller skriv fritt:</p>
            <div className="mx-auto mt-3 grid max-w-[34rem] gap-2 sm:grid-cols-2">
              {FORSLAG.map((f) => (
                <button
                  key={f}
                  type="button"
                  disabled={busy}
                  onClick={() => void skicka(f)}
                  className="focus-ring rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-left text-[0.875rem] text-ink/70 transition-colors hover:border-ink/35 hover:text-ink"
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
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
            Hämtar siffrorna …
          </p>
        ) : null}
        <div ref={slutRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void skicka();
        }}
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
            className="focus-ring inline-flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-input border border-ink/15 text-ink/60 transition-colors hover:border-ink/35 hover:text-ink"
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
            placeholder="Ställ en fråga om din bokföring"
            className="focus-ring h-11 min-w-0 flex-1 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
          />

          <button
            type="submit"
            aria-label="Skicka"
            disabled={busy || (!text.trim() && !fil)}
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
