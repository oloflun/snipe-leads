"use client";

import { CheckCircle2, Loader2 } from "lucide-react";
import { useState } from "react";
import { bokaDemo } from "@/lib/actions/demo";
import { KONTAKT_MEJL } from "@/components/marketing/copy";

/**
 * Reservvägen när ingen Cal.com-länk är konfigurerad.
 *
 * ## Vad den lovar, och vad den inte lovar
 *
 * Bekräftelsen säger att vi hört av oss "så snart vi kan", INTE att ett
 * bekräftelsemejl är på väg. Next-appen har ingen utskicksväg (se
 * lib/actions/demo.ts), och en utlovad bekräftelse som aldrig kommer gör att
 * den som väntar på den inte hör av sig igen. Sätts Cal.com upp sköter deras
 * tjänst både bekräftelse och kalendersynk, och då visas inte det här
 * formuläret alls.
 *
 * ## Progressiv förbättring
 *
 * Fälten är `required` i markup och valideras dessutom på servern. Det första
 * ger omedelbar återkoppling utan JavaScript; det andra är det som faktiskt
 * skyddar, eftersom en klient kan ta bort attributet.
 */
export function BokaDemoFormular({ kalla = "/boka-demo" }: Readonly<{ kalla?: string }>) {
  const [skickar, setSkickar] = useState(false);
  const [klart, setKlart] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  if (klart) {
    return (
      <div
        role="status"
        className="rounded-card border border-moss/25 bg-moss/[0.07] p-8 md:p-10"
      >
        <CheckCircle2 className="h-7 w-7 text-moss" aria-hidden />
        <h2 className="mt-4 font-display text-[1.5rem] font-semibold leading-snug tracking-[-0.02em]">
          Tack, vi har din förfrågan.
        </h2>
        <p className="mt-3 max-w-[52ch] text-[1rem] leading-[1.7] text-ink/75">
          En människa läser den och hör av sig med ett par tider som passar. Är det bråttom går
          det snabbare att mejla oss direkt på{" "}
          <a
            href={`mailto:${KONTAKT_MEJL}`}
            className="underline underline-offset-4 hover:text-ochre"
          >
            {KONTAKT_MEJL}
          </a>
          .
        </p>
      </div>
    );
  }

  return (
    <form
      noValidate={false}
      onSubmit={async (e) => {
        e.preventDefault();
        setSkickar(true);
        setFel(null);
        const svar = await bokaDemo(new FormData(e.currentTarget));
        setSkickar(false);
        if (svar.ok) setKlart(true);
        else setFel(svar.fel ?? "Något gick fel.");
      }}
      className="rounded-card border border-ink/12 bg-paper2/40 p-6 md:p-8"
    >
      <input type="hidden" name="kalla" value={kalla} />

      {/* Honungsfälla. `sr-only` och inte display:none — ett fält som är helt
          borttaget ur layouten fylls inte i av alla robotar, och tabIndex={-1}
          plus autoComplete="off" håller den utanför tangentbordets väg. */}
      <div className="sr-only" aria-hidden>
        <label htmlFor="webbplats">Lämna tomt</label>
        <input id="webbplats" name="webbplats" type="text" tabIndex={-1} autoComplete="off" />
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Falt etikett="Namn" namn="namn" krav autoComplete="name" />
        <Falt etikett="Företag" namn="foretag" autoComplete="organization" />
        <Falt etikett="E-post" namn="epost" typ="email" krav autoComplete="email" />
        <Falt
          etikett="Tid som passar"
          namn="onskad_tid"
          hjalp="Till exempel “tisdag förmiddag”."
        />
      </div>

      <div className="mt-5">
        <label htmlFor="meddelande" className="text-[0.9375rem] font-medium text-ink/75">
          Vad vill ni titta på?
        </label>
        <textarea
          id="meddelande"
          name="meddelande"
          rows={4}
          className="focus-ring mt-2 w-full rounded-input bg-paper px-4 py-3 text-[1rem]"
          placeholder="Vilken agent ni är nyfikna på, och hur ni jobbar i dag."
        />
      </div>

      {fel ? (
        <p role="alert" className="mt-5 text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={skickar}
        className="focus-ring mt-6 inline-flex min-h-12 items-center gap-2 rounded-input bg-ink px-7 text-[1rem] font-semibold text-paper transition-colors hover:bg-ink2 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {skickar ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
        Skicka förfrågan
      </button>

      <p className="mt-4 max-w-[52ch] text-[0.8125rem] leading-[1.6] text-ink/50">
        Vi använder uppgifterna för att kontakta dig om demon, ingenting annat. Läs mer i{" "}
        <a href="/integritetspolicy" className="underline underline-offset-4 hover:text-ochre">
          integritetspolicyn
        </a>
        .
      </p>
    </form>
  );
}

function Falt({
  etikett,
  namn,
  typ = "text",
  krav = false,
  hjalp,
  autoComplete
}: Readonly<{
  etikett: string;
  namn: string;
  typ?: string;
  krav?: boolean;
  hjalp?: string;
  autoComplete?: string;
}>) {
  const hjalpId = hjalp ? `${namn}-hjalp` : undefined;
  return (
    <div>
      <label htmlFor={namn} className="text-[0.9375rem] font-medium text-ink/75">
        {etikett}
        {krav ? (
          <span className="text-ink/45"> (obligatoriskt)</span>
        ) : (
          <span className="text-ink/45"> (valfritt)</span>
        )}
      </label>
      <input
        id={namn}
        name={namn}
        type={typ}
        required={krav}
        autoComplete={autoComplete}
        aria-describedby={hjalpId}
        className="focus-ring mt-2 min-h-12 w-full rounded-input bg-paper px-4 text-[1rem]"
      />
      {hjalp ? (
        <p id={hjalpId} className="mt-1.5 text-[0.8125rem] text-ink/50">
          {hjalp}
        </p>
      ) : null}
    </div>
  );
}
