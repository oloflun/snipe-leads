/**
 * Massutskick som jobb: starta, följ förloppet, få utfallet.
 *
 * "Godkänn och skicka alla" går igenom utkasten i tur och ordning på servern
 * och tar ofta längre än en begäran får ta. Starten svarar med ett jobb-id
 * (snajp-support/app/jobs/bakgrund.py); vyn hämtar förloppet (`klara` av
 * `totalt`) och till sist utfallet. En hämtning som faller hoppas över:
 * utskicket går vidare på servern ändå.
 */
import { readJsonBody } from "@/lib/http/json";
import { taligHamtning } from "@/lib/leads/pollning";

export type Utskicksutfall = {
  skickade: number;
  vantar_pa_fonstret: number;
  stoppade: { company_name: string | null; skal: string | null }[];
};

export type Utskicksforlopp = { klara: number; totalt: number };

type Jobbsvar = {
  status?: string;
  forlopp?: Utskicksforlopp | null;
  result?: Partial<Utskicksutfall> | null;
  error?: string | null;
  detail?: string;
};

/** Startar utskicket. `vag` är backendens väg under /api/snajp-support. */
export async function startaUtskick(vag: string): Promise<string> {
  const response = await fetch(`/api/snajp-support${vag}`, { method: "POST", cache: "no-store" });
  const kropp = await readJsonBody<{ job_id?: string; error?: string; detail?: string }>(response);
  if (!response.ok || !kropp?.job_id) {
    throw new Error(
      (typeof kropp?.error === "string" && kropp.error) ||
        (typeof kropp?.detail === "string" && kropp.detail) ||
        "Utskicket kunde inte starta. Försök igen om en stund. / The send could not start. Try again shortly."
    );
  }
  return kropp.job_id;
}

/** Följer utskicket tills det är klart. Kastar med serverns besked om det föll. */
export async function foljUtskick(
  jobId: string,
  vidForlopp: (forlopp: Utskicksforlopp) => void
): Promise<Utskicksutfall> {
  const hamta = taligHamtning(async () => {
    const response = await fetch(`/api/snajp-support/leads/jobb/${encodeURIComponent(jobId)}`, {
      cache: "no-store"
    });
    const kropp = await readJsonBody<Jobbsvar>(response);
    if (!response.ok) throw new Error(kropp?.detail ?? `status ${response.status}`);
    return kropp ?? {};
  });
  // En timme: ett utskick på flera hundra mejl ryms med marginal.
  for (let varv = 0; varv < 3600; varv += 1) {
    const jobb = await hamta();
    if (jobb?.forlopp) vidForlopp(jobb.forlopp);
    if (jobb?.status === "completed") {
      return {
        skickade: jobb.result?.skickade ?? 0,
        vantar_pa_fonstret: jobb.result?.vantar_pa_fonstret ?? 0,
        stoppade: jobb.result?.stoppade ?? []
      };
    }
    if (jobb?.status === "failed") {
      throw new Error(
        jobb.error ??
          "Utskicket gick inte att slutföra. Det som hann skickas är skickat. / The send could not be completed. What was already sent stays sent."
      );
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(
    "Utskicket pågår fortfarande. Ladda om sidan för att se läget. / The send is still running. Reload the page to see where it stands."
  );
}

/** Jobb-id:t för ett pågående utskick, så att förloppet finns kvar efter en omladdning. */
export function minnsUtskick(nyckel: string, jobId: string | null): void {
  try {
    if (jobId) window.sessionStorage.setItem(`snajp:utskick:${nyckel}`, jobId);
    else window.sessionStorage.removeItem(`snajp:utskick:${nyckel}`);
  } catch {
    // Blockerad lagring: förloppet visas ändå, bara inte efter en omladdning.
  }
}

export function mindUtskick(nyckel: string): string | null {
  try {
    return window.sessionStorage.getItem(`snajp:utskick:${nyckel}`);
  } catch {
    return null;
  }
}
