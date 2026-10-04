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
import type { Locale, Localized } from "@/lib/i18n";
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
 *
 * Språk: ytornas gränssnitt (rubriker, knappar, statusar) följer språkvalet.
 * Exempeldatan i dem (kundmejl, bolag, BAS-konton) är svensk med flit: det är
 * svenska kunders vardag som visas.
 */

type Yta = (props: Readonly<{ locale: Locale }>) => React.ReactNode;
type Falt = { rubrik: Localized; bild: Yta; not: Localized };

function T({ text, locale }: Readonly<{ text: Localized; locale: Locale }>) {
  return <>{text[locale]}</>;
}

const UI = {
  fraga: { sv: "Undrar du något?", en: "Any questions?" },
  fragaOss: { sv: "Fråga oss direkt här.", en: "Ask us right here." },
  skriv: { sv: "Skriv ditt meddelande …", en: "Write your message …" },
  vantar: { sv: "Väntar på dig", en: "Waiting for you" },
  skickat: { sv: "Skickat", en: "Sent" },
  eskalerat: { sv: "Eskalerat", en: "Escalated" },
  offertforfragan: { sv: "Offertförfrågan", en: "Quote request" },
  orderstatus: { sv: "Orderstatus", en: "Order status" },
  betalning: { sv: "Betalning", en: "Payment" },
  fran: { sv: "Från:", en: "From:" },
  agentensUtkast: { sv: "Agentens utkast", en: "Agent's draft" },
  godkannSkicka: { sv: "Godkänn & skicka", en: "Approve & send" },
  taOver: { sv: "Ta över", en: "Take over" },
  forbattra: { sv: "Förbättra", en: "Improve" },
  kortare: { sv: "Kortare", en: "Shorter" },
  personlig: { sv: "Mer personlig", en: "More personal" },
  nyaLeads: { sv: "Nya leads i natt", en: "New leads overnight" },
  irisLaste: {
    sv: "Iris har läst platsannonser, pressmeddelanden och bolagens egna sajter.",
    en: "Iris has read job ads, press releases and the companies' own sites."
  },
  poang: {
    sv: "Poängen är matchningen mot er kundprofil. Under 70 sorteras bort.",
    en: "The score is the match against your customer profile. Below 70 is filtered out."
  },
  utkastTill: { sv: "Utkast till", en: "Draft for" },
  till: { sv: "Till:", en: "To:" },
  amne: { sv: "Ämne:", en: "Subject:" },
  bifogas: { sv: "researchen bifogas", en: "research attached" },
  godkannOchSkicka: { sv: "Godkänn och skicka", en: "Approve and send" },
  redigera: { sv: "Redigera", en: "Edit" },
  hoppaOver: { sv: "Hoppa över", en: "Skip" },
  kalla: {
    sv: "Varje rad i mejlet pekar på en källa: platsannonsen, pressnotisen eller bolagets egen sajt. Inget skickas utan ditt godkännande.",
    en: "Every line in the email points to a source: the job ad, the press note or the company's own site. Nothing is sent without your approval."
  },
  bokfort: { sv: "Bokfört", en: "Posted" },
  kvittonUrMejlen: { sv: "Kvitton ur mejlen", en: "Receipts from your email" },
  lasesIn: {
    sv: "Läses in av sig själva. Vidarebefordra eller fota resten.",
    en: "They come in on their own. Forward or photograph the rest."
  },
  aritmetik: {
    sv: "Modellen läser av kvittot; all aritmetik räknas i kod, på öret.",
    en: "The model reads the receipt; all arithmetic is done in code, to the öre."
  },
  verifikat: { sv: "Verifikat", en: "Voucher" },
  konto: { sv: "Konto", en: "Account" },
  debet: { sv: "Debet", en: "Debit" },
  kredit: { sv: "Kredit", en: "Credit" },
  godkann: { sv: "Godkänn", en: "Approve" },
  andraKonto: { sv: "Ändra konto", en: "Change account" },
  osakert: {
    sv: "Osäkert belopp eller utländsk valuta flaggas för granskning, aldrig en gissning i bokföringen.",
    en: "An uncertain amount or a foreign currency is flagged for review, never a guess in the books."
  }
} satisfies Record<string, Localized>;

/* Exempeldata: svenska kunders mejl, desamma på båda språken. */
const CHATT_FRAGA = "Hej! Vad kostar frakten?";
const CHATT_SVAR = "Frakten är 49 kr, och fri frakt över 499 kr. Beställer du före kl. 14 skickas paketet samma dag. Vill du veta leveranstiden till din ort?"; // inte-copy
const ARENDE_HLR = "Offert HLR-utbildning, 40 pers";
const ARENDE_ORDER = "Var är min beställning?"; // inte-copy
const ARENDE_OCR = "Faktura saknar OCR";
const MARIA_MEJL = "Hej! Vi vill utbilda 40 medarbetare i HLR under hösten. Vad skulle det landa på, och vad ingår?"; // inte-copy
const MARIA_UTKAST = "Hej Maria! Tack för er förfrågan. För 40 deltagare blir det 1 200 kr per person: totalt 48 000 kr exkl. moms. Instruktör, material och intyg ingår, hos er eller i våra lokaler. Offerten gäller 30 dagar. Vilka veckor passar er?"; // inte-copy
const JOHAN_MOTTAGARE = "Johan Nyström, platschef"; // inte-copy
const JOHAN_AMNE = "Skyddsutrustning till Umeåprojekten"; // inte-copy
const JOHAN_MEJL = "Hej Johan! Såg att ni söker två plåtslagare till projekten i Umeå, kul att det rullar för er. När bemanningen växer brukar skyddsutrustningen släpa efter, och det är precis det vi hjälper byggbolag med. Får jag skicka ett prisförslag på paket för 15 man?"; // inte-copy

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

function WidgetYta({ locale }: Readonly<{ locale: Locale }>) {
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
              {CHATT_FRAGA}
            </div>
            <div className="w-fit max-w-[90%] rounded-[12px] rounded-bl-[4px] border border-ink/10 bg-paper2/70 px-3 py-2 text-ink">
              {CHATT_SVAR}
            </div>
          </div>
          <div className="flex items-center gap-2 border-t border-ink/10 px-3.5 py-2.5">
            <span className="flex-1 text-[0.75rem] text-ink-subtle">
              <T text={UI.skriv} locale={locale} />
            </span>
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ink text-paper">
              <Send className="h-3.5 w-3.5" />
            </span>
          </div>
        </div>

        {/* Inbjudan + knappen — stängda läget, Skatteverkets mönster. */}
        <div className="flex items-end gap-2.5">
          <div className="rounded-[12px] border border-ink/10 bg-paper px-3 py-2 text-[0.75rem] shadow-[0_6px_20px_oklch(var(--ink)/0.10)]">
            <span className="block font-semibold text-ink">
              <T text={UI.fraga} locale={locale} />
            </span>
            <span className="block text-ink-muted">
              <T text={UI.fragaOss} locale={locale} />
            </span>
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

function InkorgYta({ locale }: Readonly<{ locale: Locale }>) {
  return (
    <div aria-hidden className="grid min-h-[420px] gap-0 bg-paper text-left sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      {/* Ärendelistan */}
      <div className="hidden border-r border-ink/10 p-4 sm:block">
        <div className="divide-y divide-ink/10 border-y border-ink/12 text-[0.75rem]">
          <div className="bg-paper2/60 py-2.5 pl-2 pr-1">
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate font-medium text-ink">{ARENDE_HLR}</span>
              <Badge ton="warn">
                <T text={UI.vantar} locale={locale} />
              </Badge>
            </span>
            <span className="mt-0.5 block truncate text-ink-subtle">
              Maria Ek · <T text={UI.offertforfragan} locale={locale} />
            </span>
          </div>
          <div className="py-2.5 pl-2 pr-1">
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate font-medium text-ink">{ARENDE_ORDER}</span>
              <Badge ton="good">
                <T text={UI.skickat} locale={locale} />
              </Badge>
            </span>
            <span className="mt-0.5 block truncate text-ink-subtle">
              Johan Berg · <T text={UI.orderstatus} locale={locale} />
            </span>
          </div>
          <div className="py-2.5 pl-2 pr-1">
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate font-medium text-ink">{ARENDE_OCR}</span>
              <Badge>
                <T text={UI.eskalerat} locale={locale} />
              </Badge>
            </span>
            <span className="mt-0.5 block truncate text-ink-subtle">
              Ali Rahim · <T text={UI.betalning} locale={locale} />
            </span>
          </div>
        </div>
      </div>

      {/* Det öppna ärendet med agentens utkast */}
      <div className="p-4 sm:p-5">
        <p className="text-[0.875rem] font-semibold text-ink">{ARENDE_HLR}</p>
        <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">
          <T text={UI.fran} locale={locale} /> Maria Ek &lt;maria.ek@exempel.se&gt;
        </p>
        <p className="mt-2 border-l border-ink/15 pl-3 text-[0.75rem] leading-[1.55] text-ink-muted">
          {MARIA_MEJL}
        </p>

        <p className="mt-4 font-display text-[0.9375rem] text-ink">
          <T text={UI.agentensUtkast} locale={locale} />
        </p>
        <div className="mt-1.5 rounded-input border border-ink/12 bg-paper px-3 py-2.5 text-[0.75rem] leading-[1.55] text-ink">
          {MARIA_UTKAST}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <Knapp variant="primar">
            <Check className="h-3 w-3" />
            <T text={UI.godkannSkicka} locale={locale} />
          </Knapp>
          <Knapp>
            <Hand className="h-3 w-3" />
            <T text={UI.taOver} locale={locale} />
          </Knapp>
          <span className="mx-0.5 h-4 w-px bg-ink/15" />
          <Knapp>
            <Sparkles className="h-3 w-3" />
            <T text={UI.forbattra} locale={locale} />
          </Knapp>
          <Knapp>
            <Scissors className="h-3 w-3" />
            <T text={UI.kortare} locale={locale} />
          </Knapp>
          <Knapp>
            <Smile className="h-3 w-3" />
            <T text={UI.personlig} locale={locale} />
          </Knapp>
        </div>
      </div>
    </div>
  );
}

/* -- Ytan 3: Iris hittar och skriver ---------------------------------------- */

function IrisListYta({ locale }: Readonly<{ locale: Locale }>) {
  const rader = [
    { bolag: "Byggnads AB Norr", grund: "Söker två plåtslagare i Umeå", poang: "87" }, // inte-copy
    { bolag: "Fjällvind Energi", grund: "Nytt kontor i Östersund", poang: "82" }, // inte-copy
    { bolag: "Sundsvalls Måleri", grund: "Vann ramavtal i september", poang: "74" }, // inte-copy
    { bolag: "Höga Kusten Bygg", grund: "Utökar med markarbeten", poang: "71" } // inte-copy
  ];
  return (
    <div aria-hidden className="flex min-h-[420px] flex-col bg-paper p-4 text-left sm:p-5">
      <p className="text-[0.875rem] font-semibold text-ink">
        <T text={UI.nyaLeads} locale={locale} />
      </p>
      <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">
        <T text={UI.irisLaste} locale={locale} />
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
        <T text={UI.poang} locale={locale} />
      </p>
    </div>
  );
}

function IrisUtkastYta({ locale }: Readonly<{ locale: Locale }>) {
  return (
    <div aria-hidden className="flex min-h-[420px] flex-col bg-paper p-4 text-left sm:p-5">
      <p className="text-[0.875rem] font-semibold text-ink">
        <T text={UI.utkastTill} locale={locale} /> Byggnads AB Norr
      </p>
      <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">
        <T text={UI.till} locale={locale} /> {JOHAN_MOTTAGARE} · <T text={UI.amne} locale={locale} />{" "}
        {JOHAN_AMNE} · <T text={UI.bifogas} locale={locale} />
      </p>
      <div className="mt-3 rounded-input border border-ink/12 bg-paper px-3 py-2.5 text-[0.75rem] leading-[1.55] text-ink">
        {JOHAN_MEJL}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Knapp variant="primar">
          <Check className="h-3 w-3" />
          <T text={UI.godkannOchSkicka} locale={locale} />
        </Knapp>
        <Knapp>
          <T text={UI.redigera} locale={locale} />
        </Knapp>
        <Knapp>
          <T text={UI.hoppaOver} locale={locale} />
        </Knapp>
      </div>
      <p className="mt-auto border-t border-ink/10 pt-2.5 text-[0.6875rem] leading-[1.5] text-ink-subtle">
        <T text={UI.kalla} locale={locale} />
      </p>
    </div>
  );
}

/* -- Ytan 4: kvittoagenten -------------------------------------------------- */

function KvittoListYta({ locale }: Readonly<{ locale: Locale }>) {
  const rader = [
    { fran: "Circle K", belopp: "749,00 kr", status: UI.vantar, ton: "warn" as const },
    { fran: "ICA Maxi", belopp: "482,50 kr", status: UI.bokfort, ton: "good" as const },
    { fran: "SJ", belopp: "1 245,00 kr", status: UI.bokfort, ton: "good" as const },
    { fran: "Bauhaus", belopp: "1 899,00 kr", status: UI.bokfort, ton: "good" as const },
    { fran: "Postnord", belopp: "165,00 kr", status: UI.bokfort, ton: "good" as const }
  ];
  return (
    <div aria-hidden className="flex min-h-[420px] flex-col bg-paper p-4 text-left sm:p-5">
      <p className="text-[0.875rem] font-semibold text-ink">
        <T text={UI.kvittonUrMejlen} locale={locale} />
      </p>
      <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">
        <T text={UI.lasesIn} locale={locale} />
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
              <Badge ton={rad.ton}>
                <T text={rad.status} locale={locale} />
              </Badge>
            </span>
          </div>
        ))}
      </div>
      <p className="mt-auto pt-3 text-[0.6875rem] leading-[1.5] text-ink-subtle">
        <T text={UI.aritmetik} locale={locale} />
      </p>
    </div>
  );
}

function VerifikatYta({ locale }: Readonly<{ locale: Locale }>) {
  return (
    <div aria-hidden className="flex min-h-[420px] flex-col bg-paper p-4 text-left sm:p-5">
      <p className="text-[0.875rem] font-semibold text-ink">
        <T text={UI.verifikat} locale={locale} /> V-231 · Circle K
      </p>
      <p className="mt-0.5 text-[0.6875rem] text-ink-subtle">Drivmedel, betalkort · 18 sep 2026</p>
      <div className="mt-3 border-y border-ink/12 text-[0.75rem]">
        <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 border-b border-ink/10 py-2 text-[0.6875rem] text-ink-subtle">
          <span>
            <T text={UI.konto} locale={locale} />
          </span>
          <span className="text-right">
            <T text={UI.debet} locale={locale} />
          </span>
          <span className="text-right">
            <T text={UI.kredit} locale={locale} />
          </span>
        </div>
        {[
          ["5611 Drivmedel", "599,20", ""],
          ["2641 Ingående moms", "149,80", ""], // inte-copy
          ["1930 Företagskonto", "", "749,00"] // inte-copy
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
          <T text={UI.godkann} locale={locale} />
        </Knapp>
        <Knapp>
          <T text={UI.andraKonto} locale={locale} />
        </Knapp>
      </div>
      <p className="mt-auto pt-3 text-[0.6875rem] leading-[1.5] text-ink-subtle">
        <T text={UI.osakert} locale={locale} />
      </p>
    </div>
  );
}

/* -- Sektionen --------------------------------------------------------------- */

const FALT: Record<ProductKey, [Falt, Falt]> = {
  support: [
    {
      rubrik: { sv: "Chatten på er egen sajt", en: "The chat on your own site" },
      bild: WidgetYta,
      not: {
        sv: "En rad kod. Stängd tills besökaren behöver den, i era färger, och svaren kommer ur er kunskapsbas.",
        en: "One line of code. Closed until the visitor needs it, in your colours, with answers from your knowledge base."
      }
    },
    {
      rubrik: { sv: "Inkorgen sköter sig själv", en: "The inbox runs itself" },
      bild: InkorgYta,
      not: {
        sv: "Agenten sorterar, skriver utkastet och räknar fram offerten. Du trycker Godkänn, eller låter den skriva om sig.",
        en: "The agent sorts, drafts the reply and works out the quote. You press Approve, or have it rewrite itself."
      }
    }
  ],
  leads: [
    {
      rubrik: { sv: "Mejlet skriver sig självt", en: "The email writes itself" },
      bild: IrisUtkastYta,
      not: {
        sv: "Personligt, grundat i researchen och i ert erbjudande. Du är alltid den som trycker godkänn och skicka.",
        en: "Personal, grounded in the research and your offer. You are always the one who presses approve and send."
      }
    },
    {
      rubrik: { sv: "Iris hittar bolagen åt dig", en: "Iris finds the companies for you" },
      bild: IrisListYta,
      not: {
        sv: "Tjugo minuters research per bolag blir en poängsatt lista över dem som är värda din tid, varje morgon.",
        en: "Twenty minutes of research per company becomes a scored list of the ones worth your time, every morning."
      }
    }
  ],
  bookkeeping: [
    {
      rubrik: { sv: "Kvittona samlar ihop sig", en: "The receipts gather themselves" },
      bild: KvittoListYta,
      not: {
        sv: "Ur mejlen, ur plånboken, ur mobilen. Inget blir liggande till kvartalets sista kväll.",
        en: "From your inbox, your wallet, your phone. Nothing sits around until the last night of the quarter."
      }
    },
    {
      rubrik: { sv: "Färdiga verifikat, på öret", en: "Finished vouchers, to the öre" },
      bild: VerifikatYta,
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
}: Readonly<{ product: ProductKey; locale: Locale }>) {
  const [vanster, hoger] = FALT[product];
  return (
    <section className="border-b border-ink/12">
      <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-32">
        <div className="grid grid-cols-1 gap-y-12 lg:grid-cols-2 lg:gap-x-12">
          {[vanster, hoger].map((falt, i) => {
            const Bild = falt.bild;
            return (
              <figure key={falt.rubrik.sv} className={cn("rise", i === 1 && "rise-1")}>
                <div className="overflow-hidden rounded-panel border border-ink/12 bg-paper">
                  <Bild locale={locale} />
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
            );
          })}
        </div>
        <p className="mt-8 text-[0.8125rem] text-ink-subtle">
          <T text={EXEMPELRAD} locale={locale} />
        </p>
      </div>
    </section>
  );
}
