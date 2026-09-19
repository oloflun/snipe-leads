"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Inbox,
  Loader2,
  Mail,
  ScanLine,
  Trash2,
  Upload
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Badge,
  Cell,
  EmptyState,
  SkeletonRows,
  Tabell,
  btnLiten,
  btnPrimary,
  btnSecondary,
  tabellRad
} from "@/components/ui";
import { Integritetsnotis } from "@/components/kvitton/Integritetsnotis";
import { HttpJsonError, felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Kvittohanterarens arbetsyta — skanning, resultat och sammanfattning.
 *
 * ## Skanningen SPELAS UPP, inte simuleras
 *
 * `POST /skanna` gör hela jobbet i ett anrop och svarar med en händelse per
 * genomläst mejl. Vyn spelar upp händelserna i tur och ordning (mejlet glider
 * in, beloppet markeras när det identifierats) — samma rörelse som demon, men
 * varje rad är en RIKTIG händelse ur körningen, inte en inspelning. Reduced
 * motion hoppar direkt till slutläget.
 *
 * ## Beloppen är strängar hela vägen
 *
 * Samma regel som bokföringspanelen hade och av samma skäl: ett belopp som
 * passerar en JavaScript-float kan ändras på sista decimalen. Formateringen
 * i `kronor` arbetar på strängen.
 */

const BAS = "/api/snajp-support/kvitton";

/** Speglar `LASBARA_MIMETYPER` i app/bookkeeping/underlag.py. */
const LASBARA = ".pdf,image/jpeg,image/png,image/webp,image/heic";

const STEG_MS = 420;

type Mejlkonto = { kopplad: boolean; leverantor?: string; adress?: string };

type Kvitto = {
  id: string;
  datum: string | null;
  motpart: string | null;
  filnamn: string | null;
  brutto: string | null;
  momssats: string | null;
  kategori: string | null;
  kategorietikett: string;
  status: string;
  betalstatus: string | null;
  kalla: string;
  mejl_amne: string | null;
  mejl_avsandare: string | null;
  valuta: string;
  belopp_original: string | null;
  anmarkning: string;
};

type Sammanfattning = {
  antal: number;
  antal_klara: number;
  antal_granska: number;
  totalt: string;
  moms: string;
  per_kategori: { kategori: string; etikett: string; antal: number; summa: string }[];
  text?: string;
};

type Handelse = {
  mejl_id: string;
  avsandare: string;
  amne: string;
  datum: string;
  utfall: "kvitto" | "kvitto_granska" | "ej_kvitto" | "redan_last";
  belopp?: string | null;
  belopp_original?: string | null;
  kategori?: string | null;
  motpart?: string | null;
};

function innevarandeManad(): { fran: string; till: string } {
  const nu = new Date();
  const fran = new Date(nu.getFullYear(), nu.getMonth(), 1);
  const till = new Date(nu.getFullYear(), nu.getMonth() + 1, 0);
  const iso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { fran: iso(fran), till: iso(till) };
}

function kronor(varde: string | null): string {
  if (varde === null) return "—";
  const negativt = varde.startsWith("-");
  const [heltal, decimaler = "00"] = varde.replace("-", "").split(".");
  const grupperat = heltal.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${negativt ? "−" : ""}${grupperat},${decimaler.padEnd(2, "0")} kr`;
}

const MOMSETIKETT: Record<string, string> = {
  "0.25": "25 %",
  "0.12": "12 %",
  "0.06": "6 %",
  "0": "0 %"
};

function procent(varde: string | null): string {
  if (varde === null) return "—";
  const normaliserad = varde.includes(".")
    ? varde.replace(/0+$/, "").replace(/\.$/, "")
    : varde;
  return MOMSETIKETT[normaliserad] ?? "—";
}

function feltext(orsak: unknown): string {
  if (orsak instanceof HttpJsonError) {
    const kropp =
      orsak.body && typeof orsak.body === "object" ? (orsak.body as Record<string, unknown>) : {};
    return (
      (typeof kropp.error === "string" && kropp.error) ||
      (typeof kropp.detail === "string" && kropp.detail) ||
      orsak.message
    );
  }
  return felmeddelande(orsak);
}

export function KvittoYta() {
  const [konto, setKonto] = useState<Mejlkonto | null>(null);
  const [kvitton, setKvitton] = useState<Kvitto[] | null>(null);
  const [samman, setSamman] = useState<Sammanfattning | null>(null);
  const [period, setPeriod] = useState(innevarandeManad);
  const [fel, setFel] = useState<string | null>(null);

  const [skannar, setSkannar] = useState(false);
  const [handelser, setHandelser] = useState<Handelse[] | null>(null);
  const [visadeHandelser, setVisadeHandelser] = useState(0);

  const [laddarUpp, setLaddarUpp] = useState(false);
  const [uppladdningsfel, setUppladdningsfel] = useState<string[]>([]);
  const [rensar, setRensar] = useState(false);
  const filväljare = useRef<HTMLInputElement>(null);

  const hamta = useCallback(async () => {
    setFel(null);
    try {
      const [kontoSvar, listaSvar, sammanSvar] = await Promise.all([
        fetch(`${BAS}/mejlkonto`).then((s) => readJson<Mejlkonto>(s)),
        fetch(`${BAS}?fran=${period.fran}&till=${period.till}`).then((s) =>
          readJson<{ kvitton: Kvitto[] }>(s)
        ),
        fetch(`${BAS}/sammanfattning?fran=${period.fran}&till=${period.till}`).then((s) =>
          readJson<Sammanfattning>(s)
        )
      ]);
      setKonto(kontoSvar);
      setKvitton(listaSvar?.kvitton ?? []);
      setSamman(sammanSvar);
    } catch (orsak) {
      setFel(feltext(orsak));
      setKvitton([]);
    }
  }, [period]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Uppspelningen av skanningens händelser. Se docstringen.
  useEffect(() => {
    if (!handelser || visadeHandelser >= handelser.length) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisadeHandelser(handelser.length);
      return;
    }
    const timer = window.setTimeout(
      () => setVisadeHandelser((n) => n + 1),
      STEG_MS
    );
    return () => window.clearTimeout(timer);
  }, [handelser, visadeHandelser]);

  const uppspelningKlar = handelser !== null && visadeHandelser >= handelser.length;

  async function skanna() {
    setSkannar(true);
    setFel(null);
    setHandelser(null);
    setVisadeHandelser(0);
    try {
      const svar = await fetch(
        `${BAS}/skanna?fran=${period.fran}&till=${period.till}`,
        { method: "POST" }
      );
      const data = await readJson<{
        handelser: Handelse[];
        kvitton: Kvitto[];
        sammanfattning: Sammanfattning;
        text: string;
      }>(svar);
      setHandelser(data?.handelser ?? []);
      setKvitton(data?.kvitton ?? []);
      setSamman(data ? { ...data.sammanfattning, text: data.text } : null);
    } catch (orsak) {
      setFel(feltext(orsak));
    } finally {
      setSkannar(false);
    }
  }

  async function laddaUpp(filer: File[]) {
    if (!filer.length) return;
    setLaddarUpp(true);
    setFel(null);
    setUppladdningsfel([]);
    const misslyckade: string[] = [];
    try {
      for (const fil of filer) {
        try {
          const kropp = new FormData();
          kropp.append("fil", fil);
          const svar = await fetch(`${BAS}/underlag`, { method: "POST", body: kropp });
          await readJson(svar);
        } catch (orsak) {
          misslyckade.push(`${fil.name}: ${feltext(orsak)}`);
        }
      }
      setUppladdningsfel(misslyckade);
      await hamta();
    } finally {
      setLaddarUpp(false);
    }
  }

  async function godkann(rad: Kvitto) {
    setFel(null);
    const kropp: Record<string, string> = {};
    if (rad.brutto === null) {
      const belopp = window.prompt(
        rad.belopp_original
          ? `Kvittot är på ${rad.belopp_original}. Ange beloppet omräknat till kronor (t.ex. 495,00):`
          : "Kvittot saknar läsbart belopp. Ange beloppet i kronor (t.ex. 495,00):"
      );
      if (!belopp) return;
      kropp.brutto = belopp.replace(/\s/g, "").replace(",", ".");
    }
    if (rad.momssats === null) {
      const sats = window.prompt("Ange momssatsen i procent (25, 12, 6 eller 0):");
      if (sats === null) return;
      const normaliserad = { "25": "0.25", "12": "0.12", "6": "0.06", "0": "0" }[sats.trim()];
      if (!normaliserad) {
        setFel("Momssatsen ska vara 25, 12, 6 eller 0.");
        return;
      }
      kropp.momssats = normaliserad;
    }
    if (rad.datum === null) {
      const datum = window.prompt("Kvittot saknar datum. Ange köpdatum (ÅÅÅÅ-MM-DD):");
      if (!datum) return;
      kropp.datum = datum.trim();
    }
    if (rad.motpart === null) {
      const motpart = window.prompt("Vilken butik eller leverantör är kvittot från?");
      if (!motpart) return;
      kropp.motpart = motpart.trim();
    }    if (rad.kategori === null) {
      const kategori = window.prompt(
        "Ange kategori: drivmedel, biljett, kost_och_logi, representation, kontorsmateriel, programvara, forbrukningsinventarier eller ovrig_extern_kostnad:"
      );
      if (!kategori) return;
      kropp.kategori = kategori.trim().toLowerCase();
    }
    if (rad.betalstatus === null) {
      // Frågas, gissas aldrig: betalstatus avgör om kvittot bokas mot
      // bankkontot eller som en obetald skuld.
      const betald = window.confirm(
        "Är kvittot redan betalt?\n\nOK = betalt (kort, Swish, kontant)\nAvbryt = obetald faktura"
      );
      kropp.betalstatus = betald ? "betald" : "obetald";
    }
    try {
      const svar = await fetch(`${BAS}/${rad.id}/godkann`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(kropp)
      });
      const data = await readJson<{ godkand: boolean; brister?: string[] }>(svar);
      if (data && !data.godkand) {
        setFel(
          `Kvittot kunde inte godkännas ännu: ${(data.brister ?? []).join("; ") || "fält saknas."}`
        );
      }
      await hamta();
    } catch (orsak) {
      setFel(feltext(orsak));
    }
  }

  async function rensa() {
    if (!kvitton?.length) return;
    const bekraftat = window.confirm(
      `Rensa ${period.fran} till ${period.till}?\n\n` +
        `${kvitton.length} kvitton raderas. Det går inte att ångra.`
    );
    if (!bekraftat) return;
    setRensar(true);
    setFel(null);
    try {
      const svar = await fetch(`${BAS}/period?fran=${period.fran}&till=${period.till}`, {
        method: "DELETE"
      });
      await readJson(svar);
      setHandelser(null);
      await hamta();
    } catch (orsak) {
      setFel(feltext(orsak));
    } finally {
      setRensar(false);
    }
  }

  const harKvitton = (kvitton?.length ?? 0) > 0;

  const datumfalt = (
    <div className="flex flex-wrap items-end gap-2">
      <label className="flex flex-col gap-1">
        <span className="text-[0.75rem] font-medium text-ink-subtle">Från</span>
        <input
          type="date"
          value={period.fran}
          onChange={(e) => setPeriod((p) => ({ ...p, fran: e.target.value }))}
          className="focus-ring h-9 rounded-input bg-paper2 px-2.5 text-[0.875rem]"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-[0.75rem] font-medium text-ink-subtle">Till</span>
        <input
          type="date"
          value={period.till}
          onChange={(e) => setPeriod((p) => ({ ...p, till: e.target.value }))}
          className="focus-ring h-9 rounded-input bg-paper2 px-2.5 text-[0.875rem]"
        />
      </label>
    </div>
  );

  return (
    <div className="space-y-8">
      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[14px] text-danger">
          {fel}
        </p>
      ) : null}

      {/* Mejlkontot och skanningen. */}
      <section>
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
          {datumfalt}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={skannar || !konto?.kopplad}
              onClick={() => void skanna()}
              title={
                konto?.kopplad
                  ? undefined
                  : "Ingen inkorg kopplad."
              }
              className={cn(btnPrimary, btnLiten)}
            >
              {skannar ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <ScanLine className="h-4 w-4" aria-hidden />
              )}
              Skanna inkorgen
            </button>
            <button
              type="button"
              disabled={laddarUpp}
              onClick={() => filväljare.current?.click()}
              className={cn(btnSecondary, btnLiten)}
            >
              {laddarUpp ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Upload className="h-4 w-4" aria-hidden />
              )}
              Ladda upp kvitto
            </button>
            <a
              href={
                harKvitton
                  ? `${BAS}/export.csv?fran=${period.fran}&till=${period.till}`
                  : undefined
              }
              aria-disabled={!harKvitton}
              title={harKvitton ? undefined : "Det finns inga kvitton att exportera."}
              className={cn(btnSecondary, btnLiten, !harKvitton && "pointer-events-none opacity-40")}
            >
              <Download className="h-4 w-4" aria-hidden />
              Exportera
            </a>
            <button
              type="button"
              disabled={rensar || !harKvitton}
              onClick={() => void rensa()}
              title={harKvitton ? undefined : "Det finns inget att rensa i perioden."}
              className={cn(btnSecondary, btnLiten)}
            >
              {rensar ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Trash2 className="h-4 w-4" aria-hidden />
              )}
              Rensa
            </button>
          </div>
        </div>

        <p className="mt-3 flex flex-wrap items-center gap-2 text-[0.875rem] text-ink-muted">
          <Mail className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
          {konto === null ? (
            "Hämtar mejlkontot…"
          ) : konto.kopplad ? (
            <>
              Kopplad inkorg:{" "}
              <span className="font-medium text-ink">{konto.adress}</span>
              <Badge tone="good">
                {konto.leverantor === "gmail"
                  ? "Gmail"
                  : konto.leverantor === "microsoft"
                    ? "Outlook/Hotmail"
                    : "Demokonto"}
              </Badge>
            </>
          ) : (
            <>
              Ingen inkorg kopplad.{" "}
              <a
                href="mailto:kontakt@snajp.se?subject=Koppla%20mejl%20till%20Kvittohanteraren"
                className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-ochre"
              >
                Hör av dig
              </a>{" "}
              så kopplar vi den.
            </>
          )}
        </p>
      </section>

      {/* Inkorgsvyn — uppspelningen av senaste skanningen. */}
      {handelser !== null ? (
        <section className="rounded-card border border-ink/12 bg-paper2/30 p-5">
          <div className="flex items-baseline justify-between gap-4">
            <p className="kicker flex items-center gap-2 text-mineral">
              <Inbox className="h-3.5 w-3.5" aria-hidden />
              Inkorgen
            </p>
            <p className="text-[0.75rem] tabular-nums text-mineral" role="status">
              {uppspelningKlar
                ? `${handelser.length} mejl genomlästa`
                : `läser mejl ${Math.min(visadeHandelser + 1, handelser.length)} av ${handelser.length}…`}
            </p>
          </div>
          <ul className="mt-3 divide-y divide-ink/10 border-t border-ink/10">
            {handelser.slice(0, visadeHandelser).map((h) => (
              <li key={h.mejl_id} className="animate-mejl-in py-2.5">
                <div className="flex min-w-0 items-baseline justify-between gap-3">
                  <p className="min-w-0 truncate text-[0.875rem] font-medium text-ink">
                    {h.avsandare}
                    <span className="ml-2 font-normal text-ink-subtle">{h.amne}</span>
                  </p>
                  <span className="shrink-0">
                    {h.utfall === "kvitto" ? (
                      <Badge tone="good">Kvitto</Badge>
                    ) : h.utfall === "kvitto_granska" ? (
                      <Badge tone="warn">Granska</Badge>
                    ) : h.utfall === "redan_last" ? (
                      <span className="text-[0.75rem] text-mineral">redan inläst</span>
                    ) : (
                      <span className="text-[0.75rem] text-mineral">inte ett kvitto</span>
                    )}
                  </span>
                </div>
                {h.belopp || h.belopp_original ? (
                  <p className="mt-1 font-mono text-[0.75rem] text-ink-subtle">
                    Belopp:{" "}
                    <mark
                      className={cn(
                        "animate-belopp rounded-[3px] px-1 py-0.5 font-semibold text-ink",
                        h.belopp ? "bg-ochre/25" : "bg-copper/20"
                      )}
                    >
                      {h.belopp ? kronor(h.belopp) : h.belopp_original}
                    </mark>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
          {uppspelningKlar ? (
            <p className="mt-3 flex items-center gap-2 border-t border-ink/10 pt-3 text-[0.8125rem] text-moss">
              <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />
              Klart.
            </p>
          ) : null}
        </section>
      ) : null}

      {/* Uppladdningsfelen, per fil. */}
      {uppladdningsfel.length ? (
        <div role="status" className="max-w-[78ch] border-y border-ink/15 py-3">
          <p className="flex items-center gap-2 text-[0.9375rem] font-semibold text-ink">
            <AlertTriangle className="h-4 w-4 text-warning" aria-hidden />
            {uppladdningsfel.length}{" "}
            {uppladdningsfel.length === 1 ? "fil kom" : "filer kom"} inte in
          </p>
          <ul className="mt-2 space-y-1">
            {uppladdningsfel.map((rad, i) => (
              <li key={i} className="text-[0.875rem] text-ink-muted">
                {rad}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Kvittona. */}
      <section>
        <h2 className="font-display text-[1.25rem]">Kvitton i perioden</h2>
        {kvitton === null ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : kvitton.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="Inga kvitton i perioden" />
          </div>
        ) : (
          <div className="mt-4">
            <Tabell
              ariaLabel="Kvitton i perioden"
              kolumner={[
                { rubrik: "Datum", bredd: "12%" },
                { rubrik: "Butik", bredd: "32%" },
                { rubrik: "Kategori", bredd: "16%" },
                { rubrik: "Källa", bredd: "10%" },
                { rubrik: "Moms", bredd: "8%", hoger: true },
                { rubrik: "Belopp", bredd: "12%", hoger: true },
                { rubrik: "Status", bredd: "10%", hoger: true }
              ]}
            >
              {kvitton.map((rad) => (
                <tr key={rad.id} className={tabellRad}>
                  <Cell>
                    <span className="tabular-nums text-ink-muted">{rad.datum ?? "—"}</span>
                  </Cell>
                  <Cell titel>
                    <p className="truncate">{rad.motpart || rad.mejl_amne || rad.filnamn}</p>
                    {rad.anmarkning ? (
                      <p className="mt-1 text-[0.875rem] font-normal text-ink-subtle">
                        {rad.anmarkning}
                      </p>
                    ) : null}
                  </Cell>
                  <Cell>
                    <span className="text-ink-muted">{rad.kategorietikett}</span>
                  </Cell>
                  <Cell>
                    <span className="text-ink-muted">
                      {rad.kalla === "mejl" ? "Mejl" : "Uppladdad"}
                    </span>
                  </Cell>
                  <Cell hoger>
                    <span className="text-ink-muted">{procent(rad.momssats)}</span>
                  </Cell>
                  <Cell hoger>
                    <span className="font-medium">
                      {rad.brutto !== null ? kronor(rad.brutto) : (rad.belopp_original ?? "—")}
                    </span>
                  </Cell>
                  <Cell hoger>
                    <span className="flex flex-wrap items-center justify-end gap-1.5">
                      <Badge tone={rad.status === "granska_manuellt" ? "warn" : "good"}>
                        {rad.status === "granska_manuellt" ? "Granska" : "Klar"}
                      </Badge>
                      {rad.status === "granska_manuellt" ? (
                        <button
                          type="button"
                          onClick={() => void godkann(rad)}
                          className="focus-ring rounded-input text-[0.8125rem] font-medium text-ink underline underline-offset-4 hover:text-ochre"
                        >
                          Godkänn
                        </button>
                      ) : null}
                    </span>
                  </Cell>
                </tr>
              ))}
            </Tabell>
          </div>
        )}
      </section>

      <input
        ref={filväljare}
        type="file"
        multiple
        accept={LASBARA}
        onChange={(e) => {
          void laddaUpp(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
        className="sr-only"
      />
    </div>
  );
}

/**
 * Sammanfattningsrutan — högerkolumnens topp. Egen komponent så att
 * serverskalet kan placera den bredvid chatten utan att arbetsytan behöver
 * veta om kolumnbrytningen.
 */
export function KvittoSammanfattning() {
  const [samman, setSamman] = useState<Sammanfattning | null>(null);
  const [period] = useState(innevarandeManad);

  useEffect(() => {
    let aktiv = true;
    const hamta = () =>
      fetch(`${BAS}/sammanfattning?fran=${period.fran}&till=${period.till}`)
        .then((s) => readJson<Sammanfattning>(s))
        .then((data) => {
          if (aktiv) setSamman(data);
        })
        .catch(() => undefined);
    void hamta();
    // Sammanfattningen ändras när en skanning eller uppladdning skriver — den
    // hämtas om var 15:e sekund i stället för att koppla ihop komponenterna.
    const timer = window.setInterval(hamta, 15_000);
    return () => {
      aktiv = false;
      window.clearInterval(timer);
    };
  }, [period]);

  return (
    <div className="rounded-card border border-ink/12 bg-paper p-5">
      <p className="kicker text-mineral">Sammanfattning</p>
      {samman === null ? (
        <p className="mt-3 text-[0.875rem] text-ink-subtle">Hämtar…</p>
      ) : samman.antal === 0 ? (
        <p className="mt-3 text-[0.875rem] leading-6 text-ink-subtle">Inga inlästa kvitton.</p>
      ) : (
        <>
          <p className="mt-3 font-display text-[2.25rem] leading-none tracking-[-0.01em]">
            {kronor(samman.totalt)}
          </p>
          <p className="mt-1 text-[0.8125rem] text-ink-subtle">
            {samman.antal_klara} avlästa kvitton · ingående moms {kronor(samman.moms)}
          </p>
          {samman.per_kategori.length ? (
            <dl className="mt-4 divide-y divide-ink/10 border-y border-ink/10">
              {samman.per_kategori.map((rad) => (
                <div key={rad.kategori} className="flex items-baseline justify-between gap-4 py-2">
                  <dt className="text-[0.875rem] text-ink-muted">
                    {rad.etikett}
                    <span className="ml-1.5 text-[0.75rem] text-mineral">×{rad.antal}</span>
                  </dt>
                  <dd className="num text-[0.875rem]">{kronor(rad.summa)}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          {samman.text ? (
            <p className="mt-4 text-[0.875rem] leading-6 text-ink-muted">{samman.text}</p>
          ) : null}
        </>
      )}
      <div className="mt-4">
        <Integritetsnotis />
      </div>
    </div>
  );
}
