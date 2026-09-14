import Link from "next/link";
import { Logo } from "@/components/Logo";
import { SidMeny } from "@/components/marketing/SidMeny";
import { Sidfot } from "@/components/marketing/Sidfot";

/**
 * Skalet runt menyns innehållssidor: FAQ, Vårt team, Boka demo.
 *
 * ## Varför den finns vid sidan av JuridiskSida
 *
 * `JuridiskSida` bär två saker: skalet (sidhuvud, bredd, sidfot) OCH en
 * prosatypografi skriven för löpande juridisk text. De tre sidorna här är
 * inte prosa — de är ett dragspel, ett personrutnät och en bokningswidget —
 * och att ärva `[&_h2]:mt-14` hade tvingat varje sådan komponent att skriva
 * över regler den aldrig bett om.
 *
 * Skalet är därför brutet ut hit, och JuridiskSida använder det numera själv
 * med sin prosa som barn. Ett sidhuvud som bor på två ställen är precis det
 * JuridiskSidas egen docstring varnar för.
 *
 * `bredd` finns för att texten och rutnätet vill ha olika mått. En FAQ läses
 * som text och ska ligga runt 68 tecken; ett teamrutnät med tre kolumner
 * kvävs i den bredden. Standard är den smala, eftersom läsbarhet är det
 * vanligaste behovet och den bredare är det som kräver ett skäl.
 */
export function InnehallsSida({
  bredd = "text",
  children
}: Readonly<{ bredd?: "text" | "vid"; children: React.ReactNode }>) {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b border-ink/10">
        <div className="mx-auto flex max-w-[1480px] items-center justify-between px-6 py-5 md:px-10">
          <Link href="/" className="focus-ring" aria-label="Till startsidan">
            <Logo />
          </Link>
          {/* Menyn står MED här, inte bara på landningssidorna.
              Två skäl. Den som landat på /faq från ett sökresultat ska kunna
              nå bokningen utan att först gå hem — annars är innehållssidorna
              återvändsgränder. Och markeringen av aktiv flik i SidMeny blir
              annars kod som aldrig kan utlösas: menyn hade bara funnits på
              sidor som ingen menypost pekar på. */}
          <div className="flex items-center gap-1">
            <Link href="/" className="focus-ring rounded-input px-3 py-2 text-sm text-ink/60 hover:text-ink">
              Till startsidan
            </Link>
            <SidMeny />
          </div>
        </div>
      </header>

      <main className={bredd === "vid" ? "mx-auto max-w-[1100px] px-6 py-16 md:py-24" : "mx-auto max-w-[68ch] px-6 py-16 md:py-24"}>
        {children}
      </main>

      <Sidfot />
    </div>
  );
}

/**
 * Rubrik + ingress, i sidornas gemensamma form.
 *
 * Egen komponent och inte kopierade klasser: rubrikgraden är samma clamp som
 * JuridiskSida använder, och den dagen den justeras ska den justeras en gång.
 */
export function SidRubrik({
  rubrik,
  ingress
}: Readonly<{ rubrik: string; ingress?: React.ReactNode }>) {
  return (
    <>
      <h1 className="font-display text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.05] tracking-[-0.03em]">
        {rubrik}
      </h1>
      {ingress ? (
        <p className="mt-6 max-w-[62ch] text-[1.125rem] leading-[1.7] text-ink/75">{ingress}</p>
      ) : null}
    </>
  );
}

/**
 * Avslutande uppmaning. Varje innehållssida ska sluta med en väg vidare —
 * annars är sista raden en återvändsgränd.
 */
export function SidAvslut({
  rubrik,
  text,
  primar,
  sekundar
}: Readonly<{
  rubrik: string;
  text: string;
  primar: { etikett: string; href: string };
  sekundar?: { etikett: string; href: string };
}>) {
  return (
    <section className="mt-20 rounded-card border border-ink/12 bg-paper2/50 p-8 md:p-10">
      <h2 className="font-display text-[1.5rem] font-semibold leading-snug tracking-[-0.02em]">
        {rubrik}
      </h2>
      <p className="mt-3 max-w-[58ch] text-[1rem] leading-[1.7] text-ink/70">{text}</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href={primar.href}
          className="focus-ring inline-flex min-h-12 items-center rounded-input bg-ink px-6 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
        >
          {primar.etikett}
        </Link>
        {sekundar ? (
          <a
            href={sekundar.href}
            className="focus-ring inline-flex min-h-12 items-center rounded-input border border-ink/20 px-6 text-[0.9375rem] font-semibold transition-colors hover:border-ink"
          >
            {sekundar.etikett}
          </a>
        ) : null}
      </div>
    </section>
  );
}
