import { Suspense } from "react";
import { LoginSida } from "@/components/auth/LoginForm";

/**
 * Inloggning med lösenord eller SSO, och kontoskapande. `?mode=signup` öppnar
 * sidan i läget Skapa konto.
 *
 * Dynamisk med flit: vilka SSO-knappar som visas läses ur miljön vid varje
 * förfrågan. En statiskt byggd sida hade frusit byggmiljöns svar, och en knapp
 * för en leverantör som inte är konfigurerad kan bara svara med ett fel.
 */
export const dynamic = "force-dynamic";

export default function Page() {
  const oauth = {
    google: Boolean(process.env.AUTH_GOOGLE_ID),
    microsoft: Boolean(process.env.AUTH_MICROSOFT_ENTRA_ID_ID)
  };
  return (
    <Suspense fallback={<div className="min-h-screen bg-paper" />}>
      <LoginSida oauth={oauth} />
    </Suspense>
  );
}
