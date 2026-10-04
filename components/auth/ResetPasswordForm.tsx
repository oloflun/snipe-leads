"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { updatePassword } from "@/lib/actions/auth";
import { useLocale, type Localized } from "@/lib/i18n";

const T = {
  ogiltigRubrik: { sv: "Länken gäller inte längre", en: "This link is no longer valid" },
  ogiltigText: {
    sv: "Återställningslänkar går ut efter en timme, och de kan bara användas en gång. Begär en ny via ”Glömt lösenordet?” på inloggningssidan.",
    en: "Reset links expire after one hour and can only be used once. Request a new one via “Forgot your password?” on the sign-in page."
  },
  tillInloggningen: { sv: "Till inloggningen", en: "To the sign-in page" },
  olika: { sv: "Lösenorden är inte lika.", en: "The passwords do not match." },
  bytFel: { sv: "Lösenordet gick inte att byta.", en: "The password could not be changed." },
  bytt: { sv: "Lösenordet är bytt.", en: "Your password has been changed." },
  rubrik: { sv: "Nytt lösenord", en: "New password" },
  ingress: { sv: "Välj ett nytt lösenord. Du loggas in direkt efteråt.", en: "Choose a new password. You will be signed in right after." },
  upprepa: { sv: "Upprepa lösenordet", en: "Repeat the password" },
  sparar: { sv: "Sparar...", en: "Saving..." },
  spara: { sv: "Spara lösenordet", en: "Save password" }
} satisfies Record<string, Localized>;

/** Serverns egna besked kommer på ett språk; samma text i båda halvorna. */
function ordagrant(varde: string): Localized {
  return { sv: varde, en: varde };
}

/**
 * Länken var död — utgången, förbrukad eller aldrig riktig. Visas av
 * /auth/reset i stället för formuläret, så felet syns INNAN användaren
 * valt och upprepat ett lösenord.
 */
export function ResetLankOgiltig() {
  const { text } = useLocale();
  return (
    <div className="w-full max-w-xl">
      <h1 className="font-display text-5xl italic-disp tighten">{text(T.ogiltigRubrik)}</h1>
      <p className="mt-4 max-w-xl text-[15px] text-mineral">{text(T.ogiltigText)}</p>
      <div className="mt-8">
        <Link
          href="/login"
          className="inline-flex items-center gap-3 bg-ink px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink"
        >
          {text(T.tillInloggningen)}
          <span aria-hidden>↗</span>
        </Link>
      </div>
    </div>
  );
}

/**
 * Steg 2 i glömt-lösenord. Med `token` (länken ur mailet) validerar och
 * förbrukar updatePassword engångstoken i samma anrop som lösenordet sätts;
 * utan token gäller den inloggade sessionen (lösenordsbyte inifrån appen).
 *
 * Bekräftelsefältet finns för att det här är den enda plats i appen där ett
 * felstavat lösenord låser ute användaren i stället för att bara ge ett fel —
 * länken är redan förbrukad när sparningen gått igenom.
 */
export function ResetPasswordForm({ token }: Readonly<{ token?: string }> = {}) {
  const router = useRouter();
  const { text } = useLocale();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<Localized | null>(null);
  const [message, setMessage] = useState<Localized | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (password !== confirm) {
      setError(T.olika);
      return;
    }

    startTransition(async () => {
      const result = await updatePassword(password, token);
      if (!result.success) {
        setError(result.error ? ordagrant(result.error) : T.bytFel);
        return;
      }
      setMessage(result.message ? ordagrant(result.message) : T.bytt);
      router.push("/dashboard");
    });
  }

  return (
    <form className="w-full max-w-xl" onSubmit={handleSubmit}>
      <h2 className="font-display text-5xl italic-disp tighten">{text(T.rubrik)}</h2>
      <p className="mt-4 text-[15px] text-mineral">
        {text(T.ingress)}
      </p>

      <label className="mt-10 grid gap-2 text-[15px]">
        <span className="kicker text-mineral">{text(T.rubrik)}</span>
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
        <span className="kicker text-mineral">{text(T.upprepa)}</span>
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
          {text(error)}
        </p>
      ) : null}
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
          {isPending ? text(T.sparar) : text(T.spara)}
          <span aria-hidden>↗</span>
        </button>
      </div>
    </form>
  );
}
