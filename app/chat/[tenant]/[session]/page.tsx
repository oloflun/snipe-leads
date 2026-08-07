import Image from "next/image";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getTenant } from "@/lib/tenants";
import { SupportChat } from "@/components/snajp/SupportChat";

type Props = { params: Promise<{ tenant: string; session: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { tenant: slug } = await params;
  const tenant = getTenant(slug);
  return {
    title: tenant ? `Kundtjänst — ${tenant.name}` : "Kundtjänst",
    // En sessions-URL ska aldrig hamna i ett sökindex.
    robots: { index: false, follow: false }
  };
}

export default async function SupportSessionPage({ params }: Props) {
  const { tenant: slug, session } = await params;
  const tenant = getTenant(slug);

  if (!tenant) {
    notFound();
  }

  const { logo } = tenant;

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      {/* Logotypen ligger på mörkt fält när den är gjord för det. Livrustnings
          ordbild är vit och skulle annars försvinna helt mot papperet. */}
      <header className={logo.background === "dark" ? "bg-ink" : "border-b border-ink/10"}>
        <div className="mx-auto flex max-w-[900px] flex-wrap items-center justify-between gap-4 px-6 py-5 md:px-8">
          <a href={tenant.website} className="inline-flex items-center">
            <Image
              src={logo.src}
              alt={logo.alt}
              width={logo.width}
              height={logo.height}
              priority
              // height: auto krävs när bara ena måttet styrs via CSS, annars
              // varnar next/image för förvrängd bildproportion.
              className="h-10 w-auto md:h-12"
            />
          </a>
          <span
            className={
              logo.background === "dark"
                ? "kicker text-paper/45"
                : "kicker text-mineral"
            }
          >
            Powered by Snajp
          </span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[900px] flex-1 px-6 py-12 md:px-8 md:py-16">
        <h1 className="font-display text-[2rem] leading-tight tracking-[-0.02em] md:text-[2.5rem]">
          Kundtjänst
        </h1>
        <p className="mt-4 max-w-[60ch] text-[17px] leading-8 text-ink2">
          Beskriv ditt ärende så hjälper vi dig. Behöver frågan en kollega kopplar vi in en
          människa, och du får besked om det direkt.
        </p>
        <div className="rule mt-6 text-ink" />

        <div className="mt-10">
          <SupportChat tenant={slug} session={session} />
        </div>
      </main>

      <footer className="border-t border-ink/10">
        <div className="mx-auto max-w-[900px] px-6 py-8 md:px-8">
          <p className="text-[14px] leading-7 text-mineral">
            {tenant.company.legalName} ·{" "}
            <a href={`mailto:${tenant.company.email}`} className="hover:text-ochre">
              {tenant.company.email}
            </a>{" "}
            ·{" "}
            {tenant.company.phones.map((phone, index) => (
              <span key={phone}>
                {index > 0 ? " / " : ""}
                <a href={`tel:${phone.replace(/[^\d+]/g, "")}`} className="hover:text-ochre">
                  {phone}
                </a>
              </span>
            ))}
          </p>
          <p className="mt-2 text-[13px] text-mineral">
            Spara länken om du vill återkomma till samtalet.
          </p>
        </div>
      </footer>
    </div>
  );
}
