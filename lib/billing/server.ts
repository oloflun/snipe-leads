import "server-only";

import type { NextRequest } from "next/server";
import { hasDatabase, sqlAsUser } from "@/lib/db";
import { aktivVy } from "@/lib/vy";
import { getWorkspaceContext } from "@/lib/workspace";

/**
 * Det checkout- och portalroutern delar: vem som får betala, vart Stripe ska
 * skicka tillbaka kunden, och arbetsytans speglade abonnemang.
 */

export type Abonnemang = {
  paket_id: string | null;
  status: string;
  stripe_customer_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  is_test: boolean;
};

type Behorighet =
  | { ok: true; workspaceId: string; userId: string; epost: string | null }
  | { ok: false; status: number; fel: string };

/**
 * Samma tre grindar som paketbytet (lib/actions/plan.ts), av samma skäl:
 * läsrollen får inte ändra något, och i demo- och kundvyn är arbetsytan
 * bakom vyn ADMINENS egen, så ett köp där hade debiterat fel part.
 */
export async function kravBetalare(): Promise<Behorighet> {
  const context = await getWorkspaceContext();
  if (!context) return { ok: false, status: 401, fel: "Du måste vara inloggad." };

  const { arLasare, LASROLL_FEL } = await import("@/lib/auth/lasroll");
  if (arLasare(context)) return { ok: false, status: 403, fel: LASROLL_FEL };

  if ((await aktivVy()).vy !== "admin") {
    return {
      ok: false,
      status: 403,
      fel: "Betalning är avstängd i demo- och kundvy. Arbetsytan bakom vyn är vår egen."
    };
  }
  return {
    ok: true,
    workspaceId: context.workspace.id,
    userId: context.user.id,
    epost: context.user.email ?? null
  };
}

/**
 * Den publika adressen, byggd på x-forwarded-*. Bakom Railways proxy är
 * `request.url` den INTERNA adressen (localhost:8080) — en returlänk byggd på
 * den skickar kunden till en sida som inte finns (uppmätt på bokföringssajten
 * 2026-09-15).
 */
export function publikBas(request: NextRequest): string {
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  if (host) return `${proto.split(",")[0].trim()}://${host.split(",")[0].trim()}`;
  return new URL(request.url).origin;
}

export const FAKTURERINGSSIDA = "/settings/billing";

export async function lasAbonnemang(userId: string): Promise<Abonnemang | null> {
  if (!hasDatabase()) return null;
  try {
    const rader = await sqlAsUser<Abonnemang>(
      userId,
      `select paket_id, status, stripe_customer_id,
              current_period_end::text as current_period_end,
              cancel_at_period_end, is_test
         from public.billing_subscriptions
        where workspace_id = public.current_workspace_id()`
    );
    return rader[0] ?? null;
  } catch {
    // Tabellen finns inte förrän migration 075 körts. En saknad spegel ska
    // ge "inget abonnemang", inte en trasig faktureringssida.
    return null;
  }
}
