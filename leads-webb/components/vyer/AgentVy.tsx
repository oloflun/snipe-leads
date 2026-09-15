"use client";

import { Loader2, Play } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { btnPrimary } from "@/components/ui";
import { BAS, type Jobb } from "@/lib/api";
import { HttpJsonError, felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Kör agenten — en körning från knapp till klart, med ärlig fasrapport.
 *
 * POST /leads/runs/batch svarar 202 med sökjobbet; när det är klart ligger
 * research-jobben i resultatet (samma kedja som huvudappens LeadsRunForm).
 * Vyn pollar GET /jobs/{id} var femte sekund och säger vad som faktiskt
 * händer: söker → researchar → klart. Fel visas med backendens egen mening —
 * budgetgrinden och LLM-grinden svarar begripligt själva.
 */

type Fas =
  | { lage: "vilar" }
  | { lage: "soker" }
  | { lage: "researchar"; klara: number; totalt: number }
  | { lage: "klart"; antal: number }
  | { lage: "fel"; text: string };

const POLL_MS = 5000;

export function AgentVy() {
  const [antal, setAntal] = useState(3);
  const [fas, setFas] = useState<Fas>({ lage: "vilar" });
  const avbruten = useRef(false);

  async function pollaTillsKlart(jobId: string): Promise<Jobb> {
    for (;;) {
      if (avbruten.current) throw new Error("Avbruten.");
      const jobb = await fetch(`${BAS}/jobs/${jobId}`).then((s) => readJson<Jobb>(s));
      if (!jobb) throw new Error("Tomt jobbsvar.");
      if (jobb.status === "completed") return jobb;
      if (jobb.status === "failed") {
        throw new Error(jobb.error || "Körningen misslyckades utan besked.");
      }
      await new Promise((klar) => setTimeout(klar, POLL_MS));
    }
  }

  async function kor() {
    setFas({ lage: "soker" });
    avbruten.current = false;
    try {
      const start = await fetch(`${BAS}/leads/runs/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scope: "research_and_draft", limit: antal })
      }).then((s) => readJson<{ jobs: Array<{ job_id: string }> }>(s));
      const sokjobb = start?.jobs?.[0]?.job_id;
      if (!sokjobb) throw new Error("Körningen startade inte — inget jobb kom tillbaka.");

      const sokKlart = await pollaTillsKlart(sokjobb);
      const researchJobb: Array<{ job_id: string }> = Array.isArray(
        (sokKlart.result as { jobs?: unknown })?.jobs
      )
        ? ((sokKlart.result as { jobs: Array<{ job_id: string }> }).jobs)
        : [];

      let klara = 0;
      setFas({ lage: "researchar", klara, totalt: researchJobb.length });
      for (const jobb of researchJobb) {
        await pollaTillsKlart(jobb.job_id);
        klara += 1;
        setFas({ lage: "researchar", klara, totalt: researchJobb.length });
      }
      setFas({ lage: "klart", antal: researchJobb.length });
    } catch (orsak) {
      const text =
        orsak instanceof HttpJsonError && typeof (orsak.body as { error?: string })?.error === "string"
          ? ((orsak.body as { error: string }).error)
          : felmeddelande(orsak);
      setFas({ lage: "fel", text });
    }
  }

  const kör = fas.lage === "soker" || fas.lage === "researchar";

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik="Kör agenten"
        beskrivning="Agenten söker fram bolag som matchar din målgrupp, gör research på varje bolag och skriver utkast till de som kvalificerar sig. Utkasten hamnar i granskningskön — ingenting skickas utan ditt ja."
      />

      <section className="max-w-[38rem]">
        <div className="border-y border-ink/15 py-6">
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">Antal bolag att hämta</span>
            <input
              type="number"
              min={1}
              max={10}
              value={antal}
              disabled={kör}
              onChange={(e) => setAntal(Math.min(10, Math.max(1, Number(e.target.value) || 1)))}
              className="focus-ring mt-1.5 h-11 w-28 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
            />
            <span className="mt-1 block text-[0.8125rem] leading-5 text-ink/50">
              1–10 per körning. Research och utkast tar någon minut per bolag.
            </span>
          </label>

          <button
            type="button"
            disabled={kör}
            onClick={() => void kor()}
            className={cn(btnPrimary, "mt-5")}
          >
            {kör ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Play className="h-4 w-4" aria-hidden />
            )}
            Kör Agent
          </button>

          <div className="mt-4 min-h-[1.5rem] text-[0.9375rem] leading-6" role="status">
            {fas.lage === "soker" ? (
              <span className="text-ink/70">Söker bolag som matchar din målgrupp …</span>
            ) : fas.lage === "researchar" ? (
              <span className="text-ink/70">
                Researchar och skriver utkast: {fas.klara} av {fas.totalt} bolag klara …
              </span>
            ) : fas.lage === "klart" ? (
              <span className="text-moss">
                Klart — {fas.antal} bolag researchade. Se resultatet under{" "}
                <Link href="/prospekt" className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4">
                  Prospekt
                </Link>{" "}
                och godkänn utkasten under{" "}
                <Link href="/granskning" className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4">
                  Granskning
                </Link>
                .
              </span>
            ) : fas.lage === "fel" ? (
              <span className="break-words text-danger">{fas.text}</span>
            ) : null}
          </div>
        </div>
      </section>

      <section aria-label="Så arbetar agenten">
        <h2 className="font-display text-[1.25rem]">Så arbetar agenten</h2>
        <ol className="mt-3 grid gap-y-5 border-y border-ink/15 py-5 sm:grid-cols-3 sm:gap-x-8">
          {[
            {
              rubrik: "Söker",
              text: "Bolag som matchar målgruppen i dina inställningar — bransch, storlek och geografi. Rekryterings- och bemanningsannonser sorteras bort."
            },
            {
              rubrik: "Researchar",
              text: "Varje bolag bedöms mot din målgrupp med källor som går att kontrollera. Bolag som inte håller underkänns med skäl — de får aldrig utkast."
            },
            {
              rubrik: "Skriver — du godkänner",
              text: "Kvalificerade bolag med kontaktväg får ett utkast i granskningskön. Ingenting skickas förrän du sagt ja, och grindarna körs en gång till vid utskick."
            }
          ].map((steg, i) => (
            <li key={steg.rubrik} className="min-w-0">
              <span className="numeral text-[1.75rem] text-ochre">{i + 1}</span>
              <h3 className="mt-2 font-semibold">{steg.rubrik}</h3>
              <p className="mt-1 text-[0.9375rem] leading-6 text-ink/62">{steg.text}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
