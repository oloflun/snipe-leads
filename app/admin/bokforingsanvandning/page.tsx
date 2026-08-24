import { Bokforingsanvandning } from "@/components/admin/Bokforingsanvandning";
import { listRuns, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

// Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
// Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
export const maxDuration = 60;

/**
 * Bokföringsagentens användning, för plattformsadmin.
 *
 * Egen sida och inte en flik i `/admin/korningar`: den sidan listar ENSKILDA
 * körningar för felsökning, medan den här svarar på en annan fråga — hur
 * mycket produkten faktiskt används, och av vem. Att svara på båda i samma vy
 * hade betytt en tabell som är för lång för det ena och för grov för det andra.
 *
 * ## Varför routen INTE heter /admin/bokforing
 *
 * Den vägen är upptagen, och av något som ser ut som ingenting: `tillAdminvag`
 * mappar `/dashboard/bokforing` dit, alltså är `/admin/bokforing` hur en
 * plattformsadmin når KUNDENS bokföringsvy inuti adminskalet. Den serveras av
 * catch-allen `app/admin/[...slug]`.
 *
 * En statisk `app/admin/bokforing/page.tsx` hade skuggat catch-allen — statiska
 * segment vinner i Next — och kundvyn hade tyst ersatts av den här tabellen.
 * Ingenting hade felat; fliken hade bara visat fel sida.
 *
 * Sidan hämtar och felhanterar; `Bokforingsanvandning` räknar och renderar.
 * Samma delning som `/admin` gör med Portfoljvy, och av samma skäl:
 * räknelogiken går att testa utan att rendera något.
 */
export default async function Page() {
  const { data, error } = unwrap(await listRuns("?agent_type=bookkeeping"));

  return (
    <div>
      <h1 className="font-display text-4xl italic-disp tighten">Bokföring</h1>
      <p className="mt-4 max-w-[70ch] text-[15px] leading-7 text-ink/65">
        Hur mycket bokföringsagenten används: uppladdade underlag och frågor
        till assistenten, per kund.
      </p>

      {error ? (
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      ) : (
        <Bokforingsanvandning runs={data ?? []} />
      )}
    </div>
  );
}
