import type { Metadata } from "next";

import { FelOchEskaleringar } from "@/components/admin/FelOchEskaleringar";
import { Kundfotnot, Kundrubrik } from "@/components/admin/Kundrubrik";
import { Kundstatistik } from "@/components/admin/Kundstatistik";
import { Kundtabell } from "@/components/admin/Kundtabell";
import { berikaAlla } from "@/lib/admin/exempeldata";
import { beraknaKundstatistik } from "@/lib/admin/statistik";
import { listEvents, listTenants, unwrap } from "@/lib/data/admin";

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
        <Kundrubrik />
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
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
      <Kundrubrik />

      <Kundtabell kunder={kunder} />

      {/* Statistiken räknas på SAMMA rader som tabellen ovan, inte en egen
          hämtning — två uträkningar av samma tal blir förr eller senare två
          olika tal. `new Date()` är okej i en force-dynamic server component:
          sidan renderas per anrop.

          Exempelraderna ändrar INTE statistiken: `arRiktigKund()` filtrerar
          bort test- och demoarbetsytor, och det är hela poängen med den regeln
          — en testyta som syns i en försäljningskurva fattar beslut åt någon.
          Kurvan är därför fortsatt gles, och det är avsiktligt. */}
      {kunder.length > 0 ? (
        <Kundstatistik stat={beraknaKundstatistik(kunder, nu)} />
      ) : null}

      {/* Fel & eskaleringar: sammanfattar det som redan loggas. Renderas även
          när händelselistan inte gick att hämta — då med tom lista, eftersom
          eskaleringstalet kommer ur tenantraderna och står på egna ben. */}
      {kunder.length > 0 ? (
        <FelOchEskaleringar
          tenants={kunder}
          events={events ?? []}
          taketNaddes={(events?.length ?? 0) >= HANDELSETAK}
          nu={nu.getTime()}
        />
      ) : null}

      <Kundfotnot />
    </div>
  );
}
