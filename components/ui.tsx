import { ArrowUpRight, CheckCircle2, Loader2 } from "lucide-react";
import type { Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * One button vocabulary for every product surface. Six variants had drifted apart
 * (different padding, weight, size, and one hovering to moss green), and a save
 * button that looks different in two places means one of them is wrong.
 *
 * Exported as class strings rather than a component so existing call sites adopt
 * them with a one-line change and keep their own element and handlers.
 */
export const btnBase =
  "focus-ring inline-flex min-h-11 items-center justify-center gap-2 rounded-input px-5 text-[0.9375rem] font-semibold transition-colors active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40";

export const btnPrimary = `${btnBase} bg-ink text-paper hover:bg-ink2`;

// Hårlinjen gör knappen synlig på en paper2-yta (Tomt, kort). Utan den var
// sekundärknappen samma färg som plattan den stod på och läste som lös text.
export const btnSecondary = `${btnBase} border border-ink/15 bg-paper2 text-ink hover:border-ink/30 hover:bg-paper`;

/**
 * STORLEK, inte en sjunde variant. Läggs ovanpå btnPrimary/btnSecondary med
 * `cn()` och rör bara höjd, luft och grad — färg, vikt och fokusring är
 * fortfarande vokabulärets.
 *
 * Finns för att bokföringens knappar står i rubrikrader vid sidan av
 * datumfälten och ska ha samma höjd som dem. Skrivet en gång här i stället för
 * som lösa klasser på anropsstället, av exakt det skäl som står ovan: sex
 * varianter hade redan glidit isär, och en storlek som bor på fyra ställen
 * glider isär på samma sätt.
 *
 * VARJE KLASS BÄR `!`, och det är inte slarv. `cn()` här i huset är ett rent
 * `join(" ")` utan tailwind-merge, så ordningen i class-attributet betyder
 * ingenting — det är ordningen i den GENERERADE css-filen som avgör, och där
 * kommer `min-h-11` efter `min-h-0`. Uppmätt i webbläsaren: utan `!` blev
 * knapparna 44 px medan datumfälten var 36, alltså precis den skillnad
 * modifieraren finns för att ta bort.
 */
export const btnLiten = "!min-h-0 !h-9 !gap-1.5 !px-3 !text-[0.875rem]";

export function Badge({ children, tone = "neutral" }: Readonly<{ children: React.ReactNode; tone?: "neutral" | "good" | "warn" | "danger" }>) {
  const tones = {
    neutral: "border-ink/10 bg-ink/[0.035] text-ink-muted",
    good: "border-moss/20 bg-moss/10 text-moss",
    warn: "border-copper/25 bg-copper/10 text-ink",
    // text-ink, inte text-danger. Uppmätt på den KOMPOSITERADE ytan (badgens
    // egen 10-procentiga platta över pappret, inte token-värdet rakt av):
    // danger på den grunden ger 3,82:1 mot golvet 4,5:1 för brödtextgrad.
    // Allvaret bärs av kanten och plattan i stället, precis som tone="warn"
    // redan gör. Att mäta mot pappret ensamt hade sagt att den klarade sig.
    danger: "border-danger/40 bg-danger/10 text-ink"
  };
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-[6px] border px-2.5 py-1 text-xs font-medium", tones[tone])}>
      {children}
    </span>
  );
}

export function ButtonLink({
  href,
  children,
  variant = "primary"
}: Readonly<{ href: string; children: React.ReactNode; variant?: "primary" | "secondary" | "ghost" }>) {
  const variants = {
    primary: "bg-ink text-paper hover:bg-copper hover:text-ink",
    secondary: "bg-paper text-ink shadow-hairline hover:bg-linen",
    ghost: "text-ink-muted hover:text-ink"
  };
  return (
    <a
      href={href}
      className={cn(
        "focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] px-4 py-2.5 text-sm font-semibold transition",
        variants[variant]
      )}
    >
      {children}
      {variant !== "ghost" ? <ArrowUpRight className="h-4 w-4" /> : null}
    </a>
  );
}

/**
 * Appytornas typografi — EN skala för varje inloggad sida (plans/2026-09-27-appytor-enhetlighet.md).
 *
 * Före 2026-09-27 fanns fyra sidrubriker (Fraunces 36 rak, 36 kursiv, 26 halvfet, Geist 28),
 * sex sektionsrubriker och 282 `kicker`-etiketter i 10,5 px spärrad mono. Ingen av dem var fel
 * var för sig; tillsammans såg varje sida ut att komma från en egen produkt. Fast rem-skala och
 * inte clamp: en arbetsyta läses i samma storlek oavsett fönsterbredd (Operate-läge).
 *
 * Klassträngar av samma skäl som knapparna ovan: anropsställena behåller sina element.
 */
export const rubrikSida = "font-display text-[2.25rem] leading-[1.1] tracking-[-0.02em]";
export const rubrikSektion = "font-display text-[1.5rem] leading-tight tracking-[-0.015em]";
export const rubrikPanel = "text-[1.0625rem] font-semibold leading-snug text-ink";

/**
 * Etikett: fält, kolumnhuvud, nyckeltal, navigeringsgrupp. Ersätter `.kicker` på appytorna —
 * samma jobb (säga vad värdet är), men i brödtextens typsnitt och versaler som i vanlig text.
 * Spärrad mono i 10,5 px var det som fick varje sida att viska (F-016).
 */
export const etikett = "text-[0.8125rem] font-medium text-ink-muted";

/** Meta: datum, domän, stad, antal — det som identifierar en rad utan att vara dess rubrik. */
export const meta = "text-[0.8125rem] text-ink-subtle";

/** Filter- och vyflikar. Pillren Iris redan hade, nu det enda flikspråket. */
export const flik =
  "focus-ring inline-flex min-h-11 items-center rounded-input px-4 text-[0.875rem] font-medium transition-colors";
export const flikAktiv = "bg-ink text-paper";
export const flikInaktiv = "bg-paper2 text-ink-muted hover:text-ink";

export function Sidhuvud({
  title,
  action
}: Readonly<{ title: React.ReactNode; action?: React.ReactNode }>) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <h1 className={cn(rubrikSida, "min-w-0 break-words")}>{title}</h1>
      {/* min-w-0, inte shrink-0: breda åtgärder ska bryta rad vid 320 px, inte
          trycka sidan i sidled. */}
      {action ? <div className="flex min-w-0 flex-wrap items-center gap-2">{action}</div> : null}
    </div>
  );
}

export function Sektion({
  title,
  action,
  className,
  children
}: Readonly<{
  title: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}>) {
  return (
    <section className={cn("mt-12 first:mt-0", className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className={cn(rubrikSektion, "min-w-0 break-words")}>{title}</h2>
        {action ? <div className="flex shrink-0 flex-wrap items-center gap-2">{action}</div> : null}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

/**
 * Nyckeltal. Etiketten ovanför värdet och bär enhet och period ("Körningar, 7 dagar") —
 * talet ensamt säger inte vad det räknar. Hårlinje ovanför varje post och under raden, så
 * att två rader nyckeltal inte får dubbla linjer emellan.
 */
const nyckeltalKolumner = ["sm:grid-cols-1", "sm:grid-cols-2", "sm:grid-cols-3", "sm:grid-cols-4"];

export function Nyckeltal({
  poster
}: Readonly<{ poster: { etikett: string; varde: React.ReactNode; notis?: React.ReactNode }[] }>) {
  return (
    <dl
      className={cn(
        "grid grid-cols-2 gap-x-8 border-b border-ink/15",
        nyckeltalKolumner[Math.min(poster.length, 4) - 1]
      )}
    >
      {poster.map((post) => (
        <div key={post.etikett} className="min-w-0 border-t border-ink/15 py-4">
          <dt className={etikett}>{post.etikett}</dt>
          <dd className="num mt-2 font-display text-[2rem] leading-none tracking-[-0.02em]">{post.varde}</dd>
          {post.notis ? <dd className={cn(meta, "mt-2")}>{post.notis}</dd> : null}
        </div>
      ))}
    </dl>
  );
}

/** Tomt läge: en mening, och en handling om det finns en. Ingen ikon, ingen streckad ram. */
export function Tomt({
  children,
  action
}: Readonly<{ children: React.ReactNode; action?: React.ReactNode }>) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-input border border-ink/10 bg-paper2 px-5 py-4 text-[0.9375rem] text-ink-muted">
      <p className="min-w-0">{children}</p>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function EmptyState({ title, body }: Readonly<{ title: string; body?: string }>) {
  return (
    <div className="rounded-[8px] border border-dashed border-ink/15 bg-paper/45 p-8 text-center">
      <CheckCircle2 className="mx-auto h-6 w-6 text-moss" />
      <h3 className="mt-4 font-semibold">{title}</h3>
      {body ? <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">{body}</p> : null}
    </div>
  );
}

export function SkeletonRows() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="h-12 animate-pulse rounded-[7px] bg-ink/[0.055]" />
      ))}
    </div>
  );
}

export function LoadingToast({ label }: Readonly<{ label: string }>) {
  return (
    <div className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-[8px] bg-ink px-4 py-3 text-sm text-paper shadow-lift">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function localizedList(items: Localized[], text: (value: Localized) => string) {
  return items.map((item) => text(item));
}

/**
 * EN tabell för varje listyta. Före 2026-09-15 fanns fem rad-idiom sida vid
 * sida — riktiga tabeller med autobredd, grid-cols-12-rader, flex-rader med
 * justify-between, handmätta fasta flexbredder och kort-i-lista — och ingen av
 * de riktiga tabellerna använde `table-fixed` eller `<colgroup>`, så kolumnerna
 * hoppade med innehållet mellan sidor och laddningstillstånd.
 *
 * `Tabell` är den gemensamma formen: fast layout (kolumnbredderna deklareras,
 * inte förhandlas), `etikett`-huvuden (kicker-huvudena togs bort 2026-09-27,
 * F-016), hårlinjer mellan raderna och `tnum` på talkolumner via `Cell hoger`.
 *
 * Bredderna anges i procent och ska summera till 100. `table-fixed` betyder
 * att webbläsaren ALDRIG jämkar: en kolumn utan bredd delar på det som blir
 * över, och innehåll som inte ryms bryts eller trunkeras i cellen i stället
 * för att trycka grannkolumnen ur läge.
 */
export type TabellKolumn = {
  rubrik: React.ReactNode;
  /** Fast bredd, t.ex. "24%". Utelämnad = dela på resten. */
  bredd?: string;
  /** Högerställd kolumn — tal och status. Sätter också tnum på huvudet. */
  hoger?: boolean;
  /** Rubriken finns för skärmläsare men ritas inte (t.ex. kryssrutekolumn). */
  srOnly?: boolean;
};

export function Tabell({
  kolumner,
  minBredd = 720,
  ariaLabel,
  children
}: Readonly<{
  kolumner: TabellKolumn[];
  /** Under den här bredden (px) scrollar tabellen internt i stället för att klämmas. */
  minBredd?: number;
  ariaLabel?: string;
  children: React.ReactNode;
}>) {
  return (
    <div className="thin-scrollbar overflow-x-auto">
      <table
        aria-label={ariaLabel}
        className="w-full table-fixed border-collapse text-[15px]"
        style={{ minWidth: `${minBredd}px` }}
      >
        <colgroup>
          {kolumner.map((kolumn, i) => (
            <col key={i} style={kolumn.bredd ? { width: kolumn.bredd } : undefined} />
          ))}
        </colgroup>
        <thead>
          <tr className="border-b border-ink/15 text-left">
            {kolumner.map((kolumn, i) => (
              <th
                key={i}
                scope="col"
                // text-left OCH text-right får aldrig stå på samma element:
                // cn() är ett rent join utan tailwind-merge, så det är css-
                // filens ordning som avgör vilken som vinner — se btnLiten.
                className={cn(
                  etikett,
                  "py-3 pr-4 last:pr-0",
                  kolumn.hoger ? "text-right" : "text-left"
                )}
              >
                {kolumn.srOnly ? <span className="sr-only">{kolumn.rubrik}</span> : kolumn.rubrik}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-ink/12 border-b border-ink/15">{children}</tbody>
      </table>
    </div>
  );
}

/** Radklassen för Tabell-rader — hover hör till rader man kan agera på. */
export const tabellRad = "transition-colors hover:bg-paper2/60";

/**
 * En cell i Tabell. `hoger` ger högerställning och tabulära siffror; `titel`
 * markerar radens namnkolumn (semantiskt ett radhuvud). Trunkering är
 * medveten: i en fast tabell är det cellen som ger med sig, aldrig kolumnen.
 */
export function Cell({
  hoger = false,
  titel = false,
  className,
  children
}: Readonly<{ hoger?: boolean; titel?: boolean; className?: string; children: React.ReactNode }>) {
  const Element = titel ? "th" : "td";
  return (
    <Element
      scope={titel ? "row" : undefined}
      className={cn(
        "py-4 pr-4 align-top font-normal last:pr-0",
        // Samma regel som i huvudet: en av dem, aldrig båda.
        hoger ? "num text-right" : "text-left",
        className
      )}
    >
      {children}
    </Element>
  );
}

/**
 * Fasta rader för listor som inte är tabeller — poster med brödtext eller
 * blandat innehåll där kolumner vore en lögn. Samma hårlinjespråk som Tabell,
 * så de två kan stå på samma sida utan att se ut som två system.
 */
export function Radlista({
  ariaLabel,
  children,
  className
}: Readonly<{ ariaLabel?: string; children: React.ReactNode; className?: string }>) {
  return (
    <ul aria-label={ariaLabel} className={cn("divide-y divide-ink/12 border-y border-ink/15", className)}>
      {children}
    </ul>
  );
}

export function Rad({
  className,
  children
}: Readonly<{ className?: string; children: React.ReactNode }>) {
  return <li className={cn("py-4", className)}>{children}</li>;
}
