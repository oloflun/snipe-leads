"use client";

import { Suspense } from "react";
import { IrisKorningar, type KorningsRad } from "@/components/leads/IrisKorningar";

/**
 * Förhandsvisning (2026-11-25): Leads › Körningar med syntetiska rader, ingen
 * databas (IrisKorningar:s demoRader, ingen hämtning och ingen styrning).
 * Fasta tider. Lägena:
 *  - en vilande körning: "Letar vidare" i statuscellen, "8 av 10, letar
 *    vidare: <skäl>" i utfallscellen (korning.vila, Antons regel 2026-11-24),
 *  - en klar körning som nådde målet,
 *  - en gammal rad som slutade på taket (slutet "tak" finns inte längre).
 */
const RADER: KorningsRad[] = [
  {
    job_id: "00000000-0000-4000-a000-0000000000e1",
    status: "processing",
    scope: "batch",
    is_test: false,
    created_at: "2026-11-24T06:00:00Z",
    updated_at: "2026-11-24T08:40:00Z",
    completed_at: null,
    error: null,
    korning: {
      mal: 10,
      levererade: 8,
      undersokta: 46,
      pagaende: 0,
      klar: false,
      slut_orsak: null,
      scope: "research_and_draft",
      struktur: "a",
      tratt_antal: 38,
      jobs_antal: 46,
      vilande: { sedan: "2026-11-24T08:40:00Z", skal: "registret" }
    }
  },
  {
    job_id: "00000000-0000-4000-a000-0000000000e2",
    status: "completed",
    scope: "batch",
    is_test: false,
    created_at: "2026-11-21T06:00:00Z",
    updated_at: "2026-11-21T07:10:00Z",
    completed_at: "2026-11-21T07:10:00Z",
    error: null,
    korning: {
      mal: 10,
      levererade: 10,
      undersokta: 27,
      pagaende: 0,
      klar: true,
      slut_orsak: "klar",
      scope: "research_and_draft",
      struktur: "b",
      tratt_antal: 17,
      jobs_antal: 27
    }
  },
  {
    job_id: "00000000-0000-4000-a000-0000000000e3",
    status: "completed",
    scope: "batch",
    is_test: true,
    created_at: "2026-10-30T09:00:00Z",
    updated_at: "2026-10-30T10:30:00Z",
    completed_at: "2026-10-30T10:30:00Z",
    error: null,
    korning: {
      mal: 5,
      levererade: 3,
      undersokta: 20,
      pagaende: 0,
      tak: 20,
      klar: true,
      slut_orsak: "tak",
      scope: "research",
      tratt_antal: 17,
      jobs_antal: 20
    }
  }
];

export default function Page() {
  return (
    <main className="appyta mx-auto min-h-dvh max-w-6xl bg-paper px-4 py-10 text-ink sm:px-8">
      {/* useSearchParams i IrisKorningar kräver en Suspense-gräns vid förrendering. */}
      <Suspense>
        <IrisKorningar demoRader={RADER} />
      </Suspense>
    </main>
  );
}
