import { Testkorningar } from "@/components/admin/Testkorningar";

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
      <h1 className="font-display text-4xl tracking-[-0.03em]">Testkörningar</h1>
      <p className="mt-3 max-w-[70ch] text-[15px] leading-7 text-mineral">
        Kör agenterna på beställning i stället för att vänta på att något går fel hos en kund.
      </p>
      <div className="mt-10">
        <Testkorningar />
      </div>
    </div>
  );
}
