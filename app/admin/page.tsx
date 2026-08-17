import { Portfoljvy } from "@/components/admin/Portfoljvy";
import { listTenants, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

/**
 * Kundöversikten. Hela portföljen på en skärm: intäkt, uppskattad kostnad,
 * marginal och vilka kunder som kräver en åtgärd.
 *
 * Sidan hämtar och felhanterar; Portfoljvy räknar och renderar. Delningen gör
 * att hälsologiken i lib/admin/halsa.ts går att testa utan att rendera något.
 */
export default async function Page() {
  const { data, error } = unwrap(await listTenants());

  if (error) {
    return (
      <div>
        <h1 className="font-display text-4xl tracking-[-0.03em]">Kunder</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  return <Portfoljvy tenants={data ?? []} />;
}
