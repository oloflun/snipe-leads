"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useArbetsvag } from "@/components/AppShell";
import { skanningsfel, useWebbplatsskanning, vard } from "@/components/settings/WebbplatsForslag";
import { btnPrimary, btnSecondary, rubrikPanel, rubrikSektion } from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Första vyn efter onboardingen: vad en ny kund gör härnäst.
 *
 * Den visuella genomgången 2026-11-18 landade en nyss upplagd kund på
 * översikten, som då är en statistiksida utan statistik: sex rutor med
 * "Inget att visa än" och inget som säger vad nästa steg är. Raderna här
 * leder till de sidor som redan finns för just de stegen.
 *
 * Visas bara medan arbetsytan saknar aktivitet (villkoret bor i Aktivitet)
 * och försvinner av sig själv när första körningen finns. Det är alltså inte
 * hälsningen som Anton tog bort ur översikten 2026-10-07: den stod kvar för
 * alla, alltid. Skälet står i docs/BESLUT.md (2026-11-18).
 *
 * En linjerad lista, NOT en kortrad: stegen har en ordning, och en lista med
 * hårlinjer läses uppifrån och ned.
 */

type Steg = { id: string; rubrik: Localized; text: Localized; knapp: Localized; href: string };

const T = {
  rubrik: { sv: "Kom igång", en: "Get started" },
  ingress: {
    sv: "Arbetsytan är upplagd. De här stegen tar er till det första svaret och det första leadet.",
    en: "Your workspace is set up. These steps take you to the first reply and the first lead."
  },
  skanningPagar: {
    sv: "Vi läser {sajt} nu och skriver förslag till kunskapsbasen.",
    en: "We are reading {sajt} now and writing suggestions for the knowledge base."
  },
  skanningForslag: {
    sv: "{n} förslag från {sajt} väntar på er.",
    en: "{n} suggestions from {sajt} are waiting for you."
  },
  skanningFel: { sv: "{sajt} gick inte att läsa: {fel}", en: "{sajt} could not be read: {fel}" },
  granska: { sv: "Granska förslagen", en: "Review the suggestions" }
} satisfies Record<string, Localized>;

function fyll(mall: string, varden: Record<string, string | number>): string {
  return mall.replace(/\{(\w+)\}/g, (_, nyckel: string) => String(varden[nyckel] ?? ""));
}

const SUPPORT: Steg[] = [
  {
    id: "kunskapsbas",
    rubrik: { sv: "Fyll kunskapsbasen", en: "Fill the knowledge base" },
    text: {
      sv: "Supportagenten svarar ur kunskapsbasen. Lägg in villkor, priser och era vanligaste frågor.",
      en: "The support agent answers from the knowledge base. Add terms, prices and your most common questions."
    },
    knapp: { sv: "Kunskapsbasen", en: "Knowledge base" },
    href: "/settings/kunskapsbas"
  },
  {
    id: "testchatt",
    rubrik: { sv: "Prova supportagenten", en: "Try the support agent" },
    text: {
      sv: "Ställ en fråga i testchatten och se hur agenten svarar innan någon kund gör det.",
      en: "Ask a question in the test chat and see how the agent answers before a customer does."
    },
    knapp: { sv: "Kundtjänst", en: "Customer service" },
    href: "/dashboard/support"
  }
];

const LEADS: Steg[] = [
  {
    id: "malgrupp",
    rubrik: { sv: "Granska målgruppen", en: "Review the target group" },
    text: {
      sv: "Det ni skrev i uppstarten ligger som utkast. Justera branscher, orter och storlek.",
      en: "What you entered during setup is saved as a draft. Adjust industries, towns and size."
    },
    knapp: { sv: "Målgruppen", en: "Target group" },
    href: "/settings/leads"
  },
  {
    id: "korning",
    rubrik: { sv: "Starta första körningen", en: "Start the first run" },
    text: {
      sv: "Iris letar bolag i målgruppen och skriver utkast. Inget skickas förrän ni själva slår på utskicken.",
      en: "Iris looks for companies in the target group and writes drafts. Nothing is sent until you switch sending on yourselves."
    },
    knapp: { sv: "Leads", en: "Leads" },
    href: "/dashboard/leads"
  }
];

const ROST: Steg = {
  id: "rost",
  rubrik: { sv: "Bestäm hur agenterna ska låta", en: "Decide how the agents should sound" },
  text: {
    sv: "Ett utkast till röstdokument finns redan. Läs igenom det och ändra tonen så att den blir er.",
    en: "A draft voice document is already there. Read it through and change the tone until it is yours."
  },
  knapp: { sv: "Röstdokumentet", en: "Voice document" },
  href: "/settings/soul"
};

export function KomIgang({ iris, support }: Readonly<{ iris: boolean; support: boolean }>) {
  const { text } = useLocale();
  const vag = useArbetsvag();
  const steg = [...(support ? SUPPORT : []), ...(iris ? LEADS : []), ROST];
  // Skanningen som onboardingen startade (lib/snajp/webbplatsskanning.ts).
  // Förloppet syns på kunskapsbassteget, där kunden landar efter guiden.
  const { lage } = useWebbplatsskanning(support);
  const skanning = lage?.skanning ?? null;
  const vantande = lage?.forslag.length ?? 0;
  const sajt = skanning ? vard(skanning.webbplats) : "";

  return (
    <section aria-labelledby="kom-igang" className="rounded-card border border-ink/15 bg-paper p-5 sm:p-6">
      <h2 id="kom-igang" className={rubrikSektion}>
        {text(T.rubrik)}
      </h2>
      <p className="mt-2 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">{text(T.ingress)}</p>
      <ol className="mt-5">
        {steg.map((s, i) => (
          <li
            key={s.id}
            className="flex flex-col gap-3 border-t border-ink/12 py-4 last:pb-0 sm:flex-row sm:items-center sm:gap-5"
          >
            <span className="font-display text-[1.5rem] leading-none tabular-nums text-warning sm:w-6" aria-hidden>
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <h3 className={rubrikPanel}>{text(s.rubrik)}</h3>
              <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">{text(s.text)}</p>
              {s.id === "kunskapsbas" && skanning?.status === "pagar" ? (
                <p role="status" className="mt-2 flex items-center gap-2 text-[0.875rem] font-medium text-ink">
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-warning" aria-hidden />
                  {fyll(text(T.skanningPagar), { sajt })}
                </p>
              ) : null}
              {s.id === "kunskapsbas" && vantande > 0 ? (
                <p className="mt-2 text-[0.875rem] font-medium text-ink">
                  {fyll(text(T.skanningForslag), { n: vantande, sajt })}
                </p>
              ) : null}
              {s.id === "kunskapsbas" && skanning?.status === "fel" ? (
                <p className="mt-2 text-[0.875rem] font-medium text-danger">
                  {fyll(text(T.skanningFel), { sajt, fel: text(skanningsfel(skanning.fel)) })}
                </p>
              ) : null}
            </div>
            <Link
              href={vag(s.href)}
              className={cn(
                s.id === "kunskapsbas" && vantande > 0 ? btnPrimary : btnSecondary,
                // Hel bredd på mobil: rubriken säger redan vad steget är, knappen
                // vart det leder, och den ska aldrig brytas på två rader.
                "w-full shrink-0 whitespace-nowrap sm:w-auto sm:self-center"
              )}
            >
              {s.id === "kunskapsbas" && vantande > 0 ? text(T.granska) : text(s.knapp)}
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
