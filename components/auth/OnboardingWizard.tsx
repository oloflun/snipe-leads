"use client";

import { ArrowLeft, ArrowRight, Check, ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { useMemo, useState, useTransition } from "react";
import { saveBusinessContext } from "@/lib/actions/onboarding";
import { signOut } from "@/lib/actions/auth";
import { BRANSCHER } from "@/lib/bransch";
import { formateraOrgnr, orgnrFel } from "@/lib/orgnr";
import { PAKET, type Paket } from "@/lib/pricing";
import { cn } from "@/lib/utils";

/**
 * Onboardingen som ett flöde i fyra steg — företaget, branschen,
 * kontaktpersonen, paketet — i stället för ett formulär med allt på en gång.
 *
 * ## Varför steg och inte ett långt formulär
 *
 * Mönstret är den moderna SaaS-onboardingens (Intercom, Ebbot m.fl., som
 * agenterna tagit inspiration från): EN fråga i taget, synligt var man är,
 * och det som redan är ifyllt står kvar när man går tillbaka. Ett formulär
 * med tio fält besvaras slarvigt; fyra skärmar med två-tre fält var
 * besvaras rätt — och svaren härifrån är bokstavligen det agenterna säljer
 * och svarar utifrån.
 *
 * ## Vad som händer när man trycker "Öppna arbetsytan"
 *
 * Allt går till `saveBusinessContext` (lib/actions/onboarding.ts) i ETT
 * anrop: affärskontexten sparas, paketet sätts (samma RPC som
 * inställningarnas paketbyte), arbetsytan får sin egen backend-tenant,
 * agenterna får standardinställningar ur kundens eget underlag, och
 * kontaktpersonen + orgnr landar i vårt kundregister. Stegen innan dess rör
 * aldrig servern — den som stänger fliken mitt i har inte skrivit något.
 *
 * Designen följer DESIGN.md:s Content-familj: en spalt, typografi som bär,
 * Fraunces-numrerad stegrad i vänsterspalten (ochre-numeralerna är
 * systemets signatur), hairlines mellan fälten, `animate-mejl-in` som enda
 * rörelse — systemets egen kurva, inget nytt rörelsespråk.
 */

const STEG = [
  { kicker: "Företaget", rubrik: "Berätta om företaget" },
  { kicker: "Bransch", rubrik: "Vilken bransch är ni i?" },
  { kicker: "Kontaktperson", rubrik: "Vem pratar vi med hos er?" },
  { kicker: "Paket", rubrik: "Välj era agenter" }
] as const;

const PLACEHOLDER = {
  orgnr: "556824-9022",
  webbplats: "https://exempel.se",
  produkt: "Utbildning i hjärt-lungräddning och första hjälpen för arbetsplatser",
  fokus: "Vi vill helst nå bolag som redan köpt hjärtstartare men saknar utbildning"
};

export function OnboardingWizard({
  epost,
  namn
}: Readonly<{ epost?: string | null; namn?: string | null }>) {
  const [steg, setSteg] = useState(0);
  /** Högsta steget som nåtts — stegraden låter en hoppa TILLBAKA, aldrig fram. */
  const [maxNatt, setMaxNatt] = useState(0);

  // Steg 1 — företaget.
  const [orgnr, setOrgnr] = useState("");
  const [orgnrVarning, setOrgnrVarning] = useState<string | null>(null);
  const [testkund, setTestkund] = useState(false);
  const [webbplats, setWebbplats] = useState("");
  const [produkt, setProdukt] = useState("");
  const [fokus, setFokus] = useState("");

  // Steg 2 — branschen.
  const [bransch, setBransch] = useState<string | null>(null);

  // Steg 3 — kontaktpersonen. Mejlen förifylls med kontots adress: den som
  // registrerar sig ÄR oftast kontaktpersonen, och ett förifyllt sant värde
  // är motsatsen till de påhittade defaultvärden det gamla formuläret hade.
  const [kontaktNamn, setKontaktNamn] = useState(namn ?? "");
  const [kontaktRoll, setKontaktRoll] = useState("");
  const [kontaktMejl, setKontaktMejl] = useState(epost ?? "");
  const [kontaktTelefon, setKontaktTelefon] = useState("");

  // Steg 4 — paketet. Duo förvalt: det är paketet vi vill sälja (pricing.ts).
  const [paket, setPaket] = useState<Paket["id"]>("duo");
  const [notiser, setNotiser] = useState(true);

  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const valtPaket = useMemo(() => PAKET.find((p) => p.id === paket), [paket]);

  function vidBlurOrgnr() {
    if (!orgnr.trim()) {
      setOrgnrVarning(null);
      return;
    }
    const fel = orgnrFel(orgnr);
    setOrgnrVarning(fel);
    if (!fel) setOrgnr(formateraOrgnr(orgnr));
  }

  /** Felet för det aktiva steget, eller null om steget är komplett. */
  function stegFel(vilket: number): string | null {
    if (vilket === 0) {
      const fel = testkund ? null : orgnrFel(orgnr);
      if (fel) return fel;
      if (!webbplats.trim())
        return "Fyll i webbplatsen. Det är den agenterna läser för att förstå er.";
      if (!produkt.trim())
        return "Skriv en rad om vad ni säljer. Det är det agenterna ska sälja.";
      return null;
    }
    if (vilket === 1) {
      return bransch ? null : "Välj den bransch som ligger närmast — Annat funkar också.";
    }
    if (vilket === 2) {
      if (!kontaktNamn.trim()) return "Fyll i vem som är kontaktperson hos er.";
      if (!kontaktMejl.includes("@")) return "Fyll i kontaktpersonens e-postadress.";
      return null;
    }
    return null;
  }

  function nasta(event?: React.FormEvent) {
    event?.preventDefault();
    if (steg === 0 && !testkund) {
      // Orgnr-fältet valideras även om användaren aldrig lämnade det.
      setOrgnrVarning(orgnrFel(orgnr));
    }
    const fel = stegFel(steg);
    setError(fel);
    if (fel) return;
    const ny = Math.min(steg + 1, STEG.length - 1);
    setSteg(ny);
    setMaxNatt((m) => Math.max(m, ny));
  }

  function tillbaka() {
    setError(null);
    setSteg((s) => Math.max(0, s - 1));
  }

  function skickaIn() {
    setError(null);
    startTransition(async () => {
      const result = await saveBusinessContext({
        orgnr: testkund ? "" : orgnr,
        webbplats,
        produkt,
        fokus,
        bransch: bransch ?? "",
        kontaktNamn,
        kontaktRoll,
        kontaktMejl,
        kontaktTelefon,
        paket,
        testkund,
        notiser
      });
      if (!result.success) {
        setError(result.error ?? "Kunde inte spara. Försök igen.");
      }
    });
  }

  return (
    <div className="grid grid-cols-12 md:gap-x-8">
      {/* Stegraden — Fraunces-numeraler i ochre, systemets signatur. */}
      <aside className="col-span-12 md:col-span-4 lg:col-span-3">
        <Link href="/" className="kicker text-mineral hover:text-warning">
          Till startsidan
        </Link>
        <div className="rule mt-3 text-ink" />

        <ol className="mt-8 hidden md:block" aria-label="Steg i uppstarten">
          {STEG.map((s, i) => {
            const klar = i < steg;
            const aktiv = i === steg;
            const nabar = i <= maxNatt && i !== steg;
            return (
              <li key={s.kicker} className={cn("border-t border-ink/15", i === 0 && "border-t-0")}>
                <button
                  type="button"
                  disabled={!nabar}
                  onClick={() => {
                    setError(null);
                    setSteg(i);
                  }}
                  className={cn(
                    "focus-ring flex w-full items-baseline gap-4 rounded-input py-4 text-left",
                    nabar && "cursor-pointer hover:text-ink",
                    !nabar && "cursor-default"
                  )}
                >
                  <span
                    className={cn(
                      "font-display text-[2rem] leading-none",
                      aktiv ? "text-warning" : klar ? "text-ink" : "text-ink-subtle"
                    )}
                    aria-hidden
                  >
                    {i + 1}
                  </span>
                  <span className="min-w-0">
                    <span
                      className={cn(
                        "block text-[0.9375rem] font-semibold",
                        aktiv ? "text-ink" : klar ? "text-ink-muted" : "text-ink-subtle"
                      )}
                    >
                      {s.kicker}
                    </span>
                    <span className="mt-0.5 flex items-center gap-1.5 text-[13px] text-mineral">
                      {klar ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-moss" aria-hidden />
                          Klart
                        </>
                      ) : aktiv ? (
                        "Nu"
                      ) : (
                        "Väntar"
                      )}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>

        {/* Mobil: en rad + tunn mätare i stället för hela listan. */}
        <div className="mt-6 md:hidden">
          <p className="kicker text-ink-subtle">
            Steg {steg + 1} av {STEG.length} — {STEG[steg].kicker}
          </p>
          <div className="mt-2 h-[3px] overflow-hidden rounded-full bg-ink/10">
            <div
              className="h-full rounded-full bg-ochre transition-[width] duration-300"
              style={{ width: `${((steg + 1) / STEG.length) * 100}%` }}
            />
          </div>
        </div>

        <form action={signOut} className="mt-8 hidden md:block">
          <button type="submit" className="kicker text-mineral hover:text-warning">
            Logga ut
          </button>
        </form>
      </aside>

      {/* Steginnehållet. key={steg} + animate-mejl-in: varje steg glider in
          med systemets egen rörelse, och reduced motion släcker den. */}
      <div className="col-span-12 mt-10 md:col-span-8 md:mt-0 lg:col-span-9">
        <div key={steg} className="animate-mejl-in max-w-[720px]">
          <h1 className="font-display text-[clamp(1.75rem,3.5vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">
            {STEG[steg].rubrik}
          </h1>

          {steg === 0 ? (
            <form onSubmit={nasta}>
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                Agenterna läser er webbplats och lär sig resten själva — hur ni
                beskriver er, vad ni säljer och vilka ord er bransch använder.
              </p>
              <div className="mt-8 grid grid-cols-12 gap-y-6 md:gap-x-8">
                <Falt
                  label="Organisationsnummer"
                  hint="Identifierar er, och krävs enligt lag i sidfoten på varje utskick."
                  span="md:col-span-6"
                  value={orgnr}
                  onChange={setOrgnr}
                  onBlur={vidBlurOrgnr}
                  placeholder={PLACEHOLDER.orgnr}
                  varning={orgnrVarning}
                  inputMode="numeric"
                  autoComplete="off"
                />
                <label className="col-span-12 flex items-start gap-3 md:col-span-6 md:pt-4">
                  <input
                    type="checkbox"
                    checked={testkund}
                    onChange={(e) => {
                      setTestkund(e.target.checked);
                      if (e.target.checked) setOrgnrVarning(null);
                    }}
                    className="focus-ring mt-1 h-4 w-4 shrink-0"
                  />
                  <span className="text-[14px] leading-6 text-ink-muted">
                    <span className="font-medium text-ink">Testarbetsyta</span> — hoppa
                    över organisationsnumret. Bara för test; arbetsytan märks som
                    testkund.
                  </span>
                </label>
                <Falt
                  label="Webbplats"
                  hint="Den här läser agenterna. Utan den vet de bara ert nummer."
                  span="md:col-span-6"
                  value={webbplats}
                  onChange={setWebbplats}
                  placeholder={PLACEHOLDER.webbplats}
                  type="url"
                  autoComplete="url"
                />
                <Falt
                  label="Vad ni säljer"
                  hint="En rad räcker. Agenterna fyller på från sajten."
                  span="md:col-span-6"
                  value={produkt}
                  onChange={setProdukt}
                  placeholder={PLACEHOLDER.produkt}
                />
                <Falt
                  label="Något extra att fokusera på (valfritt)"
                  hint="En nisch, ett segment ni vill åt, eller något agenterna ska undvika."
                  span="md:col-span-12"
                  value={fokus}
                  onChange={setFokus}
                  placeholder={PLACEHOLDER.fokus}
                />
              </div>
              <Stegfot error={error} forsta />
            </form>
          ) : null}

          {steg === 1 ? (
            <form onSubmit={nasta}>
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                Branschen ger agenterna rätt ordförråd från första dagen — en
                offert i bygg låter inte som en i vården.
              </p>
              <div className="mt-8 flex flex-wrap gap-2" role="radiogroup" aria-label="Bransch">
                {BRANSCHER.map((b) => {
                  const vald = bransch === b;
                  return (
                    <button
                      key={b}
                      type="button"
                      role="radio"
                      aria-checked={vald}
                      onClick={() => {
                        setBransch(b);
                        setError(null);
                      }}
                      className={cn(
                        "focus-ring min-h-11 rounded-input border px-4 py-2.5 text-[0.9375rem] transition-colors",
                        vald
                          ? "border-ochre bg-ochre/10 font-semibold text-ink"
                          : "border-ink/15 bg-paper2/50 text-ink-muted hover:border-ink/30 hover:text-ink"
                      )}
                    >
                      {b}
                    </button>
                  );
                })}
              </div>
              <Stegfot error={error} onTillbaka={tillbaka} />
            </form>
          ) : null}

          {steg === 2 ? (
            <form onSubmit={nasta}>
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                Er kontakt hos oss är en människa, inte en kö. Vi hör av oss när
                agenterna behöver ett beslut — och innan er gratisperiod tar slut.
              </p>
              <div className="mt-8 grid grid-cols-12 gap-y-6 md:gap-x-8">
                <Falt
                  label="Namn"
                  hint="Den hos er som äger frågan om agenterna."
                  span="md:col-span-6"
                  value={kontaktNamn}
                  onChange={setKontaktNamn}
                  placeholder="Anna Andersson"
                  autoComplete="name"
                />
                <Falt
                  label="Roll (valfritt)"
                  hint="Till exempel VD, marknadschef eller kontorsansvarig."
                  span="md:col-span-6"
                  value={kontaktRoll}
                  onChange={setKontaktRoll}
                  placeholder="VD"
                  autoComplete="organization-title"
                />
                <Falt
                  label="E-post"
                  hint="Hit går besked som rör kontot — aldrig reklam."
                  span="md:col-span-6"
                  value={kontaktMejl}
                  onChange={setKontaktMejl}
                  placeholder="anna@bolag.se"
                  type="email"
                  autoComplete="email"
                />
                <Falt
                  label="Telefon (valfritt)"
                  hint="Om något brådskar ringer vi hellre än mejlar."
                  span="md:col-span-6"
                  value={kontaktTelefon}
                  onChange={setKontaktTelefon}
                  placeholder="070-123 45 67"
                  type="tel"
                  autoComplete="tel"
                />
              </div>
              <Stegfot error={error} onTillbaka={tillbaka} />
            </form>
          ) : null}

          {steg === 3 ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                skickaIn();
              }}
            >
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                <span className="font-semibold text-ink">Först två månader gratis</span> —
                ingen betalning nu, och vi hör av oss i god tid innan perioden tar
                slut. Byta paket går när som helst under Inställningar → Plan.
              </p>

              <div className="mt-8 divide-y divide-ink/10 overflow-hidden rounded-card border border-ink/15 bg-paper">
                {PAKET.map((p) => {
                  const vald = paket === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      role="radio"
                      aria-checked={vald}
                      onClick={() => setPaket(p.id)}
                      className={cn(
                        "focus-ring relative block w-full px-5 py-4 text-left transition-colors",
                        vald ? "bg-ochre/[0.07]" : "hover:bg-ink/[0.03]"
                      )}
                    >
                      <span
                        aria-hidden
                        className={cn(
                          "absolute bottom-2 left-0 top-2 w-[2px] rounded-full bg-ochre transition-opacity",
                          vald ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <span className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <span className="text-[1.0625rem] font-semibold">{p.namn}</span>
                        {p.populärast ? (
                          <span className="rounded-input border border-ochre/40 bg-ochre/10 px-2 py-0.5 text-[0.75rem] font-medium text-warning">
                            Populärast
                          </span>
                        ) : null}
                        <span className="ml-auto font-mono text-[0.9375rem] tabular-nums text-ink-muted">
                          {p.prisPerManad === null
                            ? "Pris vid kontakt"
                            : `från ${p.prisPerManad.toLocaleString("sv-SE")} kr/mån`}
                        </span>
                      </span>
                      <span className="mt-1 block max-w-[58ch] text-[14px] leading-6 text-ink-muted">
                        {p.beskrivning.sv}
                      </span>
                      {vald ? (
                        <span className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
                          {p.ingar.map((rad) => (
                            <span
                              key={rad.sv}
                              className="flex items-center gap-1.5 text-[13px] text-ink-subtle"
                            >
                              <Check className="h-3.5 w-3.5 shrink-0 text-moss" aria-hidden />
                              {rad.sv}
                            </span>
                          ))}
                        </span>
                      ) : null}
                    </button>
                  );
                })}
              </div>

              <p className="mt-4 text-[14px] leading-6 text-ink-muted">
                Osäkra?{" "}
                <a
                  href="/demo"
                  target="_blank"
                  rel="noopener"
                  className="focus-ring inline-flex items-center gap-1 rounded-input font-medium text-ink underline underline-offset-4 hover:text-warning"
                >
                  Utforska alla tre agenterna i demon
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                </a>{" "}
                — den öppnas i en ny flik, det här flödet står kvar.
              </p>

              <div className="mt-8 rounded-panel border border-ink/15 bg-paper2/50 p-5">
                <p className="kicker text-mineral">Notiser</p>
                <label className="mt-3 flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={notiser}
                    onChange={(e) => setNotiser(e.target.checked)}
                    className="focus-ring mt-1 h-4 w-4 shrink-0"
                  />
                  <span className="text-[14px] leading-6 text-ink-muted">
                    <span className="font-medium text-ink">Ja, mejla mig</span> när ett
                    nytt lead landar eller när kundtjänstagenten lämnar över ett
                    ärende till en människa. Inget annat.
                  </span>
                </label>
              </div>

              {error ? (
                <p role="alert" className="mt-6 text-[15px] text-danger">
                  {error}
                </p>
              ) : null}

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={tillbaka}
                  className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input px-4 text-[0.9375rem] font-medium text-ink-muted hover:text-ink"
                >
                  <ArrowLeft className="h-4 w-4" aria-hidden />
                  Tillbaka
                </button>
                <button
                  type="submit"
                  disabled={isPending}
                  className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2 disabled:opacity-60"
                >
                  {isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      Läser in er webbplats och startar agenterna…
                    </>
                  ) : (
                    <>Öppna arbetsytan med {valtPaket?.namn ?? "valt paket"}</>
                  )}
                </button>
              </div>

              <p className="mt-4 max-w-[62ch] text-[13px] leading-[1.55] text-mineral">
                Inget skickas till någon mottagare av det här. Agenterna läser er
                sajt och förbereder underlag — utskick kräver att ni själva slår på
                det, och de tre första granskas alltid av en människa.
              </p>
            </form>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** Fortsätt/Tillbaka-raden för steg 1–3. Sista steget har sin egen. */
function Stegfot({
  error,
  onTillbaka,
  forsta = false
}: Readonly<{ error: string | null; onTillbaka?: () => void; forsta?: boolean }>) {
  return (
    <>
      {error ? (
        <p role="alert" className="mt-6 text-[15px] text-danger">
          {error}
        </p>
      ) : null}
      <div className="mt-8 flex flex-wrap items-center gap-4">
        {!forsta && onTillbaka ? (
          <button
            type="button"
            onClick={onTillbaka}
            className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input px-4 text-[0.9375rem] font-medium text-ink-muted hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Tillbaka
          </button>
        ) : null}
        <button
          type="submit"
          className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
        >
          Fortsätt
          <ArrowRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </>
  );
}

function Falt({
  label,
  hint,
  span,
  value,
  onChange,
  onBlur,
  placeholder,
  varning,
  type = "text",
  inputMode,
  autoComplete
}: Readonly<{
  label: string;
  hint: string;
  span: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
  placeholder: string;
  varning?: string | null;
  type?: string;
  inputMode?: "numeric" | "text";
  autoComplete?: string;
}>) {
  return (
    <label className={`col-span-12 grid gap-2 border-t border-ink/15 pt-4 ${span}`}>
      <span className="kicker text-mineral">{label}</span>
      <input
        className={`h-14 rounded-input border bg-paper2/70 px-4 text-[15px] focus:border-ochre ${
          varning ? "border-danger" : "border-ink/15"
        }`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        type={type}
        inputMode={inputMode}
        autoComplete={autoComplete}
        aria-invalid={Boolean(varning)}
      />
      <span className={`text-[13px] leading-[1.5] ${varning ? "text-danger" : "text-mineral"}`}>
        {varning ?? hint}
      </span>
    </label>
  );
}
