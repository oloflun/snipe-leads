"use client";

import { useTransition } from "react";
import { signOut } from "@/lib/actions/auth";

/**
 * Utloggningsknappen.
 *
 * `signOut()` har funnits i lib/actions/auth.ts sedan inloggningen byggdes och
 * haft NOLL konsumenter: användare kunde logga in men inte ut. Det syntes inte
 * i någon typkontroll och i inget test, eftersom en oanvänd export är fullt
 * giltig kod.
 */
export function SignOutButton() {
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => startTransition(() => void signOut())}
      className="kicker border border-ink/15 px-4 py-2 text-mineral transition-colors hover:border-ochre hover:text-ochre disabled:opacity-50"
    >
      {pending ? "Loggar ut…" : "Logga ut"}
    </button>
  );
}
