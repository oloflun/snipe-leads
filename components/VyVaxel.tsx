"use client";

import { Eye, ShieldCheck } from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { bytVy } from "@/lib/actions/vy";
import { cn } from "@/lib/utils";

/**
 * Admin / Demo. Bara synlig för plattformsadmin, och den enda adminkontroll
 * som finns kvar i demovyn — annars vore den inte en demo av kundens produkt.
 *
 * Formulär och inte onClick, av samma skäl som utloggningen i AppShell:
 * `bytVy` är en server action, och knappen fungerar innan JavaScript laddat.
 * Två submit-knappar i samma formulär, var och en med `name="vy"` — den som
 * trycks är den som hamnar i FormData.
 *
 * Villkoret på `isPlatformAdmin` är en ledtråd, inte en grind. Grinden är
 * `getPlatformAdmin()` i både `bytVy` och `aktivVy` — en manipulerad flagga
 * ritar alltså en knapp som inte gör någonting.
 */
/** `ton="rail"`: mörk variant för adminens sidopanel, se BytKund. */
export function VyVaxel({ ton = "ljus" }: Readonly<{ ton?: "ljus" | "rail" }> = {}) {
  const { isPlatformAdmin, vy } = useDashboard();

  if (!isPlatformAdmin) {
    return null;
  }

  const segment = (
    varde: "admin" | "demo",
    etikett: string,
    Ikon: typeof ShieldCheck
  ) => (
    <button
      key={varde}
      type="submit"
      name="vy"
      value={varde}
      aria-current={vy === varde ? "true" : undefined}
      className={cn(
        "focus-ring inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-input px-2.5 text-[13px] font-medium transition-colors",
        ton === "rail"
          ? vy === varde
            ? "bg-paper/15 text-paper"
            : "text-paper-subtle hover:text-paper"
          : vy === varde
            ? "bg-paper text-ink shadow-sm"
            : "text-ink-subtle hover:text-ink"
      )}
    >
      <Ikon className="h-3.5 w-3.5" aria-hidden />
      {etikett}
    </button>
  );

  return (
    <form
      action={bytVy}
      className={cn(
        "flex items-center gap-0.5 rounded-input p-0.5",
        ton === "rail" ? "bg-paper/[0.06]" : "bg-paper2"
      )}
    >
      {segment("admin", "Admin", ShieldCheck)}
      {segment("demo", "Demo", Eye)}
    </form>
  );
}
