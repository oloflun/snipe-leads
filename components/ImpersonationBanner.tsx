"use client";

import { Eye } from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { bytVy } from "@/lib/actions/vy";

/**
 * "Du tittar som <kund> — admin-läge."
 *
 * ## Varför den är omöjlig att missa
 *
 * Kundbesöket renderar kundens RIKTIGA ärenden och mejladresser i exakt samma
 * gränssnitt som adminens egen arbetsyta. Utan en tydlig markör är de två
 * lägena visuellt identiska, och den som glömmer vilket läge den är i skriver
 * förr eller senare i fel kunds arbetsyta — eller, värre, tror att en kunds
 * data är vår egen och delar en skärmdump.
 *
 * Därför: full bredd, ochre, överst, `sticky` ovanför headern, och den syns på
 * VARJE undersida eftersom AppShell bär den. En banner som bara finns på
 * startsidan är en banner man scrollar förbi en gång och sedan aldrig ser.
 *
 * Utgången ligger i bannern och inte i en meny. Den som vill ut ska inte behöva
 * leta, och `VyVaxel` visar bara Admin/Demo — kundläget är ett tredje läge som
 * inte hör hemma i den växeln.
 *
 * Villkoret på `impersonation` är en ritregel, inte en grind. Grinden är
 * `aktivVy()` och `tenant_api_key_for_admin()` (migration 042): en manipulerad
 * flagga i klienten ritar en banner utan att ge tillgång till någonting.
 */
export function ImpersonationBanner() {
  const { impersonation } = useDashboard();

  if (!impersonation) {
    return null;
  }

  return (
    <div
      role="status"
      className="safe-top sticky top-0 z-40 border-b border-ochre/50 bg-ochre/20"
    >
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-2 md:px-6">
        <Eye className="h-4 w-4 shrink-0 text-ochre" aria-hidden />
        <p className="text-[13px] font-medium text-ink">
          Du testar som <strong className="font-semibold">{impersonation.namn}</strong>.
        </p>
        <p className="text-[13px] text-ink/60">
          Allt du kör här är test och syns inte på kundens riktiga profil. Inga skärmdumpar.
        </p>

        <form action={bytVy} className="ml-auto">
          <button
            type="submit"
            name="vy"
            value="admin"
            className="focus-ring inline-flex min-h-9 items-center rounded-input bg-paper px-3 text-[13px] font-medium text-ink shadow-sm"
          >
            Tillbaka till adminytan
          </button>
        </form>
      </div>
    </div>
  );
}
