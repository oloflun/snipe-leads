"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useId, useState, useTransition } from "react";
import { btnPrimary, btnSecondary, etikett, meta } from "@/components/ui";
import {
  avaktiveraMedKod,
  avbrytInrullning,
  bekraftaInrullning,
  hamtaTvafaktorStatus,
  paborjaInrullning,
  type TvafaktorFelkod
} from "@/lib/actions/tvafaktor";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Tvåstegsverifiering för plattformsadmin (migration 128, lib/actions/tvafaktor.ts).
 *
 * Fyra lägen: av, inrullning (QR-kod, manuell nyckel och en kod ur appen),
 * återställningskoderna (visas EN gång, direkt efter aktiveringen) och på
 * (avstängning kräver en giltig kod). Valfritt: tvånget är Antons beslut och
 * styrs av `TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN`.
 */

const T = {
  laddar: { sv: "Hämtar läget…", en: "Loading…" },
  ingress: {
    sv: "Ett andra steg vid inloggningen: efter lösenordet anger du en sexsiffrig kod ur en autentiseringsapp (till exempel Microsoft Authenticator, Google Authenticator, 1Password eller Bitwarden).",
    en: "A second step at sign-in: after your password you enter a six-digit code from an authenticator app (for example Microsoft Authenticator, Google Authenticator, 1Password or Bitwarden)."
  },
  kravs: {
    sv: "Tvåstegsverifiering krävs för plattformsadmin. Adminytan öppnas när den är påslagen.",
    en: "Two-step verification is required for platform admins. The admin area opens once it is turned on."
  },
  lage: { sv: "Läge", en: "Status" },
  pa: { sv: "På", en: "On" },
  av: { sv: "Av", en: "Off" },
  slaPa: { sv: "Slå på tvåstegsverifiering", en: "Turn on two-step verification" },
  paborjadIngress: {
    sv: "En inrullning påbörjades men bekräftades inte. Börja om för att få en ny QR-kod.",
    en: "A setup was started but not confirmed. Start over to get a new QR code."
  },
  borjaOm: { sv: "Börja om", en: "Start over" },
  steg1: { sv: "1. Skanna QR-koden med appen", en: "1. Scan the QR code with the app" },
  qrEtikett: { sv: "QR-kod för autentiseringsappen", en: "QR code for the authenticator app" },
  manuellt: { sv: "Går det inte att skanna? Ange nyckeln för hand:", en: "Can't scan it? Enter the key by hand:" },
  steg2: { sv: "2. Ange koden som appen visar", en: "2. Enter the code the app shows" },
  kod: { sv: "Kod", en: "Code" },
  kodHint: { sv: "Sex siffror.", en: "Six digits." },
  bekrafta: { sv: "Bekräfta och slå på", en: "Confirm and turn on" },
  avbryt: { sv: "Avbryt", en: "Cancel" },
  koderRubrik: { sv: "Spara återställningskoderna nu", en: "Save your recovery codes now" },
  koderIngress: {
    sv: "Tvåstegsverifieringen är på. Har du inte telefonen kan du logga in med en av koderna nedan i stället för koden ur appen. Varje kod fungerar en gång. Koderna visas bara nu: spara dem i din lösenordshanterare.",
    en: "Two-step verification is on. If you don't have your phone, you can sign in with one of the codes below instead of the app code. Each code works once. The codes are only shown now: save them in your password manager."
  },
  koderLista: { sv: "Återställningskoder", en: "Recovery codes" },
  kopiera: { sv: "Kopiera koderna", en: "Copy the codes" },
  kopierade: { sv: "Kopierade.", en: "Copied." },
  sparat: { sv: "Jag har sparat koderna", en: "I have saved the codes" },
  aktivIngress: {
    sv: "Inloggningen kräver en kod ur appen, eller en återställningskod, efter lösenordet.",
    en: "Sign-in requires a code from the app, or a recovery code, after the password."
  },
  koderKvar: { sv: "Oanvända återställningskoder", en: "Unused recovery codes" },
  stangAvRubrik: { sv: "Stäng av", en: "Turn off" },
  stangAvIngress: {
    sv: "Ange en kod ur appen eller en återställningskod för att stänga av tvåstegsverifieringen.",
    en: "Enter a code from the app or a recovery code to turn off two-step verification."
  },
  kodEllerAterstallning: { sv: "Kod eller återställningskod", en: "Code or recovery code" },
  stangAv: { sv: "Stäng av tvåstegsverifiering", en: "Turn off two-step verification" },
  avstangd: { sv: "Tvåstegsverifieringen är avstängd.", en: "Two-step verification is turned off." },
  bearbetar: { sv: "Ett ögonblick", en: "One moment" }
} satisfies Record<string, Localized>;

const FEL: Record<TvafaktorFelkod, Localized> = {
  ej_admin: { sv: "Bara plattformsadmin kan ändra det här.", en: "Only platform admins can change this." },
  fel_kod: { sv: "Koden stämmer inte. Kontrollera klockan i telefonen och försök igen.", en: "The code is not correct. Check the clock on your phone and try again." },
  for_manga_forsok: { sv: "För många försök. Vänta några minuter och försök igen.", en: "Too many attempts. Wait a few minutes and try again." },
  redan_aktiv: { sv: "Tvåstegsverifieringen är redan på.", en: "Two-step verification is already on." },
  ingen_inrullning: { sv: "Inrullningen hittades inte. Börja om.", en: "The setup was not found. Start over." },
  fel: { sv: "Något gick fel. Försök igen.", en: "Something went wrong. Try again." }
};

type Lage =
  | { typ: "laddar" }
  | { typ: "fel"; fel: TvafaktorFelkod }
  | { typ: "av"; paborjad: boolean; kravs: boolean }
  | { typ: "inrullning"; hemlighet: string; qr: boolean[][]; kravs: boolean }
  | { typ: "koder"; koder: string[] }
  | { typ: "pa"; koderKvar: number; kravs: boolean };

export function Tvafaktor() {
  const { text } = useLocale();
  const [lage, setLage] = useState<Lage>({ typ: "laddar" });
  const [kod, setKod] = useState("");
  const [fel, setFel] = useState<Localized | null>(null);
  const [besked, setBesked] = useState<Localized | null>(null);
  const [isPending, startTransition] = useTransition();
  const kodId = useId();

  async function lasOm() {
    const status = await hamtaTvafaktorStatus();
    if (!status.ok) {
      setLage({ typ: "fel", fel: status.fel });
      return;
    }
    setLage(
      status.aktiv
        ? { typ: "pa", koderKvar: status.koderKvar, kravs: status.kravs }
        : { typ: "av", paborjad: status.paborjad, kravs: status.kravs }
    );
  }

  useEffect(() => {
    void lasOm();
  }, []);

  function nollstallBesked() {
    setFel(null);
    setBesked(null);
  }

  function borja() {
    nollstallBesked();
    const kravs = lage.typ === "av" ? lage.kravs : false;
    startTransition(async () => {
      const svar = await paborjaInrullning();
      if (!svar.ok) {
        setFel(FEL[svar.fel]);
        return;
      }
      setKod("");
      setLage({ typ: "inrullning", hemlighet: svar.hemlighet, qr: svar.qr, kravs });
    });
  }

  function bekrafta(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    nollstallBesked();
    startTransition(async () => {
      const svar = await bekraftaInrullning(kod);
      if (!svar.ok) {
        setFel(FEL[svar.fel]);
        return;
      }
      setKod("");
      setLage({ typ: "koder", koder: svar.koder });
    });
  }

  function avbryt() {
    nollstallBesked();
    startTransition(async () => {
      await avbrytInrullning();
      setKod("");
      await lasOm();
    });
  }

  function stangAv(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    nollstallBesked();
    startTransition(async () => {
      const svar = await avaktiveraMedKod(kod);
      if (!svar.ok) {
        setFel(FEL[svar.fel]);
        return;
      }
      setKod("");
      await lasOm();
      setBesked(T.avstangd);
    });
  }

  if (lage.typ === "laddar") {
    return (
      <div className="grid gap-6" aria-busy="true">
        <p className="sr-only">{text(T.laddar)}</p>
        <div className="h-20 animate-pulse rounded-card bg-ink/[0.055]" />
        <div className="h-32 animate-pulse rounded-card bg-ink/[0.055]" />
      </div>
    );
  }

  if (lage.typ === "fel") {
    return (
      <p role="alert" className="max-w-[60ch] text-[0.9375rem] text-danger">
        {text(FEL[lage.fel])}
      </p>
    );
  }

  const kravs = "kravs" in lage && lage.kravs;

  return (
    <div className="grid max-w-[44rem] gap-7">
      <p className="max-w-[62ch] text-[0.9375rem] leading-7 text-ink-muted">{text(T.ingress)}</p>
      {kravs && lage.typ !== "pa" ? (
        <p role="status" className="max-w-[62ch] border-l-2 border-ochre pl-4 text-[0.9375rem] text-ink">
          {text(T.kravs)}
        </p>
      ) : null}

      {lage.typ === "av" ? (
        <div className="grid gap-4 border-t border-ink/15 pt-5">
          <p className="text-[0.9375rem]">
            <span className={etikett}>{text(T.lage)}: </span>
            <span className="font-medium text-ink">{text(T.av)}</span>
          </p>
          {lage.paborjad ? <p className={meta}>{text(T.paborjadIngress)}</p> : null}
          <div>
            <button type="button" onClick={borja} disabled={isPending} className={btnPrimary}>
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
              {text(lage.paborjad ? T.borjaOm : T.slaPa)}
            </button>
          </div>
        </div>
      ) : null}

      {lage.typ === "inrullning" ? (
        <form onSubmit={bekrafta} className="grid gap-6 border-t border-ink/15 pt-5" noValidate>
          <section className="grid gap-4">
            <h3 className="text-[1rem] font-semibold text-ink">{text(T.steg1)}</h3>
            <QrKod matris={lage.qr} etikett={text(T.qrEtikett)} />
            <div className="grid gap-2">
              <p className={meta}>{text(T.manuellt)}</p>
              <code className="w-fit select-all break-all rounded-input bg-paper2 px-3 py-2 font-mono text-[0.9375rem] text-ink">
                {lage.hemlighet.replace(/(.{4})/g, "$1 ").trim()}
              </code>
            </div>
          </section>
          <section className="grid gap-3">
            <h3 className="text-[1rem] font-semibold text-ink">{text(T.steg2)}</h3>
            <KodFalt id={kodId} etikett={text(T.kod)} hint={text(T.kodHint)} varde={kod} onChange={setKod} numerisk />
            <div className="flex flex-wrap gap-3">
              <button type="submit" disabled={isPending || kod.trim().length < 6} className={btnPrimary}>
                {isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
                {text(isPending ? T.bearbetar : T.bekrafta)}
              </button>
              <button type="button" onClick={avbryt} disabled={isPending} className={btnSecondary}>
                {text(T.avbryt)}
              </button>
            </div>
          </section>
        </form>
      ) : null}

      {lage.typ === "koder" ? <Aterstallningskoder koder={lage.koder} klar={() => void lasOm()} /> : null}

      {lage.typ === "pa" ? (
        <div className="grid gap-6 border-t border-ink/15 pt-5">
          <div className="grid gap-2">
            <p className="text-[0.9375rem]">
              <span className={etikett}>{text(T.lage)}: </span>
              <span className="font-medium text-moss">{text(T.pa)}</span>
            </p>
            <p className="max-w-[62ch] text-[0.9375rem] text-ink-muted">{text(T.aktivIngress)}</p>
            <p className={meta}>
              {text(T.koderKvar)}: <span className="font-medium text-ink">{lage.koderKvar}</span>
            </p>
          </div>
          <form onSubmit={stangAv} className="grid gap-3 border-t border-ink/15 pt-5" noValidate>
            <h3 className="text-[1rem] font-semibold text-ink">{text(T.stangAvRubrik)}</h3>
            <p className="max-w-[62ch] text-[0.9375rem] text-ink-muted">{text(T.stangAvIngress)}</p>
            <KodFalt id={kodId} etikett={text(T.kodEllerAterstallning)} varde={kod} onChange={setKod} />
            <div>
              <button type="submit" disabled={isPending || kod.trim().length < 6} className={btnSecondary}>
                {isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
                {text(isPending ? T.bearbetar : T.stangAv)}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {fel ? (
        <p role="alert" className="max-w-[60ch] break-words text-[0.9375rem] font-medium text-danger">
          {text(fel)}
        </p>
      ) : null}
      {besked ? (
        <p role="status" className="text-[0.9375rem] font-medium text-moss">
          {text(besked)}
        </p>
      ) : null}
    </div>
  );
}

/** Svart på vitt oavsett tema: en kamera läser inte en inverterad QR-kod. */
function QrKod({ matris, etikett: namn }: Readonly<{ matris: boolean[][]; etikett: string }>) {
  const storlek = matris.length;
  let d = "";
  matris.forEach((rad, y) =>
    rad.forEach((svart, x) => {
      if (svart) d += `M${x} ${y}h1v1h-1z`;
    })
  );
  return (
    <svg
      role="img"
      aria-label={namn}
      viewBox={`0 0 ${storlek} ${storlek}`}
      width={208}
      height={208}
      shapeRendering="crispEdges"
      className="rounded-input border border-ink/15"
    >
      <rect width={storlek} height={storlek} fill="#ffffff" />
      <path d={d} fill="#000000" />
    </svg>
  );
}

function KodFalt({
  id,
  etikett: namn,
  hint,
  varde,
  onChange,
  numerisk = false
}: Readonly<{
  id: string;
  etikett: string;
  hint?: string;
  varde: string;
  onChange: (v: string) => void;
  numerisk?: boolean;
}>) {
  return (
    <div className="grid max-w-xs gap-2">
      <label htmlFor={id} className={etikett}>
        {namn}
      </label>
      {/* 16 px (text-base): under det zoomar iOS Safari in på fältet. */}
      <input
        id={id}
        value={varde}
        onChange={(e) => onChange(e.target.value)}
        autoComplete="one-time-code"
        inputMode={numerisk ? "numeric" : "text"}
        maxLength={numerisk ? 7 : 12}
        spellCheck={false}
        aria-describedby={hint ? `${id}-hint` : undefined}
        className="h-12 w-full rounded-input border border-ink/15 bg-paper2/70 px-4 font-mono text-base text-ink focus:border-ochre"
      />
      {hint ? (
        <p id={`${id}-hint`} className={meta}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}

function Aterstallningskoder({ koder, klar }: Readonly<{ koder: string[]; klar: () => void }>) {
  const { text } = useLocale();
  const [kopierat, setKopierat] = useState(false);

  async function kopiera() {
    try {
      await navigator.clipboard.writeText(koder.join("\n"));
      setKopierat(true);
    } catch {
      setKopierat(false);
    }
  }

  return (
    <section className="grid gap-4 border-t border-ink/15 pt-5" aria-labelledby="tvafaktor-koder">
      <h3 id="tvafaktor-koder" className="text-[1rem] font-semibold text-ink">
        {text(T.koderRubrik)}
      </h3>
      <p className="max-w-[62ch] text-[0.9375rem] leading-7 text-ink-muted">{text(T.koderIngress)}</p>
      <ol
        aria-label={text(T.koderLista)}
        className="grid w-fit grid-cols-1 gap-x-8 gap-y-2 rounded-card border border-ink/15 bg-paper2 px-5 py-4 font-mono text-[0.9375rem] text-ink sm:grid-cols-2"
      >
        {koder.map((k) => (
          <li key={k} className="select-all">
            {k}
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => void kopiera()} className={btnSecondary}>
          {text(T.kopiera)}
        </button>
        <button type="button" onClick={klar} className={cn(btnPrimary)}>
          {text(T.sparat)}
        </button>
        {kopierat ? (
          <p role="status" className="text-[0.875rem] text-moss">
            {text(T.kopierade)}
          </p>
        ) : null}
      </div>
    </section>
  );
}
