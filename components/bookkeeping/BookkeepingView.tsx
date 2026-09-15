import { ArrowUpRight } from "lucide-react";
import { PageShell } from "@/components/AppShell";
import { BokforingChatt } from "@/components/bookkeeping/BokforingChatt";
import { BokforingPanel } from "@/components/bookkeeping/BokforingPanel";
import { Felanmalan } from "@/components/bookkeeping/Felanmalan";
import { Forbehall } from "@/components/bookkeeping/Forbehall";
import { btnPrimary } from "@/components/ui";
import { cn } from "@/lib/utils";

/**
 * Bokföringsvyn. Serverskal, klientpanel — samma delning som resten av
 * arbetsytan.
 *
 * Grinden sitter INTE här utan i `WorkspaceSection`, som avgör på servern om
 * arbetsytan har `bookkeeping` bland sina produkter. En kontroll i den här
 * komponenten hade körts efter att routen redan bestämt sig, alltså för sent
 * för att svara 404.
 *
 * ## Två kolumner, inte en stapel
 *
 * Arbetet och frågan är olika saker och görs samtidigt. Panelen är en
 * ARBETSYTA — ladda upp, se perioden, exportera — och assistenten är en
 * FRÅGA om det som ligger där. Låg de under varandra hamnade assistenten
 * utanför skärmen så fort kunden hade fler än en handfull underlag, alltså
 * precis när den börjar vara användbar.
 *
 * Assistenten är klistrad (`lg:sticky`) så att den följer med när man rullar
 * genom underlagen. Under lg staplas de, med panelen först: på en telefon är
 * uppladdningen det man kommit för.
 *
 * ## Förbehållet, hopfällt
 *
 * Det stod som fyra rader juridik ÖVERST och togs bort 2026-08-24. Det var rätt
 * beslut om placeringen och fel utfall: kunden mötte då villkoret ingenstans i
 * gränssnittet. `Forbehall` är kompromissen — en rad längst ned, hela texten ett
 * klick bort, på varje sidvisning.
 */
export function BookkeepingView() {
  return (
    <PageShell
      title="Kvitton, fakturor och underlag"
      description="Ladda upp dina kvitton, fakturor och andra underlag. Agenten läser av, organiserar och föreslår kontering och periodisering – så att pappersarbetet blir klart för granskning och bokföring."
    >
      {/* Vägen till den fristående bokföringssajten — en KNAPP, inte en
          redirect (Sebbes ord 2026-09-15: menyklicket ska landa här som
          vanligt). Länken går via /api/bokforing/sso, som skapar en färsk
          engångsbiljett vid klicket så att kunden landar på sajten som sig
          själv, med sin egen bokföring. Renderas bara när miljön pekat ut
          sajten — utan BOKFORING_EXTERN_URL finns ingen knapp att visa. */}
      {process.env.BOKFORING_EXTERN_URL ? (
        <div className="mb-12 flex flex-wrap items-center justify-between gap-x-8 gap-y-4 border-y border-ink/15 py-5">
          <div className="min-w-0 max-w-[62ch]">
            <p className="text-[0.9375rem] font-semibold text-ink">
              Bokföringsagenten har fått en egen arbetsyta
            </p>
            <p className="mt-1 text-[0.9375rem] leading-6 text-ink/60">
              Samma underlag och siffror som här, med mer plats: resultat,
              intäkter och utgifter, PDF-filer och assistenten som egna flikar.
              Du loggas in automatiskt.
            </p>
          </div>
          <a href="/api/bokforing/sso" className={cn(btnPrimary, "shrink-0")}>
            Öppna bokföringssajten
            <ArrowUpRight className="h-4 w-4" aria-hidden />
          </a>
        </div>
      ) : null}

      {/* gap-x först från lg. Under lg ligger allt i col-span-12, och elva
          kolumnmellanrum à 40px hade då bara ätit bredd — samma fälla som
          WorkspaceViews dokumenterar för 320px-vyn. */}
      <div className="grid grid-cols-12 gap-x-0 gap-y-12 lg:gap-x-10">
        <div className="col-span-12 lg:col-span-7">
          <BokforingPanel />
        </div>

        <aside className="col-span-12 lg:col-span-5">
          <div className="lg:sticky lg:top-24">
            <BokforingChatt />
          </div>
        </aside>
      </div>

      <Forbehall />
      <Felanmalan />
    </PageShell>
  );
}
