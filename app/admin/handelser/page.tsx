import {
  Handelsefilter,
  Handelselista,
  Handelserubrik
} from "@/components/admin/Handelselista";
import { listEvents, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

// Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
// Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
export const maxDuration = 60;

/** Nivåerna filtret får skicka vidare. Allt annat behandlas som "alla". */
const NIVAER = new Set(["error", "warning", "info"]);

/**
 * Notiscentret.
 *
 * Sidan hämtar och felhanterar; `components/admin/Handelselista.tsx` grupperar,
 * tolkar och renderar. Samma delning som Översikten, och av samma två skäl:
 * grupperings- och tolkningslogiken går att läsa utan JSX omkring sig, och
 * vyn kan vara en klientkomponent så att språkväxlaren når hela sidan.
 */
export default async function Page({
  searchParams
}: Readonly<{ searchParams: Promise<Record<string, string | undefined>> }>) {
  const params = await searchParams;
  // Vitlista och inte rå genomsläppning: `level` går rakt in i en query mot
  // backenden, och en parameter som kommer ur URL:en ska inte kunna vara vad
  // som helst bara för att den råkar tolkas snällt i andra änden.
  const niva = NIVAER.has(params.level ?? "") ? (params.level as string) : "";
  const { data, error } = unwrap(await listEvents(niva ? `?level=${niva}` : ""));

  if (error) {
    return (
      <div>
        <Handelserubrik />
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  return (
    <div>
      <Handelserubrik />
      <Handelsefilter niva={niva} />
      <Handelselista events={data ?? []} niva={niva} />
    </div>
  );
}
