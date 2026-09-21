import {
  Check,
  Hand,
  MessageCircle,
  Paperclip,
  Scissors,
  Send,
  Smile,
  Sparkles,
  X
} from "lucide-react";
import type { Localized } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";
import { cn } from "@/lib/utils";

/* Snajp · genre: nordic-editorial · design-system: DESIGN.md · designed-as-app */

/**
 * Produktbilderna — sektionen som ersatte problemtexten (2026-09-21).
 *
 * Två renderade produktytor per agent, sida vid sida: ingen skärmdump, ingen
 * fejkad webbläsarram, utan samma ytor som produkten faktiskt ritar, byggda i
 * samma tokens. DESIGN.md:s ärlighetsregel gäller: allt innehåll är
 * exempeldata och raden under sektionen säger det.
 *
 * Ordningen växlar per produkt ("andra sidan uppifrån" — Sebbes ord): den som
 * bläddrar mellan flikarna ska se bilderna byta sida, inte samma uppställning
 * tre gånger.
 *
 * Ytan är en ILLUSTRATION: inga riktiga knappar, allt är spans och div:ar,
 * aria-hidden på interiören så en skärmläsare får bildtexten i stället för
 * fyrtio rader låtsas-UI. Widgetens ruta bär "Powered by Snajp" och medvetet
 * INGET företagsnamn — på kundens sajt står kundens logotyp där, och en
 * påhittad logga här hade varit ett påstående om en kund som inte finns.
 */

type Falt = { rubrik: Localized; bild: React.ReactNode; not: Localized };

function T({ text, locale }: Readonly<{ text: Localized; locale: "sv" | "en" }>) {
  return <>{text[locale]}</>;
}

/* -- Småbitar som återkommer i flera ytor ---------------------------------- */

function Badge({
  children,
  ton = "neutral"
}: Readonly<{ children: React.ReactNode; ton?: "neutral" | "warn" | "good" }>) {
  const toner = {
    neutral: "border-ink/10 bg-ink/[0.035] text-ink-muted",
    warn: "border-ochre/25 bg-ochre/10 text-ink",
    good: "border-moss/20 bg-moss/10 text-moss"
  };
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-[6px] border px-2 py-0.5 text-[0.6875rem] font-medium",
        toner[ton]
      )}
    >
      {children}
    </span>
  );
}

function Knapp({
  children,
  variant = "sekundar"
}: Readonly<{ children: React.ReactNode; variant?: "primar" | "sekundar" }>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-input px-3 py-1.5 text-[0.75rem] font-semibold",
        variant === "primar" ? "bg-ink text-paper" : "border border-ink/15 bg-paper text-ink"
      )}
    >
      {children}
    </span>
  );
}

/* -- Ytan 1: chattwidgeten på kundens sajt ---------------------------------- */

function WidgetYta() {
  return (
    <div aria-hidden className="relative flex min-h-[420px] items-end justify-end bg-paper2/50 p-5 sm:p-7">
      {/* Kundens sida antyds med två textplan — inte en fejkad webbläsare. */}
      <div className="absolute left-5 top-6 hidden opacity-45 sm:block">
        <div className="h-2.5 w-24 rounded-full bg-ink/20" />
        <div className="mt-3 h-2 w-40 rounded-full bg-ink/10" />
        <div className="mt-2 h-2 w-32 rounded-full bg-ink/10" />
      </div>

      <div className="flex w-full max-w-[300px] flex-col items-end gap-3">
        {/* Chattpanelen, öppen. Samma anatomi som EmbedYta/SupportChat. */}
        <div className="w-full overflow-hidden rounded-[16px] border border-ink/12 bg-paper shadow-[0_12px_36px_oklch(var(--ink)/0.16)]">
          <div className="flex items-center justify-between border-b border-ink/10 px-4 py-2.5">
            <span className="kicker text-mineral">Powered by Snajp</span>
            <X className="h-3.5 w-3.5 text-ink-subtle" />
          </div>
          <div className="space-y-2.5 px-3.5 py-3.5 text-[0.75rem] leading-[1.5]">
            <div className="ml-auto w-fit max-w-[85%] rounded-[12px] rounded-br-[4px] bg-ink px-3 py-2 text-paper">
              Hej! Vad kostar frakten?
            </div>
            <div className="w-fit max-w-[90%] rounded-[12px] rounded-bl-[4px] border border-ink/10 bg-paper2/70 px-3 py-2 text-ink">
              Frakten är 49 kr, och fri frakt över 499 kr. Beställer du före
              kl. 14 skickas paketet samma dag. Vill du veta leveranstiden till
              din ort?
            </div>
          </div>
          <div className="flex items-center gap-2 border-t border-ink/10 px-3.5 py-2.5">
            <span className="flex-1 text-[0.75rem] text-ink-subtle">Skriv ditt meddelande …</span>
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ink text-paper">
              <Send className="h-3.5 w-3.5" />
            </span>
          </div>
        </div>

        {/* Inbjudan + knappen — stängda läget, Skatteverkets mönster. */}
        <div className="flex items-end gap-2.5">
          <div className="rounded-[12px] border border-ink/10 bg-paper px-3 py-2 text-[0.75rem] shadow-[0_6px_20px_oklch(var(--ink)/0.10)]">
            <span className="block font-semibold text-ink">Undrar du något?</span>
            <span className="block text-ink-muted">Fråga oss direkt här.</span>
          </div>
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-ink text-paper shadow-[0_6px_20px_oklch(var(--ink)/0.22)]">
            <MessageCircle className="h-5 w-5" />
          </span>
        </div>
      </div>
    </div>
  );
}

/* -- Ytan 2: supportinkorgen med offertutkastet ----------------------------- */

function InkorgYta() {
  return (
    <div aria-hidden className="grid min-h-[420px] gap-0 bg-paper text-left sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      {/* Ärendelistan */}
      <div className="hidden border-r border-ink/10 p-4 sm:block">
        <div className="divide-y divide-ink/10 border-y border-ink/12 text-[0.75rem]">
          <div className="bg-paper2/60 py-2.5 pl-2 pr-1">
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate font-medium text-ink">Offert HLR-utbildning, 40 pers</span>
              <Badge ton="warn">Väntar på dig</Badge>
            </span>
            <span className="mt-0.5 block truncate text-ink-subtle">Maria Ek · Offertförfrågan</span>
          </div>
          <div className="py-2.5 pl-2 pr-1">
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate font-medium text-ink">Var är min beställning?</span>
              <Badge ton="good">Skickat</Badge>
            </span>
            <span className="mt-0.5 block truncate text-ink-subtle">Johan Berg · Orderstatus</span>
          </div>
          <div className="py-2.5 pl-2 pr-1">
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate font-medium text-ink">Faktura saknar OCR</span>
              <Badge>Eskalerat</Badge>
            </span>
            <span className="mt-0.5 block truncate text-ink-subtle">Ali Rahim · Betalning</span>
          </div>
        </div>
      </div>

      {/* Det öppna ärendet med agentens utkast */}
      <div className="p-4 sm:p-5">
        <p className="text-[0.875rem] font-semibold text-ink">Offert HLR-utbildning, 40 pers</p>
        <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">
          Från: Maria Ek &lt;maria.ek@exempel.se&gt;
        </p>
        <p className="mt-2 border-l border-ink/15 pl-3 text-[0.75rem] leading-[1.55] text-ink-muted">
          Hej! Vi vill utbilda 40 medarbetare i HLR under hösten. Vad skulle det
          landa på, och vad ingår?
        </p>

        <p className="mt-4 font-display text-[0.9375rem] text-ink">Agentens utkast</p>
        <div className="mt-1.5 rounded-input border border-ink/12 bg-paper px-3 py-2.5 text-[0.75rem] leading-[1.55] text-ink">
          Hej Maria! Tack för er förfrågan. För 40 deltagare blir det 1 200 kr
          per person: totalt 48 000 kr exkl. moms. Instruktör, material och
          intyg ingår, hos er eller i våra lokaler. Offerten gäller 30 dagar.
          Vilka veckor passar er?
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <Knapp variant="primar">
            <Check className="h-3 w-3" />
            Godkänn &amp; skicka
          </Knapp>
          <Knapp>
            <Hand className="h-3 w-3" />
            Ta över
          </Knapp>
          <span className="mx-0.5 h-4 w-px bg-ink/15" />
          <Knapp>
            <Sparkles className="h-3 w-3" />
            Förbättra
          </Knapp>
          <Knapp>
            <Scissors className="h-3 w-3" />
            Kortare
          </Knapp>
          <Knapp>
            <Smile className="h-3 w-3" />
            Mer personlig
          </Knapp>
        </div>
      </div>
    </div>
  );
}

/* -- Ytan 3: Iris hittar och skriver ---------------------------------------- */

function IrisListYta() {
  const rader = [
    { bolag: "Byggnads AB Norr", grund: "Söker två plåtslagare i Umeå", poang: "87" },
    { bolag: "Fjällvind Energi", grund: "Nytt kontor i Östersund", poang: "82" },
    { bolag: "Sundsvalls Måleri", grund: "Vann ramavtal i september", poang: "74" },
    { bolag: "Höga Kusten Bygg", grund: "Utökar med markarbeten", poang: "71" }
  ];
  return (
    <div aria-hidden className="flex min-h-[420px] flex-col bg-paper p-4 text-left sm:p-5">
      <p className="text-[0.875rem] font-semibold text-ink">Nya leads i natt</p>
      <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">
        Iris har läst platsannonser, pressmeddelanden och bolagens egna sajter.
      </p>
      <div className="mt-3 divide-y divide-ink/10 border-y border-ink/12">
        {rader.map((rad) => (
          <div key={rad.bolag} className="flex items-center gap-3 py-3">
            <span className="numeral w-12 text-[1.75rem]">{rad.poang}</span>
            <span className="min-w-0">
              <span className="block truncate text-[0.8125rem] font-medium text-ink">
                {rad.bolag}
              </span>
              <span className="block truncate text-[0.6875rem] text-ink-subtle">{rad.grund}</span>
            </span>
          </div>
        ))}
      </div>
      <p className="mt-auto pt-3 text-[0.6875rem] text-ink-subtle">
        Poängen är matchningen mot er kundprofil. Under 70 sorteras bort.
      </p>
    </div>
  );
}

function IrisUtkastYta() {
  return (
    <div aria-hidden className="flex min-h-[420px] flex-col bg-paper p-4 text-left sm:p-5">
      <p className="text-[0.875rem] font-semibold text-ink">Utkast till Byggnads AB Norr</p>
      <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">
        Till: Johan Nyström, platschef · Ämne: Skyddsutrustning till
        Umeåprojekten · researchen bifogas
      </p>
      <div className="mt-3 rounded-input border border-ink/12 bg-paper px-3 py-2.5 text-[0.75rem] leading-[1.55] text-ink">
        Hej Johan! Såg att ni söker två plåtslagare till projekten i Umeå, kul
        att det rullar för er. När bemanningen växer brukar skyddsutrustningen
        släpa efter, och det är precis det vi hjälper byggbolag med. Får jag
        skicka ett prisförslag på paket för 15 man?
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Knapp variant="primar">
          <Check className="h-3 w-3" />
          Godkänn och skicka
        </Knapp>
        <Knapp>Redigera</Knapp>
        <Knapp>Hoppa över</Knapp>
      </div>
      <p className="mt-auto border-t border-ink/10 pt-2.5 text-[0.6875rem] leading-[1.5] text-ink-subtle">
        Varje rad i mejlet pekar på en källa: platsannonsen, pressnotisen eller
        bolagets egen sajt. Inget skickas utan ditt godkännande.
      </p>
    </div>
  );
}

/* -- Ytan 4: kvittoagenten -------------------------------------------------- */

function KvittoListYta() {
  const rader = [
    { fran: "Circle K", belopp: "749,00 kr", status: "Väntar på dig", ton: "warn" as const },
    { fran: "ICA Maxi", belopp: "482,50 kr", status: "Bokfört", ton: "good" as const },
    { fran: "SJ", belopp: "1 245,00 kr", status: "Bokfört", ton: "good" as const },
    { fran: "Bauhaus", belopp: "1 899,00 kr", status: "Bokfört", ton: "good" as const },
    { fran: "Postnord", belopp: "165,00 kr", status: "Bokfört", ton: "good" as const }
  ];
  return (
    <div aria-hidden className="flex min-h-[420px] flex-col bg-paper p-4 text-left sm:p-5">
      <p className="text-[0.875rem] font-semibold text-ink">Kvitton ur mejlen</p>
      <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">
        Läses in av sig själva. Vidarebefordra eller fota resten.
      </p>
      <div className="mt-3 divide-y divide-ink/10 border-y border-ink/12 text-[0.75rem]">
        {rader.map((rad) => (
          <div key={rad.fran} className="flex items-center justify-between gap-3 py-3">
            <span className="flex min-w-0 items-center gap-2.5">
              <Paperclip className="h-3.5 w-3.5 shrink-0 text-ink-subtle" />
              <span className="truncate font-medium text-ink">{rad.fran}</span>
            </span>
            <span className="flex shrink-0 items-center gap-2.5">
              <span className="tabular-nums text-ink">{rad.belopp}</span>
              <Badge ton={rad.ton}>{rad.status}</Badge>
            </span>
          </div>
        ))}
      </div>
      <p className="mt-auto pt-3 text-[0.6875rem] leading-[1.5] text-ink-subtle">
        Modellen läser av kvittot; all aritmetik räknas i kod, på öret.
      </p>
    </div>
  );
}

function VerifikatYta() {
  return (
    <div aria-hidden className="flex min-h-[420px] flex-col bg-paper p-4 text-left sm:p-5">
      <p className="text-[0.875rem] font-semibold text-ink">Verifikat V-231 · Circle K</p>
      <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">Drivmedel, betalkort · 18 sep 2026</p>
      <div className="mt-3 border-y border-ink/12 text-[0.75rem]">
        <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 border-b border-ink/10 py-2 text-[0.6875rem] text-ink-subtle">
          <span>Konto</span>
          <span className="text-right">Debet</span>
          <span className="text-right">Kredit</span>
        </div>
        {[
          ["5611 Drivmedel", "599,20", ""],
          ["2641 Ingående moms", "149,80", ""],
          ["1930 Företagskonto", "", "749,00"]
        ].map(([konto, debet, kredit]) => (
          <div
            key={konto}
            className="grid grid-cols-[1fr_auto_auto] gap-x-4 border-b border-ink/10 py-2 last:border-b-0"
          >
            <span className="truncate text-ink">{konto}</span>
            <span className="min-w-[4.5rem] text-right tabular-nums text-ink">{debet}</span>
            <span className="min-w-[4.5rem] text-right tabular-nums text-ink">{kredit}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Knapp variant="primar">
          <Check className="h-3 w-3" />
          Godkänn
        </Knapp>
        <Knapp>Ändra konto</Knapp>
      </div>
      <p className="mt-auto pt-3 text-[0.6875rem] leading-[1.5] text-ink-subtle">
        Osäkert belopp eller utländsk valuta flaggas för granskning, aldrig en
        gissning i bokföringen.
      </p>
    </div>
  );
}

/* -- Sektionen --------------------------------------------------------------- */

const FALT: Record<ProductKey, [Falt, Falt]> = {
  support: [
    {
      rubrik: { sv: "Chatten på er egen sajt", en: "The chat on your own site" },
      bild: <WidgetYta />,
      not: {
        sv: "En rad kod. Stängd tills besökaren behöver den, i era färger, och svaren kommer ur er kunskapsbas.",
        en: "One line of code. Closed until the visitor needs it, in your colours, with answers from your knowledge base."
      }
    },
    {
      rubrik: { sv: "Inkorgen sköter sig själv", en: "The inbox runs itself" },
      bild: <InkorgYta />,
      not: {
        sv: "Agenten sorterar, skriver utkastet och räknar fram offerten. Du trycker Godkänn, eller låter den skriva om sig.",
        en: "The agent sorts, drafts the reply and works out the quote. You press Approve, or have it rewrite itself."
      }
    }
  ],
  leads: [
    {
      rubrik: { sv: "Mejlet skriver sig självt", en: "The email writes itself" },
      bild: <IrisUtkastYta />,
      not: {
        sv: "Personligt, grundat i researchen och i ert erbjudande. Du är alltid den som trycker godkänn och skicka.",
        en: "Personal, grounded in the research and your offer. You are always the one who presses approve and send."
      }
    },
    {
      rubrik: { sv: "Iris hittar bolagen åt dig", en: "Iris finds the companies for you" },
      bild: <IrisListYta />,
      not: {
        sv: "Tjugo minuters research per bolag blir en poängsatt lista över dem som är värda din tid, varje morgon.",
        en: "Twenty minutes of research per company becomes a scored list of the ones worth your time, every morning."
      }
    }
  ],
  bookkeeping: [
    {
      rubrik: { sv: "Kvittona samlar ihop sig", en: "The receipts gather themselves" },
      bild: <KvittoListYta />,
      not: {
        sv: "Ur mejlen, ur plånboken, ur mobilen. Inget blir liggande till kvartalets sista kväll.",
        en: "From your inbox, your wallet, your phone. Nothing sits around until the last night of the quarter."
      }
    },
    {
      rubrik: { sv: "Färdiga verifikat, på öret", en: "Finished vouchers, to the öre" },
      bild: <VerifikatYta />,
      not: {
        sv: "Kontering och moms föreslås klart. Du godkänner raden, eller ändrar kontot med två klick.",
        en: "Posting and VAT come ready. You approve the row, or change the account in two clicks."
      }
    }
  ]
};

const EXEMPELRAD: Localized = {
  sv: "Ytorna ovan är produktens egna, återgivna med exempeldata.",
  en: "The surfaces above are the product's own, shown with example data."
};

export function ProduktBilder({
  product,
  locale
}: Readonly<{ product: ProductKey; locale: "sv" | "en" }>) {
  const [vanster, hoger] = FALT[product];
  return (
    <section className="border-b border-ink/12">
      <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-32">
        <div className="grid grid-cols-1 gap-y-12 lg:grid-cols-2 lg:gap-x-12">
          {[vanster, hoger].map((falt, i) => (
            <figure key={falt.rubrik.sv} className={cn("rise", i === 1 && "rise-1")}>
              <div className="overflow-hidden rounded-panel border border-ink/12 bg-paper">
                {falt.bild}
              </div>
              <figcaption className="mt-5">
                <p className="font-display text-[1.375rem] font-semibold leading-tight tracking-[-0.015em] text-ink">
                  <T text={falt.rubrik} locale={locale} />
                </p>
                <p className="mt-2 max-w-[52ch] text-[0.9375rem] leading-[1.6] text-ink-muted">
                  <T text={falt.not} locale={locale} />
                </p>
              </figcaption>
            </figure>
          ))}
        </div>
        <p className="mt-8 text-[0.8125rem] text-ink-subtle">
          <T text={EXEMPELRAD} locale={locale} />
        </p>
      </div>
    </section>
  );
}
