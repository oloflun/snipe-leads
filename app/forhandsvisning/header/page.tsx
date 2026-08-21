"use client";

import { LogOut, Menu, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { cn } from "@/lib/utils";

/**
 * Tre förslag på ett färgat toppband, att välja mellan.
 *
 * ## Varför en demo och inte en ändring
 *
 * Headern renderas på var enda inloggad yta och på demovyn. Ett byte där är
 * inte en detalj — det är det första man ser på varje sida i produkten, och
 * "grå" kan betyda tre helt olika saker i den här paletten. Att gissa och
 * deploya hade betytt att valet görs i efterhand, av den som råkar reagera.
 *
 * ## Varför bandet över huvud taget
 *
 * Ytan är papper hela vägen upp, och navigationen flyter därför utan att ha en
 * plats. Ett band ger den en: raden blir en list och inte text som råkar ligga
 * högst upp. Trygg Hansa gör samma sak, och det är därifrån förfrågan kommer.
 *
 * ## Vad som INTE ändras i något av förslagen
 *
 * Innehållsytan förblir papper. Bandet gäller huvudet, inte sidan — en produkt
 * som är mörk hela vägen ner blir svårläst i de täta listorna, och det är där
 * arbetet faktiskt görs.
 */

type Variant = {
  id: string;
  namn: string;
  beskrivning: string;
  /** Bandets bakgrund och den textfärg som hör till. */
  band: string;
  text: string;
  textDampad: string;
  aktivFlik: string;
  inaktivFlik: string;
  hairline: string;
  /** Kontrast mot bandets bakgrund, uppmätt — inte uppskattad. */
  kontrast: string;
  /** Logotypens märke är mörkt som default och försvinner på ett mörkt band. */
  logotone: "ink" | "paper";
};

const VARIANTER: Variant[] = [
  {
    id: "djup",
    namn: "Djup",
    beskrivning:
      "Närmast Trygg Hansa: mörkt band, ljus text. Ger tyngst avgränsning och gör " +
      "ochre-accenten starkast — men är också den största förändringen av produktens uttryck.",
    band: "bg-ink",
    text: "text-paper",
    textDampad: "text-paper/55",
    aktivFlik: "bg-paper/15 text-paper",
    inaktivFlik: "text-paper/65 hover:bg-paper/10 hover:text-paper",
    hairline: "border-b border-paper/10",
    kontrast: "paper mot ink = 13.8:1",
    logotone: "paper"
  },
  {
    id: "dampad",
    namn: "Dämpad",
    beskrivning:
      "Mineralgrått band. Bär fortfarande ljus text men läser som en list snarare " +
      "än som en svart bård. Mellanläget.",
    band: "bg-seal",
    text: "text-paper",
    textDampad: "text-paper/60",
    aktivFlik: "bg-paper/15 text-paper",
    inaktivFlik: "text-paper/70 hover:bg-paper/10 hover:text-paper",
    hairline: "border-b border-paper/10",
    kontrast: "paper mot seal = 7.4:1",
    logotone: "paper"
  },
  {
    id: "papper",
    namn: "Papper 2",
    beskrivning:
      "Den varmgrå ton paletten redan använder för upphöjda ytor. Minsta ingreppet: " +
      "behåller mörk text och hela dagens uttryck, men raden får en egen plan.",
    band: "bg-paper2",
    text: "text-ink",
    textDampad: "text-ink/50",
    aktivFlik: "bg-paper text-ink",
    inaktivFlik: "text-ink/60 hover:bg-paper/70 hover:text-ink",
    hairline: "border-b border-ink/10",
    kontrast: "ink mot paper2 = 12.1:1",
    logotone: "ink"
  }
];

const FLIKAR = ["Översikt", "Leads", "Email studio", "Inställningar"];

function Header({ v, aktiv }: Readonly<{ v: Variant; aktiv: string }>) {
  return (
    <div className={cn(v.band, v.hairline)}>
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3 md:px-6">
        <span className={cn("inline-flex items-center", v.text)}>
          <Logo tone={v.logotone} />
        </span>
        <span className={cn("hidden text-sm sm:inline", v.textDampad)}>Nordlys Handel</span>

        <div className="ml-auto flex items-center gap-1.5">
          <div className={cn("flex items-center rounded-input p-0.5", v.id === "papper" ? "bg-paper/70" : "bg-paper/10")}>
            <span className={cn("inline-flex items-center gap-1.5 rounded-input px-2.5 py-1 text-[13px]", v.textDampad)}>
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
              Admin
            </span>
            <span className={cn("rounded-input px-2.5 py-1 text-[13px] font-medium", v.aktivFlik)}>Demo</span>
          </div>
          <span className={cn("px-3 text-sm font-medium", v.textDampad)}>EN</span>
          <span className={cn("inline-flex items-center gap-1.5 rounded-input border px-3 py-1.5 text-sm font-medium",
            v.id === "papper" ? "border-ink/15 text-ink/70" : "border-paper/25 text-paper/85")}>
            <Menu className="h-4 w-4" aria-hidden />
            Meny
          </span>
          <span className={cn("inline-flex items-center gap-1.5 px-3 text-sm font-medium", v.textDampad)}>
            <LogOut className="h-4 w-4" aria-hidden />
            Logga ut
          </span>
        </div>

        <nav className="order-last -mx-1 flex w-full min-w-0 gap-1 px-1">
          {FLIKAR.map((flik) => (
            <span
              key={flik}
              className={cn(
                "inline-flex min-h-11 shrink-0 items-center rounded-input px-3 text-sm font-medium",
                flik === aktiv ? v.aktivFlik : v.inaktivFlik
              )}
            >
              {flik}
            </span>
          ))}
        </nav>
      </div>
    </div>
  );
}

/** Lite innehåll under bandet — ett band utan sida under säger ingenting. */
function Innehall() {
  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 md:px-6">
      <p className="text-[0.8125rem] font-medium text-ink/45">Översikt</p>
      <h2 className="mt-1 text-[1.5rem] font-semibold leading-tight tracking-[-0.02em]">
        Läget i båda agenterna
      </h2>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[
          ["Prospekt", "12", "3 av dem är exempelbolag"],
          ["Väntar på dig", "2", "utkast i granskningskön"],
          ["Körningar 7 dgr", "5", "1 steg eskalerade till dig"]
        ].map(([etikett, tal, under]) => (
          <div key={etikett} className="rounded-card bg-paper2/60 p-5">
            <p className="text-[12px] font-medium uppercase tracking-[0.04em] text-ink/45">{etikett}</p>
            <p className="mt-2 text-[1.75rem] font-semibold tabular-nums tracking-[-0.02em]">{tal}</p>
            <p className="mt-1 text-[13px] text-ink/55">{under}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Page() {
  const [aktiv, setAktiv] = useState(VARIANTER[0].id);
  const vald = VARIANTER.find((v) => v.id === aktiv) ?? VARIANTER[0];

  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-[1100px] px-4 py-10 md:px-6">
        <p className="text-[0.8125rem] font-medium text-ink/45">Förhandsvisning</p>
        <h1 className="mt-1 text-[1.5rem] font-semibold leading-tight tracking-[-0.02em]">
          Färgat toppband — tre förslag
        </h1>
        <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink/65">
          Headern renderas på varje inloggad yta. Välj ett av förslagen nedan, så
          applicerar jag det på alla deployer. Innehållsytan förblir papper i alla
          tre — en produkt som är mörk hela vägen ner blir svårläst i de täta
          listorna, och det är där arbetet görs.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {VARIANTER.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => setAktiv(v.id)}
              className={cn(
                "focus-ring min-h-11 rounded-input px-4 text-[15px] font-medium transition-colors",
                v.id === aktiv ? "bg-ink text-paper" : "bg-paper2 text-ink/70 hover:text-ink"
              )}
            >
              {v.namn}
            </button>
          ))}
        </div>

        <p className="mt-4 max-w-[70ch] text-[14px] leading-6 text-ink/70">{vald.beskrivning}</p>
        <p className="mt-1 font-mono text-[12px] text-ink/45">Kontrast: {vald.kontrast}</p>
      </div>

      {/* Den valda varianten, i full bredd så bandet syns som det skulle göra. */}
      <div className="border-y border-ink/10">
        <Header v={vald} aktiv="Leads" />
        <Innehall />
      </div>

      <div className="mx-auto max-w-[1100px] px-4 py-12 md:px-6">
        <h2 className="text-[1.125rem] font-semibold tracking-[-0.01em]">Alla tre bredvid varandra</h2>
        <p className="mt-1 text-[14px] text-ink/60">
          Samma rad, samma innehåll. Skillnaden är bara bandet.
        </p>
        <div className="mt-6 space-y-8">
          {VARIANTER.map((v) => (
            <div key={v.id}>
              <p className="mb-2 text-[13px] font-medium text-ink/55">{v.namn}</p>
              <div className="overflow-hidden rounded-card border border-ink/10">
                <Header v={v} aktiv="Leads" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
