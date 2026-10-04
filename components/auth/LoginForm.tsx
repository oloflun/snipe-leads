"use client";

import { useState, useTransition } from "react";
import { useSearchParams } from "next/navigation";
import {
  requestDemoAccess,
  requestPasswordReset,
  signInWithOAuth,
  signInWithPassword,
  signUpWithPassword
} from "@/lib/actions/auth";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type AuthMode = "login" | "signup" | "demo" | "reset";

const T = {
  lankFel: {
    sv: "Länken gick inte att använda. Den kan ha gått ut eller redan vara förbrukad — begär en ny nedan.",
    en: "The link could not be used. It may have expired or already been used. Request a new one below."
  },
  // Samma besked oavsett om adressen har ett konto — formuläret får inte
  // fungera som en kontolista (samma princip som inloggningens felmeddelande).
  aterstallSkickad: {
    sv: "Om adressen har ett konto hos oss har vi skickat en återställningslänk. Kolla inkorgen — och skräpposten.",
    en: "If the address has an account with us, we have sent a reset link. Check your inbox — and the spam folder."
  },
  atkomstSkickad: { sv: "Åtkomstlänk skickad.", en: "Access link sent." },
  kontoSkapat: { sv: "Konto skapat.", en: "Account created." },
  nagotFel: { sv: "Något gick fel.", en: "Something went wrong." },
  inloggningFel: { sv: "Inloggningen misslyckades.", en: "Sign-in failed." },
  oauthFel: { sv: "Inloggningen kunde inte startas.", en: "Sign-in could not be started." },
  skapaKonto: { sv: "Skapa konto", en: "Create account" },
  aterstall: { sv: "Återställ lösenordet", en: "Reset your password" },
  valkommen: { sv: "Välkommen tillbaka", en: "Welcome back" },
  google: { sv: "Fortsätt med Google", en: "Continue with Google" },
  microsoft: { sv: "Fortsätt med Microsoft", en: "Continue with Microsoft" },
  ellerEpost: { sv: "eller med e-post", en: "or with email" },
  loggaIn: { sv: "Logga in", en: "Sign in" },
  provaDemo: { sv: "Prova demo", en: "Try the demo" },
  namn: { sv: "Namn", en: "Name" },
  dittNamn: { sv: "Ditt namn", en: "Your name" },
  epost: { sv: "E-post", en: "Email" },
  epostExempel: { sv: "du@bolag.se", en: "you@company.com" },
  losenord: { sv: "Lösenord", en: "Password" },
  glomt: { sv: "Glömt lösenordet?", en: "Forgot your password?" },
  aterstallInfo: {
    sv: "Skriv adressen du registrerade dig med. Vi skickar en länk som låter dig sätta ett nytt lösenord.",
    en: "Enter the address you signed up with. We will send a link that lets you set a new password."
  },
  bearbetar: { sv: "Bearbetar...", en: "Working..." },
  skickaAtkomst: { sv: "Skicka åtkomstlänk", en: "Send access link" },
  skickaAterstall: { sv: "Skicka återställningslänk", en: "Send reset link" },
  tillbaka: { sv: "Tillbaka till inloggningen", en: "Back to sign-in" },
  demoInfo: {
    sv: "Prova demo: fyll i din mejladress så skickar vi en åtkomstlänk. Ingen auto-inloggning — du behåller kontrollen.",
    en: "Try the demo: enter your email and we will send you an access link. No automatic sign-in, so you stay in control."
  }
} satisfies Record<string, Localized>;

/** Serverns egna besked kommer på ett språk; samma text i båda halvorna. */
function ordagrant(varde: string): Localized {
  return { sv: varde, en: varde };
}

function besked(varde: string | undefined, reserv: Localized): Localized {
  return varde ? ordagrant(varde) : reserv;
}

export function LoginForm() {
  const { text } = useLocale();
  const searchParams = useSearchParams();
  // `/dashboard` och inte `/dashboard/emails`: arbetsytans rot, inte en av dess
  // flikar. Två skäl.
  //
  // 1. Email studio är EN produkt av två. En kund som bara äger Support möttes
  //    av en 404-liknande entitlement-grind som första sida efter inloggning.
  // 2. Plattformsadmin dirigeras vidare till /admin av app/dashboard/layout.tsx.
  //    Den dirigeringen sitter på arbetsytans ROT; med en flik som mål blev
  //    inloggningen en extra studs genom en vy admin ändå inte skulle se.
  //
  // Den gamla defaulten var `/emails`, som inte finns alls (lib/routes.ts) —
  // fixen då var att peka på en route som fanns, inte att välja rätt route.
  const nextPath = searchParams.get("next") ?? "/dashboard";
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [message, setMessage] = useState<Localized | null>(null);
  // Callbacken skickar hit ?error= när verifieringslänken inte gick att växla in.
  // Utan detta landade användaren på en tom inloggningssida utan förklaring.
  const [error, setError] = useState<Localized | null>(
    searchParams.get("error") === "auth_callback_failed" ? T.lankFel : null
  );
  const [isPending, startTransition] = useTransition();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    startTransition(async () => {
      if (mode === "reset") {
        const result = await requestPasswordReset(email);
        if (result.success) {
          setMessage(besked(result.message, T.aterstallSkickad));
        } else {
          setError(besked(result.error, T.nagotFel));
        }
        return;
      }

      if (mode === "demo") {
        const result = await requestDemoAccess(email, nextPath);
        if (result.success) {
          setMessage(besked(result.message, T.atkomstSkickad));
        } else {
          setError(besked(result.error, T.nagotFel));
        }
        return;
      }

      if (mode === "signup") {
        const result = await signUpWithPassword(email, password, fullName || email.split("@")[0]);
        if (result.success) {
          setMessage(besked(result.message, T.kontoSkapat));
        } else {
          setError(besked(result.error, T.nagotFel));
        }
        return;
      }

      const result = await signInWithPassword(email, password, nextPath);
      if (!result.success) {
        setError(besked(result.error, T.inloggningFel));
      }
    });
  }

  function handleOAuth(provider: "google" | "azure") {
    setMessage(null);
    setError(null);
    startTransition(async () => {
      const result = await signInWithOAuth(provider, nextPath);
      if (result.success && result.url) {
        // Navigeringen sker här, inte på servern: skipBrowserRedirect är satt
        // i action:en eftersom en server-side redirect till providern hade
        // hamnat i en fetch utan webbläsare att samtycka i.
        window.location.assign(result.url);
        return;
      }
      setError(besked(result.error, T.oauthFel));
    });
  }

  return (
    <form className="w-full max-w-xl" onSubmit={handleSubmit}>
      <h2 className="font-display text-5xl italic-disp tighten">
        {mode === "signup"
          ? text(T.skapaKonto)
          : mode === "reset"
            ? text(T.aterstall)
            : text(T.valkommen)}
      </h2>

      {/* Ink-outline, inte färgade märkesknappar. DESIGN.md har EN accent, och
          Googles fyrfärgslogotyp är inte den — två identiteter på samma sida
          gör att ingen av dem läses som avsändare. */}
      {/* Staplade, inte två i bredd. Vid 768 bröts "FORTSÄTT MED MICROSOFT"
          till TRE rader i en tvåkolumnsgrid — 12px versaler med 0.18em
          spärr är bredare än den halva kolumnen nästan överallt utom vid
          1440. Full bredd ger alltid en rad och matchar dessutom fälten
          under, som också är fullbreda. Uppmätt vid 320/375/414/768/1440. */}
      <div className="mt-8 grid gap-3">
        {([
          ["google", T.google],
          ["azure", T.microsoft]
        ] as const).map(([provider, label]) => (
          <button
            key={provider}
            type="button"
            disabled={isPending}
            onClick={() => handleOAuth(provider)}
            className="border border-ink/15 px-4 py-3 font-mono text-[12px] uppercase tracking-[0.18em] text-mineral transition hover:border-ochre hover:text-ochre disabled:opacity-60"
          >
            {text(label)}
          </button>
        ))}
      </div>

      <div className="mt-8 flex items-center gap-4">
        <span className="hrule h-px flex-1 bg-ink/15" />
        <span className="kicker text-mineral">{text(T.ellerEpost)}</span>
        <span className="hrule h-px flex-1 bg-ink/15" />
      </div>

      {/* Tabbraden döljs i återställningsläget. Det är ett FJÄRDE läge, så
          ingen av de tre var markerad — raden såg ut som en kontroll där
          inget är valt, vilket läser som en bugg och inte som "du har klivit
          åt sidan". Vägen tillbaka är den explicita länken under knappen.
          Uppmätt i en skärmdump vid 375px, inte gissat. */}
      <div className={cn("mt-8 flex-wrap gap-3", mode === "reset" ? "hidden" : "flex")}>
        {([
          ["login", T.loggaIn],
          ["signup", T.skapaKonto],
          ["demo", T.provaDemo]
        ] as const).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => {
              setMode(value);
              setError(null);
              setMessage(null);
            }}
            className={cn(
              "border px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] transition",
              mode === value
                ? "border-ink bg-ink text-paper"
                : "border-ink/15 text-mineral hover:border-ochre hover:text-ochre"
            )}
          >
            {text(label)}
          </button>
        ))}
      </div>

      {mode === "signup" ? (
        <label className="mt-10 grid gap-2 text-[15px]">
          <span className="kicker text-mineral">{text(T.namn)}</span>
          <input
            className="h-14 border border-ink/15 bg-paper2/70 px-4 focus:border-ochre"
            placeholder={text(T.dittNamn)}
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            autoComplete="name"
          />
        </label>
      ) : null}

      <label className="mt-10 grid gap-2 text-[15px]">
        <span className="kicker text-mineral">{text(T.epost)}</span>
        <input
          className="h-14 border border-ink/15 bg-paper2/70 px-4 focus:border-ochre"
          placeholder={text(T.epostExempel)}
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
        />
      </label>

      {mode === "login" || mode === "signup" ? (
        <label className="mt-5 grid gap-2 text-[15px]">
          <span className="kicker text-mineral">{text(T.losenord)}</span>
          <input
            type="password"
            className="h-14 border border-ink/15 bg-paper2/70 px-4 focus:border-ochre"
            placeholder="••••••••"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
          />
        </label>
      ) : null}

      {mode === "login" ? (
        <button
          type="button"
          onClick={() => {
            setMode("reset");
            setError(null);
            setMessage(null);
          }}
          className="mt-3 text-[13px] text-mineral underline underline-offset-4 transition hover:text-ochre"
        >
          {text(T.glomt)}
        </button>
      ) : null}

      {mode === "reset" ? (
        <p className="mt-5 text-[14px] text-mineral">{text(T.aterstallInfo)}</p>
      ) : null}

      {/* Fel var tidigare ochre — samma token som primär-CTA och fokusringen, vid
          L=0.74 mot papper L=0.965. Det lästes som hjälptext, inte som ett fel.
          DESIGN.md reserverar ochre för accenten och har --danger för fel. */}
      {error ? (
        <p role="alert" className="mt-6 break-words text-[14px] text-danger">
          {text(error)}
        </p>
      ) : null}
      {/* break-words: meddelandet innehåller användarens mailadress, och en lång
          adress är en obruten sträng som annars spräcker kolumnen. */}
      {message ? (
        <p role="status" className="mt-6 break-words text-[14px] text-moss">
          {text(message)}
        </p>
      ) : null}

      <div className="mt-8">
        <button
          type="submit"
          disabled={isPending}
          className="inline-flex items-center gap-3 bg-ink px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink disabled:opacity-60"
        >
          {isPending
            ? text(T.bearbetar)
            : mode === "signup"
              ? text(T.skapaKonto)
              : mode === "demo"
                ? text(T.skickaAtkomst)
                : mode === "reset"
                  ? text(T.skickaAterstall)
                  : text(T.loggaIn)}
          <span aria-hidden>↗</span>
        </button>
      </div>

      {mode === "reset" ? (
        <button
          type="button"
          onClick={() => {
            setMode("login");
            setError(null);
            setMessage(null);
          }}
          className="mt-4 text-[13px] text-mineral underline underline-offset-4 transition hover:text-ochre"
        >
          {text(T.tillbaka)}
        </button>
      ) : (
        <p className="mt-4 text-[12px] text-mineral">{text(T.demoInfo)}</p>
      )}
    </form>
  );
}
