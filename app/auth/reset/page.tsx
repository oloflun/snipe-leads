import { ResetLankOgiltig, ResetPasswordForm } from "@/components/auth/ResetPasswordForm";
import { hashaResetToken, serUtSomResetToken } from "@/lib/reset-token";
import { hasDatabase, sql } from "@/lib/db";
import { getWorkspaceContext } from "@/lib/workspace";

export const dynamic = "force-dynamic";

/**
 * Steg 2 i glömt-lösenord. Länken i mailet bär en engångstoken i `?token=`;
 * sidan kontrollerar att den finns, är oförbrukad och inte gått ut INNAN
 * formuläret visas — ett formulär som postar mot en död token hade sett ut
 * att fungera och misslyckats vid sparningen, efter att användaren valt och
 * upprepat ett lösenord.
 *
 * Kontrollen här är läsande; själva förbrukningen (used_at) sker atomiskt i
 * updatePassword när det nya lösenordet sparas. Token kan bara matcha en rad
 * som pekar på ett BEFINTLIGT konto i auth.users — sidan kan aldrig användas
 * för att skapa ett konto.
 *
 * Utan token fungerar sidan som förut för en redan inloggad användare
 * (lösenordsbyte på en aktiv session).
 */
export default async function Page({
  searchParams
}: Readonly<{ searchParams: Promise<{ token?: string }> }>) {
  const { token } = await searchParams;

  if (token !== undefined) {
    const giltig =
      serUtSomResetToken(token) &&
      hasDatabase() &&
      (
        await sql<{ ok: boolean }>(
          `select true as ok from public.password_reset_tokens
            where token_hash = $1 and used_at is null and expires_at > now()`,
          [hashaResetToken(token)]
        )
      ).length > 0;

    return (
      <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6">
        {giltig ? <ResetPasswordForm token={token} /> : <ResetLankOgiltig />}
      </main>
    );
  }

  const context = await getWorkspaceContext();

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6">
      {context ? <ResetPasswordForm /> : <ResetLankOgiltig />}
    </main>
  );
}
