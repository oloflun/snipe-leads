"use client";

import { useState, useTransition } from "react";
import { useSearchParams } from "next/navigation";
import {
  requestPasswordReset,
  signInWithMagicLink,
  signInWithOAuth,
  signInWithPassword,
  signUpWithPassword,
  startDemo
} from "@/lib/actions/auth";
import { cn } from "@/lib/utils";

type AuthMode = "login" | "signup" | "magic" | "reset";

export function LoginForm() {
  const searchParams = useSearchParams();
  // /emails finns inte — routen heter /dashboard/emails (lib/routes.ts). Den
  // gamla defaulten skickade varje lyckad inloggning utan ?next= till en 404.
  const nextPath = searchParams.get("next") ?? "/dashboard/emails";
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  // Callbacken skickar hit ?error= när verifieringslänken inte gick att växla in.
  // Utan detta landade användaren på en tom inloggningssida utan förklaring.
  const [error, setError] = useState<string | null>(
    searchParams.get("error") === "auth_callback_failed"
      ? "Länken gick inte att använda. Den kan ha gått ut eller redan vara förbrukad — begär en ny nedan."
      : null
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
          setMessage(result.message ?? "Återställningslänk skickad.");
        } else {
          setError(result.error ?? "Något gick fel.");
        }
        return;
      }

      if (mode === "magic") {
        const result = await signInWithMagicLink(email, nextPath);
        if (result.success) {
          setMessage(result.message ?? "Magic link skickad.");
        } else {
          setError(result.error ?? "Något gick fel.");
        }
        return;
      }

      if (mode === "signup") {
        const result = await signUpWithPassword(email, password, fullName || email.split("@")[0]);
        if (result.success) {
          setMessage(result.message ?? "Konto skapat.");
        } else {
          setError(result.error ?? "Något gick fel.");
        }
        return;
      }

      const result = await signInWithPassword(email, password, nextPath);
      if (!result.success) {
        setError(result.error ?? "Inloggningen misslyckades.");
      }
    });
  }

  function handleDemo() {
    setMessage(null);
    setError(null);
    startTransition(async () => {
      // Vid lyckat demo redirectar servern till /onboarding, så vi når bara hit
      // om något gick fel.
      const result = await startDemo();
      if (!result.success) {
        setError(result.error ?? "Demo kunde inte startas.");
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
      setError(result.error ?? "Inloggningen kunde inte startas.");
    });
  }

  return (
    <form className="w-full max-w-xl" onSubmit={handleSubmit}>
      <h2 className="font-display text-5xl italic-disp tighten">
        {mode === "signup"
          ? "Skapa konto"
          : mode === "reset"
            ? "Återställ lösenordet"
            : "Välkommen tillbaka"}
      </h2>

      {/* Ink-outline, inte färgade märkesknappar. DESIGN.md har EN accent, och
          Googles fyrfärgslogotyp är inte den — två identiteter på samma sida
          gör att ingen av dem läses som avsändare. */}
      {/* Staplade, inte två i bredd. Vid 768 bröts "FORTSÄTT MED MICROSOFT"
          till TRE rader i en tvåkolumnsgrid — 12px versaler med 0.18em
          spärr är bredare än den halva kolumnen nästan överallt utom vid
          1440. Full bredd ger alltid en rad och matchar dessutom fälten
          under, som också är fullbreda. Uppmätt vid 320/375/414/768/1440. */}
      {/* Demo-läget ersätter "magic link som ger full åtkomst": en isolerad
          workspace utan förladdad data, med begränsat antal körningar och en
          tydlig väg att uppgradera till ett konto. */}
      <button
        type="button"
        disabled={isPending}
        onClick={handleDemo}
        className="mt-8 w-full border border-ochre/40 bg-ochre/10 px-4 py-3 font-mono text-[12px] uppercase tracking-[0.18em] text-ochre transition hover:bg-ochre/15 disabled:opacity-60"
      >
        Prova demo — utan konto
      </button>

      <div className="mt-8 grid gap-3">
        {([
          ["google", "Fortsätt med Google"],
          ["azure", "Fortsätt med Microsoft"]
        ] as const).map(([provider, label]) => (
          <button
            key={provider}
            type="button"
            disabled={isPending}
            onClick={() => handleOAuth(provider)}
            className="border border-ink/15 px-4 py-3 font-mono text-[12px] uppercase tracking-[0.18em] text-mineral transition hover:border-ochre hover:text-ochre disabled:opacity-60"
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-8 flex items-center gap-4">
        <span className="hrule h-px flex-1 bg-ink/15" />
        <span className="kicker text-mineral">eller med e-post</span>
        <span className="hrule h-px flex-1 bg-ink/15" />
      </div>

      {/* Tabbraden döljs i återställningsläget. Det är ett FJÄRDE läge, så
          ingen av de tre var markerad — raden såg ut som en kontroll där
          inget är valt, vilket läser som en bugg och inte som "du har klivit
          åt sidan". Vägen tillbaka är den explicita länken under knappen.
          Uppmätt i en skärmdump vid 375px, inte gissat. */}
      <div className={cn("mt-8 flex-wrap gap-3", mode === "reset" ? "hidden" : "flex")}>
        {([
          ["login", "Logga in"],
          ["signup", "Skapa konto"],
          ["magic", "Magic link"]
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
            {label}
          </button>
        ))}
      </div>

      {mode === "signup" ? (
        <label className="mt-10 grid gap-2 text-[15px]">
          <span className="kicker text-mineral">Namn</span>
          <input
            className="h-14 border border-ink/15 bg-paper2/70 px-4 focus:border-ochre"
            placeholder="Ditt namn"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            autoComplete="name"
          />
        </label>
      ) : null}

      <label className="mt-10 grid gap-2 text-[15px]">
        <span className="kicker text-mineral">Email</span>
        <input
          className="h-14 border border-ink/15 bg-paper2/70 px-4 focus:border-ochre"
          placeholder="du@bolag.se"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
        />
      </label>

      {mode === "login" || mode === "signup" ? (
        <label className="mt-5 grid gap-2 text-[15px]">
          <span className="kicker text-mineral">Lösenord</span>
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
          Glömt lösenordet?
        </button>
      ) : null}

      {mode === "reset" ? (
        <p className="mt-5 text-[14px] text-mineral">
          Skriv adressen du registrerade dig med. Vi skickar en länk som låter dig
          sätta ett nytt lösenord.
        </p>
      ) : null}

      {/* Fel var tidigare ochre — samma token som primär-CTA och fokusringen, vid
          L=0.74 mot papper L=0.965. Det lästes som hjälptext, inte som ett fel.
          DESIGN.md reserverar ochre för accenten och har --danger för fel. */}
      {error ? (
        <p role="alert" className="mt-6 break-words text-[14px] text-danger">
          {error}
        </p>
      ) : null}
      {/* break-words: meddelandet innehåller användarens mailadress, och en lång
          adress är en obruten sträng som annars spräcker kolumnen. */}
      {message ? (
        <p role="status" className="mt-6 break-words text-[14px] text-moss">
          {message}
        </p>
      ) : null}

      <div className="mt-8">
        <button
          type="submit"
          disabled={isPending}
          className="inline-flex items-center gap-3 bg-ink px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink disabled:opacity-60"
        >
          {isPending
            ? "Bearbetar..."
            : mode === "signup"
              ? "Skapa konto"
              : mode === "magic"
                ? "Skicka magic link"
                : mode === "reset"
                  ? "Skicka återställningslänk"
                  : "Logga in"}
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
          Tillbaka till inloggningen
        </button>
      ) : (
        <p className="mt-4 text-[12px] text-mineral">
          Magic link = snabbast väg till Email Studio (endast email, omedelbar tillgång efter inloggning). Använd "Magic link" ovan för att testa Kortare, Skriv om, Förbättra m.fl. direkt.
        </p>
      )}
    </form>
  );
}