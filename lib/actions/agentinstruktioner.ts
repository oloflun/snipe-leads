"use server";

import { revalidatePath } from "next/cache";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { readJsonBody } from "@/lib/http/json";

/**
 * Globala agentinstruktioner och kundprofiler — plattformsadminens skrivyta.
 *
 * ## Varför server actions och inte en /api-route
 *
 * Den befintliga proxyn (`app/api/snajp-support/[...path]`) talar med KUNDENS
 * nyckel, härledd ur sessionen. De här anropen kräver master-nyckeln, och att
 * lägga en master-väg i en route som annars är kundskopad är precis den sortens
 * yta som blir en läcka den dag någon lägger till en parameter.
 *
 * En server action har inte den formen: den är inte adresserbar, den tar inga
 * väg-parametrar, och grinden står i funktionen.
 *
 * ## Grinden
 *
 * `getPlatformAdmin()` i VARJE funktion, inte bara i sidan som renderar
 * formuläret. En server action är en POST-endpoint med ett genererat id —
 * att den bara anropas från en skyddad sida är ett antagande om klienten,
 * och klienten är inte vår.
 *
 * ## Vad texten gör när den sparats
 *
 * Den går in i agentens SYSTEMprompt, först av allt, vid varje steg i varje
 * körning för varje kund. Det är därför den ska vara policy och inte ton —
 * se agent-core/AGENTS.md och app/agentcore/instruktioner.py.
 */

export type Instruktionslage = {
  ravtext: string;
  strukturerad_md: string;
  kalla: string;
  uppdaterad: string | null;
  /** Vad agenten FAKTISKT läser just nu — inklusive fil-fallbacken. */
  aktiv_text: string;
  /** True = ingen rad i databasen, agent-core/AGENTS.md gäller. */
  fran_fil: boolean;
  hash: string;
  historik: {
    id: string;
    kalla: string;
    aktiv: boolean;
    created_at: string;
    ravtext_tecken: number;
    strukturerad_tecken: number;
  }[];
};

export type Sparresultat = {
  success: boolean;
  error?: string;
  /** Modellen kom inte i mål — texten sparades ostrukturerad. Inte ett fel. */
  anmarkning?: string;
  dokument?: string;
};

async function masterFetch<T>(
  path: string,
  init: RequestInit
): Promise<{ data?: T; error?: string }> {
  if (!(await getPlatformAdmin())) {
    return { error: "Kräver plattformsadmin." };
  }
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) {
    return {
      error:
        "SNAJP_MASTER_API_KEY är inte satt i den här miljön. Instruktionerna kan inte nå backenden förrän den finns."
    };
  }

  const response = await proxyWithApiKey(`/api/admin${path}`, init, masterKey);
  const body = await readJsonBody<Record<string, unknown>>(response).catch(() => null);
  if (!response.ok) {
    return {
      error:
        (body?.detail as string | undefined) ??
        (body?.error as string | undefined) ??
        `Backenden svarade ${response.status}.`
    };
  }
  return { data: (body ?? {}) as T };
}

export async function hamtaInstruktioner(): Promise<
  { lage?: Instruktionslage; error?: string }
> {
  const { data, error } = await masterFetch<{ instruktioner: Instruktionslage }>(
    "/instruktioner",
    { method: "GET" }
  );
  return error ? { error } : { lage: data?.instruktioner };
}

/**
 * Strukturera utan att spara.
 *
 * Skild från sparandet med flit: den som vill se vad modellen gör av sina
 * anteckningar ska kunna göra det utan att den aktiva instruktionen byts under
 * en pågående körning.
 */
export async function forhandsgranskaInstruktioner(ravtext: string): Promise<Sparresultat> {
  const { data, error } = await masterFetch<{
    dokument: string;
    anmarkning: string;
  }>("/instruktioner/forhandsgranska", {
    method: "POST",
    body: JSON.stringify({ ravtext })
  });
  if (error) return { success: false, error };
  return {
    success: true,
    dokument: data?.dokument ?? "",
    anmarkning: data?.anmarkning || undefined
  };
}

export async function sparaInstruktioner(input: {
  ravtext: string;
  /** Satt = användaren redigerade utkastet och vill INTE ha det omstrukturerat. */
  strukturerad_md?: string;
}): Promise<Sparresultat> {
  const { data, error } = await masterFetch<{
    instruktioner: { strukturerad_md: string; anmarkning: string };
  }>("/instruktioner", {
    method: "PUT",
    body: JSON.stringify({
      ravtext: input.ravtext,
      strukturerad_md: input.strukturerad_md ?? null,
      strukturera: !input.strukturerad_md
    })
  });
  if (error) return { success: false, error };

  revalidatePath("/admin/installningar/agentinstruktioner");
  return {
    success: true,
    dokument: data?.instruktioner.strukturerad_md ?? "",
    anmarkning: data?.instruktioner.anmarkning || undefined
  };
}

// -- Kundprofilen ---------------------------------------------------------

export type Kundprofil = {
  tenant: { id: string; slug: string | null; name: string };
  agent_type: string;
  instruktioner_rav: string;
  instruktioner_md: string;
  tone: string;
  taxonomy: string[];
  language_policy: string;
  status: string;
  pinned_pack_version: string | null;
  soul: string;
  affarskontext: string;
  installningar: Record<string, unknown>;
  kb_artiklar: number;
  instruktionshash: string;
  global_fran_fil: boolean;
  position: Record<string, string>;
};

export async function hamtaKundprofil(
  tenantId: string,
  agentType = "support"
): Promise<{ profil?: Kundprofil; error?: string }> {
  const { data, error } = await masterFetch<{ profil: Kundprofil }>(
    `/tenants/${encodeURIComponent(tenantId)}/profil?agent_type=${encodeURIComponent(agentType)}`,
    { method: "GET" }
  );
  return error ? { error } : { profil: data?.profil };
}

/**
 * Sparar EN sektion. Utelämnade fält rörs inte.
 *
 * `undefined` (utelämnat) och `""` (tom sträng) betyder olika saker hela vägen
 * ner i databasen: det första låter fältet vara, det andra nollställer det.
 * Utan den skillnaden hade ett formulär som sparar en sektion i taget raderat
 * kundens röstdokument varje gång någon ändrade tonen.
 */
export async function sparaKundprofil(
  tenantId: string,
  falt: {
    agent_type?: string;
    instruktioner_rav?: string;
    instruktioner_md?: string;
    tone?: string;
    soul?: string;
    affarskontext?: string;
  }
): Promise<Sparresultat & { sparat?: string[] }> {
  const { data, error } = await masterFetch<{ sparat: string[]; anmarkning: string }>(
    `/tenants/${encodeURIComponent(tenantId)}/profil`,
    {
      method: "PUT",
      body: JSON.stringify({
        agent_type: falt.agent_type ?? "support",
        ...falt,
        strukturera: falt.instruktioner_md === undefined
      })
    }
  );
  if (error) return { success: false, error };

  revalidatePath("/admin/kunder");
  return {
    success: true,
    sparat: data?.sparat ?? [],
    anmarkning: data?.anmarkning || undefined
  };
}
