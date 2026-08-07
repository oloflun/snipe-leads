"use client";

import { useState, useTransition } from "react";
import { useSearchParams } from "next/navigation";
import {
  signInWithMagicLink,
  signInWithPassword,
  signUpWithPassword
} from "@/lib/actions/auth";
import { cn } from "@/lib/utils";

type AuthMode = "login" | "signup" | "magic";

export function LoginForm() {
  const searchParams = useSearchParams();
  // Per Snajp Prompt: quick email-only + immediate Email Studio access
  const nextPath = searchParams.get("next") ?? "/emails";
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

  return (
    <form className="w-full max-w-xl" onSubmit={handleSubmit}>
      <h2 className="font-display text-5xl italic-disp tighten">
        {mode === "signup" ? "Skapa konto" : "Välkommen tillbaka"}
      </h2>

      <div className="mt-8 flex flex-wrap gap-3">
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

      {mode !== "magic" ? (
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
                : "Logga in"}
          <span aria-hidden>↗</span>
        </button>
      </div>

      <p className="mt-4 text-[12px] text-mineral">
        Magic link = snabbast väg till Email Studio (endast email, omedelbar tillgång efter inloggning). Använd "Magic link" ovan för att testa Kortare, Skriv om, Förbättra m.fl. direkt.
      </p>
    </form>
  );
}