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
  const nextPath = searchParams.get("next") ?? "/dashboard";
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
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
            className="h-14 border border-ink/15 bg-paper2/70 px-4 outline-none focus:border-ochre"
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
          className="h-14 border border-ink/15 bg-paper2/70 px-4 outline-none focus:border-ochre"
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
            className="h-14 border border-ink/15 bg-paper2/70 px-4 outline-none focus:border-ochre"
            placeholder="••••••••"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
          />
        </label>
      ) : null}

      {error ? <p className="mt-6 text-[14px] text-ochre">{error}</p> : null}
      {message ? <p className="mt-6 text-[14px] text-moss">{message}</p> : null}

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
    </form>
  );
}