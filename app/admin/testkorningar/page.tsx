import { AdminText } from "@/components/admin/AdminText";
import { Testkorningar } from "@/components/admin/Testkorningar";
import { AdminVyhuvud } from "@/components/admin/AdminVyhuvud";

export const dynamic = "force-dynamic";

/**
 * Provkörning av båda agenterna. Grinden är app/admin/layout.tsx.
 *
 * Ingen maxDuration här: sidan hämtar ingenting server-side. Körningarna startas
 * från klienten mot /api/snajp-support/*, och de routerna har redan sitt eget
 * tak (INV-API-001).
 */
export default function Page() {
  return (
    <div>
      <AdminVyhuvud grupp="logg" />
      <div className="mt-8">
        <Testkorningar />
      </div>
    </div>
  );
}
