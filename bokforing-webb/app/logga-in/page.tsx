import type { Metadata } from "next";
import { Logo } from "@/components/Logo";
import { btnPrimary } from "@/components/ui";
import { saneraNasta } from "@/lib/session";

// Bara namnet — rotlayoutens mall lägger till "— Snajp Bokföring".
export const metadata: Metadata = { title: "Logga in" };

/**
 * Inloggningssidan — Content-familjen: en spalt, typografi, ingen meny.
 * Ren HTML-form mot /api/logga-in; fungerar utan JavaScript, och felet
 * kommer tillbaka som ?fel=1 i stället för en stum studs (det var exakt
 * så Basic Auth-rutan föll: fel lösenord såg ut som ingenting alls).
 */
export default async function Sida({
  searchParams
}: Readonly<{ searchParams: Promise<{ fel?: string; nasta?: string }> }>) {
  const { fel, nasta } = await searchParams;
  const mal = saneraNasta(nasta);

  return (
    <main className="flex min-h-dvh items-center justify-center px-5 py-10">
      <div className="w-full max-w-[24rem]">
        <Logo />
        <h1 className="font-display tighten mt-8 text-[1.75rem] leading-tight text-ink">
          Logga in
        </h1>
        <p className="mt-2 text-[0.9375rem] leading-6 text-ink/60">
          Snajp Bokföring är i förhandsversion. Logga in med uppgifterna du
          fått av Snajp.
        </p>

        <form method="post" action="/api/logga-in" className="mt-7 space-y-5">
          <input type="hidden" name="nasta" value={mal} />
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">E-postadress</span>
            <input
              name="epost"
              type="email"
              required
              autoComplete="username"
              autoFocus
              placeholder="du@bolag.se"
              className="focus-ring mt-1.5 h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] placeholder:text-ink/35"
            />
          </label>
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">Lösenord</span>
            <input
              name="losen"
              type="password"
              required
              autoComplete="current-password"
              placeholder="••••••••"
              className="focus-ring mt-1.5 h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] placeholder:text-ink/35"
            />
          </label>

          {fel ? (
            <p role="alert" className="text-[0.875rem] leading-5 text-danger">
              Fel e-postadress eller lösenord. Kontrollera uppgifterna och
              försök igen.
            </p>
          ) : null}

          <button type="submit" className={`${btnPrimary} w-full`}>
            Logga in
          </button>
        </form>

        <p className="mt-6 border-t border-ink/15 pt-4 text-[0.8125rem] leading-5 text-ink/50">
          Saknar du uppgifter? Mejla{" "}
          <a
            href="mailto:kontakt@snajp.se"
            className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4 hover:text-ink"
          >
            kontakt@snajp.se
          </a>
          .
        </p>
      </div>
    </main>
  );
}
