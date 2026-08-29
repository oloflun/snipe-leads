import { Portfoljvy } from "@/components/admin/Portfoljvy";
import { berikaAlla } from "@/lib/admin/exempeldata";
import { listTenants, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

/**
 * Sidan är en server-komponent som hämtar från Snajp-Support-backenden, och
 * den ligger på Renders gratisnivå: efter 15 minuters inaktivitet somnar den
 * och tar upp till ~35 sekunder att vakna (uppmätt 33,7 s 2026-08-17).
 *
 * Vercels standardtak är kortare än så. Utan den här raden dödas renderingen
 * mitt i uppvakningen, och adminvyn ser trasig ut just när den öppnas första
 * gången på morgonen — alltså nästan varje gång den faktiskt används.
 *
 * `route.ts`-filerna under app/api/ har redan raden och bevakas av
 * INV-API-001. Sidor omfattades inte, vilket är precis varför den här saknades.
 */
export const maxDuration = 60;

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
        <h1 className="font-display text-4xl tracking-[-0.03em]">Översikt</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  // Klockan läses HÄR, en gång, och skickas ned. `new Date()` i en
  // klientkomponent ger besökarens klocka vid hydreringen och serverns vid
  // SSR — två olika svar på samma fråga, alltså en hydreringskrock i varje rad
  // vars dagräkning råkar ligga på en dygnsgräns. En force-dynamic server
  // component får läsa klockan; klientkomponenten får talet.
  const nu = new Date();
  return <Portfoljvy tenants={berikaAlla(data ?? [], nu)} nu={nu.getTime()} />;
}
