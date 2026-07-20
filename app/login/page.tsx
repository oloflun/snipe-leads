import { Suspense } from "react";
import { LoginView } from "@/components/WorkspaceViews";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-paper" />}>
      <LoginView />
    </Suspense>
  );
}

/**
 * Per Snipra Prompt: Användare kan skapa konto enbart med email (magic link recommended).
 * Omedelbar tillgång till Email Studio efter registrering utan tung verifikation i första steget.
 * Magic link defaultar till /emails för direkt test av Kortare / Skriv om m.fl.
 */
