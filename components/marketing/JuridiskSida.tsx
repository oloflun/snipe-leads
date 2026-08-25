import Link from "next/link";
import { Logo } from "@/components/Logo";
import { Sidfot } from "@/components/marketing/Sidfot";
import { BOLAG } from "@/lib/bolag";

/**
 * Skalet runt de tre juridiska sidorna: integritetspolicy, villkor, cookies.
 *
 * ## Varför en egen komponent i stället för tre nästan lika sidor
 *
 * Sidhuvudet, typografin, utkastnotisen och sidfoten är identiska på alla
 * tre. Tre kopior hade betytt att en rättelse i utkastnotisen görs på ett
 * ställe och glöms på två — och det stället är just den text som säger att
 * innehållet inte är juridiskt granskat.
 *
 * ## Varför sidorna är enspråkigt svenska
 *
 * Resten av marknadssidan är tvåspråkig. De här är det inte, och det är ett
 * medvetet val: ett juridiskt dokument i två språkversioner har två lydelser,
 * och den dag de säger olika saker är frågan vilken som gäller. Avtalet och
 * policyn skrivs på svenska, för svensk B2B, under svensk rätt. En engelsk
 * översättning kan läggas till senare som just en ÖVERSÄTTNING, med en
 * företrädesklausul — inte som en jämbördig version.
 */
export function JuridiskSida({
  rubrik,
  ingress,
  children
}: Readonly<{ rubrik: string; ingress?: string; children: React.ReactNode }>) {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b border-ink/10">
        <div className="mx-auto flex max-w-[1480px] items-center justify-between px-6 py-5 md:px-10">
          <Link href="/" className="focus-ring" aria-label="Till startsidan">
            <Logo />
          </Link>
          <Link href="/" className="focus-ring text-sm text-ink/60 hover:text-ink">
            Till startsidan
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-[68ch] px-6 py-16 md:py-24">
        <h1 className="font-display text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.05] tracking-[-0.03em]">
          {rubrik}
        </h1>
        <p className="mt-4 text-[0.875rem] text-ink/45">
          Senast uppdaterad: {BOLAG.policyUppdaterad}
        </p>
        {ingress ? (
          <p className="mt-6 text-[1.125rem] leading-[1.7] text-ink/75">{ingress}</p>
        ) : null}

        {/* Utkastnotisen. Den står FÖRE texten och inte som en fotnot: en
            läsare som ska bedöma om dokumentet binder oss ska veta det innan
            hen läser, inte efter. Tas bort samma dag en jurist godkänt
            texten — och inte tidigare, hur bra den än låter. */}
        <p className="mt-8 rounded-card border border-ochre/40 bg-ochre/10 px-5 py-4 text-[0.9375rem] leading-[1.6] text-ink/80">
          <strong className="font-semibold">Förstautkast.</strong> Texten nedan är skriven internt
          och har ännu inte granskats av jurist. Den beskriver vår avsikt och våra rutiner, men ska
          inte läsas som en färdig juridisk handling förrän den här rutan är borta.
        </p>

        {/* Typografin sätts här i stället för per sida. `prose`-liknande
            regler skrivna för hand: kodbasen har ingen typography-plugin, och
            att lägga till ett beroende för tre sidor är fel växling. */}
        <div
          className="mt-12 space-y-6 text-[1.0625rem] leading-[1.75] text-ink/80
            [&_a]:underline [&_a]:underline-offset-4 [&_a:hover]:text-ochre
            [&_h2]:mt-14 [&_h2]:font-display [&_h2]:text-[1.5rem] [&_h2]:font-semibold
            [&_h2]:leading-snug [&_h2]:tracking-[-0.02em] [&_h2]:text-ink
            [&_h3]:mt-10 [&_h3]:text-[1.0625rem] [&_h3]:font-semibold [&_h3]:text-ink
            [&_li]:mt-2 [&_ul]:list-disc [&_ul]:pl-6
            [&_strong]:font-semibold [&_strong]:text-ink"
        >
          {children}
        </div>
      </main>

      <Sidfot />
    </div>
  );
}
