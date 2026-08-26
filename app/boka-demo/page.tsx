import type { Metadata } from "next";
import { BokaDemoFormular } from "@/components/marketing/BokaDemoFormular";
import { InnehallsSida, SidRubrik } from "@/components/marketing/InnehallsSida";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Boka demo — Snajp",
  description:
    "Femton till tjugo minuter, plattformen live mot era egna ärenden, inga förpliktelser.",
  alternates: { canonical: "/boka-demo" }
};

/**
 * ## Cal.com först, formulär som reserv
 *
 * `NEXT_PUBLIC_CAL_LANK` satt (t.ex. "snajp/demo") ger Cal.coms egen
 * bokningssida i en iframe: riktiga lediga tider, tidszoner, kalendersynk och
 * ett bekräftelsemejl — allt sådant vi annars hade fått bygga och underhålla
 * själva. Osatt visas formuläret, som sparar förfrågan i `demo_requests` och
 * lämnar tidsbokningen till ett svarsmejl från en människa.
 *
 * TODO: bekräfta med Sebbe — skapa kontot på cal.com (gratisnivån räcker) och
 * sätt NEXT_PUBLIC_CAL_LANK i Railway. Det kräver ett konto, alltså en
 * inloggning som inte kan automatiseras härifrån. Tills dess är formuläret
 * det som gäller, och det fungerar.
 *
 * ## Varför iframe och inte deras JS-widget
 *
 * Embed-skriptet laddar en tredjepartsbundle på varje sidvisning och sätter
 * egna cookies. En iframe mot bokningssidan gör samma jobb, laddas bara när
 * sidan faktiskt öppnas, och håller tredjepartskoden utanför vårt eget
 * dokument. Priset är att vi inte kan lyssna på deras händelser — och den enda
 * händelse vi hade velat ha är "bokning klar", som Cal.com redan bekräftar
 * inuti ramen.
 */
export default async function Page() {
  await notFoundOnTenant();

  const calLank = process.env.NEXT_PUBLIC_CAL_LANK?.trim();

  return (
    <InnehallsSida>
      <SidRubrik
        rubrik="Boka en demo"
        ingress="Femton till tjugo minuter. Vi visar plattformen live mot era egna ärenden, svarar på det ni undrar och säger rakt ut om vi tror att den passar er."
      />

      <ul className="mt-10 grid gap-x-8 gap-y-4 sm:grid-cols-3">
        {[
          ["15–20 minuter", "Ett möte, inte en säljprocess."],
          ["Live, inte bildspel", "Vi kör agenten mot riktiga exempel."],
          ["Inga förpliktelser", "Passar det inte säger vi det."]
        ].map(([rubrik, text]) => (
          <li key={rubrik} className="border-t border-ink/15 pt-4">
            <h2 className="text-[1rem] font-semibold leading-snug">{rubrik}</h2>
            <p className="mt-1.5 text-[0.9375rem] leading-[1.6] text-ink/70">{text}</p>
          </li>
        ))}
      </ul>

      <div className="mt-12">
        {calLank ? (
          <>
            <iframe
              // `https://cal.com/<handle>` med layouten som ger en månadsvy.
              src={`https://cal.com/${calLank}?embed=true&layout=month_view`}
              title="Välj en tid för demon"
              loading="lazy"
              className="h-[720px] w-full rounded-card border border-ink/12 bg-paper2/40"
            />
            <p className="mt-4 text-[0.875rem] text-ink/50">
              Går kalendern inte att ladda?{" "}
              <a
                href={`mailto:${KONTAKT_MEJL}?subject=${encodeURIComponent("Boka demo")}`}
                className="underline underline-offset-4 hover:text-ochre"
              >
                Mejla oss
              </a>{" "}
              så bokar vi manuellt.
            </p>
          </>
        ) : (
          <BokaDemoFormular />
        )}
      </div>
    </InnehallsSida>
  );
}
