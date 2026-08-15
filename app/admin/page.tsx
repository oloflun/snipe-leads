import Link from "next/link";
import { listTenants, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

/**
 * Kundöversikten. Ledger, inte kort — en rad per kund, hairline mellan, tal
 * i tabularsiffror så kolumnerna går att jämföra vertikalt.
 *
 * Ochre bara på avvikelsen: felkolumnen när den inte är noll. Om varje
 * kolumn hade en accent hade ingen av dem varit en.
 */
export default async function Page() {
  const { data, error } = unwrap(await listTenants());

  if (error) {
    return (
      <div>
        <h1 className="font-display text-4xl italic-disp tighten">Kunder</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  const tenants = data ?? [];

  return (
    <div>
      <h1 className="font-display text-4xl italic-disp tighten">Kunder</h1>

      {tenants.length === 0 ? (
        <p className="mt-8 border-t border-ink/15 pt-5 text-[15px] text-mineral">
          Inga kunder registrerade än.
        </p>
      ) : (
        <div className="mt-8 overflow-x-auto">
          <table className="w-full min-w-[880px] border-collapse text-[15px]">
            <thead>
              <tr className="border-b border-ink/15">
                {["Kund", "Ärenden", "Körningar", "Tokens in", "Tokens ut", "Fel", "Senast"].map(
                  (head, index) => (
                    <th
                      key={head}
                      className={`kicker py-3 text-mineral ${index === 0 ? "text-left" : "text-right"}`}
                      scope="col"
                    >
                      {head}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {tenants.map((tenant) => (
                <tr key={tenant.id} className="border-b border-ink/15">
                  <td className="py-4">
                    <Link
                      href={`/admin/korningar?tenant_id=${encodeURIComponent(tenant.id)}`}
                      className="hover:text-ochre"
                    >
                      {tenant.name}
                    </Link>
                    <span className="kicker ml-3 text-mineral">{tenant.slug ?? "—"}</span>
                  </td>
                  <td className="py-4 text-right tabular-nums">{tenant.tickets}</td>
                  <td className="py-4 text-right tabular-nums">{tenant.runs}</td>
                  <td className="py-4 text-right tabular-nums">{tenant.tokens_in}</td>
                  <td className="py-4 text-right tabular-nums">{tenant.tokens_out}</td>
                  <td
                    className={`py-4 text-right tabular-nums ${tenant.errors > 0 ? "text-ochre" : ""}`}
                  >
                    {tenant.errors}
                  </td>
                  <td className="py-4 text-right text-mineral tabular-nums">
                    {tenant.last_activity ? tenant.last_activity.slice(0, 16).replace("T", " ") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
