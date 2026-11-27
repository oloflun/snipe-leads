"use client";

import "@/components/crm/app/crm-vyer.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import NextLink from "next/link";
import { useRouter } from "next/navigation";
import { CircleDot, Clock, Layers, Radar, Search, Target, Type } from "lucide-react";
import { Badge } from "@astryxdesign/core/Badge";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { List, ListItem } from "@astryxdesign/core/List";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { useToast } from "@astryxdesign/core/Toast";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { KorIris } from "@/components/crm/app/iris/KorIris";
import { Kolumnrubrik, Objektikon, Prick, Tabellskelett, Vyval, useBestallning, useSkrivratt, useSmal } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { irisAnrop } from "@/lib/crm/iris/anrop";
import { LAGE, arbetar, korningsTyp, lage, utfallText, type Jobbsvar, type KorningsRad, type Startad } from "@/lib/crm/iris/korning";
import { useLocale, type Localized } from "@/lib/i18n";
import { taligHamtning } from "@/lib/leads/pollning";

type Filter = "alla" | "pagar" | "klara" | "fel";
const PULS = 3000;
/** Avsändaren på körningshändelserna: vyn lyssnar inte på sin egen signal. */
export const KORNINGARNAS_KALLA = "crm-iris-korningar";

/** Datum och tid för en körning, i läsarens språk. */
export function korningstid(iso: string | null, locale: "sv" | "en"): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString(locale === "en" ? "en-GB" : "sv-SE", { dateStyle: "short", timeStyle: "short" });
}

/** Statusen som helt rundad etikett med prick; den pågående pricken pulserar. */
export function Korningsstatus({ rad }: Readonly<{ rad: KorningsRad }>) {
  const { text } = useLocale();
  const l = LAGE[lage(rad)];
  return <Badge variant={l.badge} label={text(l.namn)} icon={<Prick ton={l.prick} pulserar={arbetar(rad)} />} />;
}

/** Nyckeln för körningen som startades härifrån och ännu söker, per identitet (INV-SEC-014). */
const startnyckel = (identitet: string | null | undefined) => `crm-iris-start:${identitet ?? "kund"}`;
function lasStart(nyckel: string): Startad | null {
  try {
    const s = JSON.parse(window.localStorage.getItem(nyckel) ?? "null") as Startad | null;
    return s && typeof s.jobbId === "string" ? s : null;
  } catch {
    return null;
  }
}
function sparaStart(nyckel: string, s: Startad | null) {
  try {
    if (s) window.localStorage.setItem(nyckel, JSON.stringify(s));
    else window.localStorage.removeItem(nyckel);
  } catch {
    /* utan lagring följs starten bara tills sidan laddas om; körningen syns ändå i listan */
  }
}

/** Var starten står (LK-010, LK-014): söker, researchar egna bolag, eller ett utfall. */
type Startlage =
  | { fas: "soker"; s: Startad }
  | { fas: "barn"; s: Startad; klara: number; misslyckade: number }
  | { fas: "igang"; s: Startad }
  | { fas: "klar"; s: Startad; klara: number; misslyckade: number }
  | { fas: "fel"; s: Startad; fel: string };

const vanta = (ms: number) => new Promise((r) => window.setTimeout(r, ms));

/**
 * Iris › Körningar (steg 4.4, LK-020 till LK-030, OV-031, OV-032, OV-037): alla
 * körningar, nyast först, med läge, beställt och levererat och förloppet för den
 * som går. Listan läser liggaren (`GET /leads/korningar`), så förlopp och utfall
 * står kvar efter en omladdning. Medan något arbetar hämtas listan var tredje
 * sekund, bara när fliken syns. En körning öppnas på sin egen sida
 * (`/crm/iris/korningar/<id>`), där den styrs.
 *
 * Kör Iris (sidhuvudet, och `?ny=1` från kommandopaletten) öppnar dialogen. När
 * körningen är överlämnad följs sökningen här, där den startades: en rad överst
 * säger att Iris letar, och sedan att körningen är igång eller varför den inte
 * startade. Sökjobbets id minns i webbläsaren, så att beskedet kommer även efter
 * en omladdning (LK-012).
 */
export function KorningarVy({ bas = "/crm" }: Readonly<{ bas?: string }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const router = useRouter();
  const { identitet } = useDashboard();
  // Agenternas körningar: under ett kundbesök märks de som test, läsrollen startar inget.
  const skriv = useSkrivratt("test");
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);
  const vag = (id: string) => `${bas}/iris/korningar/${encodeURIComponent(id)}`;

  const [rader, setRader] = useState<KorningsRad[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [stoppad, setStoppad] = useState(false);
  const [filter, setFilter] = useState<Filter>("alla");
  const [ny, setNy] = useState(false);
  const [start, setStart] = useState<Startlage | null>(null);
  const [statusbesked, setStatusbesked] = useState("");

  useBestallning("ny", () => {
    if (skriv.far) setNy(true);
  });

  // ---- Hämtningen -----------------------------------------------------------------------
  const nr = useRef(0);
  const sett = useRef<Map<string, { steg: number; pagar: boolean }>>(new Map());
  const hamta = useCallback(async () => {
    const mitt = ++nr.current;
    try {
      const s = await irisAnrop<{ korningar?: KorningsRad[] }>("/leads/korningar?limit=30");
      if (mitt !== nr.current) return;
      const nya = s?.korningar ?? [];
      // Leads-listan och översikten fylls bolag för bolag (LK-011, OV-032): en körning som rört sig
      // sänder steg, en som slutat sänder klar. Första hämtningen sänder inget.
      const forr = sett.current;
      let steg = false;
      let klar = false;
      if (forr.size) {
        for (const r of nya) {
          const f = forr.get(r.job_id);
          const n = (r.korning?.levererade ?? 0) + (r.korning?.undersokta ?? 0);
          if (f && f.steg !== n) steg = true;
          if (f?.pagar && !arbetar(r)) klar = true;
        }
      }
      sett.current = new Map(nya.map((r) => [r.job_id, { steg: (r.korning?.levererade ?? 0) + (r.korning?.undersokta ?? 0), pagar: arbetar(r) }]));
      if (steg) window.dispatchEvent(new CustomEvent("snipra:leads-korning-steg", { detail: KORNINGARNAS_KALLA }));
      if (klar) window.dispatchEvent(new CustomEvent("snipra:leads-korning-klar", { detail: KORNINGARNAS_KALLA }));
      setRader(nya);
      setFel(null);
    } catch (e) {
      if (mitt !== nr.current) return;
      const status = (e as { status?: number })?.status;
      if (status === 401 || status === 403 || status === 404) setStoppad(true);
      setFel(e);
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Medan något arbetar: nästa hämtning först när förra svarat, och inte när fliken är dold (LK-025).
  // En vilande körning väcks en gång per dygn och pollas inte.
  const nagotArbetar = !stoppad && (rader ?? []).some(arbetar);
  const soker = start?.fas === "soker" || start?.fas === "barn";
  useEffect(() => {
    if (!nagotArbetar && !soker) return;
    let aktiv = true;
    let timer = 0;
    const varv = async () => {
      if (document.visibilityState === "visible") await hamta();
      if (aktiv) timer = window.setTimeout(() => void varv(), PULS);
    };
    const synlig = () => {
      if (document.visibilityState === "visible") void hamta();
    };
    timer = window.setTimeout(() => void varv(), PULS);
    document.addEventListener("visibilitychange", synlig);
    return () => {
      aktiv = false;
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", synlig);
    };
  }, [nagotArbetar, soker, hamta]);

  // Körningar som startas eller styrs någon annanstans (dagens Leads, körningens sida) läses om.
  useEffect(() => {
    const lyssnare = (e: Event) => {
      if ((e as CustomEvent).detail !== KORNINGARNAS_KALLA) void hamta();
    };
    window.addEventListener("snipra:leads-korning-steg", lyssnare);
    window.addEventListener("snipra:leads-korning-klar", lyssnare);
    return () => {
      window.removeEventListener("snipra:leads-korning-steg", lyssnare);
      window.removeEventListener("snipra:leads-korning-klar", lyssnare);
    };
  }, [hamta]);

  // ---- Starten: sökjobbet och egna bolag följs här (LK-010, LK-012, LK-014) --------------
  const nyckel = startnyckel(identitet);
  const foljer = useRef(0);
  const folj = useCallback(
    async (s: Startad) => {
      const mitt = ++foljer.current;
      const aktuell = () => foljer.current === mitt;
      const jobb = (id: string) => irisAnrop<Jobbsvar>(`/leads/jobb/${encodeURIComponent(id)}`);
      const slut = (l: Startlage) => {
        if (!aktuell()) return;
        sparaStart(nyckel, null);
        setStart(l);
        void hamta();
      };
      try {
        let barn = s.barn ?? null;
        if (!barn) {
          setStart({ fas: "soker", s });
          // Sökningen tog 55 till 156 s i mätningen 2026-09-15: vänta upp till fem minuter, som dagens formulär.
          const hamtaJobb = taligHamtning(() => jobb(s.jobbId));
          let svar: Jobbsvar | null = null;
          for (let varv = 0; varv < 150 && aktuell(); varv++) {
            await vanta(varv < 5 ? 800 : 2000);
            const j = await hamtaJobb();
            if (j && (j.status === "completed" || j.status === "failed")) {
              svar = j;
              break;
            }
          }
          if (!aktuell()) return;
          if (!svar) return slut({ fas: "fel", s, fel: text({ sv: "Körningen tog för lång tid.", en: "The run took too long." }) });
          if (svar.status === "failed") return slut({ fas: "fel", s, fel: svar.error ?? text({ sv: "Sökningen hittade inga bolag.", en: "The search found no companies." }) });
          if (svar.result?.korning) return slut({ fas: "igang", s });
          barn = (svar.result?.jobs ?? []).map((j) => j.job_id);
          if (!barn.length) return slut({ fas: "fel", s, fel: text({ sv: "Inga bolag matchade målgruppen. Prova en bredare sökning.", en: "No companies matched the target group. Try a broader search." }) });
          sparaStart(nyckel, { ...s, barn, antal: barn.length });
        }
        // Egna bolag: ett researchjobb per bolag, följt ett och ett.
        const s2 = { ...s, barn, antal: barn.length };
        let klara = 0;
        let misslyckade = 0;
        setStart({ fas: "barn", s: s2, klara, misslyckade });
        for (const id of barn) {
          const hamtaJobb = taligHamtning(() => jobb(id));
          let utfall: string | null = null;
          for (let varv = 0; varv < 90 && aktuell(); varv++) {
            await vanta(varv < 5 ? 800 : 2000);
            const j = await hamtaJobb();
            if (j && (j.status === "completed" || j.status === "failed")) {
              utfall = j.status;
              break;
            }
          }
          if (!aktuell()) return;
          if (utfall === "completed") klara += 1;
          else misslyckade += 1;
          setStart({ fas: "barn", s: s2, klara, misslyckade });
        }
        slut({ fas: "klar", s: s2, klara, misslyckade });
      } catch (e) {
        if (!aktuell()) return;
        // 404: jobbet är städat. Körningen står i listan med sitt utfall; inget att följa.
        if ((e as { status?: number })?.status === 404) {
          sparaStart(nyckel, null);
          setStart(null);
          return;
        }
        slut({ fas: "fel", s, fel: text((e as { text?: Localized })?.text ?? { sv: "Förloppet gick inte att hämta.", en: "The progress could not be loaded." }) });
      }
    },
    [nyckel, hamta, text]
  );

  // En start som pågick när sidan laddades om tas upp igen.
  useEffect(() => {
    const s = lasStart(nyckel);
    if (s) void folj(s);
    return () => {
      foljer.current += 1;
    };
  }, [nyckel, folj]);

  // Startens läge sägs upp i den permanenta regionen.
  useEffect(() => {
    if (!start) return;
    if (start.fas === "soker") setStatusbesked(text({ sv: "Körningen är startad. Iris letar bolag som matchar målgruppen.", en: "The run has started. Iris is looking for companies that match the target group." }));
    else if (start.fas === "igang") setStatusbesked(text({ sv: "Iris har hittat bolag och körningen är igång.", en: "Iris has found companies and the run is under way." }));
    else if (start.fas === "fel") setStatusbesked(text({ sv: `Körningen startade inte. ${start.fel}`, en: `The run did not start. ${start.fel}` }));
    else if (start.fas === "klar")
      setStatusbesked(start.klara === 1 ? text({ sv: "Klart: 1 bolag researchat.", en: "Done: 1 company researched." }) : text({ sv: `Klart: ${start.klara} bolag researchade.`, en: `Done: ${start.klara} companies researched.` }));
  }, [start, text]);

  function startad(s: Startad) {
    setNy(false);
    sparaStart(nyckel, s);
    visa({ body: text({ sv: "Körningen är startad. Förloppet står överst i listan.", en: "The run has started. The progress is shown at the top of the list." }), uniqueID: "crm-kor-iris" });
    void hamta();
    void folj(s);
  }

  // ---- Urvalet ---------------------------------------------------------------------------
  const raknat = useMemo(() => {
    const r = rader ?? [];
    const l = r.map(lage);
    return {
      alla: r.length,
      pagar: l.filter((x) => x === "pagar" || x === "pausad" || x === "avbryts" || x === "vilar" || x === "koad").length,
      klara: l.filter((x) => x === "klar" || x === "under").length,
      fel: l.filter((x) => x === "fel" || x === "stannade").length
    };
  }, [rader]);
  const visade = useMemo(() => {
    const r = rader ?? [];
    if (filter === "alla") return r;
    return r.filter((x) => {
      const l = lage(x);
      if (filter === "pagar") return l === "pagar" || l === "pausad" || l === "avbryts" || l === "vilar" || l === "koad";
      if (filter === "klara") return l === "klar" || l === "under";
      return l === "fel" || l === "stannade";
    });
  }, [rader, filter]);
  const filtervyer: { v: Filter; namn: Localized }[] = [
    { v: "alla", namn: { sv: "Alla", en: "All" } },
    { v: "pagar", namn: { sv: "Pågår", en: "Running" } },
    { v: "klara", namn: { sv: "Klara", en: "Done" } },
    { v: "fel", namn: { sv: "Misslyckade", en: "Failed" } }
  ];

  // Sökjobbet står som en köad rad utan motortillstånd medan Iris letar: den heter då det den är.
  const typ = useCallback(
    (r: KorningsRad): string => {
      if (!r.korning && r.scope === "batch" && start?.s.jobbId === r.job_id && !start.s.egna) {
        return start.s.scope === "research_and_draft" ? text({ sv: `Research och utkast, ${start.s.struktur.toUpperCase()}`, en: `Research and drafts, ${start.s.struktur.toUpperCase()}` }) : text({ sv: "Research", en: "Research" });
      }
      return text(korningsTyp(r));
    },
    [start, text]
  );

  const kolumner = useMemo<TableColumn<KorningsRad>[]>(
    () => [
      {
        key: "created_at",
        header: <Kolumnrubrik ikon={Clock}>{text({ sv: "Startad", en: "Started" })}</Kolumnrubrik>,
        width: pixel(264),
        renderCell: (r) => (
          <NextLink href={vag(r.job_id)} className="crm-chip inline-flex h-7 max-w-full items-center gap-2 rounded-[6px] pl-1 pr-2" aria-label={text({ sv: `Öppna körningen ${korningstid(r.created_at, locale)}`, en: `Open the run ${korningstid(r.created_at, locale)}` })}>
            <Objektikon objekt="korningar" storlek={20} />
            <span className="whitespace-nowrap text-[0.875rem] font-semibold tabular-nums text-ink">{korningstid(r.created_at, locale)}</span>
            {r.is_test ? (<span className="shrink-0"><Badge variant="neutral" label={text({ sv: "Test", en: "Test" })} /></span>) : null}
          </NextLink>
        )
      },
      {
        key: "typ",
        header: <Kolumnrubrik ikon={Type}>{text({ sv: "Typ", en: "Type" })}</Kolumnrubrik>,
        width: pixel(196),
        renderCell: (r) => <span title={typ(r)} className="text-ink2">{typ(r)}</span>
      },
      {
        key: "status",
        header: <Kolumnrubrik ikon={CircleDot}>{text({ sv: "Status", en: "Status" })}</Kolumnrubrik>,
        width: pixel(160),
        renderCell: (r) => <Korningsstatus rad={r} />
      },
      {
        key: "leads",
        header: <Kolumnrubrik ikon={Target}>{text({ sv: "Leads av beställt", en: "Leads of ordered" })}</Kolumnrubrik>,
        width: pixel(156),
        renderCell: (r) => {
          const k = r.korning;
          if (!k) return <span className="text-ink-muted">-</span>;
          return (
            <div className="flex w-full min-w-0 items-center gap-2.5 pr-2">
              <span className="whitespace-nowrap text-[0.875rem] tabular-nums text-ink">{text({ sv: `${tal(k.levererade)} av ${tal(k.mal)}`, en: `${tal(k.levererade)} of ${tal(k.mal)}` })}</span>
              {arbetar(r) ? (
                <div className="min-w-0 flex-1">
                  <ProgressBar label={text({ sv: `Leads klara i körningen ${korningstid(r.created_at, locale)}`, en: `Leads done in the run ${korningstid(r.created_at, locale)}` })} isLabelHidden value={k.levererade} max={Math.max(k.mal, 1)} />
                </div>
              ) : null}
            </div>
          );
        }
      },
      {
        key: "undersokta",
        header: <Kolumnrubrik ikon={Search}>{text({ sv: "Undersökta", en: "Researched" })}</Kolumnrubrik>,
        width: pixel(116),
        renderCell: (r) => <span className="tabular-nums text-ink2">{r.korning ? tal(r.korning.undersokta) : "-"}</span>
      },
      {
        key: "utfall",
        header: <Kolumnrubrik ikon={Layers}>{text({ sv: "Utfall", en: "Outcome" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 180 }),
        renderCell: (r) => {
          const u = utfallText(r, text);
          return (
            <span title={u} className={r.error ? "text-ink" : "text-ink-muted"}>
              {u}
            </span>
          );
        }
      }
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text, tal, locale, typ, bas]
  );

  // ---- Delarna ---------------------------------------------------------------------------
  const korIrisRef = useRef<HTMLButtonElement>(null);
  const korIris = <Button ref={korIrisRef} variant="primary" label={text({ sv: "Kör Iris", en: "Run Iris" })} icon={<Icon icon={Radar} size="sm" />} isDisabled={!skriv.far} tooltip={skriv.skal ?? undefined} onClick={() => setNy(true)} />;
  // Stäng tar bort raden som hade fokus: fokus går till Kör Iris, annars till listans första körning.
  const stangStart = () => {
    setStart(null);
    window.setTimeout(() => {
      const knapp = korIrisRef.current;
      if (knapp && !knapp.disabled) knapp.focus();
      else document.querySelector<HTMLElement>(".crm-tabell a")?.focus();
    }, 80);
  };
  const laddar = rader == null;

  const startrad = start ? (
    <div className="px-4 pt-4 sm:px-6">
      {start.fas === "soker" || start.fas === "barn" ? (
        <Banner
          status="info"
          container="card"
          title={
            start.fas === "soker"
              ? start.s.egna
                ? text({ sv: "Startar körningen", en: "Starting the run" })
                : text({ sv: "Iris letar bolag som matchar målgruppen", en: "Iris is looking for companies that match the target group" })
              : start.s.antal === 1
                ? text({ sv: "Iris researchar 1 bolag", en: "Iris is researching 1 company" })
                : text({ sv: `Iris researchar ${tal(start.s.antal)} bolag`, en: `Iris is researching ${tal(start.s.antal)} companies` })
          }
          description={
            <div className="flex flex-col gap-2 pt-1">
              <ProgressBar
                label={text({ sv: "Startens förlopp", en: "Progress of the start" })}
                isLabelHidden
                value={start.fas === "barn" ? start.klara + start.misslyckade : 0}
                max={Math.max(start.s.antal, 1)}
                isIndeterminate={start.fas === "soker"}
              />
              <span>
                {start.fas === "barn"
                  ? start.misslyckade
                    ? text({ sv: `${tal(start.klara + start.misslyckade)} av ${tal(start.s.antal)} klara, ${tal(start.misslyckade)} misslyckades.`, en: `${tal(start.klara + start.misslyckade)} of ${tal(start.s.antal)} done, ${tal(start.misslyckade)} failed.` })
                    : text({ sv: `${tal(start.klara)} av ${tal(start.s.antal)} klara.`, en: `${tal(start.klara)} of ${tal(start.s.antal)} done.` })
                  : text({ sv: "Sökningen tar oftast en till tre minuter. Du kan lämna sidan, körningen fortsätter på servern.", en: "The search usually takes one to three minutes. You can leave the page, the run continues on the server." })}
              </span>
            </div>
          }
        />
      ) : start.fas === "fel" ? (
        <Banner
          status="error"
          container="card"
          title={text({ sv: "Körningen startade inte", en: "The run did not start" })}
          description={start.fel}
          endContent={<Button size="sm" variant="ghost" label={text({ sv: "Stäng", en: "Close" })} onClick={stangStart} />}
        />
      ) : (
        <Banner
          status="success"
          container="card"
          title={
            start.fas === "igang"
              ? text({ sv: "Körningen är igång", en: "The run is under way" })
              : start.misslyckade
                ? start.klara === 1
                  ? text({ sv: `Klart: 1 bolag researchat, ${tal(start.misslyckade)} misslyckades`, en: `Done: 1 company researched, ${tal(start.misslyckade)} failed` })
                  : text({ sv: `Klart: ${tal(start.klara)} bolag researchade, ${tal(start.misslyckade)} misslyckades`, en: `Done: ${tal(start.klara)} companies researched, ${tal(start.misslyckade)} failed` })
                : start.klara === 1
                  ? text({ sv: "Klart: 1 bolag researchat", en: "Done: 1 company researched" })
                  : text({ sv: `Klart: ${tal(start.klara)} bolag researchade`, en: `Done: ${tal(start.klara)} companies researched` })
          }
          description={
            start.fas === "igang"
              ? text({ sv: "Iris har hittat bolag och researchar dem. Förloppet står i listan och på körningens sida.", en: "Iris has found companies and is researching them. The progress shows in the list and on the run's page." })
              : text({ sv: "Bolagen står under Leads.", en: "The companies are under Leads." })
          }
          endContent={
            <span className="flex items-center gap-1">
              {start.fas === "igang" ? <Button size="sm" variant="secondary" label={text({ sv: "Följ körningen", en: "Follow the run" })} href={vag(start.s.jobbId)} /> : <Button size="sm" variant="secondary" label={text({ sv: "Till Leads", en: "To Leads" })} href={`${bas}/iris/leads`} />}
              <Button size="sm" variant="ghost" label={text({ sv: "Stäng", en: "Close" })} onClick={stangStart} />
            </span>
          }
        />
      )}
    </div>
  ) : null;

  const tomt = (
    <EmptyState
      icon={<Icon icon={Radar} size="lg" color="secondary" />}
      title={rader?.length ? text({ sv: "Inga körningar i den här vyn", en: "No runs in this view" }) : text({ sv: "Inga körningar än", en: "No runs yet" })}
      description={
        rader?.length
          ? text({ sv: "Listan gäller de 30 senaste körningarna.", en: "The list covers the 30 latest runs." })
          : text({ sv: "Kör Iris, så syns körningen här med förlopp medan den går och utfall efteråt.", en: "Run Iris and the run shows up here with progress while it runs and the outcome afterwards." })
      }
      actions={rader?.length ? <Button variant="secondary" label={text({ sv: "Visa alla", en: "Show all" })} onClick={() => setFilter("alla")} /> : korIris}
    />
  );

  const fot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span> <span className="crm-raknefot-tal">{tal(visade.length)}</span>{" "}
        <span className="crm-raknefot-etikett">{text({ sv: "av de senaste", en: "of the latest" })}</span> <span className="crm-raknefot-tal">{tal(rader?.length ?? 0)}</span>
      </span>
      {nagotArbetar ? (
        <span className="inline-flex items-center gap-2">
          <Prick ton="ockra" pulserar />
          <span className="crm-raknefot-etikett">{text({ sv: "Följer förloppet, uppdateras var tredje sekund", en: "Following the progress, updated every three seconds" })}</span>
        </span>
      ) : null}
    </div>
  );

  return (
    <Sida
      objekt="korningar"
      rubrik={text({ sv: "Körningar", en: "Runs" })}
      antal={rader ? tal(rader.length) : undefined}
      atgarder={korIris}
      vyrad={
        !laddar && rader.length > 0 ? (
          smal ? (
            <Selector
              label={text({ sv: "Visa körningar", en: "Show runs" })}
              isLabelHidden
              variant="secondary"
              size="md"
              value={filter}
              onChange={(v) => v && setFilter(v as Filter)}
              options={filtervyer.map((f) => ({ value: f.v, label: `${text(f.namn)}  ${tal(raknat[f.v])}` }))}
            />
          ) : (
            <Vyval value={filter} onChange={setFilter} label={text({ sv: "Visa körningar", en: "Show runs" })} val={filtervyer.map((f) => ({ v: f.v, namn: text(f.namn), antal: tal(raknat[f.v]) }))} />
          )
        ) : undefined
      }
    >
      <div role="status" className="sr-only">
        {statusbesked}
      </div>
      {startrad}
      {fel && laddar ? (
        <div className="p-4 sm:p-6">
          <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
        </div>
      ) : laddar ? (
        <Tabellskelett rader={6} kolumner={smal ? 2 : 6} markering={false} label={text({ sv: "Hämtar körningar", en: "Loading runs" })} />
      ) : visade.length === 0 ? (
        <div className="py-10">{tomt}</div>
      ) : smal ? (
        <>
          <div className="px-2">
            <List hasDividers density="balanced" edge="padded">
              {visade.map((r) => (
                <ListItem
                  key={r.job_id}
                  startContent={<Objektikon objekt="korningar" storlek={28} />}
                  label={<span className="font-semibold tabular-nums text-ink">{korningstid(r.created_at, locale)}</span>}
                  description={[
                    typ(r),
                    r.korning
                      ? r.korning.mal === 1
                        ? text({ sv: `${tal(r.korning.levererade)} av 1 lead`, en: `${tal(r.korning.levererade)} of 1 lead` })
                        : text({ sv: `${tal(r.korning.levererade)} av ${tal(r.korning.mal)} leads`, en: `${tal(r.korning.levererade)} of ${tal(r.korning.mal)} leads` })
                      : null
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                  endContent={<Korningsstatus rad={r} />}
                  onClick={() => router.push(vag(r.job_id))}
                />
              ))}
            </List>
          </div>
          {fot}
        </>
      ) : (
        <div className="crm-tabell crm-tabell-utan-val">
          {fel ? (
            <div className="px-4 pt-3 sm:px-6">
              <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
            </div>
          ) : null}
          <Table<KorningsRad> data={visade} columns={kolumner} idKey="job_id" density="balanced" dividers="rows" hasHover textOverflow="truncate" />
          {fot}
        </div>
      )}

      <KorIris oppen={ny} stang={() => setNy(false)} startad={startad} />
    </Sida>
  );
}
