import type { Metadata } from "next";

import { Kundtabell } from "@/components/admin/Kundtabell";
import { KunderOversikt } from "@/components/admin/KunderOversikt";
import { berikaAlla } from "@/lib/admin/exempeldata";
import { beraknaKundstatistik } from "@/lib/admin/statistik";
import { listEvents, listTenants, unwrap } from "@/lib/data/admin";
import { AdminVyhuvud } from "@/components/admin/AdminVyhuvud";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Snajp - Kunder&Data" };

/**
 * Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
 * Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
 */
export const maxDuration = 60;

/**
 * Kundlistan — hämtning och felhantering. Tabellen, statistiken och
 * felsektionen renderas av var sin komponent under components/admin/.
 *
 * Inga uppskattningar här — bara räknade tal ur agent_runs och ss_tickets,
 * plus kundregistret (053). Marginalen bor i Översikten, med sitt förbehåll.
 * Rader utan någon aktivitet alls får exempeltal ur `lib/admin/exempeldata.ts`
 * och är då märkta som sådana; se den filen för varför.
 *
 * Intäkter och utgifter har MEDVETET ingen sektion på den här sidan: det finns
 * ingen riktig betal- eller bokföringskälla i systemet ännu (betalsätten är
 * simulerade testkort, fakturor finns inte i kod). Bygg inte in siffror här
 * förrän en riktig datakälla är vald. Det stod förut i en fotnot längst ned på
 * sidan; den togs bort 2026-09-27 (F-016), regeln gäller fortfarande.
 *
 * Ordningen sedan 2026-10-07 (Sebbe: samma layout som de andra översikterna):
 * nyckeltalen och statistiken överst, sedan tabellen, sist fel och
 * eskaleringar bredvid provperioderna. Se components/admin/KunderOversikt.tsx.
 */

/** Händelsetaket. Fullt svar => talen i felsektionen prefixas "minst". */
const HANDELSETAK = 300;

export default async function Page() {
  // Parallellt: två oberoende backendanrop, och sidan är redan den
  // långsammaste i adminytan när backenden vaknar.
  const [tenantsSvar, eventsSvar] = await Promise.all([
    listTenants(),
    listEvents(`?limit=${HANDELSETAK}`)
  ]);
  const { data, error } = unwrap(tenantsSvar);
  const { data: events } = unwrap(eventsSvar);

  if (error) {
    return (
      <div>
        <AdminVyhuvud grupp="kunder" />
        <p role="alert" className="mt-8 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {error}
        </p>
      </div>
    );
  }

  // Sorteringen sker i tabellen, inte här: den är språkberoende (svensk
  // kollation lägger å ä ö sist, engelsk gör det inte), och språket är känt
  // först på klientsidan.
  // En enda klockavläsning för hela sidan: berikningen, statistiken och
  // felsektionen ska räkna mot SAMMA tidpunkt, och klientkomponenterna nedan
  // får talet i stället för att läsa sin egen klocka. Se app/admin/page.tsx.
  const nu = new Date();
  const kunder = berikaAlla(data ?? [], nu);

  return (
    <div>
      <AdminVyhuvud grupp="kunder" />

      {kunder.length === 0 ? (
        <Kundtabell kunder={kunder} />
      ) : (
        /* Fel & eskaleringar renderas även när händelselistan inte gick att
           hämta, då med tom lista: eskaleringstalet kommer ur tenantraderna.

           Statistiken räknas på SAMMA rader som tabellen, inte en egen
           hämtning, och test- och demoarbetsytor räknas inte
           (`raknasSomKund()` i lib/admin/statistik.ts). Exempelraderna räknas
           däremot, eftersom de är märkta, och vyn säger hur många de är. */
        <KunderOversikt
          kunder={kunder}
          events={events ?? []}
          taketNaddes={(events?.length ?? 0) >= HANDELSETAK}
          nu={nu.getTime()}
          stat={beraknaKundstatistik(kunder, nu)}
        />
      )}
    </div>
  );
}
