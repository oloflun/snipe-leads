import type { Metadata } from "next";
import { InnehallsSida, SidAvslut, SidRubrik } from "@/components/marketing/InnehallsSida";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { initialer, TEAM, teametArIfyllt } from "@/lib/team";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Vårt team — Snajp",
  description:
    "Vilka som bygger Snajp, varför bolaget finns och hur vi arbetar. Utvecklat i Göteborg och Umeå för svensk B2B.",
  alternates: { canonical: "/vart-team" }
};

const VARDERINGAR = [
  {
    rubrik: "Vi bygger det vi själva använder",
    text:
      "Alla tre agenterna körs i vår egen verksamhet. Spärrarna sitter där de sitter för att vi " +
      "själva stått med ett utkast som inte borde gå ut."
  },
  {
    rubrik: "Hellre ett nej i tid än ett ja som inte håller",
    text:
      "Agenten säger ifrån när den saknar underlag i stället för att gissa, och vi säljer hellre " +
      "rätt paket än det dyraste."
  },
  {
    rubrik: "Det som inte går att kontrollera säger vi inte",
    text:
      "Inga sifferpåståenden utan källa, inga kundlogotyper vi inte har tillstånd för, och " +
      "underleverantörerna räknas upp med namn i stället för som ”betrodda partners”."
  }
];

export default async function Page() {
  await notFoundOnTenant();

  const ifyllt = teametArIfyllt();

  return (
    <InnehallsSida bredd="vid">
      <SidRubrik
        rubrik="Vårt team"
        ingress="Snajp byggs i Göteborg och Umeå av ett litet team. Vi säljer till svensk B2B, och vi använder produkten själva varje dag."
      />

      {/* Notisen mäter NAMN och ROLL, inget annat — se teametArIfyllt.
          Foton och bios är valfria, och hade de räknats in vore notisen
          permanent: en varning ingen kan släcka är en varning ingen läser.
          Sedan namnen fylldes i 2026-08-25 renderas den inte, men den står
          kvar för nästa gång någon lägger till en tom post. */}
      {!ifyllt ? (
        <p className="mt-8 rounded-card border border-copper/30 bg-copper/10 px-5 py-4 text-[0.9375rem] leading-[1.6] text-ink">
          <strong className="font-semibold">Utkast.</strong> Någon post saknar namn eller roll.
          Fyll i <code className="text-[0.875rem]">lib/team.ts</code> innan sidan publiceras —
          rutan försvinner då automatiskt.
        </p>
      ) : null}

      <section className="mt-16">
        <h2 className="font-display text-[1.75rem] font-semibold leading-snug tracking-[-0.025em]">
          Varför Snajp finns
        </h2>
        <div className="mt-5 max-w-[62ch] space-y-5 text-[1.0625rem] leading-[1.7] text-ink/78">
          <p>
            B2B-prospektering är tidskrävande och blir opersonlig precis när den skalas. Antingen
            skriver någon femton genomtänkta mejl i veckan, eller så skickas trehundra som alla
            läser likadant. Samma sak i kundtjänsten: svaren finns redan skrivna, men i fel
            dokument, och någon måste ändå läsa varje ärende för att veta vilket som brådskar.
          </p>
          <p>
            Vi bygger verktyget som gör förarbetet — hittar företagen, sorterar ärendena, läser av
            kvittona — och lämnar beslutet till en människa. Målet är inte att ersätta den som
            säljer eller svarar, utan att ge tillbaka timmarna som gick åt till att leta.
          </p>
        </div>
      </section>

      <section className="mt-20">
        <h2 className="font-display text-[1.75rem] font-semibold leading-snug tracking-[-0.025em]">
          Vilka vi är
        </h2>
        {/* Två kolumner, inte tre. TEAM har två poster, och lg:grid-cols-3
            hade lämnat en tom tredjedel som läser som en person vi glömt.
            Rutnätet ska följa innehållet, inte tvärtom. */}
        <ul className="mt-8 grid max-w-[760px] gap-x-10 gap-y-12 sm:grid-cols-2">
          {TEAM.map((medlem) => (
            <li key={medlem.id}>
              {/* Bilden renderas bara när det FINNS en. Ett <img> mot en
                  saknad fil ger webbläsarens trasiga ikon, vilket är den
                  sämsta möjliga bilden på en sida om förtroende. */}
              {medlem.foto ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={medlem.foto}
                  alt={medlem.namn}
                  loading="lazy"
                  className="aspect-square w-full rounded-card bg-paper2 object-cover"
                />
              ) : (
                <div
                  className="flex aspect-square w-full items-center justify-center rounded-card bg-paper2"
                  aria-hidden
                >
                  <span className="font-display text-[2.5rem] font-semibold text-ink/25">
                    {initialer(medlem.namn)}
                  </span>
                </div>
              )}
              <h3 className="mt-5 font-display text-[1.25rem] font-semibold leading-snug tracking-[-0.015em]">
                {medlem.namn}
              </h3>
              <p className="mt-1 text-[0.9375rem] font-medium text-mineral">{medlem.roll}</p>
              {/* Tom bio UTELÄMNAS. Ett tomt <p> hade lämnat ett glapp under
                  rollen som ser ut som en text som inte laddat. */}
              {medlem.bio ? (
                <p className="mt-3 text-[0.9375rem] leading-[1.65] text-ink/70">{medlem.bio}</p>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-20">
        <h2 className="font-display text-[1.75rem] font-semibold leading-snug tracking-[-0.025em]">
          Så arbetar vi
        </h2>
        <ul className="mt-8 grid gap-x-10 gap-y-8 md:grid-cols-3">
          {VARDERINGAR.map((v) => (
            <li key={v.rubrik} className="border-t border-ink/15 pt-5">
              <h3 className="text-[1.0625rem] font-semibold leading-snug">{v.rubrik}</h3>
              <p className="mt-2 text-[0.9375rem] leading-[1.65] text-ink/70">{v.text}</p>
            </li>
          ))}
        </ul>
      </section>

      <SidAvslut
        rubrik="Vill du veta mer om hur vi jobbar?"
        text="Boka en demo på femton minuter. Vi visar plattformen live mot era egna ärenden och säger rakt ut om vi tror att den passar er."
        primar={{ etikett: "Boka demo", href: "/boka-demo" }}
        sekundar={{ etikett: "Skriv till oss", href: `mailto:${KONTAKT_MEJL}` }}
      />
    </InnehallsSida>
  );
}
