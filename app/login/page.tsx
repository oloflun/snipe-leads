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
 * Inloggning med lösenord eller SSO, kontoskapande, och demo-åtkomst där
 * besökaren lämnar sin mejl och får en åtkomstlänk. Ingen auto-inloggning
 * och ingen magic link.
 */
