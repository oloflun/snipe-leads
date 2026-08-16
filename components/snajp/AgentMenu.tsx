"use client";

import { useEffect, useRef, useState } from "react";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Menyn som finns på båda agentytorna: kontaktuppgifter, språkval,
 * dataskyddsinformation och en manuell eskaleringsknapp.
 *
 * ## Varför eskaleringen är en mailto och inte ett API-anrop
 *
 * Det finns ingen mejltransport i kodbasen. `send_provider.py` returnerar en
 * LoggingSendProvider eller en DryRunMailer, och ingen av dem når internet —
 * en SMTP-klass är helt enkelt inte skriven än.
 *
 * Ett POST till en egen route hade därför sett ut att fungera, svarat 200, och
 * INTE nått snajpsupport@gmail.com. En eskalering som tyst försvinner är värre
 * än ingen knapp alls: användaren tror att någon är på väg.
 *
 * En mailto öppnar användarens egen e-postklient med ärendet förifyllt. Den
 * levererar på riktigt, den kräver ingen infrastruktur, och användaren SER att
 * mejlet skickas. Byt till ett API-anrop den dag en riktig sändväg finns.
 */

export const SNAJP_SUPPORT_EPOST = "snajpsupport@gmail.com";

type Flik = "kontakt" | "gdpr" | null;

const copy = {
  meny: { sv: "Meny", en: "Menu" },
  stang: { sv: "Stäng menyn", en: "Close menu" },
  kontakt: { sv: "Kontakt", en: "Contact" },
  gdpr: { sv: "Dataskydd", en: "Data protection" },
  sprak: { sv: "Språk", en: "Language" },
  eskalera: { sv: "Anmäl felaktigt svar", en: "Report an incorrect answer" },

  kontaktRubrik: { sv: "Snajp", en: "Snajp" },
  kontaktBody: {
    sv: "Vi bygger och driftar agenten. Gäller din fråga en beställning eller ett ärende hos företaget du chattar med, skriv det i chatten i stället — de svarar snabbare på sitt eget.",
    en: "We build and operate the agent. If your question concerns an order or a case with the company you are chatting with, write it in the chat instead. They answer faster on their own matters."
  },

  eskaleraRubrik: { sv: "Svarade agenten fel?", en: "Did the agent answer incorrectly?" },
  eskaleraBody: {
    sv: "Anmäl svaret så läser en människa hos oss igenom det. Knappen öppnar din e-postklient med ärendet förifyllt — inget skickas utan att du trycker skicka.",
    en: "Report the answer and a person at our end will read it. The button opens your email client with the case prefilled. Nothing is sent until you press send."
  },
  eskaleraAmne: {
    sv: "Felaktigt svar från Snajp-agenten",
    en: "Incorrect answer from the Snajp agent"
  },
  eskaleraMall: {
    sv: "Beskriv kort vad som blev fel:\n\n\n---\nTekniska uppgifter (låt stå, de hjälper oss hitta samtalet):",
    en: "Briefly describe what went wrong:\n\n\n---\nTechnical details (please keep, they help us find the conversation):"
  },

  gdprRubrik: { sv: "Så hanterar vi dina uppgifter", en: "How we handle your data" },
  gdprPunkter: {
    sv: [
      "Det du skriver i chatten behandlas för att kunna besvara ditt ärende, och för inget annat.",
      "Personuppgiftsansvarig är företaget du chattar med. Snajp är personuppgiftsbiträde och behandlar uppgifterna på deras uppdrag.",
      "Skriv inte personnummer, kortuppgifter eller uppgifter om hälsa i chatten. Behövs sådant för ditt ärende ber vi om det på ett säkrare sätt.",
      "Du har rätt att begära utdrag, rättelse eller radering av dina uppgifter, och att invända mot behandlingen.",
      "Vill du utöva någon av de rättigheterna, kontakta i första hand företaget du chattar med."
    ],
    en: [
      "What you write in the chat is processed in order to answer your case, and for nothing else.",
      "The company you are chatting with is the data controller. Snajp is a data processor acting on their instructions.",
      "Do not write national ID numbers, card details or health information in the chat. If your case needs any of that, we will ask for it in a safer way.",
      "You have the right to request access, rectification or erasure of your data, and to object to the processing.",
      "To exercise any of those rights, contact the company you are chatting with in the first instance."
    ]
  },
  gdprFot: {
    sv: "Frågor om hur Snajp behandlar uppgifter besvaras på ",
    en: "Questions about how Snajp processes data are answered at "
  }
} satisfies Record<string, Localized | { sv: string[]; en: string[] }>;

function lokal(v: Localized, locale: "sv" | "en") {
  return v[locale];
}

export function AgentMenu({
  yta,
  kontext
}: Readonly<{
  /** Vilken agentyta menyn sitter på. Följer med i eskaleringsmejlet. */
  yta: "kundservice" | "leads";
  /** Fritt fält som hamnar i eskaleringens tekniska uppgifter (t.ex. sessions-id). */
  kontext?: string;
}>) {
  const { locale, setLocale, text } = useLocale();
  const [oppen, setOppen] = useState(false);
  const [flik, setFlik] = useState<Flik>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  // Escape stänger, och klick utanför stänger. Utan det ligger panelen kvar
  // över chatten på mobil, där den täcker precis det man ville läsa.
  useEffect(() => {
    if (!oppen) return;
    function vidTangent(e: KeyboardEvent) {
      if (e.key === "Escape") setOppen(false);
    }
    function vidKlick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOppen(false);
    }
    document.addEventListener("keydown", vidTangent);
    document.addEventListener("mousedown", vidKlick);
    return () => {
      document.removeEventListener("keydown", vidTangent);
      document.removeEventListener("mousedown", vidKlick);
    };
  }, [oppen]);

  const eskaleringsLank = (() => {
    const tekniskt = [
      `Yta: ${yta}`,
      kontext ? `Kontext: ${kontext}` : null,
      `Tidpunkt: ${new Date().toISOString()}`,
      typeof window !== "undefined" ? `Sida: ${window.location.href}` : null
    ]
      .filter(Boolean)
      .join("\n");
    const amne = encodeURIComponent(text(copy.eskaleraAmne as Localized));
    const brod = encodeURIComponent(`${text(copy.eskaleraMall as Localized)}\n${tekniskt}\n`);
    return `mailto:${SNAJP_SUPPORT_EPOST}?subject=${amne}&body=${brod}`;
  })();

  const gdprPunkter = (copy.gdprPunkter as { sv: string[]; en: string[] })[locale];

  return (
    <div ref={boxRef} className="relative">
      <button
        type="button"
        onClick={() => setOppen((v) => !v)}
        aria-expanded={oppen}
        aria-haspopup="dialog"
        className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-input border border-ink/15 px-3 text-sm font-medium text-ink/80 transition-colors hover:bg-paper2"
      >
        <span aria-hidden="true" className="flex flex-col gap-[3px]">
          <span className="block h-[2px] w-4 bg-current" />
          <span className="block h-[2px] w-4 bg-current" />
          <span className="block h-[2px] w-4 bg-current" />
        </span>
        {text(copy.meny as Localized)}
      </button>

      {oppen ? (
        <div
          role="dialog"
          aria-label={text(copy.meny as Localized)}
          className="absolute right-0 z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-input border border-ink/15 bg-paper shadow-lift"
        >
          {/* Språkvalet ligger överst och inte bakom en flik: den som behöver
              det behöver det för att kunna läsa resten av menyn. */}
          <div className="flex items-center justify-between gap-3 border-b border-ink/10 px-4 py-3">
            <span className="kicker text-mineral">{text(copy.sprak as Localized)}</span>
            <div className="flex gap-1" role="group">
              {(["sv", "en"] as const).map((val) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => setLocale(val)}
                  aria-pressed={locale === val}
                  className={cn(
                    "focus-ring min-h-9 rounded-input px-3 text-sm font-medium transition-colors",
                    locale === val
                      ? "bg-ink text-paper"
                      : "text-ink/70 hover:bg-paper2"
                  )}
                >
                  {val === "sv" ? "Svenska" : "English"}
                </button>
              ))}
            </div>
          </div>

          <div className="flex border-b border-ink/10">
            {(["kontakt", "gdpr"] as const).map((namn) => (
              <button
                key={namn}
                type="button"
                onClick={() => setFlik(flik === namn ? null : namn)}
                aria-pressed={flik === namn}
                className={cn(
                  "focus-ring min-h-11 flex-1 px-3 text-sm font-medium transition-colors",
                  flik === namn ? "bg-paper2 text-ink" : "text-ink/70 hover:bg-paper2/60"
                )}
              >
                {text(copy[namn] as Localized)}
              </button>
            ))}
          </div>

          {flik === "kontakt" ? (
            <div className="px-4 py-4">
              <p className="font-display text-[1rem] font-semibold">
                {text(copy.kontaktRubrik as Localized)}
              </p>
              <p className="mt-2 text-[0.875rem] leading-[1.6] text-ink/75">
                {text(copy.kontaktBody as Localized)}
              </p>
              <a
                href={`mailto:${SNAJP_SUPPORT_EPOST}`}
                className="focus-ring mt-3 inline-block rounded-input text-[0.875rem] font-medium text-ochre underline underline-offset-4"
              >
                {SNAJP_SUPPORT_EPOST}
              </a>
            </div>
          ) : null}

          {flik === "gdpr" ? (
            <div className="max-h-[50vh] overflow-y-auto px-4 py-4">
              <p className="font-display text-[1rem] font-semibold">
                {text(copy.gdprRubrik as Localized)}
              </p>
              <ul className="mt-3 flex flex-col gap-2.5">
                {gdprPunkter.map((punkt, i) => (
                  <li key={i} className="flex gap-2.5 text-[0.8125rem] leading-[1.55] text-ink/80">
                    <span
                      aria-hidden="true"
                      className="mt-[0.5em] h-1 w-1 shrink-0 rounded-full bg-ochre"
                    />
                    {punkt}
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[0.8125rem] leading-[1.55] text-mineral">
                {text(copy.gdprFot as Localized)}
                <a
                  href={`mailto:${SNAJP_SUPPORT_EPOST}`}
                  className="focus-ring rounded-input text-ochre underline underline-offset-4"
                >
                  {SNAJP_SUPPORT_EPOST}
                </a>
                .
              </p>
            </div>
          ) : null}

          <div className="border-t border-ink/10 bg-paper2/60 px-4 py-4">
            <p className="text-[0.875rem] font-semibold">
              {text(copy.eskaleraRubrik as Localized)}
            </p>
            <p className="mt-1.5 text-[0.8125rem] leading-[1.55] text-ink/70">
              {text(copy.eskaleraBody as Localized)}
            </p>
            <a
              href={eskaleringsLank}
              className="focus-ring mt-3 inline-flex min-h-11 items-center rounded-input bg-ink px-4 text-[0.875rem] font-semibold text-paper transition-colors hover:bg-ink2"
            >
              {text(copy.eskalera as Localized)}
            </a>
          </div>
        </div>
      ) : null}
    </div>
  );
}
