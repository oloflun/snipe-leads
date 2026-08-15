"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { updatePassword } from "@/lib/actions/auth";

/**
 * Steg 2 i glömt-lösenord. Recovery-sessionen är redan växlad in av
 * /auth/reset innan den här renderas; formuläret sätter bara det nya
 * lösenordet på den sessionen.
 *
 * Bekräftelsefältet finns för att det här är den enda plats i appen där ett
 * felstavat lösenord låser ute användaren i stället för att bara ge ett fel —
 * det gamla lösenordet är redan förbrukat när länken klickats.
 */
export function ResetPasswordForm() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (password !== confirm) {
      setError("Lösenorden är inte lika.");
      return;
    }

    startTransition(async () => {
      const result = await updatePassword(password);
      if (!result.success) {
        setError(result.error ?? "Lösenordet gick inte att byta.");
        return;
      }
      setMessage(result.message ?? "Lösenordet är bytt.");
      router.push("/dashboard");
    });
  }

  return (
    <form className="w-full max-w-xl" onSubmit={handleSubmit}>
      <h2 className="font-display text-5xl italic-disp tighten">Nytt lösenord</h2>
      <p className="mt-4 text-[15px] text-mineral">
        Välj ett nytt lösenord. Du loggas in direkt efteråt.
      </p>

      <label className="mt-10 grid gap-2 text-[15px]">
        <span className="kicker text-mineral">Nytt lösenord</span>
        <input
          type="password"
          className="h-14 border border-ink/15 bg-paper2/70 px-4 focus:border-ochre"
          placeholder="••••••••"
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="new-password"
        />
      </label>

      <label className="mt-5 grid gap-2 text-[15px]">
        <span className="kicker text-mineral">Upprepa lösenordet</span>
        <input
          type="password"
          className="h-14 border border-ink/15 bg-paper2/70 px-4 focus:border-ochre"
          placeholder="••••••••"
          required
          minLength={8}
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
          autoComplete="new-password"
        />
      </label>

      {error ? (
        <p role="alert" className="mt-6 break-words text-[14px] text-danger">
          {error}
        </p>
      ) : null}
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
          {isPending ? "Sparar..." : "Spara lösenordet"}
          <span aria-hidden>↗</span>
        </button>
      </div>
    </form>
  );
}
