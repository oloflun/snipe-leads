"use client";

import { Check } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { btnPrimary } from "@/components/ui";
import { TOM_PROFIL, useProfil, type Profil } from "@/lib/profil";

/**
 * Företagsprofilen. Tre saker läser den: SIE-exportens filhuvud
 * (företagsnamn + orgnr), assistentens sammanhang, och hälsningen på
 * Översikt. Den sparas i den här webbläsaren — sajten har inga konton ännu,
 * och det står ärligt i vyn i stället för att låtsas vara ett moln.
 */

const FALT: Array<{
  nyckel: keyof Profil;
  etikett: string;
  hjalp: string;
  placeholder: string;
  flerRader?: boolean;
}> = [
  {
    nyckel: "foretagsnamn",
    etikett: "Företagsnamn",
    hjalp: "Hamnar i SIE-exportens filhuvud och i assistentens sammanhang.",
    placeholder: "Eknäs Bygg Gruppen AB"
  },
  {
    nyckel: "orgnr",
    etikett: "Organisationsnummer",
    hjalp: "Skrivs in i SIE-filen så att bokföringsprogrammet vet vems siffror det är.",
    placeholder: "556677-8890"
  },
  {
    nyckel: "webbplats",
    etikett: "Webbplats",
    hjalp: "Hjälper assistenten att förstå vad företaget gör.",
    placeholder: "https://www.exempel.se"
  },
  {
    nyckel: "beskrivning",
    etikett: "Om verksamheten",
    hjalp: "Ett par meningar räcker: vad ni säljer, till vem. Assistenten riktar svaren efter det.",
    placeholder: "Byggfirma med fem anställda. Mest ROT-jobb åt privatpersoner i Uppsala.",
    flerRader: true
  }
];

export function InstallningarVy() {
  const { profil, sattProfil, laddad } = useProfil();
  const [utkast, setUtkast] = useState<Profil>(TOM_PROFIL);
  const [sparat, setSparat] = useState(false);

  // Formuläret speglar den sparade profilen först när den faktiskt lästs —
  // annars skriver ett tomt förstavärde över det kunden redan fyllt i.
  useEffect(() => {
    if (laddad) setUtkast(profil);
  }, [laddad, profil]);

  function spara(e: React.FormEvent) {
    e.preventDefault();
    sattProfil({
      foretagsnamn: utkast.foretagsnamn.trim(),
      orgnr: utkast.orgnr.trim(),
      webbplats: utkast.webbplats.trim(),
      beskrivning: utkast.beskrivning.trim()
    });
    setSparat(true);
  }

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Inställningar"
        beskrivning="Berätta vems bokföring det här är. Uppgifterna används i SIE-exporten och ger assistenten sammanhang om företaget."
      />

      <form onSubmit={spara} className="max-w-[38rem] space-y-6">
        {FALT.map(({ nyckel, etikett, hjalp, placeholder, flerRader }) => (
          <label key={nyckel} className="block">
            <span className="text-[0.875rem] font-medium text-ink">{etikett}</span>
            {flerRader ? (
              <textarea
                value={utkast[nyckel]}
                onChange={(e) => {
                  setUtkast({ ...utkast, [nyckel]: e.target.value });
                  setSparat(false);
                }}
                placeholder={placeholder}
                rows={3}
                className="focus-ring mt-1.5 w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6 placeholder:text-ink/35"
              />
            ) : (
              <input
                value={utkast[nyckel]}
                onChange={(e) => {
                  setUtkast({ ...utkast, [nyckel]: e.target.value });
                  setSparat(false);
                }}
                placeholder={placeholder}
                className="focus-ring mt-1.5 h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] placeholder:text-ink/35"
              />
            )}
            <span className="mt-1 block text-[0.8125rem] leading-5 text-ink/50">{hjalp}</span>
          </label>
        ))}

        <div className="flex items-center gap-3 border-t border-ink/15 pt-5">
          <button type="submit" className={btnPrimary}>
            Spara profilen
          </button>
          {sparat ? (
            <span role="status" className="flex items-center gap-1.5 text-[0.875rem] text-moss">
              <Check className="h-4 w-4" aria-hidden />
              Sparat
            </span>
          ) : null}
        </div>
      </form>

      <section className="max-w-[38rem]">
        <h2 className="font-display text-[1.25rem]">Var uppgifterna bor</h2>
        <p className="mt-2 text-[0.9375rem] leading-6 text-ink/62">
          Profilen sparas i den här webbläsaren. Dina underlag och siffror ligger hos Snajp och
          raderas när du rensar en period under PDF-filer — originalfilerna sparas aldrig, bara
          de avlästa fälten.
        </p>
      </section>
    </div>
  );
}
