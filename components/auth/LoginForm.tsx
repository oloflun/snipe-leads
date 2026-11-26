"use client";

import Image from "next/image";
import Link from "next/link";
import { useState, useTransition } from "react";
import { useSearchParams } from "next/navigation";
import { Logo } from "@/components/Logo";
import { oppnaEfterIdentitetsbyte } from "@/components/dashboard/DashboardContext";
import { btnPrimary, btnSecondary, etikett, flik, flikAktiv, flikInaktiv, fliklista } from "@/components/ui";
import {
  requestPasswordReset,
  signInWithOAuth,
  signInWithPassword,
  signUpWithPassword
} from "@/lib/actions/auth";
import { SPARRKOD, TVAFAKTOR_FEL, TVAFAKTOR_KRAVS } from "@/lib/auth/sparrkod";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Inloggning och kontoskapande: första sidan i onboardingen.
 *
 * ## Det den visuella genomgången 2026-11-18 ändrade, och varför
 *
 * - `?mode=signup` öppnar sidan i läget Skapa konto. Länkar som betyder
 *   "kom igång" landade förut i inloggningsläget, under rubriken "Välkommen
 *   tillbaka", och den nya kunden fick själv hitta fliken.
 * - Den mörka panelen säger vad som gäller för läget man står i. Förut lovade
 *   den "magic link", som inte finns, och bad kunden fylla i "affärskontexten".
 * - "Prova demo" var en flik som bara kunde svara med ett fel: mejlvägen för
 *   åtkomstlänken är inte kopplad (requestDemoAccess). Demon är öppen på
 *   /demo, så fliken är en länk dit.
 * - Google och Microsoft visas bara när de är konfigurerade i miljön. En knapp
 *   som alltid svarar "inte konfigurerad än" är sämre än ingen knapp.
 * - Samma knappar, flikar och etiketter som resten av produkten
 *   (components/ui.tsx), i stället för spärrad mono i versaler med pil.
 *
 * ## Fotot (Anton 2026-11-23)
 *
 * Sidan hade blivit "mer basic än tidigare": en bläckplatta med två rader text
 * bredvid formuläret. Av fyra förslag (koncept/login-2026-11-23) valde Anton
 * B: landningssidans Göteborgsfoto över hela skärmen, rubriken direkt på
 * fotot och formuläret på en pappersplatta till höger. På mobil är fotot ett
 * band överst. Lägestexten flyttade från panelen till formuläret, och
 * trestegslistan i läget Skapa konto utgick med panelen.
 *
 * Rubriken och formuläret bor i samma komponent eftersom de delar läget.
 */

type AuthMode = "login" | "signup" | "reset";

export type OAuthUtbud = Readonly<{ google: boolean; microsoft: boolean }>;

const EPOST = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MINSTA_LOSENORD = 8;

const T = {
  lankFel: {
    sv: "Länken gick inte att använda. Den kan ha gått ut eller redan vara förbrukad. Begär en ny nedan.",
    en: "The link could not be used. It may have expired or already been used. Request a new one below."
  },
  // Samma besked oavsett om adressen har ett konto — formuläret får inte
  // fungera som en kontolista (samma princip som inloggningens felmeddelande).
  aterstallSkickad: {
    sv: "Om adressen har ett konto hos oss har vi skickat en återställningslänk. Titta i inkorgen, och i skräpposten.",
    en: "If the address has an account with us, we have sent a reset link. Check your inbox, and the spam folder."
  },
  nagotFel: { sv: "Något gick fel. Försök igen.", en: "Something went wrong. Try again." },
  // Spärren mot upprepade försök (lib/auth/inloggningsregler.ts). Samma besked
  // för en adress med och utan konto.
  forMangaForsok: {
    sv: "För många försök. Vänta några minuter och försök igen.",
    en: "Too many attempts. Wait a few minutes and try again."
  },
  inloggningFel: { sv: "Inloggningen misslyckades.", en: "Sign-in failed." },
  // Andra steget (lib/auth.ts:authorize, migration 128). Visas bara efter ett
  // rätt lösenord.
  tvaRubrik: { sv: "Tvåstegsverifiering", en: "Two-step verification" },
  tvaPanel: {
    sv: "Ange koden ur din autentiseringsapp för att slutföra inloggningen.",
    en: "Enter the code from your authenticator app to finish signing in."
  },
  tvaKod: { sv: "Kod", en: "Code" },
  tvaHint: {
    sv: "Sex siffror ur appen, eller en av dina återställningskoder.",
    en: "Six digits from the app, or one of your recovery codes."
  },
  tvaTom: { sv: "Fyll i koden.", en: "Enter the code." },
  tvaFel: {
    sv: "Koden stämmer inte, eller har redan använts. Försök med nästa kod ur appen.",
    en: "The code is not correct, or has already been used. Try the next code from the app."
  },
  tvaVerifiera: { sv: "Verifiera och logga in", en: "Verify and sign in" },
  oauthFel: { sv: "Inloggningen kunde inte startas.", en: "Sign-in could not be started." },
  felNamn: { sv: "Fyll i ditt namn.", en: "Enter your name." },
  felEpost: { sv: "Fyll i en e-postadress, till exempel du@bolag.se.", en: "Enter an email address, for example you@company.com." },
  felLosenordTomt: { sv: "Fyll i lösenordet.", en: "Enter your password." },
  felLosenordKort: {
    sv: "Lösenordet ska ha minst 8 tecken.",
    en: "The password must have at least 8 characters."
  },
  // Rubriken på fotot i inloggningsläget: "Välkommen tillbaka", med det andra
  // ordet markerat. Läget Skapa konto har sin egen rubrik: en ny kund ska inte
  // hälsas välkommen tillbaka.
  valkommen: { sv: "Välkommen", en: "Welcome" },
  tillbakaOrd: { sv: "tillbaka", en: "back" },
  fotoKredit: { sv: "Foto: Aron Fjell, Unsplash", en: "Photo: Aron Fjell, Unsplash" },
  lagen: { sv: "Logga in eller skapa konto", en: "Sign in or create an account" },
  loggaIn: { sv: "Logga in", en: "Sign in" },
  skapaKonto: { sv: "Skapa konto", en: "Create account" },
  aterstall: { sv: "Återställ lösenordet", en: "Reset your password" },
  panelLoggaIn: {
    sv: "Logga in för att fortsätta där ni slutade.",
    en: "Sign in to continue where you left off."
  },
  panelAterstall: {
    sv: "Skriv adressen du registrerade dig med, så skickar vi en länk som låter dig välja ett nytt lösenord.",
    en: "Enter the address you signed up with, and we will send a link that lets you choose a new password."
  },
  panelSkapa: {
    sv: "Två månader gratis. Inget kort och ingen bindningstid.",
    en: "Two months free. No card and no minimum term."
  },
  google: { sv: "Fortsätt med Google", en: "Continue with Google" },
  microsoft: { sv: "Fortsätt med Microsoft", en: "Continue with Microsoft" },
  eller: { sv: "eller", en: "or" },
  namn: { sv: "Namn", en: "Name" },
  dittNamn: { sv: "Ditt namn", en: "Your name" },
  epost: { sv: "E-post", en: "Email" },
  epostExempel: { sv: "du@bolag.se", en: "you@company.com" },
  losenord: { sv: "Lösenord", en: "Password" },
  losenordHint: { sv: "Minst 8 tecken.", en: "At least 8 characters." },
  visa: { sv: "Visa", en: "Show" },
  dolj: { sv: "Dölj", en: "Hide" },
  glomt: { sv: "Glömt lösenordet?", en: "Forgot your password?" },
  bearbetar: { sv: "Ett ögonblick", en: "One moment" },
  skickaAterstall: { sv: "Skicka återställningslänk", en: "Send reset link" },
  tillbaka: { sv: "Tillbaka till inloggningen", en: "Back to sign-in" },
  inteKonto: { sv: "Inget konto än?", en: "No account yet?" },
  harKonto: { sv: "Har ni redan ett konto?", en: "Already have an account?" },
  seForst: { sv: "Vill ni se agenterna först?", en: "Want to see the agents first?" },
  oppnaDemon: { sv: "Öppna demon", en: "Open the demo" },
  tillStartsidan: { sv: "Snajp, till startsidan", en: "Snajp, back to home" }
} satisfies Record<string, Localized>;

type FaltId = "namn" | "epost" | "losenord" | "kod";

/**
 * Fotots band och rubrikfärg. Fasta värden (bläck och papper ur DESIGN.md
 * § Theme) och inte temats tokens: i mörkt tema byter `--ink` och `--paper`
 * plats, men fotot är lika mörkt i båda.
 */
const FOTOBAND =
  "linear-gradient(to top, oklch(0.20 0.018 252 / 0.80) 0%, oklch(0.20 0.018 252 / 0.52) 30%, oklch(0.20 0.018 252 / 0.22) 52%, oklch(0.20 0.018 252 / 0) 72%)";
const FOTOTEXT = "oklch(0.965 0.008 88)";

/** Serverns egna besked kommer på ett språk; samma text i båda halvorna. */
function besked(varde: string | undefined, reserv: Localized): Localized {
  return varde ? { sv: varde, en: varde } : reserv;
}

/** Ett serverbesked med en känd kod skrivs här, på sidans språk. */
function svarsfel(result: { error?: string; kod?: string }, reserv: Localized): Localized {
  if (result.kod === SPARRKOD) return T.forMangaForsok;
  if (result.kod === TVAFAKTOR_FEL) return T.tvaFel;
  return besked(result.error, reserv);
}

export function LoginSida({ oauth }: Readonly<{ oauth: OAuthUtbud }>) {
  const { text } = useLocale();
  const searchParams = useSearchParams();
  // `/dashboard` och inte en av dess flikar: arbetsytans rot. En kund som bara
  // äger Support ska inte mötas av en annan agents grind, och plattformsadmin
  // dirigeras vidare till /admin från roten (app/dashboard/layout.tsx).
  const nextPath = searchParams.get("next") ?? "/dashboard";
  const [mode, setMode] = useState<AuthMode>(
    searchParams.get("mode") === "signup" ? "signup" : "login"
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visaLosenord, setVisaLosenord] = useState(false);
  const [fullName, setFullName] = useState("");
  // Andra steget: lösenordet stämde och kontot har tvåstegsverifiering.
  // Adress och lösenord står kvar i formulärets tillstånd och skickas om
  // tillsammans med koden; servern prövar båda stegen i samma anrop.
  const [tvaSteg, setTvaSteg] = useState(false);
  const [tvaKod, setTvaKod] = useState("");
  const [faltFel, setFaltFel] = useState<Partial<Record<FaltId, Localized>>>({});
  const [message, setMessage] = useState<Localized | null>(null);
  // Callbacken skickar hit ?error= när verifieringslänken inte gick att växla in.
  // Utan detta landade användaren på en tom inloggningssida utan förklaring.
  const [error, setError] = useState<Localized | null>(
    searchParams.get("error") === "auth_callback_failed"
      ? T.lankFel
      : searchParams.get("code") === SPARRKOD
        ? T.forMangaForsok
        : null
  );
  const [isPending, startTransition] = useTransition();

  function bytLage(nytt: AuthMode) {
    setMode(nytt);
    setError(null);
    setMessage(null);
    setFaltFel({});
    setTvaSteg(false);
    setTvaKod("");
  }

  function andra(id: FaltId, satt: (v: string) => void) {
    return (v: string) => {
      satt(v);
      if (faltFel[id]) setFaltFel(({ [id]: _borta, ...kvar }) => kvar);
    };
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    // Egen kontroll i stället för webbläsarens: besked på sidans språk, vid
    // fältet, och alla på en gång.
    const fel: Partial<Record<FaltId, Localized>> = {};
    if (tvaSteg) {
      if (!tvaKod.trim()) {
        setFaltFel({ kod: T.tvaTom });
        document.getElementById("login-kod")?.focus();
        return;
      }
      setFaltFel({});
      startTransition(async () => {
        const result = await signInWithPassword(email.trim(), password, nextPath, tvaKod.trim());
        if (result.success && result.url) {
          oppnaEfterIdentitetsbyte(result.url);
          return;
        }
        if (!result.success) {
          setTvaKod("");
          setError(svarsfel(result, T.inloggningFel));
        }
      });
      return;
    }
    if (mode === "signup" && !fullName.trim()) fel.namn = T.felNamn;
    if (!EPOST.test(email.trim())) fel.epost = T.felEpost;
    if (mode !== "reset") {
      if (!password) fel.losenord = T.felLosenordTomt;
      else if (mode === "signup" && password.length < MINSTA_LOSENORD) fel.losenord = T.felLosenordKort;
    }
    setFaltFel(fel);
    const forsta = Object.keys(fel)[0];
    if (forsta) {
      document.getElementById(`login-${forsta}`)?.focus();
      return;
    }

    startTransition(async () => {
      if (mode === "reset") {
        const result = await requestPasswordReset(email.trim());
        if (result.success) setMessage(besked(result.message, T.aterstallSkickad));
        else setError(svarsfel(result, T.nagotFel));
        return;
      }
      if (mode === "signup") {
        // Lyckas det svarar servern med /onboarding, som öppnas hårt
        // (INV-SEC-014: ingen mjuk navigering vid ett identitetsbyte).
        const result = await signUpWithPassword(email.trim(), password, fullName.trim());
        if (result.success && result.url) oppnaEfterIdentitetsbyte(result.url);
        else if (!result.success) setError(besked(result.error, T.nagotFel));
        return;
      }
      const result = await signInWithPassword(email.trim(), password, nextPath);
      if (result.success && result.url) {
        oppnaEfterIdentitetsbyte(result.url);
        return;
      }
      if (result.kod === TVAFAKTOR_KRAVS) {
        setTvaSteg(true);
        // Fältet finns först efter nästa rendering.
        setTimeout(() => document.getElementById("login-kod")?.focus(), 0);
        return;
      }
      if (!result.success) setError(svarsfel(result, T.inloggningFel));
    });
  }

  function handleOAuth(provider: "google" | "azure") {
    setMessage(null);
    setError(null);
    startTransition(async () => {
      const result = await signInWithOAuth(provider, nextPath);
      if (result.success && result.url) {
        // Navigeringen sker här, inte på servern: en server-side redirect till
        // providern hade hamnat i en fetch utan webbläsare att samtycka i.
        window.location.assign(result.url);
        return;
      }
      setError(besked(result.error, T.oauthFel));
    });
  }

  const rubrik = tvaSteg ? T.tvaRubrik : mode === "signup" ? T.skapaKonto : mode === "reset" ? T.aterstall : T.loggaIn;
  const panelText = tvaSteg
    ? T.tvaPanel
    : mode === "signup"
      ? T.panelSkapa
      : mode === "reset"
        ? T.panelAterstall
        : T.panelLoggaIn;
  const oauthVal = (
    [
      ["google", T.google, oauth.google],
      ["azure", T.microsoft, oauth.microsoft]
    ] as const
  ).filter(([, , aktiv]) => aktiv);

  return (
    <main className="relative min-h-[100svh] bg-paper text-ink min-[900px]:bg-ink">
      {/* Fotot bär sidan (Anton 2026-11-23, förslag B i koncept/login-2026-11-23):
          samma Göteborgsfoto som landningssidan, över hela skärmen på desktop
          och som ett band överst på mobil. Det står helt, utan avtäckning.
          NOT en bläckplatta med två textrader, som sidan var förut. */}
      <div className="relative h-[clamp(220px,38svh,380px)] overflow-hidden min-[900px]:fixed min-[900px]:inset-0 min-[900px]:h-auto">
        <Image
          src="/photos/goteborg-golden.webp"
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-cover object-[50%_78%] min-[900px]:object-[50%_60%]"
        />
        {/* Bandet ligger i fotot, underifrån, där rubriken står: ingen form
            bakom texten. Fasta värden och inte temats tokens, eftersom fotot
            är lika mörkt i ljust och mörkt tema. */}
        <div aria-hidden className="pointer-events-none absolute inset-0" style={{ background: FOTOBAND }} />
        <div className="absolute bottom-5 left-5 right-5 min-[900px]:bottom-[clamp(40px,9vh,96px)] min-[900px]:left-[clamp(24px,3vw,48px)] min-[900px]:right-[calc(clamp(400px,34vw,480px)+clamp(72px,9vw,144px))]">
          <h1
            className="font-display text-[clamp(2.25rem,10.5vw,3.75rem)] font-light leading-[0.98] tracking-[-0.025em] min-[900px]:text-[clamp(3.25rem,7.2vw,7rem)]"
            style={{ color: FOTOTEXT }}
          >
            {mode === "login" && !tvaSteg ? (
              <>
                <span className="block">{text(T.valkommen)}</span>
                {/* Ett markerat ord, sist, i den ljusa ockran: den mörkare
                    försvinner mot solnedgången (DESIGN.md § Hjälten). */}
                <em className="block font-normal italic text-ochre">{text(T.tillbakaOrd)}</em>
              </>
            ) : (
              text(rubrik)
            )}
          </h1>
        </div>
      </div>

      <div className="relative z-10 min-[900px]:flex min-[900px]:min-h-[100svh] min-[900px]:justify-end min-[900px]:p-[clamp(24px,3vw,48px)]">
        <section className="flex w-full flex-col border-t border-ink/15 bg-paper px-5 pb-8 pt-6 min-[900px]:w-[clamp(400px,34vw,480px)] min-[900px]:rounded-[2px] min-[900px]:border min-[900px]:p-[clamp(28px,3vw,44px)]">
          <Link href="/" aria-label={text(T.tillStartsidan)} className="focus-ring inline-flex self-start rounded-input">
            <Logo />
          </Link>
          <form className="mt-7 w-full min-[900px]:mt-auto min-[900px]:pt-10" onSubmit={handleSubmit} noValidate>
            {/* Flikraden döljs i återställningsläget: det är ett sidospår, och
                vägen tillbaka är länken under knappen. */}
            {mode === "reset" || tvaSteg ? null : (
              <div className={fliklista} role="tablist" aria-label={text(T.lagen)}>
                {(
                  [
                    ["login", T.loggaIn],
                    ["signup", T.skapaKonto]
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    role="tab"
                    aria-selected={mode === value}
                    onClick={() => bytLage(value)}
                    className={cn(flik, mode === value ? flikAktiv : flikInaktiv)}
                  >
                    {text(label)}
                  </button>
                ))}
              </div>
            )}

            {/* Vad som gäller för läget man står i. Stod förut på den mörka
                panelen; nu under flikarna, där formuläret börjar. */}
            <p className="mt-5 max-w-[40ch] text-[0.9375rem] leading-6 text-ink-muted">{text(panelText)}</p>

            {tvaSteg ? (
              <div className="mt-7 grid gap-5">
                <Falt
                  id="kod"
                  label={text(T.tvaKod)}
                  value={tvaKod}
                  onChange={andra("kod", setTvaKod)}
                  placeholder="123456"
                  hint={text(T.tvaHint)}
                  fel={faltFel.kod ? text(faltFel.kod) : null}
                  autoComplete="one-time-code"
                />
              </div>
            ) : (
            <div className="mt-7 grid gap-5">
              {mode === "signup" ? (
                <Falt
                  id="namn"
                  label={text(T.namn)}
                  value={fullName}
                  onChange={andra("namn", setFullName)}
                  placeholder={text(T.dittNamn)}
                  fel={faltFel.namn ? text(faltFel.namn) : null}
                  autoComplete="name"
                />
              ) : null}
              <Falt
                id="epost"
                label={text(T.epost)}
                value={email}
                onChange={andra("epost", setEmail)}
                placeholder={text(T.epostExempel)}
                fel={faltFel.epost ? text(faltFel.epost) : null}
                type="email"
                autoComplete="email"
              />
              {mode === "reset" ? null : (
                <Falt
                  id="losenord"
                  label={text(T.losenord)}
                  value={password}
                  onChange={andra("losenord", setPassword)}
                  // QA-skripten (scripts/qa_*.mjs) hittar fältet på platshållaren.
                  placeholder="••••••••"
                  hint={mode === "signup" ? text(T.losenordHint) : undefined}
                  fel={faltFel.losenord ? text(faltFel.losenord) : null}
                  type={visaLosenord ? "text" : "password"}
                  autoComplete={mode === "signup" ? "new-password" : "current-password"}
                  knapp={
                    <button
                      type="button"
                      onClick={() => setVisaLosenord((v) => !v)}
                      aria-pressed={visaLosenord}
                      className="focus-ring absolute inset-y-0 right-0 rounded-input px-4 text-[0.8125rem] font-medium text-ink-muted hover:text-ink"
                    >
                      {text(visaLosenord ? T.dolj : T.visa)}
                    </button>
                  }
                />
              )}
            </div>
            )}

            {mode === "login" && !tvaSteg ? (
              <button
                type="button"
                onClick={() => bytLage("reset")}
                className="focus-ring mt-3 rounded-input text-[0.875rem] text-ink-muted underline underline-offset-4 hover:text-ink"
              >
                {text(T.glomt)}
              </button>
            ) : null}

            {error ? (
              <p role="alert" className="mt-6 break-words text-[0.9375rem] font-medium text-danger">
                {text(error)}
              </p>
            ) : null}
            {/* break-words: meddelandet kan bära användarens mejladress, och en
                lång adress är en obruten sträng som annars spräcker kolumnen. */}
            {message ? (
              <p role="status" className="mt-6 break-words text-[0.9375rem] font-medium text-moss">
                {text(message)}
              </p>
            ) : null}

            <button type="submit" disabled={isPending} className={cn(btnPrimary, "mt-6 min-h-12 w-full text-[0.9375rem]")}>
              {isPending
                ? text(T.bearbetar)
                : tvaSteg
                  ? text(T.tvaVerifiera)
                  : mode === "signup"
                  ? text(T.skapaKonto)
                  : mode === "reset"
                    ? text(T.skickaAterstall)
                    : text(T.loggaIn)}
            </button>

            {mode !== "reset" && !tvaSteg && oauthVal.length > 0 ? (
              <>
                <div className="mt-6 flex items-center gap-4" aria-hidden>
                  <span className="h-px flex-1 bg-ink/15" />
                  <span className="text-[0.8125rem] text-ink-subtle">{text(T.eller)}</span>
                  <span className="h-px flex-1 bg-ink/15" />
                </div>
                <div className="mt-6 grid gap-3">
                  {oauthVal.map(([provider, label]) => (
                    <button
                      key={provider}
                      type="button"
                      disabled={isPending}
                      onClick={() => handleOAuth(provider)}
                      className={cn(btnSecondary, "min-h-12 w-full text-[0.9375rem]")}
                    >
                      {text(label)}
                    </button>
                  ))}
                </div>
              </>
            ) : null}

            <div className="mt-8 grid gap-2 border-t border-ink/15 pt-5 text-[0.875rem] text-ink-muted">
              {mode === "reset" || tvaSteg ? (
                <button
                  type="button"
                  onClick={() => bytLage("login")}
                  className="focus-ring justify-self-start rounded-input font-medium text-ink underline underline-offset-4 hover:text-warning"
                >
                  {text(T.tillbaka)}
                </button>
              ) : (
                <p>
                  {text(mode === "login" ? T.inteKonto : T.harKonto)}{" "}
                  <button
                    type="button"
                    onClick={() => bytLage(mode === "login" ? "signup" : "login")}
                    className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-warning"
                  >
                    {text(mode === "login" ? T.skapaKonto : T.loggaIn)}
                  </button>
                </p>
              )}
              <p>
                {text(T.seForst)}{" "}
                <Link
                  href="/demo"
                  className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-warning"
                >
                  {text(T.oppnaDemon)}
                </Link>
              </p>
            </div>
          </form>
          <p className="mt-7 text-[0.8125rem] text-ink-subtle">{text(T.fotoKredit)}</p>
        </section>
      </div>
    </main>
  );
}

function Falt({
  id,
  label,
  value,
  onChange,
  placeholder,
  hint,
  fel,
  type = "text",
  autoComplete,
  knapp
}: Readonly<{
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  hint?: string;
  fel: string | null;
  type?: string;
  autoComplete?: string;
  /** En knapp inne i fältets högerkant (visa/dölj lösenord). */
  knapp?: React.ReactNode;
}>) {
  const domId = `login-${id}`;
  const beskrivning = fel ?? hint;
  return (
    <div className="grid gap-2">
      <label htmlFor={domId} className={etikett}>
        {label}
      </label>
      <div className="relative">
        {/* 16 px (text-base): under det zoomar iOS Safari in på fältet. */}
        <input
          id={domId}
          className={cn(
            "h-12 w-full rounded-input border bg-paper2/70 px-4 text-base text-ink focus:border-ochre",
            knapp ? "pr-16" : null,
            fel ? "border-danger" : "border-ink/15"
          )}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          type={type}
          autoComplete={autoComplete}
          aria-invalid={Boolean(fel)}
          aria-describedby={beskrivning ? `${domId}-text` : undefined}
        />
        {knapp}
      </div>
      {beskrivning ? (
        <p
          id={`${domId}-text`}
          className={cn("text-[0.8125rem] leading-[1.5]", fel ? "font-medium text-danger" : "text-ink-subtle")}
        >
          {beskrivning}
        </p>
      ) : null}
    </div>
  );
}
