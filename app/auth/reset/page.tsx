import Link from "next/link";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";
import { getWorkspaceContext } from "@/lib/workspace";

export const dynamic = "force-dynamic";

/**
 * Steg 2 i glömt-lösenord. Recovery-koden är redan växlad mot en session av
 * /auth/callback (se requestPasswordReset), så sidan behöver bara kontrollera
 * att sessionen finns.
 *
 * Utan session visas inte formuläret alls. Ett formulär som postar mot en
 * session som inte finns hade sett ut att fungera och misslyckats vid
 * sparningen — felet ska synas innan användaren skrivit något.
 */
export default async function Page() {
  const context = await getWorkspaceContext();

  if (!context) {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6">
        <h1 className="font-display text-5xl italic-disp tighten">Länken gäller inte längre</h1>
        <p className="mt-4 max-w-xl text-[15px] text-mineral">
          Återställningslänkar går ut, och de kan bara användas en gång. Begär en
          ny från inloggningssidan.
        </p>
        <div className="mt-8">
          <Link
            href="/login"
            className="inline-flex items-center gap-3 bg-ink px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink"
          >
            Till inloggningen
            <span aria-hidden>↗</span>
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6">
      <ResetPasswordForm />
    </main>
  );
}
