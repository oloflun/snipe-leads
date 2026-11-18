"use client";

import { useTransition } from "react";
import { signOut } from "@/lib/actions/auth";
import { btnSecondary } from "@/components/ui";
import { useLocale } from "@/lib/i18n";

/**
 * Utloggningsknappen.
 *
 * `signOut()` har funnits i lib/actions/auth.ts sedan inloggningen byggdes och
 * haft NOLL konsumenter: användare kunde logga in men inte ut. Det syntes inte
 * i någon typkontroll och i inget test, eftersom en oanvänd export är fullt
 * giltig kod.
 *
 * Tvåspråkig sedan 2026-11-18: den stod på svenska i det engelska
 * gränssnittet, och INV-COPY-001 såg det inte eftersom texten saknar å, ä och ö.
 */
export function SignOutButton() {
  const [pending, startTransition] = useTransition();
  const { text } = useLocale();

  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => startTransition(() => void signOut())}
      className={btnSecondary}
    >
      {pending ? text({ sv: "Loggar ut…", en: "Signing out…" }) : text({ sv: "Logga ut", en: "Sign out" })}
    </button>
  );
}
