"use server";

import { revalidatePath } from "next/cache";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { readJsonBody } from "@/lib/http/json";

export type KonverteraRapport = {
  ok: boolean;
  apply?: boolean;
  meddelande?: string;
  fel?: string;
  fran?: { slug: string; id: string; name?: string };
  till?: { slug: string; id: string; name?: string };
  kunskapsbas?: { fran: number; till: number };
  rostdokument?: { fran: number; till: number };
  fackregler?: { fran: number; till: number };
  prospekt?: { id: string; namn: string | null; atgard: string; detalj?: string[] }[];
};

export async function konverteraTestkund(input: {
  fran: string;
  till: string;
  apply: boolean;
  prospekt?: string[];
}): Promise<{ rapport?: KonverteraRapport; error?: string }> {
  if (!(await getPlatformAdmin())) {
    return { error: "Kräver plattformsadmin." };
  }
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) {
    return { error: "SNAJP_MASTER_API_KEY är inte satt i den här miljön." };
  }

  const response = await proxyWithApiKey(
    "/api/admin/konvertera",
    {
      method: "POST",
      body: JSON.stringify({
        fran: input.fran,
        till: input.till,
        apply: input.apply,
        prospekt: input.prospekt ?? []
      })
    },
    masterKey
  );
  const body = await readJsonBody<{ rapport?: KonverteraRapport; detail?: string; error?: string }>(
    response
  ).catch(() => null);
  if (!response.ok) {
    return {
      error:
        (typeof body?.detail === "string" ? body.detail : null) ??
        body?.error ??
        `Backenden svarade ${response.status}.`
    };
  }
  if (input.apply) {
    revalidatePath("/admin/kunder");
  }
  return { rapport: body?.rapport };
}
