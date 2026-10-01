import { PaketHantering } from "@/components/admin/PaketHantering";
import { Nyckeltal, Sidhuvud, Tomt } from "@/components/ui";
import { listTenants, unwrap } from "@/lib/data/admin";
import { paketForProdukter } from "@/lib/paket";
import { formateraPris } from "@/lib/pricing";

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

  const aktiva = kunder.filter((rad) => (rad.status ?? (rad.active === false ? "avstangd" : "aktiv")) === "aktiv");
  const pausade = kunder.filter((rad) => rad.status === "pausad");
  const avstangda = kunder.filter(
    (rad) => (rad.status ?? (rad.active === false ? "avstangd" : "aktiv")) === "avstangd"
  );

  // Månadsintäkten ur paketpriserna, bara för AKTIVA kunder med ett exakt
  // paket. Ett eget urval utan paketpris räknas inte med, hellre en siffra
  // som är för låg och sann än en som gissar.
  const manadsintakt = aktiva.reduce((summa, rad) => {
    const paket = paketForProdukter(rad.products);
    return summa + (paket?.prisPerManad ?? 0);
  }, 0);

  return (
    <div>
      <Sidhuvud title="Paket" />

      {error ? (
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {error}
        </p>
      ) : (
        <>
          <div className="mt-8">
            <Nyckeltal
              poster={[
                { etikett: "Aktiva kunder", varde: aktiva.length },
                { etikett: "Pausade", varde: pausade.length },
                { etikett: "Avslutade", varde: avstangda.length },
                {
                  etikett: "Paketvärde per månad",
                  varde: formateraPris(manadsintakt),
                  notis: "Aktiva kunder med exakt paket"
                }
              ]}
            />
          </div>

          <div className="mt-10">
            {kunder.length === 0 ? (
              <Tomt>Inga kunder ännu. Raderna dyker upp när första kunden onboardats.</Tomt>
            ) : (
              <PaketHantering tenants={kunder} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
