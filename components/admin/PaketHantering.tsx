"use client";

import { useEffect, useState, useTransition } from "react";
import { ChevronDown } from "lucide-react";

import { Tillaggsvaljare } from "@/components/admin/Tillaggsvaljare";
import {
  Badge,
  Cell,
  Sektion,
  Tabell,
  btnBase,
  btnLiten,
  btnSecondary,
  meta,
  tabellRad
} from "@/components/ui";
import { hamtaTillagg } from "@/lib/actions/tillagg";
import { bytPaket } from "@/lib/actions/paket";
import { sattKundStatus, type Kundstatus } from "@/lib/actions/kundstatus";
import type { TenantRow } from "@/lib/data/admin";
import { paketForProdukter } from "@/lib/paket";
import { PAKET, formateraPris, type Paket } from "@/lib/pricing";
import { cn } from "@/lib/utils";

/**
 * Fliken Paket: kundens paket, tillval och kontoläge på EN rad per kund.
 *
 * ## Varför en egen flik när kundprofilen redan har tillägg
 *
 * Kundprofilen är innehållsytan (instruktioner, ton, röst) med tilläggen som
 * bihang. Paketfrågan är en annan syssla: "vad betalar kunden för, och ska
 * det ändras?" ställs över ALLA kunder, inte inne i en enskild profil. Raden
 * expanderas på plats i stället för att länka vidare, så ett paketbyte och en
 * paus är två klick, inte en navigering.
 *
 * ## Tvåstegsmönstren
 *
 * Paketbyte och avslut/paus bekräftas i två steg (samma mönster som
 * Avstangning): valet öppnar en panel som säger exakt vad som händer, och
 * först den namngivna knappen skriver. Återaktivering är ETT klick utan
 * panel, med samma motivering som där: den öppnar, raderar inget och är
 * själv ångervägen.
 *
 * ## Tilläggen laddas vid expandering
 *
 * `hamtaTillagg` är en databasrundtur per kund. Att hämta den för varje rad
 * vid sidladdning hade gjort fliken långsam i proportion till kundlistan;
 * vid expandering kostar den bara för kunden någon faktiskt tittar på.
 */

const STATUS_VISNING: Record<
  Kundstatus,
  { text: string; tone: "good" | "warn" | "danger" }
> = {
  aktiv: { text: "Aktiv", tone: "good" },
  pausad: { text: "Pausad", tone: "warn" },
  avstangd: { text: "Avstängd", tone: "danger" }
};

/** Radens läge: backendens status, eller härlett ur active för äldre svar. */
function statusForRad(rad: TenantRow): Kundstatus {
  if (rad.status === "aktiv" || rad.status === "pausad" || rad.status === "avstangd") {
    return rad.status;
  }
  return rad.active === false ? "avstangd" : "aktiv";
}

function prisText(paket: Paket | null): string {
  if (!paket) return "";
  return paket.prisPerManad === null
    ? "Pris på förfrågan"
    : `${formateraPris(paket.prisPerManad)}/mån`;
}

export function PaketHantering({ tenants }: Readonly<{ tenants: TenantRow[] }>) {
  const [oppen, setOppen] = useState<string | null>(null);

  const rader = [...tenants].sort((a, b) => a.name.localeCompare(b.name, "sv"));

  return (
    <Tabell
      ariaLabel="Kundernas paket och kontoläge"
      minBredd={760}
      kolumner={[
        { rubrik: "Kund", bredd: "26%" },
        { rubrik: "Paket", bredd: "18%" },
        { rubrik: "Pris", bredd: "13%", hoger: true },
        { rubrik: "Status", bredd: "13%" },
        { rubrik: "Avtal", bredd: "18%" },
        { rubrik: "Hantera", bredd: "12%", hoger: true, srOnly: true }
      ]}
    >
      {rader.map((rad) => (
        <KundRad
          key={rad.id}
          rad={rad}
          oppen={oppen === rad.id}
          onToggle={() => setOppen(oppen === rad.id ? null : rad.id)}
        />
      ))}
    </Tabell>
  );
}

function KundRad({
  rad,
  oppen,
  onToggle
}: Readonly<{ rad: TenantRow; oppen: boolean; onToggle: () => void }>) {
  const status = statusForRad(rad);
  const paket = paketForProdukter(rad.products);
  const visning = STATUS_VISNING[status];

  return (
    <>
      <tr className={tabellRad}>
        <Cell titel>
          <span className="block truncate font-medium">{rad.name}</span>
          {rad.slug ? <span className={cn(meta, "block truncate")}>{rad.slug}</span> : null}
        </Cell>
        <Cell>
          {paket ? (
            paket.namn
          ) : rad.products && rad.products.length > 0 ? (
            <span className={meta}>Eget urval: {rad.products.join(", ")}</span>
          ) : (
            <span className={meta}>Ingen arbetsyta</span>
          )}
        </Cell>
        <Cell hoger>{prisText(paket)}</Cell>
        <Cell>
          <Badge tone={visning.tone}>{visning.text}</Badge>
        </Cell>
        <Cell>
          {rad.avtal_signerat ? (
            `Avtal ${String(rad.avtal_signerat).slice(0, 10)}`
          ) : rad.trial_slut ? (
            <span className={meta}>Trial till {String(rad.trial_slut).slice(0, 10)}</span>
          ) : (
            <span className={meta}>Inget avtal</span>
          )}
        </Cell>
        <Cell hoger>
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={oppen}
            className={cn(btnSecondary, btnLiten)}
          >
            Hantera
            <ChevronDown
              className={cn("h-4 w-4 transition-transform", oppen && "rotate-180")}
              aria-hidden
            />
          </button>
        </Cell>
      </tr>
      {oppen ? (
        <tr>
          <td colSpan={6} className="bg-paper2/40 px-5 pb-10 pt-2">
            <Paketval tenantId={rad.id} namn={rad.name} nuvarande={paket} harArbetsyta={rad.products != null} />
            <TillaggPanel tenantId={rad.id} />
            <Kontolage tenantId={rad.id} namn={rad.name} status={status} />
          </td>
        </tr>
      ) : null}
    </>
  );
}

function Paketval({
  tenantId,
  namn,
  nuvarande,
  harArbetsyta
}: Readonly<{ tenantId: string; namn: string; nuvarande: Paket | null; harArbetsyta: boolean }>) {
  const [aktuellt, setAktuellt] = useState<Paket | null>(nuvarande);
  const [valt, setValt] = useState<Paket["id"] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [kvitto, setKvitto] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const kandidat = valt ? PAKET.find((p) => p.id === valt) : undefined;

  const skriv = () => {
    if (!kandidat) return;
    start(async () => {
      setFel(null);
      setKvitto(null);
      const svar = await bytPaket(tenantId, kandidat.id);
      if (!svar.success) {
        setFel(svar.error ?? "Paketet kunde inte bytas.");
        return;
      }
      setAktuellt(paketForProdukter(svar.products) ?? kandidat);
      setValt(null);
      setKvitto(`${namn} har nu ${kandidat.namn}. Kundens meny och vyer följer direkt.`);
    });
  };

  return (
    <Sektion title="Paket">
      {!harArbetsyta ? (
        <p className={cn(meta, "max-w-[70ch]")}>
          Kunden har ingen kopplad arbetsyta, så det finns inget paket att byta här.
        </p>
      ) : (
        <>
          <div className="divide-y divide-ink/12 border-y border-ink/15">
            {PAKET.map((paket) => {
              const arAktuellt = aktuellt?.id === paket.id;
              const arValt = valt === paket.id;
              return (
                <button
                  key={paket.id}
                  type="button"
                  aria-pressed={arValt || (valt === null && arAktuellt)}
                  onClick={() => {
                    setValt(arAktuellt ? null : paket.id);
                    setFel(null);
                    setKvitto(null);
                  }}
                  className={cn(
                    "focus-ring flex w-full flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-2 py-3.5 text-left transition-colors",
                    arValt ? "bg-ochre/10" : "hover:bg-paper2"
                  )}
                >
                  <span className="flex min-w-0 items-baseline gap-3">
                    <span className="font-medium">{paket.namn}</span>
                    {arAktuellt ? <Badge tone="neutral">Nuvarande</Badge> : null}
                    {arValt && !arAktuellt ? <Badge tone="warn">Valt</Badge> : null}
                  </span>
                  <span className="num shrink-0 text-[0.9375rem] text-ink-muted">
                    {paket.prisPerManad === null
                      ? "Pris på förfrågan"
                      : `${formateraPris(paket.prisPerManad)}/mån`}
                  </span>
                </button>
              );
            })}
          </div>

          {kandidat && kandidat.id !== aktuellt?.id ? (
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={pending}
                onClick={skriv}
                className={`${btnBase} bg-ink text-paper hover:bg-ink2`}
              >
                {pending ? "Byter paket …" : `Byt till ${kandidat.namn}`}
              </button>
              <button
                type="button"
                disabled={pending}
                onClick={() => setValt(null)}
                className={btnSecondary}
              >
                Avbryt
              </button>
              <p className={cn(meta, "basis-full")}>
                Bytet gäller direkt: vyer utanför det nya paketet försvinner ur kundens meny,
                och faktureringen är manuell så nästa faktura skrivs efter det nya paketet.
              </p>
            </div>
          ) : null}
        </>
      )}

      {fel ? (
        <p role="alert" className="mt-5 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}
      {kvitto && !fel ? (
        <p role="status" className="mt-5 text-[0.9375rem] text-moss">
          {kvitto}
        </p>
      ) : null}
    </Sektion>
  );
}

function TillaggPanel({ tenantId }: Readonly<{ tenantId: string }>) {
  const [laddat, setLaddat] = useState<{
    addons: Parameters<typeof Tillaggsvaljare>[0]["initialaAddons"];
    lasfel?: string;
    migrationSaknas?: boolean;
  } | null>(null);
  const [laddar, setLaddar] = useState(true);

  useEffect(() => {
    let avbruten = false;
    void hamtaTillagg(tenantId).then((svar) => {
      if (avbruten) return;
      setLaddat({
        addons: svar.addons ?? [],
        lasfel: svar.error,
        migrationSaknas: svar.migrationSaknas
      });
      setLaddar(false);
    });
    return () => {
      avbruten = true;
    };
  }, [tenantId]);

  if (laddar || !laddat) {
    return (
      <Sektion title="Tillägg">
        <p className={meta}>Hämtar tilläggen …</p>
      </Sektion>
    );
  }

  return (
    <Tillaggsvaljare
      tenantId={tenantId}
      initialaAddons={laddat.addons}
      lasfel={laddat.lasfel}
      migrationSaknas={laddat.migrationSaknas}
    />
  );
}

function Kontolage({
  tenantId,
  namn,
  status
}: Readonly<{ tenantId: string; namn: string; status: Kundstatus }>) {
  const [lage, setLage] = useState<Kundstatus>(status);
  const [bekraftar, setBekraftar] = useState<"pausad" | "avstangd" | null>(null);
  const [orsak, setOrsak] = useState("");
  const [fel, setFel] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const skriv = (nytt: Kundstatus, orsakstext: string) => {
    start(async () => {
      setFel(null);
      const svar = await sattKundStatus(tenantId, nytt, orsakstext);
      if (svar.error) {
        setFel(svar.error);
        return;
      }
      setLage(svar.status ?? nytt);
      setBekraftar(null);
      setOrsak("");
    });
  };

  return (
    <Sektion title="Kontoläge">
      {lage === "aktiv" ? (
        <p className="max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
          Kontot är öppet: agenterna, arbetsytan och den publika chatten svarar.
        </p>
      ) : lage === "pausad" ? (
        <p className="max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
          Kontot är pausat: nycklarna avvisas och inget svarar, men allt står orört
          och väntar. Att öppna igen är ett klick.
        </p>
      ) : (
        <p className="max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
          Kontot är avslutat: nycklarna avvisas och inget svarar. Ingenting är
          raderat, så en återaktivering öppnar allt igen.
        </p>
      )}

      {bekraftar ? (
        <div
          className={cn(
            "mt-6 max-w-[70ch] rounded-input border p-5",
            bekraftar === "avstangd" ? "border-danger/40 bg-danger/5" : "border-copper/40 bg-copper/5"
          )}
        >
          <p className="text-[0.9375rem] leading-7 text-ink">
            {bekraftar === "pausad"
              ? "Pausen låser ute alla agenter, arbetsytan, portalen och chatten i samma ögonblick. Ingenting raderas, och kontot öppnas igen med ett klick här."
              : "Avslutet låser ute alla agenter, arbetsytan, portalen och chatten i samma ögonblick. Ingenting raderas, men läget är tänkt som ett avslut, inte en paus."}
          </p>
          <label className="mt-4 block text-[13px] font-medium text-ink">
            Orsak, hamnar i händelseloggen
            <input
              type="text"
              value={orsak}
              onChange={(event) => setOrsak(event.target.value)}
              placeholder={
                bekraftar === "pausad" ? "Kunden vill pausa över sommaren." : "Kunden har sagt upp avtalet."
              }
              maxLength={500}
              className="focus-ring mt-1.5 block w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[0.9375rem]"
            />
          </label>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={pending || !orsak.trim()}
              onClick={() => skriv(bekraftar, orsak)}
              className={cn(
                btnBase,
                bekraftar === "avstangd"
                  ? "bg-danger text-paper hover:bg-danger/90"
                  : "bg-ink text-paper hover:bg-ink2"
              )}
            >
              {pending
                ? bekraftar === "pausad"
                  ? "Pausar …"
                  : "Avslutar …"
                : bekraftar === "pausad"
                  ? `Pausa ${namn}`
                  : `Avsluta ${namn}`}
            </button>
            <button
              type="button"
              disabled={pending}
              onClick={() => {
                setBekraftar(null);
                setFel(null);
              }}
              className={btnSecondary}
            >
              Avbryt
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-6 flex flex-wrap gap-3">
          {lage === "aktiv" ? (
            <>
              <button type="button" onClick={() => setBekraftar("pausad")} className={btnSecondary}>
                Pausa kontot …
              </button>
              <button
                type="button"
                onClick={() => setBekraftar("avstangd")}
                className={`${btnSecondary} !text-danger hover:!bg-danger/10`}
              >
                Avsluta kontot …
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                disabled={pending}
                onClick={() =>
                  skriv(
                    "aktiv",
                    lage === "pausad" ? "Pausen hävd från paketfliken." : "Återaktiverad från paketfliken."
                  )
                }
                className={btnSecondary}
              >
                {pending ? "Öppnar …" : "Öppna kontot igen"}
              </button>
              {lage === "pausad" ? (
                <button
                  type="button"
                  onClick={() => setBekraftar("avstangd")}
                  className={`${btnSecondary} !text-danger hover:!bg-danger/10`}
                >
                  Avsluta kontot …
                </button>
              ) : null}
            </>
          )}
        </div>
      )}

      {fel ? (
        <p
          role="alert"
          className="mt-4 max-w-[70ch] rounded-input bg-danger/10 px-4 py-3 text-[0.875rem] text-danger"
        >
          {fel}
        </p>
      ) : null}
    </Sektion>
  );
}
