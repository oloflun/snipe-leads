"use client";

import { Samtalslista } from "@/components/leads/Samtalslista";

/**
 * Förhandsvisning (2026-10-08): Leads › Samtal med syntetiska bolag, ingen
 * databas. Utfallen sparas bara i webbläsaren; samma mönster som
 * /forhandsvisning/leads-skickat.
 */
export default function Page() {
  return (
    <main className="appyta mx-auto min-h-dvh max-w-6xl bg-paper px-4 py-10 text-ink sm:px-8">
      <Samtalslista demo />
    </main>
  );
}
