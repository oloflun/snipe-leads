import Link from "next/link";

import { Kundprofil } from "@/components/admin/Kundprofil";
import { hamtaKundprofil } from "@/lib/actions/agentinstruktioner";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

/**
 * En enskild kunds agentprofil.
 *
 * Statiskt segment under `kunder/`, alltså före `app/admin/[...slug]` — samma
 * mönster som `app/admin/installningar`. Grinden är `app/admin/layout.tsx`
 * (notFound för den som inte är plattformsadmin), och server-actionerna
 * kontrollerar dessutom själva: en action är en POST-endpoint med ett eget id,
 * och att den bara anropas från den här sidan är ett antagande om klienten.
 *
 * Adressen bär tenantens UUID och inte sluggen. Backendens profil-endpoint
 * scopar på tenant_id, och att översätta slug -> id i en yta som skriver
 * betyder ett uppslag till som kan peka fel kund.
 */
export default async function Page({
  params,
  searchParams
}: Readonly<{
  params: Promise<{ id: string }>;
  searchParams: Promise<{ agent?: string }>;
}>) {
  const { id } = await params;
  const { agent } = await searchParams;
  const agentType = agent === "leads" ? "leads" : "support";
  const { profil, error } = await hamtaKundprofil(id, agentType);

  if (error || !profil) {
    return (
      <div>
        <h1 className="font-display text-4xl tracking-[-0.03em]">Kundprofil</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {error ?? "Kunden gick inte att hämta."}
        </p>
        <Link href="/admin/kunder" className="mt-6 inline-block text-[0.9375rem] underline underline-offset-4">
          Tillbaka till kundlistan
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Link
        href="/admin/kunder"
        className="text-[0.8125rem] text-mineral underline underline-offset-4 hover:text-ochre"
      >
        Kunder
      </Link>
      <h1 className="mt-2 font-display text-4xl tracking-[-0.03em]">{profil.tenant.name}</h1>
      <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
        Allt som formar den här kundens agent. Ändringar gäller nästa körning. Pågående
        ärenden kör klart på de regler de startade med.
      </p>

      {/* Två agenter, två profiler. Samma kund kan behöva olika instruktioner för
          kundtjänst och för utskick, och agent_configs är nycklad på båda. */}
      <div className="mt-6 flex gap-2 text-[0.8125rem]">
        {(["support", "leads"] as const).map((typ) => (
          <Link
            key={typ}
            href={`/admin/kunder/${profil.tenant.id}?agent=${typ}`}
            aria-current={agentType === typ ? "page" : undefined}
            // min-h-11 = 44px, inte min-h-9. DESIGN.md sätter tryckytan till 44
            // utan undantag, och en flik är lika mycket en tryckyta som en knapp.
            // Hårfin linje på paper2-varianten av samma skäl som överallt annars:
            // planet ligger 0.035 från pappret och separerar inte av sig självt.
            className={`focus-ring inline-flex min-h-11 items-center rounded-input px-4 font-medium ${
              agentType === typ
                ? "bg-ink text-paper"
                : "border border-ink/15 bg-paper2/50 text-ink hover:bg-paper2"
            }`}
          >
            {typ === "support" ? "Kundtjänst" : "Leads"}
          </Link>
        ))}
      </div>

      <div className="mt-10">
        <Kundprofil profil={profil} />
      </div>
    </div>
  );
}
