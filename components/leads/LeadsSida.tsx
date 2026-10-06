"use client";

import { X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { PageShell } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { IrisGranskning } from "@/components/leads/IrisGranskning";
import { IrisInkorg } from "@/components/leads/IrisInkorg";
import { IrisKorningar } from "@/components/leads/IrisKorningar";
import { LeadDetail, ListorUpsell, exempelTillRad, type ExempelRad } from "@/components/leads/IrisBolag";
import { LeadsRunForm } from "@/components/leads/LeadsRunForm";
import { LeadsTabell } from "@/components/leads/LeadsTabell";
import { CrmKundlista } from "@/components/leads/CrmKundlista";
import { LeadslistorView } from "@/components/leads/LeadslistorView";
import { SaljlistaUtforska } from "@/components/leads/Saljlista";
import { btnPrimary, flik, flikAktiv, flikInaktiv, fliklista } from "@/components/ui";
import { EXEMPELBOLAG, EXEMPEL_OMGANG_1, EXEMPEL_OMGANG_2 } from "@/lib/demo/iris-exempel";
import { useLocale, type Localized } from "@/lib/i18n";
import type { SuiteProspekt } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Leads (plan 2026-10-05, fas 4) — en sektion med underflikar:
 *
 *   Leads · Inkorg · Utkast · Listor · Körningar
 *
 * Antons beställning: leadsinkorgen och utkasten hörde inte hemma längst ner
 * i Att göra, Tabell och Pipeline var två halva vyer av samma sak, och det
 * fanns inget sätt att se en pågående Iris-körning. Fliken bär adressen i
 * `?vy=` och leadet vars låda är öppen i `?lead=`, så att båda går att länka
 * till och överlever en omladdning.
 *
 * Detaljen öppnas i en låda från höger i stället för att ta halva sidan: listan
 * får hela bredden, och lådan stängs med Esc, krysset eller ett klick utanför.
 */

type Segment = "leads" | "inkorg" | "utkast" | "listor" | "korningar";

const SEGMENT_ETIKETT: Record<Segment, Localized> = {
  leads: { sv: "Leads", en: "Leads" },
  inkorg: { sv: "Inkorg", en: "Inbox" },
  utkast: { sv: "Utkast", en: "Drafts" },
  listor: { sv: "Listor", en: "Lists" },
  korningar: { sv: "Körningar", en: "Runs" }
};

/** Gamla vyadresser (före 2026-10-05) landar i den sammanslagna vyn. */
const GAMLA: Record<string, Segment> = { bolag: "leads", tabell: "leads", pipeline: "leads" };

const T = {
  korIris: { sv: "Kör Iris", en: "Run Iris" },
  bestallLeads: { sv: "Beställ leads-lista", en: "Order a lead list" },
  hittaBolag: { sv: "Hitta bolag", en: "Find companies" },
  hittaBolagText: {
    sv: "Utan filter hittar Iris själv de bolag som passar er produkt bäst, utifrån er sparade målgrupp.",
    en: "Without filters, Iris finds the companies that fit your product best, based on your saved target audience."
  },
  exempelOverst: { sv: "Exempelbolag läggs överst i listan.", en: "Example companies are added to the top of the list." },
  kor: { sv: "Kör…", en: "Running…" },
  allaTillagda: { sv: "Alla tillagda", en: "All added" },
  allaExempelTillagda: { sv: "Alla exempelbolag tillagda", en: "All example companies added" },
  korExempel: { sv: "Kör exempel", en: "Run example" },
  korExempelkorningen: { sv: "Kör exempelkörningen", en: "Run the example" },
  vy: { sv: "Vy", en: "View" },
  stang: { sv: "Stäng", en: "Close" },
  lead: { sv: "Lead", en: "Lead" },
  inkorgDemo: {
    sv: "Svar från leads hamnar här när en brevlåda är kopplad.",
    en: "Replies from leads land here once a mailbox is connected."
  }
} satisfies Record<string, Localized>;

function tolkaSegment(vy: string | null): Segment {
  if (!vy) return "leads";
  if (vy in GAMLA) return GAMLA[vy];
  return (Object.keys(SEGMENT_ETIKETT) as Segment[]).includes(vy as Segment) ? (vy as Segment) : "leads";
}

export function IrisBolag({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { addons, isDemo, vy } = useDashboard();
  const { text } = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const sokParams = useSearchParams();

  const segmentVal = tolkaSegment(sokParams.get("vy"));
  const valdId = segmentVal === "leads" ? sokParams.get("lead") : null;
  // Översiktens "Ladda upp CRM-kundlista" landar på ?vy=listor&crm=1.
  const crmOppen = segmentVal === "listor" && sokParams.get("crm") === "1";
  const flikRefs = useRef<Partial<Record<Segment, HTMLButtonElement | null>>>({});
  const [korOppen, setKorOppen] = useState(false);
  const [exempelRader, setExempelRader] = useState<ExempelRad[]>([]);
  const [demoKorFas, setDemoKorFas] = useState<"vilar" | "kor">("vilar");

  const segment: Segment[] = demo
    ? ["leads", "utkast", "listor"]
    : ["leads", "inkorg", "utkast", "listor", "korningar"];

  const satt = useCallback(
    (andring: Record<string, string | null>) => {
      const p = new URLSearchParams(sokParams.toString());
      for (const [k, v] of Object.entries(andring)) {
        if (v === null) p.delete(k);
        else p.set(k, v);
      }
      const q = p.toString();
      router.replace(`${pathname}${q ? `?${q}` : ""}`, { scroll: false });
    },
    [pathname, router, sokParams]
  );

  const valjSegment = (s: Segment) => satt({ vy: s === "leads" ? null : s, lead: null });

  // En avslutad körning stänger formuläret så att de nya raderna syns direkt.
  useEffect(() => {
    const klar = () => setKorOppen(false);
    window.addEventListener("snipra:leads-korning-klar", klar);
    return () => window.removeEventListener("snipra:leads-korning-klar", klar);
  }, []);

  const allaExempelTillagda = exempelRader.length >= EXEMPELBOLAG.length;

  function korExempel() {
    if (demoKorFas === "kor" || allaExempelTillagda) return;
    setDemoKorFas("kor");
    window.setTimeout(() => {
      setExempelRader((forr) => {
        const redan = new Set(forr.map((r) => r.id));
        const kandidat = EXEMPEL_OMGANG_1.some((b) => !redan.has(b.id)) ? EXEMPEL_OMGANG_1 : EXEMPEL_OMGANG_2;
        return [...kandidat.filter((b) => !redan.has(b.id)).map(exempelTillRad), ...forr];
      });
      setDemoKorFas("vilar");
      setKorOppen(false);
    }, 650);
  }

  const valtExempel = exempelRader.find((r) => r.id === valdId)?._exempel;
  const harListaddon = addons.includes("leadlists");

  return (
    <PageShell
      title={{ sv: "Leads", en: "Leads" }}
      action={
        segmentVal === "listor" && harListaddon && !demo ? (
          // Listor-fliken beställer körningar som landar i säljlistan
          // (Sebbe 2026-10-06): knappen öppnar formuläret där nere.
          <button
            type="button"
            onClick={() => window.dispatchEvent(new Event("snipra:saljlista-bestall"))}
            className={btnPrimary}
          >
            {text(T.bestallLeads)}
          </button>
        ) : (
          <button type="button" aria-expanded={korOppen} onClick={() => setKorOppen((v) => !v)} className={btnPrimary}>
            {text(T.korIris)}
          </button>
        )
      }
    >
      {korOppen ? (
        <div className="mb-10 rounded-card border border-ink/12 bg-paper2/40 p-5 md:p-6">
          <LeadsRunForm
            isTest={demo || isDemo || vy === "demo"}
            demo={demo}
            filtrerbar
            rubrik={
              <div>
                <h2 className="text-[1.125rem] font-semibold tracking-[-0.01em]">{text(T.hittaBolag)}</h2>
                <p className="mt-1 max-w-[52ch] text-[13px] leading-5 text-ink-subtle">{text(T.hittaBolagText)}</p>
              </div>
            }
            demoAction={
              <div className="mt-6 rounded-card bg-paper p-5">
                <p className="max-w-[65ch] text-[15px] leading-7 text-ink-muted">{text(T.exempelOverst)}</p>
                <button
                  type="button"
                  disabled={demoKorFas === "kor" || allaExempelTillagda}
                  onClick={korExempel}
                  className={cn(btnPrimary, "mt-4 whitespace-nowrap")}
                >
                  {demoKorFas === "kor" ? (
                    text(T.kor)
                  ) : allaExempelTillagda ? (
                    <>
                      <span className="sm:hidden">{text(T.allaTillagda)}</span>
                      <span className="hidden sm:inline">{text(T.allaExempelTillagda)}</span>
                    </>
                  ) : (
                    <>
                      <span className="sm:hidden">{text(T.korExempel)}</span>
                      <span className="hidden sm:inline">{text(T.korExempelkorningen)}</span>
                    </>
                  )}
                </button>
              </div>
            }
          />
        </div>
      ) : null}

      {/* Pilnavigering: vänster/höger flyttar fokus och val, och bara den valda
          fliken ligger i tabbordningen. */}
      <div
        className={fliklista}
        role="tablist"
        aria-label={text(T.vy)}
        onKeyDown={(e) => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
          e.preventDefault();
          const i = segment.indexOf(segmentVal);
          const nasta =
            e.key === "Home"
              ? segment[0]
              : e.key === "End"
                ? segment[segment.length - 1]
                : segment[(i + (e.key === "ArrowRight" ? 1 : segment.length - 1)) % segment.length];
          valjSegment(nasta);
          flikRefs.current[nasta]?.focus();
        }}
      >
        {segment.map((s) => (
          <button
            key={s}
            ref={(el) => {
              flikRefs.current[s] = el;
            }}
            type="button"
            role="tab"
            id={`leads-flik-${s}`}
            aria-selected={segmentVal === s}
            aria-controls="leads-flikpanel"
            tabIndex={segmentVal === s ? 0 : -1}
            onClick={() => valjSegment(s)}
            className={cn(flik, segmentVal === s ? flikAktiv : flikInaktiv)}
          >
            {text(SEGMENT_ETIKETT[s])}
          </button>
        ))}
      </div>

      <div className="mt-6" role="tabpanel" id="leads-flikpanel" aria-labelledby={`leads-flik-${segmentVal}`}>
        {segmentVal === "inkorg" ? (
          demo ? (
            <p className="text-[0.9375rem] text-ink-muted">{text(T.inkorgDemo)}</p>
          ) : (
            <IrisInkorg />
          )
        ) : segmentVal === "utkast" ? (
          <IrisGranskning demo={demo} />
        ) : segmentVal === "listor" ? (
          harListaddon || demo ? (
            <LeadslistorView demo={demo} crmOppen={crmOppen} />
          ) : (
            // CRM-kundlistan gäller Iris också (uteslutningen), så den står
            // här även utan listtillägget. Säljlistans utforskare frontar
            // tillvalet med exempelbolag (Sebbes beställning 2026-10-06).
            <div className="grid gap-8">
              <SaljlistaUtforska />
              <CrmKundlista startOppen={crmOppen} />
              <ListorUpsell />
            </div>
          )
        ) : segmentVal === "korningar" ? (
          <IrisKorningar />
        ) : (
          <LeadsTabell
            demo={demo}
            valdId={valdId}
            exempel={exempelRader as unknown as SuiteProspekt[]}
            onValj={(id) => satt({ lead: id })}
          />
        )}
      </div>

      {valdId ? (
        <Lada etikett={text(T.lead)} aterFokus={`iris-rad-${valdId}`} onStang={() => satt({ lead: null })}>
          <LeadDetail key={valdId} id={valdId} demo={demo} exempel={valtExempel} />
        </Lada>
      ) : null}
    </PageShell>
  );
}

/**
 * Lådan från höger. Modal: fokus flyttas in, stannar inne (Tab/Shift+Tab) och
 * går tillbaka till raden som öppnade den. Under 640 px fyller den skärmen.
 */
function Lada({
  etikett,
  aterFokus,
  onStang,
  children
}: Readonly<{ etikett: string; aterFokus: string; onStang: () => void; children: React.ReactNode }>) {
  const { text } = useLocale();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panel.current?.focus();
    const forraOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = forraOverflow;
      document.getElementById(aterFokus)?.focus();
    };
  }, [aterFokus]);

  function tangent(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.stopPropagation();
      onStang();
      return;
    }
    if (e.key !== "Tab" || !panel.current) return;
    const fokuserbara = panel.current.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );
    if (fokuserbara.length === 0) return;
    const forsta = fokuserbara[0];
    const sista = fokuserbara[fokuserbara.length - 1];
    if (e.shiftKey && document.activeElement === forsta) {
      e.preventDefault();
      sista.focus();
    } else if (!e.shiftKey && document.activeElement === sista) {
      e.preventDefault();
      forsta.focus();
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onKeyDown={tangent}>
      <button
        type="button"
        tabIndex={-1}
        aria-label={text(T.stang)}
        onClick={onStang}
        className="absolute inset-0 cursor-default bg-ink/25 motion-safe:animate-[fadeIn_160ms_ease-out]"
      />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={etikett}
        tabIndex={-1}
        className="relative h-full w-full overflow-y-auto bg-paper shadow-[-24px_0_48px_-24px_rgba(17,17,17,0.35)] outline-none sm:w-[min(720px,92vw)] motion-safe:animate-[ladaIn_220ms_cubic-bezier(0.22,1,0.36,1)]"
      >
        <div className="sticky top-0 z-10 flex justify-end bg-paper/90 px-4 py-3 backdrop-blur">
          <button
            type="button"
            onClick={onStang}
            aria-label={text(T.stang)}
            className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-full text-ink-muted hover:bg-paper2 hover:text-ink"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>
        <div className="px-4 pb-8 sm:px-6">{children}</div>
      </div>
    </div>
  );
}
