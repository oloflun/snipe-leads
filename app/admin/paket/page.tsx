import { AdminText } from "@/components/admin/AdminText";
import { PaketOversikt } from "@/components/admin/PaketOversikt";
import { Panelrubrik } from "@/components/dashboard/OversiktPaneler";
import { ADMIN } from "@/lib/admin/sprak";
import { cn } from "@/lib/utils";
import { PaketHantering } from "@/components/admin/PaketHantering";
import { Tomt, panelKort } from "@/components/ui";
import { listTenants, unwrap } from "@/lib/data/admin";
import { AdminVyhuvud } from "@/components/admin/AdminVyhuvud";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

/**
 * Fliken Paket: alla kunders paket, tillval och kontoläge på ett ställe.
 *
 * Statiskt segment under `admin/`, alltså före `app/admin/[...slug]`, samma
 * mönster som `app/admin/kunder`. Grinden är `app/admin/layout.tsx`
 * (notFound för den som inte är plattformsadmin), och varje skrivning
 * kontrollerar dessutom själv: bytPaket och sattTillagg via sina
 * security definer-funktioner, sattKundStatus via master-nyckeln.
 *
 * Testkunderna (`testkund-`) är borta ur listan med flit: de har inget paket
 * att fakturera och inget konto att pausa, och varje rad här är ett löfte om
 * att knapparna betyder något.
 */
export default async function Page() {
  const { data, error } = unwrap(await listTenants());
  const kunder = (data ?? []).filter((rad) => !rad.slug?.startsWith("testkund-"));

  return (
    <div>
      <AdminVyhuvud grupp="kunder" />

      {error ? (
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {error}
        </p>
      ) : (
        <>
          <PaketOversikt kunder={kunder} />

          <section aria-labelledby="paket-tabell" className={cn(panelKort, "mt-6 min-w-0")}>
            <Panelrubrik id="paket-tabell" titel={ADMIN.kundernasPaket} antal={kunder.length} />
            {kunder.length === 0 ? (
              <Tomt>
                <AdminText n="ingaKunderPaket" />
              </Tomt>
            ) : (
              <PaketHantering tenants={kunder} />
            )}
          </section>
        </>
      )}
    </div>
  );
}
