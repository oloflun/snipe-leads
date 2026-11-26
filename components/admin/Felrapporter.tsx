"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Badge,
  Rad,
  Radlista,
  Tomt,
  btnLiten,
  btnPrimary,
  btnSecondary,
  chip,
  chipAktiv,
  chipInaktiv,
  chiplista,
  etikett,
  meta,
  rubrikPanel
} from "@/components/ui";
import { ADMIN, a, ordagrant, tidpunkt } from "@/lib/admin/sprak";
import {
  FILTER,
  aktorNyckel,
  antalOppna,
  atgard,
  atgarderFor,
  bildadress,
  ersatt,
  lasBild,
  passarFilter,
  statuskropp,
  synligaArenden,
  validera,
  type AdminArende,
  type AtgardId,
  type Filter,
  type Valideringsfel
} from "@/lib/admin/plattformsarenden";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Locale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Felrapporterna i Fel & eskaleringar (PLAN-HJALPRUTAN-2026-11-25, del 5).
 *
 * Ingen egen panel: listan står i FelOchEskaleringars sektion, under
 * topplistan över fel, med samma radanatomi (rubrik, läge till höger, källa
 * och tid i metaraden) och samma `<details>` för det som fälls ut som
 * Händelselista. Antalet öppna står i panelens rad nyckeltal, inte här.
 *
 * Läses från backendens `GET /api/admin/plattformsarenden` genom adminproxyn;
 * ett lägesbyte är `POST /api/admin/plattformsarenden/{id}/status`, och svaret
 * (hela ärendet med den nya händelsen) ersätter raden. Läget ligger i
 * databasen, så det står kvar efter en omladdning.
 *
 * Kundens text visas här och bara här: plattformsadmin ser rapporten för att
 * kunna rätta felet. Listan bär bara att en bild finns (`har_bild`); bilden
 * själv hämtas för ett ärende i taget när admin trycker Visa bilden
 * (`GET /api/admin/plattformsarenden/{id}/bild`), så att listan aldrig drar
 * flera MB bilder som ingen öppnat.
 */

const LISTA = "/api/admin/plattformsarenden";

type Laddning =
  | { lage: "hamtar" }
  | { lage: "fel"; meddelande: Localized }
  | { lage: "klar"; arenden: AdminArende[] };

async function felmeddelande(svar: Response, reserv: Localized): Promise<Localized> {
  try {
    const kropp = (await readJsonBody<{ error?: unknown; detail?: unknown }>(svar)) ?? {};
    const ord = typeof kropp.error === "string" ? kropp.error : typeof kropp.detail === "string" ? kropp.detail : null;
    return ord ? ordagrant(ord) : reserv;
  } catch {
    return reserv;
  }
}

/** Listans tillstånd. FelOchEskaleringar äger det, så att talet i nyckeltalsraden och listan läser samma svar. */
export function useFelrapporter() {
  const [laddning, setLaddning] = useState<Laddning>({ lage: "hamtar" });

  const hamta = useCallback(async () => {
    setLaddning({ lage: "hamtar" });
    try {
      const svar = await fetch(LISTA, { cache: "no-store" });
      if (!svar.ok) {
        setLaddning({ lage: "fel", meddelande: await felmeddelande(svar, ADMIN.frKundeInteHamta) });
        return;
      }
      const kropp = await readJsonBody<{ arenden?: AdminArende[] }>(svar);
      setLaddning({ lage: "klar", arenden: Array.isArray(kropp?.arenden) ? kropp.arenden : [] });
    } catch {
      setLaddning({ lage: "fel", meddelande: ADMIN.frKundeInteHamta });
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  const uppdatera = useCallback((nytt: AdminArende) => {
    setLaddning((forra) => (forra.lage === "klar" ? { lage: "klar", arenden: ersatt(forra.arenden, nytt) } : forra));
  }, []);

  const oppna = laddning.lage === "klar" ? antalOppna(laddning.arenden) : null;
  return { laddning, hamta, uppdatera, oppna };
}

export type FelrapportState = ReturnType<typeof useFelrapporter>;

/**
 * Ett internt värde ur ärendet (läge, vy, roll, händelsetyp, aktör) med
 * adminytans ord. Ett okänt värde visas som det kom, hellre än inte alls.
 */
function dataetikett(prefix: "frStatus_" | "frVy_" | "frRoll_" | "frTyp_" | "frAktor_", varde: string, locale: Locale): string {
  const nyckel = `${prefix}${varde}`;
  return nyckel in ADMIN ? a(nyckel, locale) : varde;
}

function statusetikett(status: string, locale: Locale): string {
  return dataetikett("frStatus_", status, locale);
}

function ton(arende: AdminArende): "neutral" | "good" | "warn" | "danger" {
  if (arende.status === "mottagen" || arende.status === "kund_godkand") return "warn";
  if (arende.status === "i_main") return "good";
  return "neutral";
}

const VALIDERINGSTEXT: Record<Valideringsfel, Localized> = {
  meddelandeKravs: ADMIN.frMeddelandeKravs,
  adressKravs: ADMIN.frAdressKravs,
  adressOgiltig: ADMIN.frAdressOgiltig
};

const falt =
  "focus-ring w-full rounded-input border border-ink/15 bg-paper px-2.5 py-2 text-[1rem] text-ink hover:border-ink/30 [@media(pointer:fine)]:text-[0.875rem]";

export function Felrapporter({ state }: Readonly<{ state: FelrapportState }>) {
  const { locale, text } = useLocale();
  const [filter, setFilter] = useState<Filter>("oppna");
  // Ärenden admin bytt läge på under det här filtret: de står kvar tills filtret byts.
  const [kvar, setKvar] = useState<ReadonlySet<string>>(() => new Set());
  const { laddning, hamta, uppdatera: uppdateraLista } = state;
  const uppdatera = useCallback(
    (nytt: AdminArende) => {
      setKvar((forra) => new Set(forra).add(nytt.id));
      uppdateraLista(nytt);
    },
    [uppdateraLista]
  );

  return (
    <div className="mt-6 min-w-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <h3 id="kunder-felrapporter" className={rubrikPanel}>
          {a("frRubrik", locale)}
        </h3>
        <div role="group" aria-label={a("frFilter", locale)} className={chiplista}>
          {FILTER.map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={filter === f}
              onClick={() => {
                setFilter(f);
                setKvar(new Set());
              }}
              className={cn(chip, filter === f ? chipAktiv : chipInaktiv)}
            >
              {a(`frFilter_${f}`, locale)}
            </button>
          ))}
        </div>
      </div>

      {laddning.lage === "hamtar" ? (
        <p className={cn(meta, "mt-3")} role="status">
          {a("frHamtar", locale)}
        </p>
      ) : laddning.lage === "fel" ? (
        <div className="mt-3" role="alert">
          <Tomt
            action={
              <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, btnLiten)}>
                {a("frForsokIgen", locale)}
              </button>
            }
          >
            {text(laddning.meddelande)}
          </Tomt>
        </div>
      ) : (
        <Lista arenden={laddning.arenden} filter={filter} kvar={kvar} uppdatera={uppdatera} />
      )}
    </div>
  );
}

function Lista({
  arenden,
  filter,
  kvar,
  uppdatera
}: Readonly<{
  arenden: AdminArende[];
  filter: Filter;
  kvar: ReadonlySet<string>;
  uppdatera: (nytt: AdminArende) => void;
}>) {
  const { locale } = useLocale();
  const synliga = synligaArenden(arenden, filter, kvar);

  if (synliga.length === 0) {
    return (
      <div className="mt-3">
        <Tomt>{a(arenden.length === 0 ? "frTomt" : "frTomtFilter", locale)}</Tomt>
      </div>
    );
  }

  return (
    <Radlista className="mt-3" ariaLabel={a("frRubrik", locale)}>
      {synliga.map((x) => (
        <Rad key={x.id} className="min-w-0">
          <Arenderad arende={x} utanforFilter={!passarFilter(x.status, filter)} uppdatera={uppdatera} />
        </Rad>
      ))}
    </Radlista>
  );
}

function Arenderad({
  arende,
  utanforFilter,
  uppdatera
}: Readonly<{ arende: AdminArende; utanforFilter: boolean; uppdatera: (nytt: AdminArende) => void }>) {
  const { locale } = useLocale();

  return (
    <details className="group min-w-0">
      <summary className="focus-ring -mx-1 block cursor-pointer list-none rounded-input px-1 [&::-webkit-details-marker]:hidden">
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-6 gap-y-1">
          <h4 className={cn(rubrikPanel, "min-w-0 break-words")}>
            <span className="num">{arende.nummer}</span>
            <span className="font-normal text-ink-muted"> · </span>
            <span className="break-all font-mono text-[0.9375rem] font-normal">{arende.sida}</span>
          </h4>
          <span className="flex shrink-0 flex-wrap items-center gap-1.5">
            {arende.besok_av_admin ? <Badge tone="danger">{a("frBesokAvAdmin", locale)}</Badge> : null}
            <Badge tone={ton(arende)}>{statusetikett(arende.status, locale)}</Badge>
          </span>
        </div>
        <p className={cn(meta, "num mt-1 break-words")}>
          {arende.kund_tenant_slug} · {tidpunkt(arende.created_at, locale)}
          {arende.updated_at && arende.updated_at !== arende.created_at ? (
            <>
              {" · "}
              {statusetikett(arende.status, locale)} {tidpunkt(arende.updated_at, locale)}
            </>
          ) : null}
        </p>
        {utanforFilter ? (
          <p className={cn(meta, "mt-1")} role="status">
            {a("frAndradDoljs", locale)}
          </p>
        ) : null}
      </summary>

      <div className="mt-3 grid min-w-0 gap-4">
        <dl className="grid min-w-0 gap-3">
          {(
            [
              ["frGjorde", arende.gjorde],
              ["frHande", arende.hande],
              ["frVantade", arende.vantade]
            ] as const
          ).map(([nyckel, varde]) => (
            <div key={nyckel} className="min-w-0">
              <dt className={etikett}>{a(nyckel, locale)}</dt>
              <dd className="mt-0.5 whitespace-pre-wrap break-words text-[0.9375rem] text-ink">{varde}</dd>
            </div>
          ))}
        </dl>

        {arende.har_bild ? <Bild arendeId={arende.id} /> : null}

        <dl className="grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-4">
          {(
            [
              ["frRapportor", arende.rapportor_namn ?? arende.rapportor_user_id],
              ["frArbetsyta", arende.kund_tenant_slug],
              ["frVy", dataetikett("frVy_", arende.vy, locale)],
              ["frRoll", dataetikett("frRoll_", arende.roll, locale)]
            ] as const
          ).map(([nyckel, varde]) => (
            <div key={nyckel} className="min-w-0">
              <dt className={etikett}>{a(nyckel, locale)}</dt>
              <dd className="mt-0.5 break-words text-[0.875rem] text-ink">{varde}</dd>
            </div>
          ))}
        </dl>

        {arende.testversion_url ? (
          <p>
            <a
              href={arende.testversion_url}
              target="_blank"
              rel="noopener noreferrer"
              className="focus-ring rounded-input text-[0.875rem] font-medium underline underline-offset-4 hover:text-ochre"
            >
              {a("frTestversion", locale)}
            </a>
          </p>
        ) : null}

        <Handelsekedja arende={arende} />
        <Lagesbyte arende={arende} uppdatera={uppdatera} />
      </div>
    </details>
  );
}

type Bildlage =
  | { lage: "dold" }
  | { lage: "hamtar" }
  | { lage: "fel"; meddelande: Localized }
  | { lage: "klar"; url: string };

/**
 * Kundens bild, på begäran. Hämtas först när admin trycker, en gång per
 * öppning av sidan; svaret är `no-store` och sparas bara i komponentens
 * tillstånd. Bara de fyra format inlämningen tillåter visas (`lasBild`).
 */
function Bild({ arendeId }: Readonly<{ arendeId: string }>) {
  const { locale, text } = useLocale();
  const [bild, setBild] = useState<Bildlage>({ lage: "dold" });

  async function hamtaBild() {
    setBild({ lage: "hamtar" });
    try {
      const svar = await fetch(bildadress(arendeId), { cache: "no-store" });
      if (!svar.ok) {
        setBild({ lage: "fel", meddelande: svar.status === 415 ? ADMIN.frBildFormat : ADMIN.frBildKundeInteHamta });
        return;
      }
      const url = lasBild(await readJsonBody<unknown>(svar));
      setBild(url ? { lage: "klar", url } : { lage: "fel", meddelande: ADMIN.frBildFormat });
    } catch {
      setBild({ lage: "fel", meddelande: ADMIN.frBildKundeInteHamta });
    }
  }

  return (
    <div className="min-w-0">
      <p className={etikett}>{a("frBild", locale)}</p>
      {bild.lage === "klar" ? (
        // <img> och inte next/image: en data-URL ur backenden, inget att optimera.
        <img
          src={bild.url}
          alt={a("frBildAlt", locale)}
          className="mt-1 max-h-80 max-w-full rounded-input border border-ink/12"
        />
      ) : bild.lage === "hamtar" ? (
        <p className={cn(meta, "mt-0.5")} role="status">
          {a("frHamtarBild", locale)}
        </p>
      ) : bild.lage === "fel" ? (
        <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5" role="alert">
          <p className="text-[0.875rem] text-danger">{text(bild.meddelande)}</p>
          <button type="button" onClick={() => void hamtaBild()} className={cn(btnSecondary, btnLiten)}>
            {a("frForsokIgen", locale)}
          </button>
        </div>
      ) : (
        <button type="button" onClick={() => void hamtaBild()} className={cn(btnSecondary, btnLiten, "mt-1")}>
          {a("frVisaBild", locale)}
        </button>
      )}
    </div>
  );
}

function Handelsekedja({ arende }: Readonly<{ arende: AdminArende }>) {
  const { locale } = useLocale();
  if (arende.handelser.length === 0) return null;
  const handelser = [...arende.handelser].sort((x, y) => x.tid.localeCompare(y.tid));
  return (
    <div className="min-w-0">
      <p className={etikett}>{a("frHandelser", locale)}</p>
      <ol className="mt-1 divide-y divide-ink/10 border-y border-ink/10">
        {handelser.map((h, i) => (
          <li key={`${h.tid}-${i}`} className="flex min-w-0 flex-wrap items-start justify-between gap-x-4 gap-y-1 py-2">
            <div className="min-w-0">
              <p className="text-[0.875rem] text-ink">
                {h.status ? statusetikett(h.status, locale) : dataetikett("frTyp_", h.typ, locale)}
              </p>
              {h.meddelande ? (
                <p className="mt-0.5 whitespace-pre-wrap break-words text-[0.875rem] text-ink-muted">{h.meddelande}</p>
              ) : null}
              <p className={cn(meta, "num mt-0.5")}>
                {tidpunkt(h.tid, locale)}
                {h.aktor ? ` · ${dataetikett("frAktor_", aktorNyckel(h.aktor), locale)}` : ""}
              </p>
            </div>
            <Badge tone={h.synlig_for_kund ? "good" : "neutral"}>
              {a(h.synlig_for_kund ? "frKundenSer" : "frBaraSnajp", locale)}
            </Badge>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Lagesbyte({ arende, uppdatera }: Readonly<{ arende: AdminArende; uppdatera: (nytt: AdminArende) => void }>) {
  const { locale, text } = useLocale();
  const [vald, setVald] = useState<AtgardId | null>(null);
  const [meddelande, setMeddelande] = useState("");
  const [adress, setAdress] = useState(arende.testversion_url ?? "");
  const [sparar, setSparar] = useState(false);
  const [fel, setFel] = useState<Localized | null>(null);

  const valdAtgard = vald ? atgard(vald) : null;
  const idMeddelande = `fr-meddelande-${arende.id}`;
  const idAdress = `fr-adress-${arende.id}`;
  const idFel = `fr-fel-${arende.id}`;

  async function skicka(event: React.FormEvent) {
    event.preventDefault();
    if (!valdAtgard) return;
    const ogiltigt = validera(valdAtgard, meddelande, adress);
    if (ogiltigt) {
      setFel(VALIDERINGSTEXT[ogiltigt]);
      return;
    }
    setSparar(true);
    setFel(null);
    try {
      const svar = await fetch(`${LISTA}/${encodeURIComponent(arende.id)}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(statuskropp(valdAtgard, meddelande, adress))
      });
      if (!svar.ok) {
        setFel(await felmeddelande(svar, ADMIN.frKundeInteSpara));
        return;
      }
      const nytt = await readJsonBody<AdminArende>(svar);
      if (!nytt) {
        setFel(ADMIN.frKundeInteSpara);
        return;
      }
      uppdatera(nytt);
      setVald(null);
      setMeddelande("");
    } catch {
      setFel(ADMIN.frKundeInteSpara);
    } finally {
      setSparar(false);
    }
  }

  return (
    <form onSubmit={skicka} className="min-w-0 border-t border-ink/10 pt-3" noValidate>
      <fieldset className="min-w-0">
        <legend className={etikett}>{a("frValjLage", locale)}</legend>
        <div className={cn(chiplista, "mt-1.5")}>
          {atgarderFor(arende.status).map((x) => (
            <button
              key={x.id}
              type="button"
              aria-pressed={vald === x.id}
              onClick={() => {
                setVald(vald === x.id ? null : x.id);
                setFel(null);
              }}
              className={cn(chip, "border border-ink/12", vald === x.id ? chipAktiv : chipInaktiv)}
            >
              {a(`frAtgard_${x.id}`, locale)}
            </button>
          ))}
        </div>
      </fieldset>

      {valdAtgard ? (
        <div className="mt-3 grid min-w-0 gap-3">
          {valdAtgard.kraverAdress ? (
            <div className="min-w-0">
              <label htmlFor={idAdress} className={etikett}>
                {a("frTestadress", locale)}
              </label>
              <input
                id={idAdress}
                type="url"
                inputMode="url"
                required
                value={adress}
                onChange={(e) => setAdress(e.target.value)}
                aria-describedby={fel ? idFel : undefined}
                placeholder="https://"
                className={cn(falt, "mt-1 h-9 py-0")}
              />
            </div>
          ) : null}
          <div className="min-w-0">
            <label htmlFor={idMeddelande} className={etikett}>
              {a(valdAtgard.kraverMeddelande ? "frMeddelande" : "frMeddelandeValfritt", locale)}
            </label>
            <textarea
              id={idMeddelande}
              rows={3}
              required={valdAtgard.kraverMeddelande}
              value={meddelande}
              onChange={(e) => setMeddelande(e.target.value)}
              aria-describedby={fel ? idFel : undefined}
              className={cn(falt, "mt-1 resize-y")}
            />
          </div>
          {fel ? (
            <p id={idFel} role="alert" className="text-[0.875rem] text-danger">
              {text(fel)}
            </p>
          ) : null}
          <div>
            <button type="submit" disabled={sparar} className={cn(btnPrimary, btnLiten)}>
              {sparar ? a("frSparar", locale) : `${a("frBytLage", locale)}: ${a(`frAtgard_${valdAtgard.id}`, locale)}`}
            </button>
          </div>
        </div>
      ) : null}
    </form>
  );
}
