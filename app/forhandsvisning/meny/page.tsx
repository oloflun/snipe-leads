"use client";

import { Eye, LogOut, Menu, ShieldCheck } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Menyraden: tre ändringar, före och efter.
 *
 * Ingenting här är applicerat i produkten. Sidan finns för att ändringarna ska
 * gå att SE bredvid varandra innan de görs — headern renderas på varje inloggad
 * yta, och ett byte där märks på alla sidor samtidigt.
 *
 * ## 1. Kundtjänst saknas i menyn, och det är ett fel
 *
 * Flikarna ÄR lägesväxeln (`FLIKENS_LAGE` i components/AppShell.tsx): Leads
 * smalnar av hela vyn till leads, Kundtjänst till support, Översikt tar
 * tillbaka båda. Samtidigt filtreras flikraden på `shows()`, alltså på det läge
 * man just valt.
 *
 * De två tillsammans blir en fälla: står man i Leads döljs Kundtjänst-fliken —
 * och det är den man skulle ha tryckt på för att komma till kundtjänst. Enda
 * vägen tillbaka är Översikt, och att man ska gå via den står ingenstans.
 *
 * Förslaget: produktflikarna renderas alltid när arbetsytan äger produkten.
 * Entitlement styr vad som FINNS, läget styr vad som VISAS i innehållet — men
 * en kontroll får aldrig gömma sig själv.
 *
 * ## 2. Flikarna centrerade
 *
 * Lika långt till båda kanterna, i stället för vänsterställda under logotypen.
 *
 * ## 3. Större logotyp
 *
 * Logotypen flyttas ut i vänsterkanten och tillåts fylla höjden ner till
 * flikraden, i stället för att sitta på en egen rad ovanför den.
 */

const FLIKAR_NU = ["Översikt", "Leads", "Email studio", "Inställningar"];
const FLIKAR_FORSLAG = ["Översikt", "Leads", "Kundtjänst", "Email studio", "Inställningar"];

function Kontroller({ stor = false }: Readonly<{ stor?: boolean }>) {
  return (
    <div className={cn("flex items-center gap-1.5", stor && "self-start")}>
      <div className="flex items-center rounded-input bg-paper2/70 p-0.5">
        <span className="inline-flex items-center gap-1.5 rounded-input px-2.5 py-1 text-[13px] text-ink/50">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
          Admin
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-input bg-paper px-2.5 py-1 text-[13px] font-medium text-ink">
          <Eye className="h-3.5 w-3.5" aria-hidden />
          Demo
        </span>
      </div>
      <span className="px-3 text-sm font-medium text-ink/55">EN</span>
      <span className="inline-flex items-center gap-1.5 rounded-input border border-ink/15 px-3 py-1.5 text-sm font-medium text-ink/70">
        <Menu className="h-4 w-4" aria-hidden />
        Meny
      </span>
      <span className="inline-flex items-center gap-1.5 px-3 text-sm font-medium text-ink/55">
        <LogOut className="h-4 w-4" aria-hidden />
        Logga ut
      </span>
    </div>
  );
}

/** Dagens header, återskapad. */
function HeaderNu({ aktiv }: Readonly<{ aktiv: string }>) {
  return (
    <header className="bg-paper">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3 md:px-6">
        <span className="inline-flex items-center gap-2.5">
          <Image src="/snajp-symbol-black.svg" alt="" width={200} height={158} className="h-[18px] w-auto" />
          <span className="text-[19px] font-semibold leading-none tracking-[-0.02em]">Snajp</span>
        </span>
        <span className="hidden text-sm text-ink/45 sm:inline">Nordlys Handel</span>

        <div className="ml-auto">
          <Kontroller />
        </div>

        <nav className="order-last -mx-1 flex w-full min-w-0 gap-1 px-1 pb-1">
          {FLIKAR_NU.map((flik) => (
            <span
              key={flik}
              className={cn(
                "inline-flex min-h-11 shrink-0 items-center rounded-input px-3 text-sm font-medium",
                flik === aktiv ? "bg-paper2 text-ink" : "text-ink/55"
              )}
            >
              {flik}
            </span>
          ))}
        </nav>
      </div>
    </header>
  );
}

/** Förslaget: stor logotyp till vänster, centrerade flikar, Kundtjänst med. */
function HeaderForslag({
  aktiv,
  onValj
}: Readonly<{ aktiv: string; onValj: (flik: string) => void }>) {
  return (
    <header className="bg-paper">
      <div className="mx-auto flex max-w-[1400px] items-stretch gap-x-6 px-4 py-3 md:px-6">
        {/* Logotypen får egen kolumn och fyller båda radernas höjd. Den ligger
            därmed i vänsterkanten i stället för på en rad ovanför flikarna. */}
        <span className="flex shrink-0 items-center gap-3">
          <Image src="/snajp-symbol-black.svg" alt="" width={200} height={158} className="h-[34px] w-auto" />
          <span className="flex flex-col justify-center">
            <span className="text-[26px] font-semibold leading-none tracking-[-0.02em]">Snajp</span>
            <span className="mt-1 text-[13px] leading-none text-ink/45">Nordlys Handel</span>
          </span>
        </span>

        {/* Flikarna centreras i det utrymme som blir över. `flex-1` på båda
            sidor om raden ger lika mycket luft åt vänster och höger oavsett hur
            breda logotypen och kontrollerna är. */}
        <nav className="flex flex-1 items-center justify-center">
          <div className="flex flex-wrap justify-center gap-1">
            {FLIKAR_FORSLAG.map((flik) => (
              <button
                key={flik}
                type="button"
                onClick={() => onValj(flik)}
                className={cn(
                  "focus-ring inline-flex min-h-11 shrink-0 items-center rounded-input px-3.5 text-sm font-medium transition-colors",
                  flik === aktiv ? "bg-paper2 text-ink" : "text-ink/55 hover:bg-paper2/60 hover:text-ink"
                )}
              >
                {flik}
              </button>
            ))}
          </div>
        </nav>

        <Kontroller stor />
      </div>
    </header>
  );
}

function Innehall({ flik }: Readonly<{ flik: string }>) {
  const text: Record<string, string> = {
    Översikt: "Läget i båda agenterna, och vad som väntar på dig.",
    Leads: "Bolag agenterna hittat, vad de grundade urvalet i, och vad som väntar på dig.",
    Kundtjänst: "Inkommande ärenden, agenternas klassificering och svaren som väntar på godkännande.",
    "Email studio": "Ämnesrad, brödtext och uppföljning. Varje åtgärd visar vad den ändrade.",
    Inställningar: "Vad agenterna vet, vad de får göra, och kontot."
  };
  return (
    <div className="mx-auto max-w-[1400px] border-t border-ink/10 px-4 py-8 md:px-6">
      <p className="text-[0.8125rem] font-medium text-ink/45">{flik}</p>
      <h2 className="mt-1 text-[1.5rem] font-semibold leading-tight tracking-[-0.02em]">
        {flik === "Kundtjänst" ? "Inkorg och utkast" : flik}
      </h2>
      <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink/65">{text[flik]}</p>
    </div>
  );
}

export default function Page() {
  const [flik, setFlik] = useState("Översikt");

  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-[1100px] px-4 py-10 md:px-6">
        <p className="text-[0.8125rem] font-medium text-ink/45">Förhandsvisning</p>
        <h1 className="mt-1 text-[1.5rem] font-semibold leading-tight tracking-[-0.02em]">
          Menyraden — tre ändringar
        </h1>
        <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink/65">
          Ingenting är applicerat. Så här skulle det se ut.
        </p>

        <ol className="mt-5 max-w-[72ch] space-y-3 text-[15px] leading-6 text-ink/75">
          <li>
            <strong className="font-semibold">Kundtjänst finns i menyn</strong> och går att klicka
            på. Att den saknas idag är ett fel, inte ett val: flikarna är lägesväxeln, och när du
            står i Leads filtreras Kundtjänst bort — alltså göms den kontroll du skulle ha använt
            för att komma dit. Enda vägen tillbaka är Översikt, och det står ingenstans.
          </li>
          <li>
            <strong className="font-semibold">Flikarna är centrerade</strong> — lika långt till
            båda kanterna, oavsett hur breda logotypen och kontrollerna är.
          </li>
          <li>
            <strong className="font-semibold">Logotypen är större</strong>, ligger i vänsterkanten
            och fyller höjden ner till flikraden i stället för att sitta på en egen rad ovanför.
          </li>
        </ol>
      </div>

      <section className="border-y border-ink/10 bg-paper2/30 py-8">
        <div className="mx-auto max-w-[1400px] px-4 md:px-6">
          <p className="text-[13px] font-medium uppercase tracking-[0.04em] text-ink/45">Nu</p>
        </div>
        <div className="mt-3 border-y border-ink/10 bg-paper">
          <HeaderNu aktiv="Översikt" />
        </div>
      </section>

      <section className="py-8">
        <div className="mx-auto max-w-[1400px] px-4 md:px-6">
          <p className="text-[13px] font-medium uppercase tracking-[0.04em] text-ochre">
            Förslag — klicka på flikarna
          </p>
        </div>
        <div className="mt-3 border-y border-ink/10 bg-paper">
          <HeaderForslag aktiv={flik} onValj={setFlik} />
          <Innehall flik={flik} />
        </div>
      </section>
    </main>
  );
}
