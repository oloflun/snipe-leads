import Link from "next/link";

import { Sidhuvud, flik, flikAktiv, flikInaktiv } from "@/components/ui";
import { KonverteraTestkund } from "@/components/admin/KonverteraTestkund";
import { Kundprofil } from "@/components/admin/Kundprofil";
import { Tillaggsvaljare } from "@/components/admin/Tillaggsvaljare";
import { hamtaKundprofil } from "@/lib/actions/agentinstruktioner";
import { hamtaTillagg } from "@/lib/actions/tillagg";
import { listTenants, unwrap } from "@/lib/data/admin";

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
 *
 * Länken "Kunder" ovanför rubriken, "Tillbaka till kundlistan" i felläget och
 * ingressen under rubriken togs bort 2026-09-27: railens Kunder-post är aktiv
 * på den här sidan och leder dit länkarna ledde (regel 4 i
 * plans/2026-09-27-appytor-enhetlighet.md), och ingressen beskrev sidan
 * (F-016). Att en ändring gäller nästa körning säger kvittot vid Spara.
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
  // Parallellt, inte i följd: profilen är ett master-nyckelanrop över HTTP
  // till snajp-support och tilläggen en databasrundtur, och de vet inget om
  // varandra. Sekventiellt lade de sina latenser på varandra i en sida som
  // redan bär maxDuration = 60.
  const [{ profil, error }, tillagg] = await Promise.all([
    hamtaKundprofil(id, agentType),
    hamtaTillagg(id)
  ]);

  if (error || !profil) {
    return (
      <div>
        <Sidhuvud title="Kundprofil" />
        <p role="alert" className="mt-8 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {error ?? "Kunden gick inte att hämta."}
        </p>

        {/* Tilläggen står kvar även när agentprofilen inte gick att hämta.
            De läses ur databasen, inte ur backenden, och adressen bär redan
            tenant-id:t. Förut försvann hela Tillägg-sektionen med profilen —
            en sovande backend gjorde alltså tilläggen omöjliga att slå på. */}
        <div className="mt-12">
          <Tillaggsvaljare
            tenantId={id}
            initialaAddons={tillagg.addons ?? []}
            lasfel={tillagg.error}
            migrationSaknas={tillagg.migrationSaknas}
          />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Sidhuvud title={profil.tenant.name} />

      {/* Två agenter, två profiler. Samma kund kan behöva olika instruktioner för
          kundtjänst och för utskick, och agent_configs är nycklad på båda. */}
      <div className="mt-8 flex flex-wrap gap-2">
        {(["support", "leads"] as const).map((typ) => (
          <Link
            key={typ}
            href={`/admin/kunder/${profil.tenant.id}?agent=${typ}`}
            aria-current={agentType === typ ? "page" : undefined}
            // Husets flikar (samma piller som Iris "Alla bolag / Listor"), inte
            // egna klasser: 44 px tryckyta och samma aktiva läge som överallt.
            className={`${flik} ${agentType === typ ? flikAktiv : flikInaktiv}`}
          >
            {typ === "support" ? "Kundtjänst" : "Iris"}
          </Link>
        ))}
      </div>

      <div className="mt-8">
        <Kundprofil profil={profil} />
      </div>

      {/* Tilläggen står EFTER agentprofilen och före befordran: profilen är
          det som formar agentens svar, tilläggen är vad agenten får göra —
          och befordran flyttar hela kunden. Ordningen är från innehåll till
          omfattning till flytt.

          Läsfelet skickas ned i stället för att fälla sidan: en trasig
          tilläggsläsning ska inte dölja instruktionerna ovanför, som är
          sidans huvudsak. */}
      <div className="mt-12">
        <Tillaggsvaljare
          tenantId={profil.tenant.id}
          initialaAddons={tillagg.addons ?? []}
          lasfel={tillagg.error}
          migrationSaknas={tillagg.migrationSaknas}
        />
      </div>

      {profil.tenant.slug?.startsWith("testkund-") ? (
        <KonverteraTestkund
          fran={profil.tenant.slug}
          mal={
            unwrap(await listTenants())
              .data?.filter((t) => t.slug && !t.slug.startsWith("testkund-"))
              .map((t) => ({ slug: t.slug as string, name: t.name })) ?? []
          }
        />
      ) : null}
    </div>
  );
}
